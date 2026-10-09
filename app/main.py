import os
import io
import csv
import json
import sqlite3
import hashlib
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, Request, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from .database import get_db_connection, init_db
from .cleaner import process_participant_batch
from .generator import (
    generate_unique_cert_id,
    compute_cert_hash,
    verify_cert_hash,
    generate_certificate_image,
    create_batch_zip
)

# Initialize application and database
init_db()

app = FastAPI(
    title="CertifyPro - Academic & Event Certificate Platform",
    description="Enterprise certificate issuance, AI cleaning, and QR verification system",
    version="2.0.0"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
STORAGE_DIR = os.path.join(PROJECT_ROOT, "storage")
CERT_STORAGE = os.path.join(STORAGE_DIR, "certificates")
UPLOAD_STORAGE = os.path.join(STORAGE_DIR, "uploads")
SAMPLES_DIR = os.path.join(BASE_DIR, "samples")

os.makedirs(CERT_STORAGE, exist_ok=True)
os.makedirs(UPLOAD_STORAGE, exist_ok=True)

app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
app.mount("/certificates-files", StaticFiles(directory=CERT_STORAGE), name="certificates-files")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


# Pydantic Schemas
class EventCreate(BaseModel):
    name: str
    organization: str
    event_date: str
    category: str
    description: Optional[str] = ""
    template_id: Optional[str] = "modern_tech"
    signatory1_name: str
    signatory1_title: str
    signatory2_name: str
    signatory2_title: str
    citation_text: Optional[str] = "has successfully participated in"

class ParticipantUpdate(BaseModel):
    clean_name: str
    clean_email: Optional[str] = ""
    college: Optional[str] = ""
    department: Optional[str] = ""
    roll_number: Optional[str] = ""
    role: Optional[str] = "Participant"
    is_approved: Optional[int] = 1

class BulkAction(BaseModel):
    participant_ids: List[int]
    action: str  # 'approve', 'reject', 'delete', 'apply_ai'

class TemplateChange(BaseModel):
    template_id: str


# Helper function to get base URL
def get_base_url(request: Request) -> str:
    # Use request URL base
    scheme = request.url.scheme
    netloc = request.url.netloc
    return f"{scheme}://{netloc}"


# --- HTML Web Pages ---

@app.get("/", response_class=HTMLResponse)
async def dashboard_view(request: Request):
    return templates.TemplateResponse(request=request, name="index.html", context={})

@app.get("/verify", response_class=HTMLResponse)
async def public_verify_portal(request: Request):
    return templates.TemplateResponse(request=request, name="verify.html", context={"cert_id": None})

@app.get("/verify/{cert_id}", response_class=HTMLResponse)
async def public_verify_page(request: Request, cert_id: str):
    conn = get_db_connection()
    cert = conn.execute("SELECT * FROM certificates WHERE id = ?", (cert_id,)).fetchone()
    
    # Log verification request
    client_ip = request.client.host if request.client else "127.0.0.1"
    ua = request.headers.get("user-agent", "")
    
    status_result = "VALID" if cert and cert["status"] == "ACTIVE" else "INVALID"
    if cert and cert["status"] == "REVOKED":
        status_result = "REVOKED"

    conn.execute("""
    INSERT INTO verification_logs (certificate_id, status_result, ip_address, user_agent)
    VALUES (?, ?, ?, ?)
    """, (cert_id, status_result, client_ip, ua))

    if cert:
        conn.execute("UPDATE certificates SET view_count = view_count + 1, last_verified_at = CURRENT_TIMESTAMP WHERE id = ?", (cert_id,))

    conn.commit()

    event = None
    tamper_verified = False
    if cert:
        event = conn.execute("SELECT * FROM events WHERE id = ?", (cert["event_id"],)).fetchone()
        tamper_verified = verify_cert_hash(
            cert["id"],
            cert["participant_name"],
            cert["event_name"],
            cert["issue_date"],
            cert["cert_hash"]
        )

    conn.close()

    return templates.TemplateResponse(request=request, name="verify.html", context={
        "cert_id": cert_id,
        "cert": dict(cert) if cert else None,
        "event": dict(event) if event else None,
        "tamper_verified": tamper_verified,
        "status_result": status_result
    })


# --- REST API Endpoints ---

@app.get("/api/dashboard/stats")
async def get_dashboard_stats():
    conn = get_db_connection()
    events_count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    certs_count = conn.execute("SELECT COUNT(*) FROM certificates").fetchone()[0]
    participants_count = conn.execute("SELECT COUNT(*) FROM participants").fetchone()[0]
    verifications_count = conn.execute("SELECT COUNT(*) FROM verification_logs").fetchone()[0]
    
    # Quality metrics
    auto_fixed_count = conn.execute("SELECT COUNT(*) FROM participants WHERE validation_status = 'AUTO_FIXED'").fetchone()[0]
    duplicates_caught = conn.execute("SELECT COUNT(*) FROM participants WHERE validation_status = 'DUPLICATE'").fetchone()[0]

    recent_events = conn.execute("SELECT * FROM events ORDER BY id DESC LIMIT 5").fetchall()
    recent_certs = conn.execute("SELECT * FROM certificates ORDER BY created_at DESC LIMIT 6").fetchall()
    
    conn.close()
    return {
        "events_count": events_count,
        "certificates_count": certs_count,
        "participants_count": participants_count,
        "verifications_count": verifications_count,
        "auto_fixed_count": auto_fixed_count,
        "duplicates_caught": duplicates_caught,
        "recent_events": [dict(r) for r in recent_events],
        "recent_certificates": [dict(r) for r in recent_certs]
    }


@app.get("/api/events")
async def list_events():
    conn = get_db_connection()
    events = conn.execute("""
        SELECT e.*, 
        (SELECT COUNT(*) FROM certificates WHERE event_id = e.id) as cert_count,
        (SELECT COUNT(*) FROM participants WHERE event_id = e.id) as participant_count
        FROM events e ORDER BY e.id DESC
    """).fetchall()
    conn.close()
    return [dict(e) for e in events]


@app.post("/api/events")
async def create_event(data: EventCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO events (name, organization, event_date, category, description, template_id, signatory1_name, signatory1_title, signatory2_name, signatory2_title, citation_text)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.name, data.organization, data.event_date, data.category,
        data.description, data.template_id, data.signatory1_name,
        data.signatory1_title, data.signatory2_name, data.signatory2_title,
        data.citation_text
    ))
    event_id = cursor.lastrowid
    conn.commit()
    event = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    conn.close()
    return dict(event)


