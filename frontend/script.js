// ==========================================
// 1. MOBILE NAVIGATION TOGGLE
// ==========================================
const menu = document.getElementById("menu");
const nav = document.getElementById("nav");

if (menu && nav) {
  menu.addEventListener("click", () => {
    const isOpen = nav.classList.toggle("open");
    menu.setAttribute("aria-expanded", String(isOpen));
  });

  nav.addEventListener("click", (e) => {
    if (e.target.closest("a")) {
      nav.classList.remove("open");
      menu.setAttribute("aria-expanded", "false");
    }
  });

  addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      nav.classList.remove("open");
      menu.setAttribute("aria-expanded", "false");
    }
  });
}

// ==========================================
// 2. MATHEMATICAL 2D-DCT pHash ENGINE
// True Discrete Cosine Transform (DCT-II)
// Runs 100% locally inside the browser.
// Original images NEVER leave the device.
// ==========================================
class PerceptualHasher {
  constructor() {
    this.SAMPLE_SIZE = 32; // 32x32 input matrix
    this.HASH_SIZE = 8;     // 8x8 low-frequency matrix (64 bits)

    // Precompute Cosine Basis Table: cos((2x + 1) * u * PI / (2 * N))
    this.cosTable = [];
    for (let u = 0; u < this.HASH_SIZE; u++) {
      this.cosTable[u] = [];
      for (let x = 0; x < this.SAMPLE_SIZE; x++) {
        this.cosTable[u][x] = Math.cos(((2 * x + 1) * u * Math.PI) / (2 * this.SAMPLE_SIZE));
      }
    }
  }

  /**
   * Generates a 64-bit DCT-II pHash hexadecimal string from an Image File
   */
  hashFile(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();

      reader.onload = (event) => {
        const img = new Image();

        img.onload = () => {
          try {
            // Step 1: Draw downsampled 32x32 image to canvas
            const canvas = document.createElement("canvas");
            canvas.width = this.SAMPLE_SIZE;
            canvas.height = this.SAMPLE_SIZE;
            const ctx = canvas.getContext("2d", { willReadFrequently: true });

            ctx.drawImage(img, 0, 0, this.SAMPLE_SIZE, this.SAMPLE_SIZE);
            const imgData = ctx.getImageData(0, 0, this.SAMPLE_SIZE, this.SAMPLE_SIZE).data;

            // Step 2: Convert to 32x32 Grayscale Matrix
            const matrix = [];
            for (let y = 0; y < this.SAMPLE_SIZE; y++) {
              matrix[y] = [];
              for (let x = 0; x < this.SAMPLE_SIZE; x++) {
                const idx = (y * this.SAMPLE_SIZE + x) * 4;
                // Standard perceptual luminance formula
                const gray = imgData[idx] * 0.299 + imgData[idx + 1] * 0.587 + imgData[idx + 2] * 0.114;
                matrix[y][x] = gray;
              }
            }

            // Step 3: Fast Separable 2D Discrete Cosine Transform (DCT-II)
            // Pass 1: Row transform (32 rows x 8 low-frequency columns)
            const rowDct = [];
            for (let y = 0; y < this.SAMPLE_SIZE; y++) {
              rowDct[y] = [];
              for (let u = 0; u < this.HASH_SIZE; u++) {
                let sum = 0;
                for (let x = 0; x < this.SAMPLE_SIZE; x++) {
                  sum += matrix[y][x] * this.cosTable[u][x];
                }
                rowDct[y][u] = sum;
              }
            }

            // Pass 2: Column transform (8 columns x 8 low-frequency rows)
            const dctCoeffs = [];
            for (let v = 0; v < this.HASH_SIZE; v++) {
              for (let u = 0; u < this.HASH_SIZE; u++) {
                let sum = 0;
                for (let y = 0; y < this.SAMPLE_SIZE; y++) {
                  sum += rowDct[y][u] * this.cosTable[v][y];
                }
                dctCoeffs.push(sum);
              }
            }

            // Step 4: Calculate Median of AC coefficients (exclude DC at index 0)
            const acCoeffs = dctCoeffs.slice(1);
            const sortedAc = [...acCoeffs].sort((a, b) => a - b);
            const median = sortedAc[Math.floor(sortedAc.length / 2)];

            // Step 5: Construct 64-bit binary representation based on median
            let binaryString = "";
            for (let i = 0; i < 64; i++) {
              binaryString += dctCoeffs[i] > median ? "1" : "0";
            }

            // Step 6: Convert 64 bits to 16-character Hexadecimal string
            let hexHash = "";
            for (let i = 0; i < 64; i += 4) {
              const nibble = binaryString.substring(i, i + 4);
              hexHash += parseInt(nibble, 2).toString(16);
            }

            resolve(hexHash);
          } catch (err) {
            reject(err);
          }
        };

        img.onerror = () => reject(new Error("Unable to read image data"));
        img.src = event.target.result;
      };

      reader.onerror = () => reject(new Error("File read error"));
      reader.readAsDataURL(file);
    });
  }
}

