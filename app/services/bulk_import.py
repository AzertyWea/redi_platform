import io
import re
import pandas as pd
from datetime import datetime
from werkzeug.security import generate_password_hash
from app import db
from app.models import User, StudentProfile, SemesterResult, Department, Program

REQUIRED_COLUMNS = {
    "roster": ["matricule", "name", "role", "department"],
    "grades": ["matricule", "ca_score", "exam_score"],
    "documents": ["matricule", "doc_type", "filename"],
}

COLUMN_ALIASES = {
    "matricule": ["matricule", "matricule", "student_id", "id", "matr"],
    "name": ["name", "full_name", "nom", "student_name"],
    "role": ["role", "rôle", "type"],
    "department": ["department", "dept", "departement", "filiere"],
    "program": ["program", "programme", "course_of_study", "field"],
    "ca_score": ["ca_score", "ca", "cc", "continuous_assessment", "note_cc"],
    "exam_score": ["exam_score", "exam", "examen", "note_exam"],
    "doc_type": ["doc_type", "document_type", "type", "doctype"],
    "filename": ["filename", "file_name", "file", "fichier"],
}

def normalize_columns(cols):
    alias_map = {}
    for col in cols:
        col_lower = col.strip().lower()
        for canonical, aliases in COLUMN_ALIASES.items():
            if col_lower in aliases:
                alias_map[col] = canonical
                break
        else:
            alias_map[col] = col
    return alias_map

def generate_template(import_type):
    output = io.BytesIO()
    if import_type == "roster":
        df = pd.DataFrame(columns=["matricule", "name", "role", "department", "program", "password"])
        df.loc[0] = ["STU001", "John Doe", "student", "Informatique", "HND Software Engineering", "student123"]
        df.loc[1] = ["TCH001", "Jane Smith", "teacher", "Informatique", "", "teacher123"]
    elif import_type == "grades":
        df = pd.DataFrame(columns=["matricule", "ca_score", "exam_score", "semester_number"])
        df.loc[0] = ["S0010", 15.5, 12.0, 1]
        df.loc[1] = ["S0011", 14.0, 11.5, 1]
    elif import_type == "documents":
        df = pd.DataFrame(columns=["matricule", "doc_type", "filename"])
        df.loc[0] = ["S0010", "transcript", "transcript_s0010.pdf"]
        df.loc[1] = ["S0010", "certificate", "cert_s0010.pdf"]
    else:
        raise ValueError(f"Unknown import type: {import_type}")
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="data")
    output.seek(0)
    return output

def parse_upload(file, import_type):
    filename = ""
    if hasattr(file, "filename") and file.filename:
        filename = file.filename.lower()
    elif hasattr(file, "name") and file.name:
        filename = file.name.lower()
    if filename.endswith(".csv"):
        df = pd.read_csv(file)
    elif filename.endswith((".xls", ".xlsx")) or not filename:
        df = pd.read_excel(file, engine="openpyxl") if hasattr(file, "seek") else pd.read_excel(io.BytesIO(file.read()), engine="openpyxl")
    else:
        return None, "Unsupported file format. Please upload .xlsx, .xls, or .csv."

    if df.empty:
        return None, "The uploaded file is empty."

    col_map = normalize_columns(df.columns)
    df = df.rename(columns=col_map)
    df = df.loc[:, ~df.columns.duplicated()]

    required = REQUIRED_COLUMNS[import_type]
    missing = [c for c in required if c not in df.columns]
    if missing:
        return None, f"Missing required columns: {', '.join(missing)}. Found: {', '.join(df.columns)}"

    df = df.where(pd.notna(df), None)
    return df, None

def validate_row(row, import_type, row_index):
    errors = []
    if import_type == "roster":
        raw = row.get("matricule")
        matricule = str(raw).strip() if pd.notna(raw) else ""
        if not matricule or len(matricule) < 3:
            errors.append("Invalid or missing matricule")
        if not str(row.get("name", "")).strip():
            errors.append("Missing name")
        role = str(row.get("role", "")).strip().lower()
        if role not in ("student", "teacher", "employer", "admin"):
            errors.append(f"Invalid role '{role}' (must be student/teacher/employer/admin)")
    elif import_type == "grades":
        matricule = str(row.get("matricule", "")).strip()
        if not matricule:
            errors.append("Missing matricule")
        try:
            ca = float(row.get("ca_score", 0) or 0)
            if ca < 0 or ca > 20:
                errors.append(f"CA score {ca} out of range (0-20)")
        except (ValueError, TypeError):
            errors.append("Invalid CA score")
        try:
            exam = float(row.get("exam_score", 0) or 0)
            if exam < 0 or exam > 20:
                errors.append(f"Exam score {exam} out of range (0-20)")
        except (ValueError, TypeError):
            errors.append("Invalid exam score")
    elif import_type == "documents":
        if not str(row.get("matricule", "")).strip():
            errors.append("Missing matricule")
        if not str(row.get("filename", "")).strip():
            errors.append("Missing filename")
    return errors

