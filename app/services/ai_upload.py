import re
import os
import pandas as pd
from io import BytesIO
from PIL import Image
from werkzeug.datastructures import FileStorage

def parse_file(file_storage):
    """Parse an uploaded file and return structured data."""
    filename = (getattr(file_storage, "filename", "") or "").lower()
    raw = file_storage.read()
    file_storage.seek(0)
    ext = os.path.splitext(filename)[1] if filename else ""

    if ext in (".xlsx", ".xls", ".csv"):
        return _parse_excel(raw, ext)
    elif ext == ".pdf":
        return _parse_pdf(file_storage)
    elif ext in (".png", ".jpg", ".jpeg"):
        return _parse_image(file_storage)
    return []

def _parse_excel(raw, ext):
    try:
        if ext == ".csv":
            df = pd.read_csv(BytesIO(raw))
        else:
            df = pd.read_excel(BytesIO(raw))
    except Exception:
        return []
    return _df_to_rows(df)

def _parse_pdf(file_storage):
    try:
        import pdfplumber
    except ImportError:
        return []
    rows = []
    with pdfplumber.open(file_storage) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            for line in text.split("\n"):
                line = line.strip()
                if not line or any(skip in line.lower() for skip in ("page", "summary", "total", "average")):
                    continue
                row = _extract_row_from_text(line)
                if row:
                    rows.append(row)
        for page in pdf.pages:
            for table in page.extract_tables():
                for t in table:
                    if t and any(cell and cell.strip() for cell in t):
                        parsed = [str(c or "").strip() for c in t]
                        if not _is_header(parsed):
                            rows.append(parsed)
    return rows

def _parse_image(file_storage):
    try:
        import pytesseract
    except ImportError:
        return []
    try:
        img = Image.open(file_storage)
        text = pytesseract.image_to_string(img)
    except Exception:
        return []
    rows = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        row = _extract_row_from_text(line)
        if row:
            rows.append(row)
    return rows

def _extract_row_from_text(line):
    parts = re.split(r"\s{2,}|\t", line)
    parts = [p.strip() for p in parts if p.strip()]
    if len(parts) >= 3:
        return parts
    return None

def _is_header(parts):
    headers = {"matricule", "student", "name", "score", "grade", "attendance",
               "ca", "exam", "total", "course", "code", "class"}
    return any(p.lower().strip() in headers for p in parts)

def _df_to_rows(df):
    df = df.dropna(how="all")
    rows = []
    for _, row in df.iterrows():
        vals = [str(v).strip() if pd.notna(v) else "" for v in row]
        if any(v for v in vals):
            rows.append(vals)
    return rows

def detect_data_type(rows):
    """Guess what kind of data this is: attendance, grades, roster, etc."""
    if not rows:
        return "unknown"
    text = " ".join(" ".join(str(c) for c in r) for r in rows).lower()
    score_words = sum(1 for w in ("score", "grade", "mark", "ca", "exam", "result", "gpa") if w in text)
    att_words = sum(1 for w in ("present", "absent", "attendance", "late") if w in text)
    roster_words = sum(1 for w in ("matricule", "student", "name", "program", "class") if w in text)
    if score_words >= 2:
        return "grades"
    if att_words >= 2:
        return "attendance"
    if roster_words >= 2:
        return "roster"
    return "general"

def map_to_parameters(rows, data_type):
    """Convert parsed rows into structured parameters for database updates."""
    if not rows:
        return []
    result = []
    for row in rows:
        entry = {"raw": row, "type": data_type, "matricule": "", "value": "", "confidence": "low"}
        text = " ".join(str(c) for c in row)
        mat_match = re.search(r"([A-Z]\d{3,6})", text)
        if mat_match:
            entry["matricule"] = mat_match.group(1)
            entry["confidence"] = "high"
        num_match = re.findall(r"(\d{1,3}(?:\.\d)?)", text)
        scores = [float(n) for n in num_match if 0 <= float(n) <= 100]
        if scores:
            entry["value"] = str(max(scores))
        if data_type == "attendance" and entry["matricule"]:
            entry["value"] = "present"
        result.append(entry)
    return result