const phashEngine = new PerceptualHasher();

// ==========================================
// 3. CASE CREATION WIZARD CONTROLLER
// ==========================================
class CaseWizard {
  constructor() {
    this.currentStep = 0;
    this.userEmail = "";
    this.fingerprints = []; // Array of { filename, hash }

    this.modal = document.getElementById("caseModal");
    this.progressBar = document.getElementById("progressBar");
    this.stepCounterText = document.getElementById("stepCounterText");

    this.initButtons();
    this.initFileInput();
  }

  initButtons() {
    document.querySelectorAll(".start-case-btn").forEach((btn) => {
      btn.addEventListener("click", () => this.open());
    });

    const closeBtn = document.getElementById("closeModalBtn");
    if (closeBtn) {
      closeBtn.addEventListener("click", () => this.close());
    }

    if (this.modal) {
      this.modal.addEventListener("click", (e) => {
        if (e.target === this.modal) this.close();
      });
    }

    addEventListener("keydown", (e) => {
      if (e.key === "Escape" && this.modal && this.modal.classList.contains("active")) {
        this.close();
      }
    });
  }

  open() {
    this.currentStep = 0;
    this.fingerprints = [];
    this.userEmail = "";

    const emailInput = document.getElementById("userEmail");
    if (emailInput) emailInput.value = "";

    const fileInput = document.getElementById("mediaFileInput");
    if (fileInput) fileInput.value = "";

    const listContainer = document.getElementById("hashedFilesList");
    if (listContainer) listContainer.innerHTML = "";

    const nextWrapper = document.getElementById("step7NextBtnWrapper");
    if (nextWrapper) nextWrapper.style.display = "none";

    const submitBtn = document.getElementById("finalSubmitBtn");
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.innerText = "Register Fingerprints";
    }

    this.showStep(0);
    this.modal.classList.add("active");
    this.modal.setAttribute("aria-hidden", "false");
  }

  close() {
    if (this.modal) {
      this.modal.classList.remove("active");
      this.modal.setAttribute("aria-hidden", "true");
    }
  }

  reset() {
    this.close();
    this.showStep(0);
  }

  showStep(stepId) {
    document.querySelectorAll(".wizard-step").forEach((el) => {
      el.style.display = "none";
    });

    const target = document.querySelector(`.wizard-step[data-step="${stepId}"]`);
    if (target) {
      target.style.display = "block";
    }

    if (typeof stepId === "number") {
      this.currentStep = stepId;
      const percent = Math.round((stepId / 10) * 100);
      if (this.stepCounterText) {
        this.stepCounterText.innerText = `${stepId} / 10 (${percent}%)`;
      }
      if (this.progressBar) {
        this.progressBar.style.width = `${percent}%`;
      }
    }
  }

  nextStep() {
    this.showStep(this.currentStep + 1);
  }

  selectAge(ageChoice) {
    if (ageChoice === "under18") {
      this.showStep("under18-warning");
    } else {
      this.showStep(2);
    }
  }

  selectDepicted(depictedChoice) {
    if (depictedChoice === "someone_else") {
      alert("Only the individual depicted in the media (or someone depicted alongside them) can create a protection case.");
      return;
    }
    this.showStep(3);
  }

  alertNotEligible(message) {
    alert(message || "This media is not eligible for protection under IntiShield.");
  }

  // ==========================================
  // CLIENT-SIDE pHash GENERATION
  // ==========================================
  initFileInput() {
    const input = document.getElementById("mediaFileInput");
    if (!input) return;

    input.addEventListener("change", async (e) => {
      const files = Array.from(e.target.files);
      if (!files.length) return;

      const listContainer = document.getElementById("hashedFilesList");
      listContainer.innerHTML = "<p style='font-size:13px; color:var(--muted);'>Computing Discrete Cosine Transform (pHash) locally on your device...</p>";

      this.fingerprints = [];

      for (const file of files.slice(0, 20)) {
        try {
          // Uses real 2D-DCT pHash
          const hash = await phashEngine.hashFile(file);
          this.fingerprints.push({ filename: file.name, hash: hash });
        } catch (err) {
          console.error("pHash computation error for:", file.name, err);
        }
      }

      listContainer.innerHTML = "";
      this.fingerprints.forEach((item) => {
        const row = document.createElement("div");
        row.className = "hash-item";
        row.innerHTML = `
          <span><i class="ri-file-shield-line" style="color:var(--accent); margin-right:6px;"></i><strong>${item.filename}</strong></span>
          <span class="hash-badge">pHash: ${item.hash}</span>
        `;
        listContainer.appendChild(row);
      });

      const nextBtnWrapper = document.getElementById("step7NextBtnWrapper");
      if (nextBtnWrapper && this.fingerprints.length > 0) {
        nextBtnWrapper.style.display = "flex";
      }
    });
  }

  submitEmail() {
    const emailInput = document.getElementById("userEmail");
    const val = emailInput ? emailInput.value.trim() : "";

    if (!val || !val.includes("@") || !val.includes(".")) {
      alert("Please enter a valid email address.");
      return;
    }

    this.userEmail = val;

    document.getElementById("summaryCount").innerText = this.fingerprints.length;
    document.getElementById("summaryEmail").innerText = this.userEmail;

    this.showStep(9);
  }

  async finalizeCase() {
    const submitBtn = document.getElementById("finalSubmitBtn");
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.innerText = "Registering pHash...";
    }

    try {
      const response = await fetch("/api/cases/create", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: this.userEmail,
          fingerprints: this.fingerprints,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        alert(data.error || "Failed to register case.");
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.innerText = "Register Fingerprints";
        }
        return;
      }

      document.getElementById("createdCaseId").innerText = data.case_id;
      document.getElementById("createdSecretToken").innerText = data.secret_token;

      const trackBtn = document.getElementById("goToStatusBtn");
      if (trackBtn) {
        trackBtn.href = `/status?case_id=${encodeURIComponent(data.case_id)}`;
      }

      this.showStep(10);
    } catch (err) {
      console.error(err);
      alert("Connection error. Ensure your backend server is active on port 3000.");
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerText = "Register Fingerprints";
      }
    }
  }
}

