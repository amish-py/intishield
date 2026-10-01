import os
import json
import uuid
import secrets
import smtplib
import math
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from database import init_db, get_connection

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

app = Flask(__name__)
CORS(app)

init_db()

BASE_URL = os.environ.get("BASE_URL", "http://localhost:3000")
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "lamsalamish7@gmail.com")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "bpkb tswq yfob djpn")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", SMTP_USERNAME)


def hamming_distance(hex1: str, hex2: str) -> int:
    try:
        val1 = int(hex1, 16)
        val2 = int(hex2, 16)
        return bin(val1 ^ val2).count('1')
    except (ValueError, TypeError):
        return 999


def cosine_similarity(vec1, vec2) -> float:
    """Calculates cosine similarity between two 128-d face vectors."""
    try:
        if not vec1 or not vec2:
            return 0.0
        v1 = json.loads(vec1) if isinstance(vec1, str) else vec1
        v2 = json.loads(vec2) if isinstance(vec2, str) else vec2
        if len(v1) != len(v2) or len(v1) == 0:
            return 0.0

        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(b * b for b in v2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)
    except Exception:
        return 0.0


def evaluate_match(post, fp):
    """
    Evaluates whether a Niscord post matches a protected IntiShield fingerprint
    based on the user's selected protection_mode.
    """
    mode = fp.get("protection_mode", "face_biometric")

    if mode == "face_biometric":
        sim = cosine_similarity(post.get("face_descriptor"), fp.get("face_descriptor"))
        # Facial similarity >= 0.70 confirms same face in different scenes/poses
        if sim >= 0.70:
            return True, f"Face Biometric Match (Confidence: {sim*100:.1f}%)"
    else:
        # Standard pHash mode
        dist = hamming_distance(post.get("phash", ""), fp.get("fingerprint", ""))
        if dist <= 10:
            return True, f"Perceptual Hash Match (Hamming distance: {dist})"

    return False, None


def scan_and_takedown_niscord():
    """Scans all active posts on Niscord against active/pending IntiShield records."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, post_id, phash, face_descriptor FROM niscord_posts WHERE status = 'active'")
        active_posts = [dict(r) for r in cursor.fetchall()]

        cursor.execute("SELECT case_id, fingerprint, face_descriptor, protection_mode FROM protected_fingerprints WHERE status IN ('pending', 'active')")
        fingerprints = [dict(r) for r in cursor.fetchall()]

        takedowns_count = 0
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

        for post in active_posts:
            for fp in fingerprints:
                matched, reason = evaluate_match(post, fp)
                if matched:
                    cursor.execute("""
                        UPDATE niscord_posts
                        SET status = 'taken_down', takedown_case_id = ?, takedown_reason = ?, takedown_time = ?
                        WHERE id = ?
                    """, (fp["case_id"], reason, now, post["id"]))
                    takedowns_count += 1
                    break

        conn.commit()
    return takedowns_count


def send_confirmation_email(recipient_email: str, case_id: str, secret_token: str, mode: str, items_count: int, file_names: list):
    subject = f"IntiShield Case Protection Notice: {case_id}"
    status_url = f"{BASE_URL}/status?case_id={case_id}"
    mode_label = "Face Biometric Recognition" if mode == "face_biometric" else "Perceptual Image Hash (pHash)"
    files_list_html = "".join([f"<li style='margin-bottom: 6px; color: #3d444c;'>• {name}</li>" for name in file_names])

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f5f6f7; margin: 0; padding: 24px; color: #111418;">
      <div style="max-width: 580px; margin: 0 auto; background: #ffffff; border: 1px solid #d9dde1; border-radius: 6px; overflow: hidden;">
        <div style="background-color: #1f3a5f; padding: 24px; color: #ffffff;">
          <h1 style="margin: 0; font-size: 20px; font-weight: 700;">IntiShield Case Notice</h1>
          <p style="margin: 6px 0 0; font-size: 13px; opacity: 0.9;">Mode: {mode_label}</p>
        </div>
        <div style="padding: 28px;">
          <p style="font-size: 15px; line-height: 1.6; margin-top: 0;">
            Your protection case is active. Your media was analyzed locally on your device, and the fingerprints are registered with partner platforms.
          </p>
          <div style="background-color: #f5f6f7; border: 1px solid #d9dde1; border-radius: 4px; padding: 18px; margin: 20px 0;">
            <p style="margin: 0; font-size: 12px; color: #6b727a; font-weight: 600; text-transform: uppercase;">Confidential Case ID</p>
            <p style="margin: 4px 0 14px; font-size: 20px; font-weight: 700; color: #111418; letter-spacing: 0.5px;">{case_id}</p>
            <p style="margin: 0; font-size: 12px; color: #6b727a; font-weight: 600; text-transform: uppercase;">Secret Revocation Token</p>
            <code style="display: block; margin-top: 4px; background: #ffffff; border: 1px solid #d9dde1; padding: 8px 12px; border-radius: 4px; font-size: 13px; color: #1f3a5f; word-break: break-all;">{secret_token}</code>
          </div>
          <div style="text-align: center; margin: 28px 0;">
            <a href="{status_url}" style="background-color: #1f3a5f; color: #ffffff; text-decoration: none; padding: 12px 28px; border-radius: 4px; font-weight: 600; font-size: 14px; display: inline-block;">
              View Case Status
            </a>
          </div>
          <h3 style="font-size: 14px; margin: 20px 0 8px; color: #111418;">Protected Media ({items_count}):</h3>
          <ul style="padding-left: 20px; margin: 0 0 20px; font-size: 13px;">{files_list_html}</ul>
        </div>
      </div>
    </body>
    </html>
    """

    if not SMTP_USERNAME or "@" not in SMTP_USERNAME or not SMTP_PASSWORD or SMTP_USERNAME == "your_gmail@gmail.com":
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = SENDER_EMAIL
        msg["To"] = recipient_email
        msg.attach(MIMEText(html_body, "html"))
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(SMTP_USERNAME, SMTP_PASSWORD.replace(" ", ""))
            server.sendmail(SENDER_EMAIL, [recipient_email], msg.as_string())
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")
        return False