@app.get("/api/events/{event_id}")
async def get_event(event_id: int):
    conn = get_db_connection()
    event = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    if not event:
        conn.close()
        raise HTTPException(status_code=404, detail="Event not found")
    
    batches = conn.execute("SELECT * FROM batches WHERE event_id = ? ORDER BY id DESC", (event_id,)).fetchall()
    certs = conn.execute("SELECT * FROM certificates WHERE event_id = ? ORDER BY created_at DESC", (event_id,)).fetchall()
    
    res = dict(event)
    res["batches"] = [dict(b) for b in batches]
    res["certificates"] = [dict(c) for c in certs]
    conn.close()
    return res


@app.put("/api/events/{event_id}")
async def update_event(event_id: int, data: EventCreate):
    conn = get_db_connection()
    conn.execute("""
    UPDATE events
    SET name = ?, organization = ?, event_date = ?, category = ?, description = ?,
        template_id = ?, signatory1_name = ?, signatory1_title = ?,
        signatory2_name = ?, signatory2_title = ?, citation_text = ?
    WHERE id = ?
    """, (
        data.name, data.organization, data.event_date, data.category,
        data.description, data.template_id, data.signatory1_name,
        data.signatory1_title, data.signatory2_name, data.signatory2_title,
        data.citation_text, event_id
    ))
    conn.commit()
    event = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    conn.close()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return dict(event)