// ==========================================
// 4. PARTNER INTEGRATION CONTROLLER
// ==========================================
class PartnerWizard {
  constructor() {
    this.modal = document.getElementById("partnerModal");
    this.selectedTier = "Approved Participant";

    this.initButtons();
  }

  initButtons() {
    document.querySelectorAll(".open-integrate-btn").forEach((btn) => {
      btn.addEventListener("click", () => this.open());
    });

    const closeBtn = document.getElementById("closePartnerModalBtn");
    if (closeBtn) {
      closeBtn.addEventListener("click", () => this.close());
    }

    if (this.modal) {
      this.modal.addEventListener("click", (e) => {
        if (e.target === this.modal) this.close();
      });
    }

    addEventListener("keydown", (e) => {
      if (e.key === "Escape" && this.modal && this.modal.classList.contains("active")) {
        this.close();
      }
    });
  }

  open() {
    if (this.modal) {
      this.modal.classList.add("active");
      this.modal.setAttribute("aria-hidden", "false");
    }
  }

  close() {
    if (this.modal) {
      this.modal.classList.remove("active");
      this.modal.setAttribute("aria-hidden", "true");
    }
  }

  selectTier(tierName, element) {
    this.selectedTier = tierName;
    document.querySelectorAll(".pathway-card").forEach((c) => c.classList.remove("active"));
    if (element) {
      element.classList.add("active");
    }
  }

  async submit() {
    const nameInput = document.getElementById("partnerName");
    const emailInput = document.getElementById("partnerEmail");
    const websiteInput = document.getElementById("partnerWebsite");
    const storeUrlInput = document.getElementById("partnerStoreUrl");

    const name = nameInput ? nameInput.value.trim() : "";
    const email = emailInput ? emailInput.value.trim() : "";
    const website = websiteInput ? websiteInput.value.trim() : "";
    const storeUrl = storeUrlInput ? storeUrlInput.value.trim() : "";

    const hasHashTech = document.getElementById("checkHashTech")?.checked;
    const agreedZeroRetention = document.getElementById("checkZeroRetention")?.checked;
    const agreedAction = document.getElementById("checkImmediateAction")?.checked;

    if (!name || !email || !email.includes("@")) {
      alert("Please enter a valid platform name and technical contact email.");
      return;
    }

    if (!hasHashTech) {
      alert("Platform must implement perceptual hash technology before integrating.");
      return;
    }

    const btn = document.getElementById("submitPartnerBtn");
    if (btn) {
      btn.disabled = true;
      btn.innerText = "Submitting Inquiry...";
    }

    try {
      const res = await fetch("/api/partners/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          platform_name: name,
          contact_email: email,
          website_url: website,
          store_url: storeUrl,
          tier: this.selectedTier,
          has_hash_tech: hasHashTech,
          agreed_zero_retention: agreedZeroRetention,
          agreed_immediate_action: agreedAction,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        alert(data.error || "Submission failed.");
      } else {
        alert("Thank you! Your integration request has been submitted. Our technical team will reach out with API access.");
        if (nameInput) nameInput.value = "";
        if (emailInput) emailInput.value = "";
        if (websiteInput) websiteInput.value = "";
        if (storeUrlInput) storeUrlInput.value = "";
        this.close();
      }
    } catch (e) {
      alert("Connection error. Ensure the backend is running on port 3000.");
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.innerText = "Submit Integration Request";
      }
    }
  }
}

// Instantiate Global Controllers
const wizard = new CaseWizard();
const partnerWizard = new PartnerWizard();