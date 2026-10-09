import re
import difflib
from typing import List, Dict, Any, Tuple

COMMON_EMAIL_TYPOS = {
    "gmaill.com": "gmail.com",
    "gamil.com": "gmail.com",
    "gmai.com": "gmail.com",
    "gmial.com": "gmail.com",
    "gmal.com": "gmail.com",
    "gnail.com": "gmail.com",
    "yaho.com": "yahoo.com",
    "yahooo.com": "yahoo.com",
    "yhaoo.com": "yahoo.com",
    "hotmial.com": "hotmail.com",
    "hotmai.com": "hotmail.com",
    "outlok.com": "outlook.com",
    "outloo.com": "outlook.com",
    "outllok.com": "outlook.com",
    "rediffmial.com": "rediffmail.com",
}

DEPARTMENT_CANONICAL = {
    "cse": "Computer Science & Engineering",
    "cs": "Computer Science & Engineering",
    "computer science": "Computer Science & Engineering",
    "computer sc": "Computer Science & Engineering",
    "comp sci": "Computer Science & Engineering",
    "copmuter science": "Computer Science & Engineering",
    "coputer science": "Computer Science & Engineering",
    "ece": "Electronics & Communication Engineering",
    "electronics": "Electronics & Communication Engineering",
    "elec & comm": "Electronics & Communication Engineering",
    "electronics and communication": "Electronics & Communication Engineering",
    "it": "Information Technology",
    "info tech": "Information Technology",
    "information technology": "Information Technology",
    "mech": "Mechanical Engineering",
    "mechnical": "Mechanical Engineering",
    "mechanical": "Mechanical Engineering",
    "mechanical engineering": "Mechanical Engineering",
    "civil": "Civil Engineering",
    "civil engineering": "Civil Engineering",
    "eee": "Electrical & Electronics Engineering",
    "electrical": "Electrical & Electronics Engineering",
    "ai&ds": "Artificial Intelligence & Data Science",
    "aids": "Artificial Intelligence & Data Science",
    "ai & ds": "Artificial Intelligence & Data Science",
    "aiml": "AI & Machine Learning",
    "ai & ml": "AI & Machine Learning",
    "biotech": "Biotechnology",
    "biotechnology": "Biotechnology",
}

ROLE_CANONICAL = {
    "1st": "1st Place Winner",
    "first": "1st Place Winner",
    "first place": "1st Place Winner",
    "winner": "1st Place Winner",
    "1st prize": "1st Place Winner",
    "2nd": "2nd Place Winner",
    "second": "2nd Place Winner",
    "second place": "2nd Place Winner",
    "runner up": "2nd Place Winner",
    "runners up": "2nd Place Winner",
    "1st runner up": "2nd Place Winner",
    "3rd": "3rd Place Winner",
    "third": "3rd Place Winner",
    "third place": "3rd Place Winner",
    "2nd runner up": "3rd Place Winner",
    "special mention": "Special Mention",
    "best design": "Best Design Award",
    "best innovation": "Best Innovation Award",
    "participant": "Participant",
    "attendee": "Participant",
    "delegate": "Delegate",
    "organizer": "Student Coordinator",
    "coordinator": "Student Coordinator",
    "volunteer": "Volunteer",
}

def clean_name_string(raw_name: str) -> Tuple[str, List[Dict[str, Any]]]:
    issues = []
    if not raw_name or not raw_name.strip():
        issues.append({
            "type": "error",
            "field": "name",
            "message": "Participant name is missing or blank",
            "old_val": raw_name,
            "new_val": ""
        })
        return "", issues

    cleaned = raw_name.strip()
    original = cleaned

    # Check for excessive inner spaces
    if re.search(r"\s{2,}", cleaned):
        cleaned = re.sub(r"\s+", " ", cleaned)
        issues.append({
            "type": "fix",
            "field": "name",
            "message": "Collapsed irregular double/trailing spaces",
            "old_val": original,
            "new_val": cleaned
        })

    # Check for invalid symbols or numbers
    if re.search(r"[\d!@#$%^&*()_+={}\[\]:;\"<>?,/\\|]", cleaned):
        sanitized = re.sub(r"[\d!@#$%^&*()_+={}\[\]:;\"<>?,/\\|]", "", cleaned).strip()
        issues.append({
            "type": "warning",
            "field": "name",
            "message": "Removed digits or non-alphabetic symbols from participant name",
            "old_val": cleaned,
            "new_val": sanitized
        })
        cleaned = sanitized

    # Capitalization normalization
    words = cleaned.split()
    fixed_words = []
    has_casing_change = False

    honorifics = {"dr.", "dr", "mr.", "mr", "ms.", "ms", "mrs.", "mrs", "prof.", "prof"}
    special_suffixes = {"ii", "iii", "iv", "jr", "jr.", "sr", "sr."}

    for word in words:
        w_lower = word.lower()
        if w_lower in honorifics:
            proper = w_lower.capitalize()
            if not proper.endswith("."):
                proper += "."
            fixed_words.append(proper)
            if proper != word:
                has_casing_change = True
        elif w_lower in special_suffixes:
            proper = w_lower.upper()
            fixed_words.append(proper)
            if proper != word:
                has_casing_change = True
        elif w_lower.startswith("mc") and len(w_lower) > 2:
            proper = "Mc" + w_lower[2:].capitalize()
            fixed_words.append(proper)
            if proper != word:
                has_casing_change = True
        elif "." in word and len(word) <= 4:
            # Initials like A.K. or R.
            parts = [p.capitalize() for p in word.split(".") if p]
            proper = ".".join(parts) + "."
            fixed_words.append(proper)
            if proper != word:
                has_casing_change = True
        else:
            proper = word.capitalize()
            fixed_words.append(proper)
            if proper != word:
                has_casing_change = True

    final_name = " ".join(fixed_words)
    if has_casing_change and final_name != original:
        issues.append({
            "type": "fix",
            "field": "name",
            "message": f"Auto-normalized casing from '{original}' to '{final_name}'",
            "old_val": original,
            "new_val": final_name
        })

    if len(final_name) < 2:
        issues.append({
            "type": "error",
            "field": "name",
            "message": "Name is unrealistically short (< 2 characters)",
            "old_val": original,
            "new_val": final_name
        })

    return final_name, issues