@app.post("/api/events/{event_id}/change-template")
async def change_event_template(event_id: int, payload: TemplateChange):
    conn = get_db_connection()
    tpl = conn.execute("SELECT * FROM templates WHERE id = ?", (payload.template_id,)).fetchone()
    if not tpl:
        conn.close()
        raise HTTPException(status_code=400, detail="Invalid template ID")
    
    conn.execute("UPDATE events SET template_id = ? WHERE id = ?", (payload.template_id, event_id))
    conn.commit()
    event = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    conn.close()
    return {
        "message": f"Template successfully updated to '{tpl['name']}'",
        "event": dict(event),
        "template": dict(tpl)
    }


@app.get("/api/templates")
async def list_templates():
    conn = get_db_connection()
    templates_list = conn.execute("SELECT * FROM templates ORDER BY is_default DESC, name ASC").fetchall()
    conn.close()
    return [dict(t) for t in templates_list]


@app.get("/api/templates/{template_id}/preview")
async def get_template_preview(template_id: str):
    preview_file = os.path.join(CERT_STORAGE, f"PREVIEW_{template_id}.png")
    if not os.path.exists(preview_file):
        conn = get_db_connection()
        t = conn.execute("SELECT * FROM templates WHERE id = ?", (template_id,)).fetchone()
        conn.close()
        if not t:
            raise HTTPException(status_code=404, detail="Template not found")
        evt = {'name': 'College Symposium 2026', 'organization': 'Apex Institute of Technology & Engineering', 'event_date': 'October 15, 2026', 'signatory1_name': 'Dr. Rajesh V. Sharma', 'signatory1_title': 'Convener & Head of CS', 'signatory2_name': 'Prof. Ananya Sen', 'signatory2_title': 'Dean of Academic Affairs', 'citation_text': 'has demonstrated exemplary dedication and excellence in'}
        part = {'clean_name': 'Aarav Sharma', 'college': 'Apex Institute of Technology', 'department': 'Computer Science & Engineering', 'roll_number': 'CS2026-042', 'role': '1st Place Winner'}
        generate_certificate_image(f'PREVIEW_{template_id}', part, evt, dict(t), 'http://127.0.0.1:8000', CERT_STORAGE)
    return FileResponse(preview_file, media_type="image/png")


@app.get("/api/samples/{sample_type}")
async def download_sample_csv(sample_type: str):
    if sample_type == "clean":
        filepath = os.path.join(SAMPLES_DIR, "sample_clean_participants.csv")
    else:
        filepath = os.path.join(SAMPLES_DIR, "sample_dirty_participants.csv")
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Sample CSV not found")
    return FileResponse(filepath, filename=f"{sample_type}_participants_sample.csv", media_type="text/csv")


@app.post("/api/events/{event_id}/upload-csv")
async def upload_csv_file(event_id: int, file: UploadFile = File(...)):
    conn = get_db_connection()
    event = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    if not event:
        conn.close()
        raise HTTPException(status_code=404, detail="Event not found")

    content = await file.read()
    try:
        decoded = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        decoded = content.decode("latin-1")

    # Parse CSV records
    reader = csv.DictReader(io.StringIO(decoded))
    raw_rows = [row for row in reader]

    if not raw_rows:
        conn.close()
        raise HTTPException(status_code=400, detail="CSV file is empty or headers could not be parsed")

    # Fetch existing participants for this event to cross-check duplicates
    existing_records = conn.execute("SELECT id, clean_name, clean_email, college, department, roll_number FROM participants WHERE event_id = ?", (event_id,)).fetchall()
    existing_list = [dict(r) for r in existing_records]

    # Process with AI Cleaning Engine
    processed = process_participant_batch(raw_rows, existing_list)

    # Compute stats
    clean_count = sum(1 for p in processed if p["validation_status"] == "CLEAN")
    fixed_count = sum(1 for p in processed if p["validation_status"] == "AUTO_FIXED")
    flagged_count = sum(1 for p in processed if p["validation_status"] == "FLAGGED")
    dup_count = sum(1 for p in processed if p["validation_status"] == "DUPLICATE")

    # Insert batch
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO batches (event_id, filename, total_records, clean_records, flagged_records, duplicate_records, status)
    VALUES (?, ?, ?, ?, ?, ?, 'PENDING_REVIEW')
    """, (event_id, file.filename, len(processed), clean_count + fixed_count, flagged_count, dup_count))
    batch_id = cursor.lastrowid

    # Insert participants
    for p in processed:
        cursor.execute("""
        INSERT INTO participants (
            batch_id, event_id, original_name, clean_name, original_email, clean_email,
            college, department, roll_number, role, validation_status, validation_issues,
            confidence_score, is_approved
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            batch_id, event_id, p["original_name"], p["clean_name"], p["original_email"],
            p["clean_email"], p["college"], p["department"], p["roll_number"], p["role"],
            p["validation_status"], json.dumps(p["validation_issues"]),
            p["confidence_score"], p["is_approved"]
        ))

    conn.commit()
    batch = conn.execute("SELECT * FROM batches WHERE id = ?", (batch_id,)).fetchone()
    conn.close()

    return {
        "message": "CSV uploaded and analyzed successfully by AI Cleaning Engine",
        "batch": dict(batch),
        "summary": {
            "total": len(processed),
            "clean": clean_count,
            "auto_fixed": fixed_count,
            "flagged": flagged_count,
            "duplicates": dup_count
        }
    }


