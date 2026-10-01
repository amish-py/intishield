import os
import uuid
import secrets
import smtplib
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

# Initialize database
init_db()

# ==========================================
# CONFIGURATION
# ==========================================
BASE_URL = os.environ.get("BASE_URL", "http://localhost:3000")
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
# Replace with your Gmail address:
SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "intishield.case@gmail.com")
# Replace with your 16-character Google App Password:
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "ueuw yhfn lxuy fxgf")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", SMTP_USERNAME)


def send_confirmation_email(recipient_email: str, case_id: str, secret_token: str, items_count: int, file_names: list):
    """Sends confirmation email with live status link."""
    subject = f"IntiShield Case Protection Notice: {case_id}"
    status_url = f"{BASE_URL}/status?case_id={case_id}"

    files_list_html = "".join([f"<li style='margin-bottom: 6px; color: #3d444c;'>• {name}</li>" for name in file_names])

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f5f6f7; margin: 0; padding: 24px; color: #111418;">
      <div style="max-width: 580px; margin: 0 auto; background: #ffffff; border: 1px solid #d9dde1; border-radius: 6px; overflow: hidden;">
        
        <div style="background-color: #1f3a5f; padding: 24px; color: #ffffff;">
          <h1 style="margin: 0; font-size: 20px; font-weight: 700;">IntiShield Case Notice</h1>
          <p style="margin: 6px 0 0; font-size: 13px; opacity: 0.9;">Case Status: Pending Review</p>
        </div>

        <div style="padding: 28px;">
          <p style="font-size: 15px; line-height: 1.6; margin-top: 0;">
            Your case has been created. The visual fingerprints computed on your device have been received and are currently <strong>Pending</strong> in the protection registry.
          </p>

          <div style="background-color: #f5f6f7; border: 1px solid #d9dde1; border-radius: 4px; padding: 18px; margin: 20px 0;">
            <p style="margin: 0; font-size: 12px; color: #6b727a; font-weight: 600; text-transform: uppercase;">Confidential Case ID</p>
            <p style="margin: 4px 0 14px; font-size: 20px; font-weight: 700; color: #111418; letter-spacing: 0.5px;">{case_id}</p>
            
            <p style="margin: 0; font-size: 12px; color: #6b727a; font-weight: 600; text-transform: uppercase;">Secret Revocation Token (Save this to delete case)</p>
            <code style="display: block; margin-top: 4px; background: #ffffff; border: 1px solid #d9dde1; padding: 8px 12px; border-radius: 4px; font-size: 13px; color: #1f3a5f; word-break: break-all;">{secret_token}</code>
          </div>

          <!-- Live Status Button -->
          <div style="text-align: center; margin: 28px 0;">
            <a href="{status_url}" style="background-color: #1f3a5f; color: #ffffff; text-decoration: none; padding: 12px 28px; border-radius: 4px; font-weight: 600; font-size: 14px; display: inline-block;">
              View Case Status
            </a>
            <p style="margin: 8px 0 0; font-size: 12px; color: #6b727a;">
              Or visit: <a href="{status_url}" style="color: #1f3a5f;">{status_url}</a>
            </p>
          </div>

          <h3 style="font-size: 14px; margin: 20px 0 8px; color: #111418;">Protected Files ({items_count}):</h3>
          <ul style="padding-left: 20px; margin: 0 0 20px; font-size: 13px;">
            {files_list_html}
          </ul>

          <div style="background-color: #f5f6f7; border-left: 3px solid #1f3a5f; padding: 12px 16px; margin: 20px 0;">
            <p style="margin: 0; font-size: 13px; line-height: 1.5; color: #3d444c;">
              <strong>Zero-Knowledge Protection:</strong> Your original photos/videos were processed in your browser and were not uploaded. Only perceptual hashes are shared with participating platforms like Niscord.
            </p>
          </div>

          <div style="border-top: 1px solid #d9dde1; padding-top: 16px; margin-top: 24px; font-size: 12px; color: #6b727a; line-height: 1.5;">
            Reporting in Nepal: Nepal Police Cyber Bureau hotline <strong>01-4219044</strong> or Childline <strong>1098</strong>.
          </div>
        </div>
      </div>
    </body>
    </html>
    """

    if not SMTP_USERNAME or "@" not in SMTP_USERNAME or not SMTP_PASSWORD or SMTP_USERNAME == "your_gmail@gmail.com":
        print("\n" + "="*60)
        print("[MOCK EMAIL LOG] (Set SMTP_USERNAME & SMTP_PASSWORD for live delivery)")
        print(f"Recipient : {recipient_email}")
        print(f"Case ID   : {case_id}")
        print(f"Status URL: {status_url}")
        print("="*60 + "\n")
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
        
        print(f"[EMAIL SUCCESS] Confirmation email delivered to {recipient_email}")
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] Failed to send email via SMTP: {e}")
        return False


# ==========================================
# STATIC FILE ROUTES
# ==========================================

@app.route("/")
def serve_index():
    return send_from_directory(FRONTEND_DIR, "index.html")

@app.route("/status")
def serve_status_page():
    return send_from_directory(FRONTEND_DIR, "status.html")

@app.route("/assets/<path:filename>")
def serve_assets(filename):
    return send_from_directory(ASSETS_DIR, filename)

@app.route("/frontend/<path:filename>")
def serve_frontend_subdir(filename):
    return send_from_directory(FRONTEND_DIR, filename)

@app.route("/<path:filename>")
def serve_frontend_files(filename):
    file_path = os.path.join(FRONTEND_DIR, filename)
    if os.path.exists(file_path):
        return send_from_directory(FRONTEND_DIR, filename)
    return jsonify({"error": "File not found"}), 404


# ==========================================
# API ROUTES
# ==========================================

@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy", "service": "IntiShield Backend API"}), 200


@app.route("/api/cases/create", methods=["POST"])
def create_case():
    data = request.get_json() or {}
    email = data.get("email", "").strip()
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
            INSERT INTO cases (case_id, secret_token, email, total_items, status)
            VALUES (?, ?, ?, ?, 'pending')
        """, (case_id, secret_token, email, len(fingerprints)))

        for item in fingerprints:
            fp_hash = item.get("hash") if isinstance(item, dict) else str(item)
            fname = item.get("filename", "protected_image.png") if isinstance(item, dict) else "protected_item"
            file_names.append(fname)
            cursor.execute("""
                INSERT INTO protected_fingerprints (case_id, fingerprint, file_name, status)
                VALUES (?, ?, ?, 'pending')
            """, (case_id, fp_hash, fname))

        conn.commit()

    email_sent = send_confirmation_email(email, case_id, secret_token, len(fingerprints), file_names)

    return jsonify({
        "success": True,
        "case_id": case_id,
        "secret_token": secret_token,
        "email": email,
        "status": "pending",
        "total_items": len(fingerprints),
        "email_sent": email_sent,
        "message": "Case registered successfully."
    }), 201