def clean_email_string(raw_email: str) -> Tuple[str, List[Dict[str, Any]]]:
    issues = []
    if not raw_email or not raw_email.strip():
        issues.append({
            "type": "warning",
            "field": "email",
            "message": "Email address is missing (certificate cannot be emailed directly)",
            "old_val": raw_email,
            "new_val": ""
        })
        return "", issues

    cleaned = raw_email.strip().lower()
    original = raw_email.strip()

    # Domain typo correction
    if "@" in cleaned:
        user_part, domain_part = cleaned.split("@", 1)
        if domain_part in COMMON_EMAIL_TYPOS:
            fixed_domain = COMMON_EMAIL_TYPOS[domain_part]
            cleaned = f"{user_part}@{fixed_domain}"
            issues.append({
                "type": "fix",
                "field": "email",
                "message": f"Corrected common domain typo '@{domain_part}' to '@{fixed_domain}'",
                "old_val": original,
                "new_val": cleaned
            })
    else:
        issues.append({
            "type": "error",
            "field": "email",
            "message": "Missing '@' symbol in email address",
            "old_val": original,
            "new_val": cleaned
        })
        return cleaned, issues

    # Standard email regex check
    email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    if not re.match(email_regex, cleaned):
        issues.append({
            "type": "error",
            "field": "email",
            "message": "Malformed email format syntax",
            "old_val": original,
            "new_val": cleaned
        })

    return cleaned, issues


def clean_department_string(raw_dept: str) -> Tuple[str, List[Dict[str, Any]]]:
    issues = []
    if not raw_dept or not raw_dept.strip():
        return "General", []

    cleaned = raw_dept.strip()
    key = cleaned.lower()

    if key in DEPARTMENT_CANONICAL:
        canonical = DEPARTMENT_CANONICAL[key]
        if canonical != cleaned:
            issues.append({
                "type": "fix",
                "field": "department",
                "message": f"Standardized department from '{cleaned}' to canonical '{canonical}'",
                "old_val": cleaned,
                "new_val": canonical
            })
        return canonical, issues

    # Fuzzy match with department canonical keys
    matches = difflib.get_close_matches(key, DEPARTMENT_CANONICAL.keys(), n=1, cutoff=0.75)
    if matches:
        canonical = DEPARTMENT_CANONICAL[matches[0]]
        issues.append({
            "type": "fix",
            "field": "department",
            "message": f"Fuzzy corrected department typo '{cleaned}' to '{canonical}'",
            "old_val": cleaned,
            "new_val": canonical
        })
        return canonical, issues

    return cleaned.title(), issues


def clean_role_string(raw_role: str) -> Tuple[str, List[Dict[str, Any]]]:
    issues = []
    if not raw_role or not raw_role.strip():
        return "Participant", []

    cleaned = raw_role.strip()
    key = cleaned.lower()

    if key in ROLE_CANONICAL:
        canonical = ROLE_CANONICAL[key]
        if canonical != cleaned:
            issues.append({
                "type": "fix",
                "field": "role",
                "message": f"Standardized role from '{cleaned}' to '{canonical}'",
                "old_val": cleaned,
                "new_val": canonical
            })
        return canonical, issues

    return cleaned.title(), issues