def preview_import(file, import_type):
    df, error = parse_upload(file, import_type)
    if error:
        return None, error

    rows = []
    seen_roles = set()
    for idx, row in df.iterrows():
        r = row.to_dict()
        r["_index"] = idx
        r["_errors"] = validate_row(r, import_type, idx)
        r["_valid"] = len(r["_errors"]) == 0
        if import_type == "roster" and r.get("role"):
            seen_roles.add(str(r["role"]).strip().lower())
        rows.append(r)

    stats = {
        "total": len(rows),
        "valid": sum(1 for r in rows if r["_valid"]),
        "invalid": sum(1 for r in rows if not r["_valid"]),
        "import_type": import_type,
    }

    return {"rows": rows, "stats": stats, "seen_roles": list(seen_roles)}, None

def commit_import(preview_data):
    import_type = preview_data["stats"]["import_type"]
    rows = preview_data["rows"]
    created = 0
    skipped = 0
    errors = []

    for r in rows:
        if not r["_valid"]:
            skipped += 1
            continue

        try:
            if import_type == "roster":
                matricule = str(r["matricule"]).strip()
                name = str(r["name"]).strip()
                role = str(r["role"]).strip().lower()
                department = str(r.get("department", "")).strip() or None
                program_name = str(r.get("program", "")).strip() or None
                password = str(r.get("password", f"{role}123")).strip()

                existing = User.query.filter_by(matricule=matricule).first()
                if existing:
                    skipped += 1
                    continue

                email = f"{matricule.lower()}@redi.local"
                user = User(
                    matricule=matricule, name=name, email=email,
                    role=role, department=department,
                    password_hash=generate_password_hash(password)
                )
                db.session.add(user)
                db.session.flush()

                if role == "student":
                    prog = None
                    if program_name:
                        prog = Program.query.filter_by(name=program_name).first()
                    profile = StudentProfile(
                        user_id=user.id, eri_score=0.0,
                        filiere=program_name or department,
                        program=program_name or department
                    )
                    db.session.add(profile)
                created += 1

            elif import_type == "grades":
                matricule = str(r["matricule"]).strip()
                ca = float(r.get("ca_score", 0) or 0)
                exam = float(r.get("exam_score", 0) or 0)
                semester = int(r.get("semester_number", 1) or 1)

                user = User.query.filter_by(matricule=matricule).first()
                if not user:
                    skipped += 1
                    continue
                profile = StudentProfile.query.filter_by(user_id=user.id).first()
                if not profile:
                    skipped += 1
                    continue

                overall = round(ca * 0.4 + exam * 0.6, 2)

                existing = SemesterResult.query.filter_by(
                    student_id=profile.id, semester_number=semester
                ).first()
                if existing:
                    existing.ca_score = ca
                    existing.exam_score = exam
                    existing.overall_score = overall
                else:
                    result = SemesterResult(
                        student_id=profile.id, semester_number=semester,
                        ca_score=ca, exam_score=exam, overall_score=overall
                    )
                    db.session.add(result)
                created += 1

            elif import_type == "documents":
                matricule = str(r["matricule"]).strip()
                doc_type = str(r.get("doc_type", "other")).strip()
                filename = str(r.get("filename", "")).strip()

                user = User.query.filter_by(matricule=matricule).first()
                if not user:
                    skipped += 1
                    continue
                profile = StudentProfile.query.filter_by(user_id=user.id).first()
                if not profile:
                    skipped += 1
                    continue

                from app.models import Document
                doc = Document(
                    student_id=profile.id,
                    doc_type=doc_type, filename=filename,
                    qr_hash=None, is_verified=False
                )
                db.session.add(doc)
                created += 1

        except Exception as e:
            errors.append(f"Row {r.get('_index', '?')}: {str(e)}")
            skipped += 1

    db.session.commit()
    return {"created": created, "skipped": skipped, "errors": errors}
