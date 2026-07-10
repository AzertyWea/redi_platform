from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from app import db
from app.models import StudentProfile, SemesterResult, User, SchoolClass, Course
from app.services.ai_upload import parse_file, detect_data_type, map_to_parameters
import json

ai_bp = Blueprint("ai_upload", __name__)

@ai_bp.route("/ai-upload/analyze", methods=["POST"])
@login_required
def analyze():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "Empty file"}), 400
    rows = parse_file(file)
    if not rows:
        return jsonify({"error": "Could not extract any data from this file"}), 400
    data_type = detect_data_type(rows)
    preview = []
    for r in rows[:20]:
        entry = {}
        if len(r) >= 3:
            entry["Matricule"] = r[0]
            entry["Name"] = r[1]
            entry["Value"] = r[2]
        else:
            for i, v in enumerate(r):
                entry[f"Column {i+1}"] = v
        preview.append(entry)
    params = map_to_parameters(rows, data_type)
    return jsonify({
        "rows": len(rows),
        "data_type": data_type,
        "preview": preview,
        "parameters": params
    })

@ai_bp.route("/ai-upload/commit", methods=["POST"])
@login_required
def commit():
    data = request.get_json()
    if not data or "data" not in data:
        return jsonify({"error": "No data"}), 400
    d = data["data"]
    params = d.get("parameters", [])
    data_type = d.get("data_type", "general")
    updated = 0
    for p in params:
        mat = p.get("matricule", "")
        val = p.get("value", "")
        if not mat:
            continue
        user = User.query.filter_by(matricule=mat).first()
        if not user:
            continue
        profile = StudentProfile.query.filter_by(user_id=user.id).first()
        if not profile:
            continue
        if data_type == "grades" and val:
            try:
                score = float(val)
            except ValueError:
                score = 0
            existing = SemesterResult.query.filter_by(student_id=profile.id).order_by(SemesterResult.semester_number.desc()).first()
            sem = (existing.semester_number + 1) if existing else 1
            result = SemesterResult(
                student_id=profile.id, semester_number=sem,
                ca_score=score if score <= 30 else 0,
                exam_score=score if score > 30 else 0,
                attendance=100, project_score=0, internship_score=0,
                overall_score=score
            )
            db.session.add(result)
            updated += 1
        elif data_type == "attendance":
            existing = SemesterResult.query.filter_by(student_id=profile.id).order_by(SemesterResult.semester_number.desc()).first()
            if existing:
                existing.attendance = min(100, (existing.attendance or 0) + 5)
                updated += 1
        elif data_type == "roster":
            if not profile.department and p.get("value"):
                profile.department = p["value"]
                updated += 1
    from app.services.audit_logger import log_action
    log_action("ai_upload_commit", target_type=data_type, target_id=None,
               old_value=None, new_value=f"AI upload committed {updated} records ({data_type}) by {current_user.name}")
    db.session.commit()
    return jsonify({"success": True, "updated": updated})
