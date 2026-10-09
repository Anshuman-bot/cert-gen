import os
import io
import uuid
import hashlib
import zipfile
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import qrcode
from reportlab.lib.pagesizes import landscape, A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

SECRET_SALT = "CERTIFY_PRO_SECURE_SALT_2026_COLLEGE_KEY_X89A"

# Font resolver helper
def get_font(font_name: str, size: int):
    system_font_dir = "C:/Windows/Fonts"
    font_paths = {
        "title_serif": os.path.join(system_font_dir, "georgiab.ttf"),
        "serif": os.path.join(system_font_dir, "georgia.ttf"),
        "serif_italic": os.path.join(system_font_dir, "georgiai.ttf"),
        "title_sans": os.path.join(system_font_dir, "ariblk.ttf"),
        "sans_bold": os.path.join(system_font_dir, "arialbd.ttf"),
        "sans": os.path.join(system_font_dir, "arial.ttf"),
        "sans_italic": os.path.join(system_font_dir, "ariali.ttf"),
        "script": os.path.join(system_font_dir, "segoesc.ttf"),
        "calligraphy": os.path.join(system_font_dir, "segoepr.ttf")
    }

    target_path = font_paths.get(font_name, font_paths["sans"])
    if not os.path.exists(target_path):
        target_path = os.path.join(system_font_dir, "arial.ttf")

    if os.path.exists(target_path):
        try:
            return ImageFont.truetype(target_path, size)
        except Exception:
            pass

    return ImageFont.load_default()


def generate_unique_cert_id(event_name: str) -> str:
    words = [w for w in event_name.split() if len(w) > 2]
    prefix = "".join(w[0].upper() for w in words[:3]) if words else "EVT"
    year = datetime.now().year
    random_part = uuid.uuid4().hex[:6].upper()
    return f"CRT-{year}-{prefix}-{random_part}"


def compute_cert_hash(cert_id: str, participant_name: str, event_name: str, issue_date: str) -> str:
    raw = f"{cert_id}|{participant_name.strip()}|{event_name.strip()}|{issue_date.strip()}|{SECRET_SALT}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def verify_cert_hash(cert_id: str, participant_name: str, event_name: str, issue_date: str, expected_hash: str) -> bool:
    computed = compute_cert_hash(cert_id, participant_name, event_name, issue_date)
    return computed.lower() == expected_hash.lower()


def draw_star(draw, cx, cy, r_outer, r_inner, fill, points=5):
    import math
    angle = math.pi / points
    poly = []
    # Start pointing up
    start_rot = -math.pi / 2
    for i in range(2 * points):
        r = r_outer if i % 2 == 0 else r_inner
        curr_angle = start_rot + i * angle
        x = cx + r * math.cos(curr_angle)
        y = cy + r * math.sin(curr_angle)
        poly.append((x, y))
    draw.polygon(poly, fill=fill)

def draw_centered_text(draw, y, text, font, fill):
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    x = (2000 - text_width) // 2
    draw.text((x, y), text, font=font, fill=fill)
    return y + (bbox[3] - bbox[1])


