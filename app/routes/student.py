from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, jsonify
from flask_login import login_required, current_user
from app.models import (StudentProfile, SemesterResult, Document, Notification,
    ScheduleEntry, Program, Department, Internship, Certification, Project,
    Conversation, Message)
from app import db
from datetime import datetime as dt
import os
from werkzeug.utils import secure_filename

student_bp = Blueprint("student", __name__)

@student_bp.route("/dashboard")
@login_required
def dashboard():
    from app.services.eri_engine import calculate_eri_trend, calculate_class_eri_trend, predict_next_eri

    profile = StudentProfile.query.filter_by(user_id=current_user.id).first()
    results = SemesterResult.query.filter_by(student_id=profile.id).order_by(SemesterResult.semester_number).all() if profile else []
    docs = Document.query.filter_by(student_id=profile.id).limit(3).all() if profile else []
    notifs = Notification.query.filter_by(recipient_id=current_user.id).order_by(Notification.created_at.desc()).limit(5).all()

    schedule = []
    eri_trend = []
    class_avg_trend = []
    predicted_next = 0
    attendance_timeline = []

    if profile:
        if profile.school_class:
            course_ids = [c.id for c in profile.school_class.courses]
            schedule = ScheduleEntry.query.filter(
                ScheduleEntry.course_id.in_(course_ids), ScheduleEntry.is_active == True
            ).order_by(ScheduleEntry.day_of_week, ScheduleEntry.start_time).all() if course_ids else []
            class_avg_trend = calculate_class_eri_trend(profile.school_class)
        elif profile.filiere:
            prog = Program.query.filter_by(name=profile.filiere).first()
            if prog:
                course_ids = [c.id for c in prog.courses]
                schedule = ScheduleEntry.query.filter(
                    ScheduleEntry.course_id.in_(course_ids), ScheduleEntry.is_active == True
                ).order_by(ScheduleEntry.day_of_week, ScheduleEntry.start_time).all()

        eri_trend = calculate_eri_trend(profile)
        predicted_next = predict_next_eri(eri_trend)

        from app.models import AttendanceRecord
        attendance_timeline = AttendanceRecord.query.filter_by(student_id=profile.id) \
            .order_by(AttendanceRecord.date.desc()).limit(30).all()

    return render_template("student/dashboard.html", profile=profile, results=results, docs=docs,
        notifs=notifs, schedule=schedule, eri_trend=eri_trend, class_avg_trend=class_avg_trend,
        predicted_next=predicted_next, attendance_timeline=attendance_timeline)

@student_bp.route("/results")
@login_required
def results():
    profile = StudentProfile.query.filter_by(user_id=current_user.id).first()
    results = SemesterResult.query.filter_by(student_id=profile.id).order_by(SemesterResult.semester_number).all() if profile else []
    return render_template("student/results.html", profile=profile, results=results)

@student_bp.route("/documents")
@login_required
def documents():
    profile = StudentProfile.query.filter_by(user_id=current_user.id).first()
    docs = Document.query.filter_by(student_id=profile.id).all() if profile else []
    return render_template("student/documents.html", docs=docs)

@student_bp.route("/coach")
@login_required
def coach():
    profile = StudentProfile.query.filter_by(user_id=current_user.id).first()
    return render_template("student/coach.html",
        eri=profile.eri_score if profile else 0,
        name=current_user.name,
        dept=current_user.department or "Informatique")

@student_bp.route("/messages")
@login_required
def messages():
    convos = Conversation.query.filter_by(student_id=current_user.id)\
        .order_by(Conversation.created_at.desc()).all()
    unread_counts = {}
    for c in convos:
        unread_counts[c.id] = Message.query.filter_by(conversation_id=c.id, is_read=False)\
            .filter(Message.sender_id != current_user.id).count()
    return render_template("student/messages.html", convos=convos, unread_counts=unread_counts)

@student_bp.route("/messages/<int:conversation_id>")
@login_required
def view_conversation(conversation_id):
    convo = Conversation.query.get_or_404(conversation_id)
    if convo.student_id != current_user.id:
        flash("Access denied.", "danger")
        return redirect(url_for("student.messages"))
    Message.query.filter_by(conversation_id=convo.id, is_read=False)\
        .filter(Message.sender_id != current_user.id)\
        .update({"is_read": True})
    db.session.commit()
    return render_template("student/conversation.html", convo=convo)

@student_bp.route("/messages/<int:conversation_id>/send", methods=["POST"])
@login_required
def reply_message(conversation_id):
    convo = Conversation.query.get_or_404(conversation_id)
    if convo.student_id != current_user.id:
        return jsonify({"error": "Forbidden"}), 403
    content = request.form.get("content", "").strip()
    if not content:
        return jsonify({"error": "Empty message"}), 400
    msg = Message(conversation_id=convo.id, sender_id=current_user.id, content=content)
    db.session.add(msg)
    from app.services.notification_service import emit_notification
    emit_notification(
        recipient_id=convo.employer_id, recipient_role="employer",
        type_="message", title="New Message from Student",
        body=f"{current_user.name}: {content[:80]}",
        link="/employer/chat",
    )
    db.session.commit()
    return jsonify({"success": True, "message_id": msg.id})

