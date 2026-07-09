import re
import os
import difflib
from PIL import Image
from app.models import Course, SchoolClass

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

def _parse_time_range(text):
    match = re.search(r'(\d{1,2}:\d{2})\s*(?:-|to|–)\s*(\d{1,2}:\d{2})', text)
    if match:
        return match.group(1), match.group(2)
    return None, None

def _guess_class(full_text):
    classes = SchoolClass.query.all()
    if not classes:
        return None
    names = {c.display_name: c for c in classes}
    matches = difflib.get_close_matches(full_text[:200], list(names.keys()), n=1, cutoff=0.2)
    return names[matches[0]] if matches else None

def _guess_academic_year(full_text):
    match = re.search(r'(\d{4}-\d{4})', full_text)
    return match.group(1) if match else ""

def _match_course_by_code(code, course_by_code):
    return course_by_code.get(code.strip().lower()) if code else None

def _extract_table_rows(pdf):
    """Attempt 1: structured table extraction (best case - clean, text-based PDF)."""
    full_text = ""
    all_rows = []
    for page in pdf.pages:
        text = page.extract_text() or ""
        full_text += text + "\n"
        for table in page.extract_tables():
            all_rows.extend(table)
    return full_text, all_rows

def _ocr_extract_text(images):
    """Attempt 2: OCR fallback for scanned PDFs or photographed/image timetables."""
    import pytesseract
    full_text = ""
    for img in images:
        full_text += pytesseract.image_to_string(img) + "\n"
    return full_text

def _parse_ocr_lines_to_rows(text, course_by_code):
    """
    Best-effort line-by-line parsing of raw OCR text.
    Less reliable than structured table extraction: OCR loses column alignment,
    so each line is scanned independently for a day name, a time range, and a
    course code. Anything else on the line is kept as free-text for the admin
    to review in the preview screen, since OCR cannot reliably separate
    course name / teacher / room without column structure.
    """
    rows = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        day_match = next((d for d in DAY_NAMES if d.lower() in line.lower()), None)
        start_time, end_time = _parse_time_range(line)
        code_match = re.search(r'\b([A-Z]{2,6}\d{2,4})\b', line)
        code = code_match.group(1) if code_match else ""

        if not (day_match or start_time or code):
            continue

        course_match = _match_course_by_code(code, course_by_code)
        row_ok = bool(day_match and start_time and end_time and course_match)
        rows.append({
            "day": day_match or "", "start_time": start_time or "", "end_time": end_time or "",
            "code": code, "course_name": line, "teacher_name": "", "room": "",
            "course_match": course_match, "row_ok": row_ok
        })
    return rows

def extract_timetable_from_pdf(file_storage):
    """
    Extracts a weekly timetable from an uploaded PDF or image file.
    Strategy:
      1. If it's a PDF with a real text-based table -> use structured extraction (most accurate).
      2. If that finds nothing (scanned PDF, or the file is a plain image) -> fall back to OCR.
    Returns a dict: { title_text, class_guess, academic_year_guess, rows: [...], used_ocr: bool, errors: [...] }
    """
    import pdfplumber
    result = {"title_text": "", "class_guess": None, "academic_year_guess": "",
              "rows": [], "used_ocr": False, "errors": []}

    filename = (getattr(file_storage, "filename", "") or "").lower()
    all_courses = Course.query.all()
    course_by_code = {c.code.strip().lower(): c for c in all_courses if c.code}

    try:
        if filename.endswith((".png", ".jpg", ".jpeg")):
            image = Image.open(file_storage)
            full_text = _ocr_extract_text([image])
            result["used_ocr"] = True
            result["rows"] = _parse_ocr_lines_to_rows(full_text, course_by_code)
        else:
            with pdfplumber.open(file_storage) as pdf:
                full_text, all_rows = _extract_table_rows(pdf)

                if all_rows:
                    header = [(h or "").strip().lower() for h in all_rows[0]]
                    col_idx = {}
                    for i, h in enumerate(header):
                        if "day" in h: col_idx["day"] = i
                        elif "time" in h: col_idx["time"] = i
                        elif "code" in h: col_idx["code"] = i
                        elif "course" in h or "name" in h: col_idx["course"] = i
                        elif "teacher" in h or "lecturer" in h: col_idx["teacher"] = i
                        elif "room" in h: col_idx["room"] = i

                    if all(k in col_idx for k in ["day", "time", "code"]):
                        for raw_row in all_rows[1:]:
                            if not raw_row or all(not (c or "").strip() for c in raw_row):
                                continue
                            def get(key):
                                idx = col_idx.get(key)
                                return (raw_row[idx] or "").strip() if idx is not None and idx < len(raw_row) else ""
                            day, time_text, code = get("day"), get("time"), get("code")
                            course_name, teacher_name, room = get("course"), get("teacher"), get("room")
                            start_time, end_time = _parse_time_range(time_text)
                            course_match = _match_course_by_code(code, course_by_code)
                            row_ok = bool(day and start_time and end_time and course_match)
                            result["rows"].append({
                                "day": day, "start_time": start_time or "", "end_time": end_time or "",
                                "code": code, "course_name": course_name, "teacher_name": teacher_name,
                                "room": room, "course_match": course_match, "row_ok": row_ok
                            })

                if not result["rows"]:
                    # Fallback: no usable table found -> likely a scanned/image-based PDF, try OCR
                    result["used_ocr"] = True
                    images = [page.to_image(resolution=200).original for page in pdf.pages]
                    full_text = _ocr_extract_text(images)
                    result["rows"] = _parse_ocr_lines_to_rows(full_text, course_by_code)

        result["title_text"] = full_text.strip().split("\n")[0] if full_text.strip() else ""
        result["class_guess"] = _guess_class(full_text)
        result["academic_year_guess"] = _guess_academic_year(full_text)

        if not result["rows"]:
            result["errors"].append("No timetable data could be extracted from this file, even with OCR. Try a clearer scan or a text-based file.")

    except Exception as e:
        result["errors"].append(f"Failed to read file: {str(e)}")

    return result