def generate_qr_image(data_url: str, size: int = 200) -> Image.Image:
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(data_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0f172a", back_color="#ffffff").convert("RGBA")
    return img.resize((size, size), Image.Resampling.LANCZOS)


def generate_certificate_image(
    cert_id: str,
    participant: dict,
    event: dict,
    template_data: dict,
    base_verification_url: str,
    output_dir: str
) -> tuple[str, str]:
    """
    Renders high-definition 2000x1414 PNG and vector PDF for the certificate.
    Returns (png_path, pdf_path).
    """
    os.makedirs(output_dir, exist_ok=True)
    png_path = os.path.join(output_dir, f"{cert_id}.png")
    pdf_path = os.path.join(output_dir, f"{cert_id}.pdf")

    # Dimensions: 2000 x 1414 (standard landscape)
    W, H = 2000, 1414
    template_style = template_data.get("id", "modern_tech")

    # Colors configuration based on style
    if template_style == "royal_academic":
        bg_color = (253, 251, 247)       # Warm ivory
        primary_color = (30, 41, 59)     # Deep navy
        accent_color = (180, 83, 9)      # Classic burnished gold
        border_gold = (217, 119, 6)
        sub_text_color = (82, 82, 91)
        card_bg = (255, 255, 255)
    elif template_style == "sleek_minimal":
        bg_color = (250, 250, 250)      # Clean white
        primary_color = (6, 78, 59)      # Deep emerald
        accent_color = (5, 150, 105)     # Fresh emerald
        border_gold = (16, 185, 129)
        sub_text_color = (75, 85, 99)
        card_bg = (255, 255, 255)
    elif template_style == "prestige_sports":
        bg_color = (254, 242, 242)      # Soft rose white
        primary_color = (136, 19, 55)    # Crimson
        accent_color = (225, 29, 72)     # Vivid rose
        border_gold = (244, 63, 94)
        sub_text_color = (76, 29, 44)
        card_bg = (255, 255, 255)
    else: # modern_tech (default)
        bg_color = (15, 23, 42)          # Rich midnight slate
        primary_color = (255, 255, 255)  # Clean white
        accent_color = (56, 189, 248)    # Cyber cyan
        border_gold = (2, 132, 199)      # Deep cyan blue
        sub_text_color = (148, 163, 184) # Muted slate
        card_bg = (30, 41, 59)

    img = Image.new("RGBA", (W, H), bg_color)
    draw = ImageDraw.Draw(img)

    # 1. Ornamental Outer & Inner Borders
    border_margin = 40
    inner_margin = 55
    detail_margin = 65

    if template_style == "modern_tech":
        # Multi-layer tech geometric frame
        draw.rectangle([border_margin, border_margin, W - border_margin, H - border_margin], outline=border_gold, width=4)
        draw.rectangle([inner_margin, inner_margin, W - inner_margin, H - inner_margin], outline=(56, 189, 248, 120), width=2)
        # Tech corner accents
        corner_len = 60
        for cx, cy in [(border_margin, border_margin), (W - border_margin, border_margin), 
                       (border_margin, H - border_margin), (W - border_margin, H - border_margin)]:
            dx = 1 if cx == border_margin else -1
            dy = 1 if cy == border_margin else -1
            draw.line([(cx, cy), (cx + dx * corner_len, cy)], fill=accent_color, width=8)
            draw.line([(cx, cy), (cx, cy + dy * corner_len)], fill=accent_color, width=8)

        # Subtle circuit background dots / lines
        for i in range(120, W - 120, 160):
            draw.line([(i, 90), (i + 40, 90)], fill=(30, 58, 95, 80), width=2)
            draw.line([(i, H - 90), (i + 40, H - 90)], fill=(30, 58, 95, 80), width=2)
    else:
        # Classical double ornate border
        draw.rectangle([border_margin, border_margin, W - border_margin, H - border_margin], outline=accent_color, width=6)
        draw.rectangle([inner_margin, inner_margin, W - inner_margin, H - inner_margin], outline=border_gold, width=2)
        draw.rectangle([detail_margin, detail_margin, W - detail_margin, H - detail_margin], outline=(200, 200, 200), width=1)
        # Elegant corner flourishes
        flourish_size = 45
        for cx, cy in [(detail_margin, detail_margin), (W - detail_margin, detail_margin),
                       (detail_margin, H - detail_margin), (W - detail_margin, H - detail_margin)]:
            dx = 1 if cx == detail_margin else -1
            dy = 1 if cy == detail_margin else -1
            draw.arc([cx - flourish_size if dx == -1 else cx,
                      cy - flourish_size if dy == -1 else cy,
                      cx + flourish_size if dx == 1 else cx,
                      cy + flourish_size if dy == 1 else cy],
                      0, 360, fill=accent_color, width=3)

    # 2. Header: Institution / College Name
    org_name = (event.get("organization") or "Apex Institute of Technology & Engineering").upper()
    font_org = get_font("sans_bold" if template_style == "modern_tech" else "serif", 32)
    draw_centered_text(draw, 110, org_name, font_org, accent_color)

    # 3. Certificate Badge / Title
    badge_text = template_data.get("badge_text", "CERTIFICATE OF EXCELLENCE").upper()
    font_badge = get_font("title_sans" if template_style == "modern_tech" else "title_serif", 46)
    draw_centered_text(draw, 185, badge_text, font_badge, primary_color)

    # Subtle divider rule
    divider_y = 265
    divider_w = 400
    draw.line([(W // 2 - divider_w, divider_y), (W // 2 + divider_w, divider_y)], fill=accent_color, width=3)
    draw.polygon([(W // 2 - 10, divider_y), (W // 2, divider_y - 6), (W // 2 + 10, divider_y), (W // 2, divider_y + 6)], fill=accent_color)

    # 4. Presentation Lead
    font_lead = get_font("serif_italic" if template_style != "modern_tech" else "sans_italic", 28)
    draw_centered_text(draw, 305, "This credential is distinguished and proudly presented to", font_lead, sub_text_color)

    # 5. Participant Name (Centerpiece)
    participant_name = participant.get("clean_name", "Honored Participant")
    font_name = get_font("title_serif" if template_style != "modern_tech" else "sans_bold", 68)
    name_y = draw_centered_text(draw, 365, participant_name, font_name, accent_color if template_style == "modern_tech" else primary_color)

    # Subtle under-name ornamental bar
    name_bar_w = 500
    draw.line([(W // 2 - name_bar_w, name_y + 15), (W // 2 + name_bar_w, name_y + 15)], fill=border_gold, width=2)

    # 6. Institution / Roll Number Details
    college = participant.get("college") or ""
    dept = participant.get("department") or ""
    roll = participant.get("roll_number") or ""
    affiliation_parts = []
    if dept and dept != "General": affiliation_parts.append(dept)
    if college: affiliation_parts.append(college)
    if roll and roll != "N/A": affiliation_parts.append(f"Roll No: {roll}")
    affiliation_str = " | ".join(affiliation_parts)

    if affiliation_str:
        font_affil = get_font("sans", 24)
        draw_centered_text(draw, name_y + 35, affiliation_str, font_affil, sub_text_color)

    # 7. Achievement / Role Citation
    role = participant.get("role", "Participant")
    event_name = event.get("name", "College Technical Symposium")
    event_date = event.get("event_date", datetime.now().strftime("%B %d, %Y"))
    custom_citation = event.get("citation_text") or "has successfully participated and exhibited exemplary dedication in"

    citation_line1 = f"{custom_citation}"
    citation_line2 = f"\"{event_name}\""
    citation_line3 = f"conducted with distinction on {event_date}."

    font_cite = get_font("sans", 26)
    font_event_cite = get_font("sans_bold", 30)

    cite_y = name_y + 90
    draw_centered_text(draw, cite_y, citation_line1, font_cite, sub_text_color)
    draw_centered_text(draw, cite_y + 40, citation_line2, font_event_cite, primary_color)
    draw_centered_text(draw, cite_y + 85, citation_line3, font_cite, sub_text_color)

    if role and role.lower() != "participant":
        # Highlight award banner
        role_text = f"AWARDED: {role.upper()}"
        font_award = get_font("sans_bold", 28)
        bbox_award = draw.textbbox((0, 0), role_text, font=font_award)
        award_w = bbox_award[2] - bbox_award[0]
        award_y = cite_y + 135
        draw_centered_text(draw, award_y, role_text, font_award, accent_color)
        draw_star(draw, (W - award_w) // 2 - 30, award_y + 15, 14, 6, border_gold)
        draw_star(draw, (W + award_w) // 2 + 30, award_y + 15, 14, 6, border_gold)

    # 8. Dual Signatures & Issuer Seals
    sig_y = H - 280
    font_sig_name = get_font("sans_bold", 24)
    font_sig_title = get_font("sans", 20)
    font_script = get_font("script", 36)

    # Signatory 1 (Left)
    sig1_name = event.get("signatory1_name", "Dr. Rajesh V. Sharma")
    sig1_title = event.get("signatory1_title", "Event Convener")
    # Draw cursive simulated signature
    sig1_line_x = 220
    draw.text((sig1_line_x + 20, sig_y - 45), sig1_name, font=font_script, fill=accent_color)
    draw.line([(sig1_line_x, sig_y), (sig1_line_x + 360, sig_y)], fill=border_gold, width=2)
    draw.text((sig1_line_x + 10, sig_y + 10), sig1_name, font=font_sig_name, fill=primary_color)
    draw.text((sig1_line_x + 10, sig_y + 40), sig1_title, font=font_sig_title, fill=sub_text_color)

    # Signatory 2 (Right)
    sig2_name = event.get("signatory2_name", "Prof. Ananya Sen")
    sig2_title = event.get("signatory2_title", "Dean / Principal")
    sig2_line_x = W - 580
    draw.text((sig2_line_x + 20, sig_y - 45), sig2_name, font=font_script, fill=accent_color)
    draw.line([(sig2_line_x, sig_y), (sig2_line_x + 360, sig_y)], fill=border_gold, width=2)
    draw.text((sig2_line_x + 10, sig_y + 10), sig2_name, font=font_sig_name, fill=primary_color)
    draw.text((sig2_line_x + 10, sig_y + 40), sig2_title, font=font_sig_title, fill=sub_text_color)

    # 9. Center Official Digital Seal / Emblem
    seal_cx = W // 2
    seal_cy = H - 240
    seal_r = 65
    draw.ellipse([seal_cx - seal_r, seal_cy - seal_r, seal_cx + seal_r, seal_cy + seal_r], outline=border_gold, width=4)
    draw.ellipse([seal_cx - seal_r + 8, seal_cy - seal_r + 8, seal_cx + seal_r - 8, seal_cy + seal_r - 8], outline=accent_color, width=2)
    font_seal_text = get_font("sans_bold", 14)
    # Vector Seal star & text
    draw_star(draw, seal_cx, seal_cy - 16, 20, 9, border_gold)
    draw_centered_text(draw, seal_cy + 12, "OFFICIAL SEAL", font_seal_text, primary_color)
    draw_centered_text(draw, seal_cy + 28, "VERIFIED", font_seal_text, border_gold)

    # 10. QR Code for Instant Public Verification
    verify_url = f"{base_verification_url.rstrip('/')}/verify/{cert_id}"
    qr_img = generate_qr_image(verify_url, size=150)
    qr_x = W - 220
    qr_y = 90
    # Clean white rounded background card for QR code
    draw.rectangle([qr_x - 8, qr_y - 8, qr_x + 158, qr_y + 158], fill=(255, 255, 255), outline=border_gold, width=2)
    img.paste(qr_img, (qr_x, qr_y), qr_img)

    # QR Helper text
    font_qr_label = get_font("sans_bold", 13)
    draw.text((qr_x - 12, qr_y + 164), "SCAN TO VERIFY", font=font_qr_label, fill=accent_color if template_style == "modern_tech" else primary_color)

    # 11. Footer: Certificate ID, Cryptographic Hash preview, and Issue Date
    cert_hash = compute_cert_hash(cert_id, participant_name, event_name, event_date)
    font_meta = get_font("sans", 16)
    font_meta_bold = get_font("sans_bold", 16)

    meta_y = H - 80
    draw.text((border_margin + 30, meta_y), f"Certificate ID: ", font=font_meta_bold, fill=border_gold)
    draw.text((border_margin + 160, meta_y), cert_id, font=font_meta, fill=primary_color)

    draw.text((border_margin + 420, meta_y), f"Security Hash: {cert_hash[:16]}...{cert_hash[-8:]}", font=font_meta, fill=sub_text_color)
    draw.text((W - 360, meta_y), f"Issued: {event_date}", font=font_meta, fill=sub_text_color)

    # Save PNG
    img.convert("RGB").save(png_path, "PNG", quality=95)

    # Generate matching Vector/Printable PDF using ReportLab
    try:
        c = canvas.Canvas(pdf_path, pagesize=landscape(A4))
        # A4 Landscape is 841.89 x 595.27 points
        pdf_w, pdf_h = landscape(A4)
        c.drawImage(ImageReader(png_path), 0, 0, width=pdf_w, height=pdf_h)
        c.setTitle(f"Certificate - {participant_name} - {cert_id}")
        c.setAuthor(event.get("organization", "College Administration"))
        c.setSubject(f"Certificate of Excellence - {event_name}")
        c.save()
    except Exception as e:
        # Fallback to direct Pillow PDF export if needed
        img.convert("RGB").save(pdf_path, "PDF", resolution=150.0)

    return png_path, pdf_path


def create_batch_zip(batch_id: int, certificates_list: list, output_zip_path: str) -> str:
    """
    Creates a downloadable .zip archive of all certificates with a CSV summary index.
    """
    with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        manifest_lines = ["Certificate ID,Participant Name,Email,Role,College,Department,Issue Date,Verification URL\n"]
        for cert in certificates_list:
            png_file = cert.get("png_path")
            pdf_file = cert.get("pdf_path")
            cid = cert.get("id")
            name = cert.get("participant_name")

            if pdf_file and os.path.exists(pdf_file):
                zipf.write(pdf_file, arcname=f"PDFs/{cid}_{name.replace(' ', '_')}.pdf")
            if png_file and os.path.exists(png_file):
                zipf.write(png_file, arcname=f"PNGs/{cid}_{name.replace(' ', '_')}.png")

            manifest_lines.append(f'"{cid}","{name}","{cert.get("clean_email", "")}","{cert.get("role", "")}","{cert.get("college", "")}","{cert.get("department", "")}","{cert.get("issue_date", "")}","{cert.get("verify_url", "")}"\n')

        zipf.writestr("MANIFEST_INDEX.csv", "".join(manifest_lines))

    return output_zip_path