@student_bp.route("/report/pdf")
@login_required
def download_pdf():
    from app.services.pdf_service import generate_student_report
    profile = StudentProfile.query.filter_by(user_id=current_user.id).first()
    results = SemesterResult.query.filter_by(student_id=profile.id).all() if profile else []
    buffer = generate_student_report(current_user, profile, results)
    return send_file(buffer, mimetype="application/pdf",
                     download_name=f"rapport_{current_user.matricule}.pdf",
                     as_attachment=True)

ALLOWED_EXTENSIONS = {"png","jpg","jpeg","gif"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".",1)[1].lower() in ALLOWED_EXTENSIONS

@student_bp.route("/profile", methods=["GET","POST"])
@login_required
def profile():
    p = StudentProfile.query.filter_by(user_id=current_user.id).first()
    departments = Department.query.all()
    if request.method == "POST":
        p.bio         = request.form.get("bio","").strip()
        p.skills      = request.form.get("skills","").strip()
        p.linkedin_url= request.form.get("linkedin_url","").strip()
        p.filiere     = request.form.get("filiere","").strip()
        current_user.department = request.form.get("department","").strip()
        photo = request.files.get("photo")
        if photo and allowed_file(photo.filename):
            filename = secure_filename(f"{current_user.matricule}_{photo.filename}")
            photo.save(os.path.join("app","static","uploads","profiles", filename))
            p.photo_filename = filename
        db.session.commit()
        flash("Profil mis a jour avec succes !", "success")
        return redirect(url_for("student.profile"))
    return render_template("student/profile.html", p=p, departments=departments)

@student_bp.route("/career-data", methods=["GET","POST"])
@login_required
def career_data():
    p = StudentProfile.query.filter_by(user_id=current_user.id).first()
    if request.method == "POST":
        action = request.form.get("action")

        if action == "add_internship":
            i = Internship(
                student_id=p.id,
                company_name=request.form.get("company_name","").strip(),
                role_title=request.form.get("role_title","").strip(),
                start_date=dt.strptime(request.form.get("start_date"), "%Y-%m-%d").date() if request.form.get("start_date") else None,
                end_date=dt.strptime(request.form.get("end_date"), "%Y-%m-%d").date() if request.form.get("end_date") else None,
                description=request.form.get("description","").strip()
            )
            db.session.add(i)
            from app.services.notification_service import emit_notification
            emit_notification(
                recipient_id=current_user.id, recipient_role="student",
                type_="internship_offer", title="Internship Added",
                body=f"Your internship at {i.company_name} as {i.role_title} has been recorded.",
                link="/student/career-data",
            )
            flash("Internship added successfully!", "success")

        elif action == "add_certification":
            c = Certification(
                student_id=p.id,
                title=request.form.get("cert_title","").strip(),
                issuer=request.form.get("issuer","").strip(),
                date_obtained=dt.strptime(request.form.get("date_obtained"), "%Y-%m-%d").date() if request.form.get("date_obtained") else None
            )
            db.session.add(c)
            flash("Certification added successfully!", "success")

        elif action == "add_project":
            pr = Project(
                student_id=p.id,
                title=request.form.get("proj_title","").strip(),
                description=request.form.get("proj_description","").strip(),
                technologies=request.form.get("technologies","").strip(),
                project_url=request.form.get("project_url","").strip(),
                course_related=request.form.get("course_related","").strip()
            )
            db.session.add(pr)
            flash("Project added successfully!", "success")

        db.session.commit()
        return redirect(url_for("student.career_data"))

    internships = Internship.query.filter_by(student_id=p.id).order_by(Internship.start_date.desc()).all() if p else []
    certifications = Certification.query.filter_by(student_id=p.id).order_by(Certification.date_obtained.desc()).all() if p else []
    projects = Project.query.filter_by(student_id=p.id).order_by(Project.created_at.desc()).all() if p else []
    return render_template("student/career_data.html", internships=internships, certifications=certifications, projects=projects)

@student_bp.route("/career-data/delete/<string:item_type>/<int:item_id>", methods=["POST"])
@login_required
def delete_career_item(item_type, item_id):
    model_map = {"internship": Internship, "certification": Certification, "project": Project}
    model = model_map.get(item_type)
    if model:
        item = model.query.get_or_404(item_id)
        db.session.delete(item)
        db.session.commit()
        flash("Item deleted.", "success")
    return redirect(url_for("student.career_data"))

@student_bp.route("/programs-by-department")
@login_required
def programs_by_department():
    name = request.args.get("name","")
    dept = Department.query.filter_by(name=name).first()
    if not dept:
        return jsonify([])
    programs = Program.query.filter_by(department_id=dept.id).all()
    return jsonify([p.name for p in programs])