@app.route("/api/cases/<case_id>", methods=["GET"])
def get_case_status(case_id):
    """Returns real status of a case."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT case_id, email, total_items, created_at, status FROM cases WHERE case_id = ?",
            (case_id.strip().upper(),)
        )
        row = cursor.fetchone()

        if not row:
            return jsonify({"error": "Case ID not found in database."}), 404

        cursor.execute(
            "SELECT file_name, status, created_at FROM protected_fingerprints WHERE case_id = ?",
            (row["case_id"],)
        )
        items = [dict(item) for item in cursor.fetchall()]

    # Mask email for privacy (e.g., j***@gmail.com)
    raw_email = row["email"]
    parts = raw_email.split("@")
    masked_email = f"{parts[0][0]}***@{parts[1]}" if len(parts) == 2 else raw_email

    return jsonify({
        "case_id": row["case_id"],
        "status": row["status"], # 'pending' or 'completed'
        "total_items": row["total_items"],
        "created_at": row["created_at"],
        "masked_email": masked_email,
        "items": items
    }), 200


@app.route("/api/cases/<case_id>", methods=["DELETE"])
def revoke_case(case_id):
    """Allows user to revoke their protection case with secret token."""
    data = request.get_json() or {}
    secret_token = data.get("secret_token", "").strip()

    if not secret_token:
        return jsonify({"error": "Secret token is required to revoke protection"}), 400

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM cases WHERE case_id = ? AND secret_token = ?",
            (case_id.strip().upper(), secret_token)
        )
        row = cursor.fetchone()

        if not row:
            return jsonify({"error": "Invalid Case ID or Secret Revocation Token"}), 403

        cursor.execute("DELETE FROM cases WHERE case_id = ?", (case_id,))
        cursor.execute("DELETE FROM protected_fingerprints WHERE case_id = ?", (case_id,))
        conn.commit()

    return jsonify({"success": True, "message": "Case and associated digital fingerprints permanently deleted."}), 200


@app.route("/api/partners/register", methods=["POST"])
def register_partner():
    """Registers platform integration inquiries."""
    data = request.get_json() or {}
    name = data.get("platform_name", "").strip()
    website = data.get("website_url", "").strip()
    store_url = data.get("store_url", "").strip()
    email = data.get("contact_email", "").strip()
    tier = data.get("tier", "Approved Participant")
    has_hash_tech = 1 if data.get("has_hash_tech") else 0
    agreed_zero_retention = 1 if data.get("agreed_zero_retention") else 0
    agreed_action = 1 if data.get("agreed_immediate_action") else 0

    if not name or not email or "@" not in email:
        return jsonify({"error": "Platform name and a valid contact email are required."}), 400

    if not has_hash_tech:
        return jsonify({"error": "Platform must support or implement perceptual hash matching to integrate."}), 400

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO partners (platform_name, website_url, store_url, contact_email, tier, has_hash_tech, agreed_zero_retention, agreed_immediate_action)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, website, store_url, email, tier, has_hash_tech, agreed_zero_retention, agreed_action))
        conn.commit()

    return jsonify({
        "success": True,
        "message": "Platform registration submitted successfully. Technical onboarding details will follow."
    }), 201


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)