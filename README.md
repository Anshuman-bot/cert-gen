# 🎓 CertifyPro — Enterprise College Event Certificate & Verification Platform

**CertifyPro** is an end-to-end collegiate certificate management platform built to handle large-scale academic symposia, hackathons, workshops, and sports fests. It automates participant data sanitation, bulk certificate generation, cryptographic signing, and public QR verification.

---

## 🌟 Key Features

1. **Event & Certificate Template Management**:
   - Manage events, dates, college branding, and dual official signatories (e.g., Event Convener & Dean/Principal).
   - Built-in high-definition templates:
     - *Cyber Tech & Hackathon* (Midnight navy & cyan geometric grid)
     - *Imperial Academic Merit* (Ivory parchment with metallic gold borders)
     - *Clean Emerald Workshop* (Minimalist modern Swiss layout)
     - *Crimson Athletic & Cultural* (Dynamic ribbon and honor seal)

2. **Bulk Participant Upload via CSV**:
   - Drag-and-drop CSV uploader with auto-header mapping (`Full Name`, `Email`, `Department`, `College`, `Roll Number`, `Role`).
   - Downloadable sample test datasets directly in the UI:
     - `sample_clean_participants.csv`: Ready-to-generate pristine records.
     - `sample_dirty_participants.csv`: Realistic messy dataset with casing errors, email typos, duplicates, and missing fields.

3. **AI-Assisted Data Cleaning & Validation**:
   - **Name Sanitizer**: Normalizes irregular casing (UPPERCASE/lowercase -> Title Case), cleans double spaces, handles honorifics (`Dr.`, `Prof.`, `Mr.`, `Ms.`) and initials.
   - **Email Domain Typo Corrector**: Automatically detects and fixes common email typos (`gmaill.com` &rarr; `gmail.com`, `yaho.com` &rarr; `yahoo.com`, `rediffmial.com` &rarr; `rediffmail.com`).
   - **Department Canonicalization**: Fuzzy matches variations like `copmuter sci`, `cse`, `comp sc` &rarr; `Computer Science & Engineering`.
   - **Duplicate Collision Guard**: Intercepts duplicate registrations by matching email, roll numbers, or fuzzy name similarity at the same institution.
   - **Audit Scoring**: Computes per-record AI confidence score (0-100%) and itemizes every modification made.

4. **Human Review & Audit Workspace**:
   - Side-by-side comparison of original raw input vs. AI-cleaned values.
   - Filter by status: `Clean`, `Auto-Fixed`, `Flagged`, `Duplicates`.
   - 1-Click "Apply All AI Recommendations".
   - Inline cell/modal editing for manual overrides.
   - Batch selection for bulk approvals or rejections.

5. **Bulk Certificate Generation**:
   - Generates both **Print-Ready Vector PDFs** and **High-Resolution (2000x1414) PNGs** at 300 DPI equivalent.
   - **Unique Certificate ID**: Collision-resistant alphanumeric identifier (e.g., `CRT-2026-NH2-4DDAF0`).
   - **Cryptographic Tamper-Proof Signature**: Stored SHA-256 hash of payload `(cert_id + name + event + date + salt)`.
   - **Embedded Dynamic QR Code**: Real-time QR code directing scanners straight to the credential verification URL.
   - **Batch ZIP Archive**: One-click download of all certificates bundled with a `MANIFEST_INDEX.csv`.

6. **Public Verification Portal & QR Scanner**:
   - Instant verification at `/verify/{cert_id}` with green shield trust badge.
   - SHA-256 integrity verification: guarantees zero tampering since official conferral.
   - Interactive certificate document replica and 1-click downloads.
   - Webcam / mobile camera QR scanner powered by HTML5-QRCode.
   - Real-time audit trail tracking view count and verification timestamps.

7. **Simulated Email Dispatcher**:
   - Direct delivery simulation to participant emails with an outbox delivery log.

---

## 🚀 Running the Platform

### Prerequisites
- Python 3.10+
- Dependencies installed: `fastapi`, `uvicorn`, `pillow`, `qrcode`, `reportlab`, `python-multipart`

### Launch Command
```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Access URLs
- **Admin Dashboard & Management Suite**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Public Credential Verification Portal**: [http://127.0.0.1:8000/verify](http://127.0.0.1:8000/verify)
- **Direct Certificate Verification Link**: [http://127.0.0.1:8000/verify/CRT-2026-NH2-4DDAF0](http://127.0.0.1:8000/verify/CRT-2026-NH2-4DDAF0)