@app.get("/api/batches/{batch_id}/participants")
async def get_batch_participants(batch_id: int):
    conn = get_db_connection()
    participants = conn.execute("SELECT * FROM participants WHERE batch_id = ? ORDER BY id ASC", (batch_id,)).fetchall()
    batch = conn.execute("SELECT * FROM batches WHERE id = ?", (batch_id,)).fetchone()
    conn.close()

    parsed = []
    for p in participants:
        row = dict(p)
        try:
            row["validation_issues"] = json.loads(row["validation_issues"])
        except Exception:
            row["validation_issues"] = []
        parsed.append(row)

    return {
        "batch": dict(batch) if batch else None,
        "participants": parsed
    }


@app.put("/api/participants/{participant_id}")
async def update_participant(participant_id: int, data: ParticipantUpdate):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE participants
    SET clean_name = ?, clean_email = ?, college = ?, department = ?, roll_number = ?, role = ?, is_approved = ?, validation_status = 'CLEAN'
    WHERE id = ?
    """, (data.clean_name, data.clean_email, data.college, data.department, data.roll_number, data.role, data.is_approved, participant_id))
    conn.commit()
    updated = conn.execute("SELECT * FROM participants WHERE id = ?", (participant_id,)).fetchone()
    conn.close()
    if not updated:
        raise HTTPException(status_code=404, detail="Participant not found")
    
    row = dict(updated)
    try: row["validation_issues"] = json.loads(row["validation_issues"])
    except: row["validation_issues"] = []
    return row


@app.post("/api/batches/{batch_id}/apply-all-fixes")
async def apply_all_ai_fixes(batch_id: int):
    """
    Approves all AUTO_FIXED and CLEAN records, resolving all recommendations in one click.
    """
    conn = get_db_connection()
    conn.execute("""
    UPDATE participants
    SET is_approved = 1
    WHERE batch_id = ? AND validation_status != 'DUPLICATE'
    """, (batch_id,))
    conn.commit()
    conn.close()
    return {"message": "All recommended AI fixes approved and queued for generation"}


@app.post("/api/batches/{batch_id}/bulk-action")
async def bulk_action_participants(batch_id: int, payload: BulkAction):
    conn = get_db_connection()
    if payload.action == "approve":
        conn.executemany("UPDATE participants SET is_approved = 1 WHERE id = ?", [(pid,) for pid in payload.participant_ids])
    elif payload.action == "reject":
        conn.executemany("UPDATE participants SET is_approved = 0 WHERE id = ?", [(pid,) for pid in payload.participant_ids])
    elif payload.action == "delete":
        conn.executemany("DELETE FROM participants WHERE id = ?", [(pid,) for pid in payload.participant_ids])
    conn.commit()
    conn.close()
    return {"message": f"Successfully performed '{payload.action}' on {len(payload.participant_ids)} records"}


@app.post("/api/batches/{batch_id}/generate")
async def generate_batch_certificates(batch_id: int, request: Request, template_id: Optional[str] = None):
    conn = get_db_connection()
    batch = conn.execute("SELECT * FROM batches WHERE id = ?", (batch_id,)).fetchone()
    if not batch:
        conn.close()
        raise HTTPException(status_code=404, detail="Batch not found")

    event = conn.execute("SELECT * FROM events WHERE id = ?", (batch["event_id"],)).fetchone()
    chosen_template_id = template_id or event["template_id"]
    template = conn.execute("SELECT * FROM templates WHERE id = ?", (chosen_template_id,)).fetchone()
    if not template:
        template = conn.execute("SELECT * FROM templates LIMIT 1").fetchone()

    # Select only approved participants without certificates
    participants = conn.execute("""
    SELECT * FROM participants
    WHERE batch_id = ? AND is_approved = 1 AND (certificate_id IS NULL OR certificate_id = '')
    """, (batch_id,)).fetchall()

    if not participants:
        conn.close()
        return {"message": "No ungenerated approved participants in this batch", "count": 0}

    base_url = get_base_url(request)
    generated_count = 0
    generated_list = []

    for p in participants:
        cert_id = generate_unique_cert_id(event["name"])
        p_dict = dict(p)
        e_dict = dict(event)
        t_dict = dict(template)

        png_path, pdf_path = generate_certificate_image(
            cert_id=cert_id,
            participant=p_dict,
            event=e_dict,
            template_data=t_dict,
            base_verification_url=base_url,
            output_dir=CERT_STORAGE
        )

        cert_hash = compute_cert_hash(cert_id, p_dict["clean_name"], e_dict["name"], e_dict["event_date"])

        # Insert certificate record
        conn.execute("""
        INSERT INTO certificates (
            id, participant_id, event_id, cert_hash, participant_name, event_name,
            organization, role, issue_date, png_path, pdf_path, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE')
        """, (
            cert_id, p["id"], event["id"], cert_hash, p_dict["clean_name"],
            e_dict["name"], e_dict["organization"], p_dict["role"], e_dict["event_date"],
            png_path, pdf_path
        ))

        # Update participant with cert_id and hash
        conn.execute("UPDATE participants SET certificate_id = ?, cert_hash = ? WHERE id = ?", (cert_id, cert_hash, p["id"]))

        generated_count += 1
        generated_list.append({
            "id": cert_id,
            "participant_name": p_dict["clean_name"],
            "clean_email": p_dict.get("clean_email", ""),
            "role": p_dict["role"],
            "college": p_dict["college"],
            "department": p_dict["department"],
            "issue_date": e_dict["event_date"],
            "verify_url": f"{base_url}/verify/{cert_id}",
            "png_path": png_path,
            "pdf_path": pdf_path
        })

    # Update batch status
    conn.execute("UPDATE batches SET status = 'GENERATED' WHERE id = ?", (batch_id,))
    conn.commit()

    # Pre-create batch zip
    zip_path = os.path.join(CERT_STORAGE, f"Batch_{batch_id}_Certificates.zip")
    create_batch_zip(batch_id, generated_list, zip_path)

    conn.close()

    return {
        "message": f"Successfully generated {generated_count} verified certificates",
        "generated_count": generated_count,
        "zip_url": f"/api/batches/{batch_id}/download-zip"
    }


@app.get("/api/batches/{batch_id}/download-zip")
async def download_batch_zip(batch_id: int):
    zip_path = os.path.join(CERT_STORAGE, f"Batch_{batch_id}_Certificates.zip")
    if not os.path.exists(zip_path):
        # Build it on the fly if not exists
        conn = get_db_connection()
        certs = conn.execute("""
        SELECT c.*, p.clean_email, p.college, p.department
        FROM certificates c
        JOIN participants p ON c.participant_id = p.id
        WHERE p.batch_id = ?
        """, (batch_id,)).fetchall()
        conn.close()

        if not certs:
            raise HTTPException(status_code=404, detail="No certificates found for this batch")

        create_batch_zip(batch_id, [dict(c) for c in certs], zip_path)

    return FileResponse(zip_path, filename=f"CertifyPro_Batch_{batch_id}_All_Certificates.zip", media_type="application/zip")


@app.get("/api/certificates/{cert_id}")
async def get_certificate(cert_id: str, request: Request):
    conn = get_db_connection()
    cert = conn.execute("SELECT * FROM certificates WHERE id = ?", (cert_id,)).fetchone()
    if not cert:
        conn.close()
        raise HTTPException(status_code=404, detail="Certificate not found")

    event = conn.execute("SELECT * FROM events WHERE id = ?", (cert["event_id"],)).fetchone()
    conn.close()

    c_dict = dict(cert)
    c_dict["event"] = dict(event) if event else {}
    c_dict["verify_url"] = f"{get_base_url(request)}/verify/{cert_id}"
    c_dict["png_url"] = f"/certificates-files/{cert_id}.png"
    c_dict["pdf_url"] = f"/certificates-files/{cert_id}.pdf"
    return c_dict


@app.get("/api/certificates/{cert_id}/download/{fmt}")
async def download_cert_file(cert_id: str, fmt: str):
    conn = get_db_connection()
    cert = conn.execute("SELECT * FROM certificates WHERE id = ?", (cert_id,)).fetchone()
    conn.close()
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")

    if fmt.lower() == "pdf":
        file_path = cert["pdf_path"]
        media_type = "application/pdf"
        filename = f"{cert['id']}_{cert['participant_name'].replace(' ', '_')}.pdf"
    else:
        file_path = cert["png_path"]
        media_type = "image/png"
        filename = f"{cert['id']}_{cert['participant_name'].replace(' ', '_')}.png"

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Certificate asset file not found on disk")

    return FileResponse(file_path, filename=filename, media_type=media_type)


@app.post("/api/certificates/{cert_id}/send-email")
async def send_certificate_email(cert_id: str):
    conn = get_db_connection()
    cert = conn.execute("SELECT * FROM certificates WHERE id = ?", (cert_id,)).fetchone()
    if not cert:
        conn.close()
        raise HTTPException(status_code=404, detail="Certificate not found")

    participant = conn.execute("SELECT * FROM participants WHERE id = ?", (cert["participant_id"],)).fetchone()
    recipient_email = participant["clean_email"] if participant and participant["clean_email"] else "participant@college.edu"
    
    # Record in simulated email delivery outbox
    conn.execute("""
    INSERT INTO email_logs (certificate_id, recipient_email, recipient_name, event_name, status)
    VALUES (?, ?, ?, ?, 'SENT')
    """, (cert_id, recipient_email, cert["participant_name"], cert["event_name"]))
    conn.commit()
    conn.close()

    return {
        "status": "SENT",
        "recipient": recipient_email,
        "message": f"Official digital certificate delivered to {recipient_email}"
    }


@app.get("/api/email-logs")
async def get_email_logs():
    conn = get_db_connection()
    logs = conn.execute("SELECT * FROM email_logs ORDER BY id DESC LIMIT 50").fetchall()
    conn.close()
    return [dict(l) for l in logs]


@app.post("/api/verify-lookup")
async def verify_lookup(payload: dict):
    cert_id = payload.get("cert_id", "").strip().upper()
    conn = get_db_connection()
    cert = conn.execute("SELECT * FROM certificates WHERE id = ?", (cert_id,)).fetchone()
    if not cert:
        conn.close()
        return {
            "valid": False,
            "message": f"No certificate found matching ID: {cert_id}"
        }

    event = conn.execute("SELECT * FROM events WHERE id = ?", (cert["event_id"],)).fetchone()
    tamper_verified = verify_cert_hash(cert["id"], cert["participant_name"], cert["event_name"], cert["issue_date"], cert["cert_hash"])
    
    conn.close()
    return {
        "valid": cert["status"] == "ACTIVE" and tamper_verified,
        "certificate": dict(cert),
        "event": dict(event) if event else {},
        "tamper_verified": tamper_verified,
        "status": cert["status"]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