def process_participant_batch(rows: List[Dict[str, Any]], existing_participants: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Processes a list of raw participant records, cleans data, checks for duplicates
    within the batch and against existing registrations, and assigns confidence scores.
    """
    if existing_participants is None:
        existing_participants = []

    seen_emails = {}
    seen_roll_numbers = {}
    seen_names_by_college = {}

    # Register existing database participants for duplicate prevention
    for p in existing_participants:
        e = (p.get("clean_email") or "").strip().lower()
        r = (p.get("roll_number") or "").strip().upper()
        n = (p.get("clean_name") or "").strip().lower()
        c = (p.get("college") or "").strip().lower()
        if e: seen_emails[e] = p.get("id")
        if r: seen_roll_numbers[r] = p.get("id")
        if n and c: seen_names_by_college[(n, c)] = p.get("id")

    processed = []

    for idx, row in enumerate(rows):
        row_issues = []
        raw_name = str(row.get("name", "") or row.get("Full Name", "") or row.get("Participant Name", ""))
        raw_email = str(row.get("email", "") or row.get("Email ID", "") or row.get("Email", ""))
        raw_college = str(row.get("college", "") or row.get("College", "") or row.get("Institution", "") or "Apex University")
        raw_dept = str(row.get("department", "") or row.get("Department", "") or row.get("Branch", "") or "")
        raw_roll = str(row.get("roll_number", "") or row.get("Roll Number", "") or row.get("USN", "") or row.get("Reg No", "") or "").strip().upper()
        raw_role = str(row.get("role", "") or row.get("Role", "") or row.get("Position", "") or row.get("Category", "") or "Participant")

        clean_name, name_issues = clean_name_string(raw_name)
        clean_email, email_issues = clean_email_string(raw_email)
        clean_dept, dept_issues = clean_department_string(raw_dept)
        clean_role, role_issues = clean_role_string(raw_role)
        clean_college = raw_college.strip().title() if raw_college else "Apex Institute of Technology"

        row_issues.extend(name_issues)
        row_issues.extend(email_issues)
        row_issues.extend(dept_issues)
        row_issues.extend(role_issues)

        # Duplicate checking
        is_duplicate = False
        dup_reason = ""

        # 1. Email collision
        if clean_email:
            if clean_email in seen_emails:
                is_duplicate = True
                dup_reason = f"Duplicate email address '{clean_email}' already present in records"
            else:
                seen_emails[clean_email] = f"batch_{idx}"

        # 2. Roll number collision
        if raw_roll:
            if raw_roll in seen_roll_numbers:
                is_duplicate = True
                dup_reason = f"Duplicate Roll/USN number '{raw_roll}' already registered"
            else:
                seen_roll_numbers[raw_roll] = f"batch_{idx}"

        # 3. Name & College exact collision
        name_college_key = (clean_name.lower(), clean_college.lower())
        if clean_name and clean_college:
            if name_college_key in seen_names_by_college:
                is_duplicate = True
                dup_reason = f"Participant '{clean_name}' at '{clean_college}' is already recorded"
            else:
                seen_names_by_college[name_college_key] = f"batch_{idx}"

        # 4. Fuzzy duplicate check within current batch
        if not is_duplicate and clean_name:
            for (prev_name, prev_col), orig_ref in seen_names_by_college.items():
                if prev_col == clean_college.lower():
                    ratio = difflib.SequenceMatcher(None, clean_name.lower(), prev_name).ratio()
                    if 0.85 <= ratio < 1.0:
                        row_issues.append({
                            "type": "warning",
                            "field": "name",
                            "message": f"High fuzzy similarity ({int(ratio*100)}%) with participant '{prev_name.title()}' at same institution",
                            "old_val": clean_name,
                            "new_val": clean_name
                        })

        if is_duplicate:
            row_issues.append({
                "type": "duplicate",
                "field": "duplicate",
                "message": dup_reason,
                "old_val": raw_name,
                "new_val": clean_name
            })

        # Calculate Confidence Score and Status
        error_count = sum(1 for iss in row_issues if iss["type"] == "error")
        duplicate_count = sum(1 for iss in row_issues if iss["type"] == "duplicate")
        warning_count = sum(1 for iss in row_issues if iss["type"] == "warning")
        fix_count = sum(1 for iss in row_issues if iss["type"] == "fix")

        confidence = 100
        if error_count > 0:
            confidence -= error_count * 35
        if duplicate_count > 0:
            confidence -= 40
        if warning_count > 0:
            confidence -= warning_count * 15
        if fix_count > 0:
            confidence -= fix_count * 5
        confidence = max(5, min(100, confidence))

        if duplicate_count > 0:
            status = "DUPLICATE"
            approved = 0
        elif error_count > 0:
            status = "FLAGGED"
            approved = 0
        elif warning_count > 0:
            status = "FLAGGED"
            approved = 1 # approved with warning pending review
        elif fix_count > 0:
            status = "AUTO_FIXED"
            approved = 1
        else:
            status = "CLEAN"
            approved = 1

        processed.append({
            "original_name": raw_name,
            "clean_name": clean_name if clean_name else raw_name,
            "original_email": raw_email,
            "clean_email": clean_email,
            "college": clean_college,
            "department": clean_dept,
            "roll_number": raw_roll or "N/A",
            "role": clean_role,
            "validation_status": status,
            "validation_issues": row_issues,
            "confidence_score": confidence,
            "is_approved": approved
        })

    return processed