# Static Routes
@app.route("/")
def serve_index(): return send_from_directory(FRONTEND_DIR, "index.html")

@app.route("/status")
def serve_status_page(): return send_from_directory(FRONTEND_DIR, "status.html")

@app.route("/niscord")
def serve_niscord_page(): return send_from_directory(FRONTEND_DIR, "niscord.html")

@app.route("/admin")
def serve_admin_page(): return send_from_directory(FRONTEND_DIR, "admin.html")

@app.route("/assets/<path:filename>")
def serve_assets(filename): return send_from_directory(ASSETS_DIR, filename)

@app.route("/<path:filename>")
def serve_frontend_files(filename):
    file_path = os.path.join(FRONTEND_DIR, filename)
    if os.path.exists(file_path):
        return send_from_directory(FRONTEND_DIR, filename)
    return jsonify({"error": "File not found"}), 404


# API Routes
@app.route("/api/cases/create", methods=["POST"])
def create_case():
    data = request.get_json() or {}
    email = data.get("email", "").strip()
    protection_mode = data.get("protection_mode", "face_biometric")
    fingerprints = data.get("fingerprints", [])

    if not email or "@" not in email:
        return jsonify({"error": "A valid email address is required"}), 400

    if not fingerprints or not isinstance(fingerprints, list):
        return jsonify({"error": "At least one digital fingerprint is required"}), 400

    case_id = f"INTI-{uuid.uuid4().hex[:8].upper()}"
    secret_token = secrets.token_urlsafe(24)
    file_names = []

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO cases (case_id, secret_token, email, protection_mode, total_items, status)
            VALUES (?, ?, ?, ?, ?, 'pending')
        """, (case_id, secret_token, email, protection_mode, len(fingerprints)))

        for item in fingerprints:
            fp_hash = item.get("hash") if isinstance(item, dict) else str(item)
            fname = item.get("filename", "protected_image.png") if isinstance(item, dict) else "protected_item"
            face_desc = json.dumps(item.get("face_descriptor")) if (isinstance(item, dict) and item.get("face_descriptor")) else None
            file_names.append(fname)
            cursor.execute("""
                INSERT INTO protected_fingerprints (case_id, fingerprint, file_name, face_descriptor, protection_mode, status)
                VALUES (?, ?, ?, ?, ?, 'pending')
            """, (case_id, fp_hash, fname, face_desc, protection_mode))

        conn.commit()

    scan_and_takedown_niscord()
    send_confirmation_email(email, case_id, secret_token, protection_mode, len(fingerprints), file_names)

    return jsonify({
        "success": True,
        "case_id": case_id,
        "secret_token": secret_token,
        "email": email,
        "protection_mode": protection_mode,
        "total_items": len(fingerprints)
    }), 201


@app.route("/api/cases/<case_id>", methods=["GET"])
def get_case_status(case_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT case_id, email, protection_mode, total_items, created_at, status FROM cases WHERE case_id = ?", (case_id.strip().upper(),))
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "Case ID not found."}), 404

        cursor.execute("SELECT file_name, status, created_at FROM protected_fingerprints WHERE case_id = ?", (row["case_id"],))
        items = [dict(item) for item in cursor.fetchall()]

    raw_email = row["email"]
    parts = raw_email.split("@")
    masked_email = f"{parts[0][0]}***@{parts[1]}" if len(parts) == 2 else raw_email

    return jsonify({
        "case_id": row["case_id"],
        "status": row["status"],
        "protection_mode": row["protection_mode"],
        "total_items": row["total_items"],
        "created_at": row["created_at"],
        "masked_email": masked_email,
        "items": items
    }), 200


@app.route("/api/cases/<case_id>", methods=["DELETE"])
def revoke_case(case_id):
    data = request.get_json() or {}
    secret_token = data.get("secret_token", "").strip()

    if not secret_token:
        return jsonify({"error": "Secret token is required"}), 400

    clean_id = case_id.strip().upper()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM cases WHERE case_id = ? AND secret_token = ?", (clean_id, secret_token))
        if not cursor.fetchone():
            return jsonify({"error": "Invalid Case ID or Secret Token"}), 403

        cursor.execute("UPDATE cases SET status = 'removed' WHERE case_id = ?", (clean_id,))
        cursor.execute("UPDATE protected_fingerprints SET status = 'removed' WHERE case_id = ?", (clean_id,))
        cursor.execute("UPDATE niscord_posts SET status = 'active', takedown_case_id = NULL, takedown_reason = NULL, takedown_time = NULL WHERE takedown_case_id = ?", (clean_id,))
        conn.commit()

    return jsonify({"success": True, "status": "removed"}), 200


# Niscord Simulator API
@app.route("/api/niscord/posts", methods=["GET"])
def get_niscord_posts():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM niscord_posts ORDER BY id DESC")
        posts = [dict(p) for p in cursor.fetchall()]
    return jsonify({"posts": posts}), 200


@app.route("/api/niscord/posts", methods=["POST"])
def create_niscord_post():
    data = request.get_json() or {}
    author = data.get("author", "Member").strip() or "Member"
    caption = data.get("caption", "").strip()
    image_data = data.get("image_data", "").strip()
    phash = data.get("phash", "").strip()
    face_desc = json.dumps(data.get("face_descriptor")) if data.get("face_descriptor") else None

    if not image_data:
        return jsonify({"error": "Image is required"}), 400

    post_id = f"NIS-{uuid.uuid4().hex[:6].upper()}"

    # Always starts active initially for the 10-second inspection demo
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO niscord_posts (post_id, author, caption, image_data, phash, face_descriptor, status)
            VALUES (?, ?, ?, ?, ?, ?, 'active')
        """, (post_id, author, caption, image_data, phash, face_desc))
        conn.commit()

    return jsonify({"success": True, "post_id": post_id, "status": "active"}), 201


@app.route("/api/niscord/check-post/<post_id>", methods=["POST"])
def check_single_niscord_post(post_id):
    """Called after 10 seconds of background inspection."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, post_id, phash, face_descriptor, status FROM niscord_posts WHERE post_id = ?", (post_id,))
        post = cursor.fetchone()
        if not post or post["status"] == "taken_down":
            return jsonify({"status": post["status"] if post else "not_found"}), 200

        post_dict = dict(post)
        cursor.execute("SELECT case_id, fingerprint, face_descriptor, protection_mode FROM protected_fingerprints WHERE status IN ('pending', 'active')")
        fingerprints = [dict(r) for r in cursor.fetchall()]

        for fp in fingerprints:
            matched, reason = evaluate_match(post_dict, fp)
            if matched:
                now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
                cursor.execute("""
                    UPDATE niscord_posts 
                    SET status = 'taken_down', takedown_case_id = ?, takedown_reason = ?, takedown_time = ? 
                    WHERE post_id = ?
                """, (fp["case_id"], reason, now, post_id))
                conn.commit()
                return jsonify({"status": "taken_down", "case_id": fp["case_id"], "reason": reason}), 200

    return jsonify({"status": "active", "reason": "cleared"}), 200


# Admin Endpoints
@app.route("/api/admin/overview", methods=["GET"])
def get_admin_overview():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT case_id, email, protection_mode, total_items, status, created_at FROM cases ORDER BY id DESC")
        cases = [dict(c) for c in cursor.fetchall()]
        for c in cases:
            cursor.execute("SELECT file_name, fingerprint FROM protected_fingerprints WHERE case_id = ?", (c["case_id"],))
            c["fingerprints"] = [dict(f) for f in cursor.fetchall()]

        cursor.execute("SELECT * FROM partners ORDER BY id DESC")
        partners = [dict(p) for p in cursor.fetchall()]

    return jsonify({
        "stats": {
            "total_cases": len(cases),
            "pending_cases": sum(1 for c in cases if c["status"] == "pending"),
            "active_cases": sum(1 for c in cases if c["status"] == "active"),
            "removed_cases": sum(1 for c in cases if c["status"] == "removed"),
            "total_partners": len(partners)
        },
        "cases": cases,
        "partners": partners
    }), 200


@app.route("/api/admin/cases/<case_id>/status", methods=["POST"])
def update_case_status_admin(case_id):
    new_status = request.get_json().get("status", "").strip().lower()
    clean_id = case_id.strip().upper()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE cases SET status = ? WHERE case_id = ?", (new_status, clean_id))
        cursor.execute("UPDATE protected_fingerprints SET status = ? WHERE case_id = ?", (new_status, clean_id))
        if new_status == "removed":
            cursor.execute("UPDATE niscord_posts SET status = 'active', takedown_case_id = NULL WHERE takedown_case_id = ?", (clean_id,))
        elif new_status in ["active", "pending"]:
            scan_and_takedown_niscord()
        conn.commit()
    return jsonify({"success": True}), 200


@app.route("/api/admin/partners/<int:partner_id>/status", methods=["POST"])
def update_partner_status_admin(partner_id):
    new_status = request.get_json().get("status", "").strip().lower()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE partners SET status = ? WHERE id = ?", (new_status, partner_id))
        conn.commit()
    return jsonify({"success": True}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)