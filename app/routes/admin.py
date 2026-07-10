from flask import Blueprint, render_template, request, flash, redirect, url_for, send_file, abort
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from functools import wraps
from sqlalchemy import or_
from app.models import User, StudentProfile, Document, AttendanceRecord, SemesterResult
from app import db

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != "admin":
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

admin_bp = Blueprint("admin", __name__)

@admin_bp.route("/dashboard")
@login_required
def dashboard():
    total_students = StudentProfile.query.count()
    total_teachers = User.query.filter_by(role="teacher").count()
    total_docs = Document.query.count()
    students = StudentProfile.query.all()
    avg_eri = sum(s.eri_score for s in students) / len(students) if students else 0
    return render_template("admin/dashboard.html",
        total_students=total_students, total_teachers=total_teachers,
        total_docs=total_docs, avg_eri=round(avg_eri,1), students=students)

@admin_bp.route("/search")
@login_required
@admin_required
def search():
    q = request.args.get("q", "").strip()
    results = []
    if q:
        pattern = f"%{q}%"
        users = User.query.filter(
            or_(User.name.ilike(pattern), User.matricule.ilike(pattern)),
            User.role.in_(["student", "teacher"])
        ).order_by(User.role, User.name).limit(50).all()
        for u in users:
            profile = StudentProfile.query.filter_by(user_id=u.id).first()
            results.append({"user": u, "profile": profile})
    return render_template("admin/search.html", query=q, results=results)

@admin_bp.route("/student/<int:user_id>")
@login_required
@admin_required
def student_detail(user_id):
    from app.services.eri_engine import calculate_eri, predict_next_eri
    from app.models import Notification, ScheduleEntry
    viewed = User.query.get_or_404(user_id)
    if viewed.role != "student":
        abort(404)
    profile = StudentProfile.query.filter_by(user_id=viewed.id).first_or_404()
    results = SemesterResult.query.filter_by(student_id=profile.id).order_by(SemesterResult.semester_number).all()
    attendance_timeline = AttendanceRecord.query.filter_by(student_id=profile.id).order_by(AttendanceRecord.date.desc()).limit(30).all()
    docs = Document.query.filter_by(student_id=profile.id).order_by(Document.uploaded_at.desc()).all()
    notifs = Notification.query.filter_by(recipient_id=viewed.id).order_by(Notification.created_at.desc()).limit(10).all()
    schedule = ScheduleEntry.query.filter(ScheduleEntry.class_group_id == profile.class_group_id, ScheduleEntry.is_active == True).order_by(ScheduleEntry.day_of_week, ScheduleEntry.start_time).all() if profile.class_group_id else []
    eri_trend = []
    class_avg_trend = []
    sem_numbers = sorted(set(r.semester_number for r in results))
    class_students = StudentProfile.query.filter_by(class_group_id=profile.class_group_id).all() if profile.class_group_id else []
    for sem in sem_numbers:
        sem_results = [r for r in results if r.semester_number == sem]
        if sem_results:
            last = sem_results[-1]
            eri_trend.append({"semester": sem, "eri": last.overall_score})
            classmates = [s for s in class_students if s.id != profile.id]
            class_scores = []
            for cs in classmates:
                cr = SemesterResult.query.filter_by(student_id=cs.id, semester_number=sem).order_by(SemesterResult.semester_number.desc()).first()
                if cr:
                    class_scores.append(cr.overall_score)
            class_avg_trend.append({"semester": sem, "avg_eri": round(sum(class_scores)/len(class_scores), 1) if class_scores else 0})
    predicted_next = predict_next_eri(profile)
    return render_template("student/dashboard.html",
        profile=profile, results=results, attendance_timeline=attendance_timeline,
        docs=docs, notifs=notifs, schedule=schedule, eri_trend=eri_trend,
        class_avg_trend=class_avg_trend, predicted_next=predicted_next)

@admin_bp.route("/teacher/<int:user_id>")
@login_required
@admin_required
def teacher_detail(user_id):
    from app.models import ScheduleEntry, Course, SchoolClass, Assignment, Quiz, AttendanceRecord
    viewed = User.query.get_or_404(user_id)
    if viewed.role != "teacher":
        abort(404)
    courses = Course.query.filter_by(teacher_id=viewed.id).order_by(Course.code).all()
    course_ids = [c.id for c in courses]
    schedule = ScheduleEntry.query.filter(ScheduleEntry.course_id.in_(course_ids), ScheduleEntry.is_active == True).order_by(ScheduleEntry.day_of_week, ScheduleEntry.start_time).all() if course_ids else []
    assignments = Assignment.query.filter_by(teacher_id=viewed.id).order_by(Assignment.created_at.desc()).limit(20).all()
    quizzes = Quiz.query.filter_by(teacher_id=viewed.id).order_by(Quiz.created_at.desc()).limit(20).all()
    recent_attendance = AttendanceRecord.query.filter_by(teacher_id=viewed.id).order_by(AttendanceRecord.date.desc()).limit(30).all()
    students = StudentProfile.query.all()
    return render_template("admin/teacher_detail.html",
        viewed=viewed, courses=courses, schedule=schedule,
        assignments=assignments, quizzes=quizzes,
        recent_attendance=recent_attendance, students=students)

from app.models import SchoolClass, AuditLog
from app.services.eri_engine import calculate_eri

@admin_bp.route("/classes")
@login_required
@admin_required
def class_list():
    sort = request.args.get("sort", "")
    classes = SchoolClass.query.order_by(SchoolClass.program_id, SchoolClass.level, SchoolClass.section).all()
    class_data = []
    for cls in classes:
        student_count = StudentProfile.query.filter_by(class_group_id=cls.id).count()
        teachers = set()
        for c in cls.courses:
            if c.teacher:
                teachers.add(c.teacher.name)
        eri_scores = [s.eri_score for s in cls.students if s.eri_score]
        avg_eri = round(sum(eri_scores) / len(eri_scores), 1) if eri_scores else 0
        class_data.append({"class": cls, "student_count": student_count, "teachers": sorted(teachers), "avg_eri": avg_eri})
    if sort == "eri":
        class_data.sort(key=lambda x: x["avg_eri"], reverse=True)
    elif sort == "count":
        class_data.sort(key=lambda x: x["student_count"], reverse=True)
    return render_template("admin/class_list.html", class_data=class_data)

@admin_bp.route("/classes/<int:class_id>/roster")
@login_required
@admin_required
def class_roster(class_id):
    cls = SchoolClass.query.get_or_404(class_id)
    sort = request.args.get("sort", "")
    students = StudentProfile.query.filter_by(class_group_id=cls.id).all()
    roster = []
    for s in students:
        att_records = AttendanceRecord.query.filter_by(student_id=s.id).count()
        att_present = AttendanceRecord.query.filter_by(student_id=s.id, status="present").count()
        att_pct = round(att_present / att_records * 100, 1) if att_records else 0
        roster.append({"profile": s, "attendance_pct": att_pct, "eri": s.eri_score or 0})
    if sort == "eri":
        roster.sort(key=lambda x: x["eri"], reverse=True)
    elif sort == "attendance":
        roster.sort(key=lambda x: x["attendance_pct"], reverse=True)
    return render_template("admin/class_roster.html", cls=cls, roster=roster)

@admin_bp.route("/upload", methods=["GET","POST"])
@login_required
def upload():
    return redirect(url_for("admin.bulk_import"))

@admin_bp.route("/documents")
@login_required
def documents():
    docs = Document.query.all()
    # TODO: hook emit_notification(type_="letter_issued") here when
    # admin verifies/issues an official document/attestation/letter
    return render_template("admin/documents.html", docs=docs)

@admin_bp.route("/announce", methods=["GET", "POST"])
@login_required
@admin_required
def announce():
    from app.services.notification_service import emit_notification
    from app.models import SchoolClass
    if request.method == "POST":
        target = request.form.get("target", "all_students")
        title = request.form.get("title", "").strip()
        body = request.form.get("body", "").strip()
        if not title or not body:
            flash("Title and body are required.", "danger")
            return redirect(url_for("admin.announce"))
        recipients = []
        if target == "all_students":
            users = User.query.filter_by(role="student").all()
            recipients = [(u.id, "student") for u in users]
        elif target == "all_teachers":
            users = User.query.filter_by(role="teacher").all()
            recipients = [(u.id, "teacher") for u in users]
        elif target == "all_admins":
            users = User.query.filter_by(role="admin").all()
            recipients = [(u.id, "admin") for u in users]
        elif target.startswith("class_"):
            class_id = int(target.split("_")[1])
            cls = SchoolClass.query.get(class_id)
            if cls:
                for s in cls.students:
                    if s.user:
                        recipients.append((s.user.id, "student"))
        sent = 0
        for uid, role in recipients:
            emit_notification(
                recipient_id=uid, recipient_role=role,
                type_="announcement", title=title, body=body,
                link=None,
            )
            sent += 1
        db.session.commit()
        flash(f"Announcement sent to {sent} recipient(s).", "success")
        return redirect(url_for("admin.announce"))
    classes = SchoolClass.query.order_by(SchoolClass.name).all()
    return render_template("admin/announce.html", classes=classes)

@admin_bp.route("/users")
@login_required
def users():
    from app.models import Department
    all_users = User.query.filter(User.role != "admin").order_by(User.role).all()
    departments = Department.query.all()
    return render_template("admin/users.html", users=all_users, departments=departments)

@admin_bp.route("/users/create", methods=["POST"])
@login_required
def create_user():
    matricule = request.form.get("matricule","").strip()
    name      = request.form.get("full_name","").strip()
    filiere   = request.form.get("filiere","").strip()
    role      = request.form.get("role","").strip()
    password  = request.form.get("password","").strip()
    department= request.form.get("department","").strip()
    if not all([matricule, name, role, password]):
        flash("All fields are required.", "danger")
        return redirect(url_for("admin.users"))
    if User.query.filter_by(matricule=matricule).first():
        flash(f"Matricule {matricule} is already in use.", "danger")
        return redirect(url_for("admin.users"))
    email = f"{matricule.lower()}@redi.local"
    user = User(matricule=matricule, name=name, email=email, role=role,
                department=department, password_hash=generate_password_hash(password))
    db.session.add(user)
    if role == "student":
        db.session.flush()
        db.session.add(StudentProfile(user_id=user.id, eri_score=0.0, filiere=filiere))
    db.session.commit()
    flash(f"{role.capitalize()} account created: {name} ({matricule})", "success")
    return redirect(url_for("admin.users"))

@admin_bp.route("/users/delete/<int:user_id>", methods=["POST"])
@login_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash(f"Account {user.name} deleted.", "success")
    return redirect(url_for("admin.users"))

from app.services.eri_engine import calculate_eri

@admin_bp.route("/recalculate-eri", methods=["POST"])
@login_required
def recalculate_eri():
    students = StudentProfile.query.all()
    for s in students:
        s.eri_score = calculate_eri(s)
    db.session.commit()
    flash(f"ERI recalculated for {len(students)} students.", "success")
    return redirect(url_for("admin.dashboard"))

from app.models import Department, Program, Course, SchoolClass

@admin_bp.route("/structure", methods=["GET","POST"])
@login_required
def structure():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "add_department":
            d = Department(name=request.form.get("dept_name","").strip())
            db.session.add(d)
            flash("Department added!", "success")
        elif action == "add_program":
            p = Program(name=request.form.get("prog_name","").strip(), department_id=request.form.get("department_id"))
            db.session.add(p)
            flash("Program added!", "success")
        elif action == "add_course":
            c = Course(
                name=request.form.get("course_name","").strip(),
                code=request.form.get("course_code","").strip(),
                program_id=request.form.get("program_id"),
                semester_number=request.form.get("semester_number", type=int)
            )
            db.session.add(c)
            flash("Course added!", "success")
        elif action == "add_class":
            cls = SchoolClass(
                name=request.form.get("class_name","").strip(),
                department_id=request.form.get("class_department_id", type=int),
                program_id=request.form.get("class_program_id", type=int),
                level=request.form.get("class_level", type=int),
                section=request.form.get("class_section","").strip() or None,
                academic_year=request.form.get("class_academic_year","").strip()
            )
            db.session.add(cls)
            flash("Class added!", "success")
        elif action == "assign_teacher":
            course = Course.query.get(request.form.get("assign_course_id", type=int))
            teacher_id = request.form.get("assign_teacher_id", type=int)
            if course:
                course.teacher_id = teacher_id
                flash(f"{course.name} assigned to teacher.", "success")
        elif action == "link_course_class":
            course = Course.query.get(request.form.get("link_course_id", type=int))
            cls = SchoolClass.query.get(request.form.get("link_class_id", type=int))
            if course and cls:
                if cls not in course.classes:
                    course.classes.append(cls)
                    flash(f"{course.name} linked to {cls.display_name}.", "success")
                else:
                    flash("That course is already linked to that class.", "warning")
        elif action == "unlink_course_class":
            course = Course.query.get(request.form.get("unlink_course_id", type=int))
            cls = SchoolClass.query.get(request.form.get("unlink_class_id", type=int))
            if course and cls and cls in course.classes:
                course.classes.remove(cls)
                flash(f"{course.name} unlinked from {cls.display_name}.", "success")
        db.session.commit()
        return redirect(url_for("admin.structure"))

    departments = Department.query.all()
    programs = Program.query.all()
    courses = Course.query.order_by(Course.code).all()
    classes = SchoolClass.query.order_by(SchoolClass.program_id, SchoolClass.level, SchoolClass.section).all()
    teachers = User.query.filter_by(role="teacher").order_by(User.name).all()
    return render_template("admin/structure.html", departments=departments, programs=programs,
        courses=courses, classes=classes, teachers=teachers)

from app.models import ScheduleEntry
from datetime import time as dtime

@admin_bp.route("/timetable", methods=["GET","POST"])
@login_required
def timetable():
    if request.method == "POST":
        title         = request.form.get("title","").strip()
        course_id     = request.form.get("course_id", type=int)
        class_id      = request.form.get("class_id", type=int)
        day_of_week   = request.form.get("day_of_week","").strip()
        start_time    = request.form.get("start_time","").strip()
        end_time      = request.form.get("end_time","").strip()
        room          = request.form.get("room","").strip()
        academic_year = request.form.get("academic_year","").strip()
        semester      = request.form.get("semester_number", type=int)
        if not all([course_id, class_id, day_of_week, start_time, end_time]):
            flash("Course, class, day, start time and end time are required.", "danger")
            return redirect(url_for("admin.timetable"))
        h1,m1 = map(int, start_time.split(":"))
        h2,m2 = map(int, end_time.split(":"))
        entry = ScheduleEntry(
            title=title or None,
            course_id=course_id,
            class_group_id=class_id,
            day_of_week=day_of_week,
            start_time=dtime(h1,m1),
            end_time=dtime(h2,m2),
            room=room,
            academic_year=academic_year,
            semester_number=semester,
            is_active=True
        )
        db.session.add(entry)
        db.session.commit()
        flash("Schedule entry added successfully!", "success")
        return redirect(url_for("admin.timetable"))

    days = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"]
    courses = Course.query.order_by(Course.code).all()
    entries = ScheduleEntry.query.filter_by(is_active=True).order_by(ScheduleEntry.day_of_week, ScheduleEntry.start_time).all()
    entries_by_day = {d: [e for e in entries if e.day_of_week == d] for d in days}
    return render_template("admin/timetable.html", courses=courses, days=days,
        entries_by_day=entries_by_day, entries=entries)

@admin_bp.route("/timetable/delete/<int:entry_id>", methods=["POST"])
@login_required
def delete_schedule_entry(entry_id):
    entry = ScheduleEntry.query.get_or_404(entry_id)
    db.session.delete(entry)
    db.session.commit()
    flash("Schedule entry deleted.", "success")
    return redirect(url_for("admin.timetable"))

from app.services import bulk_import as bi

@admin_bp.route("/bulk-import", methods=["GET"])
@login_required
def bulk_import():
    return render_template("admin/bulk_import.html")

@admin_bp.route("/bulk-import/template/<import_type>")
@login_required
def bulk_import_template(import_type):
    if import_type not in ("roster", "grades", "documents"):
        flash("Invalid import type.", "danger")
        return redirect(url_for("admin.bulk_import"))
    buffer = bi.generate_template(import_type)
    return send_file(buffer, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                     download_name=f"redi_{import_type}_template.xlsx", as_attachment=True)

@admin_bp.route("/bulk-import/preview", methods=["POST"])
@login_required
def bulk_import_preview():
    import_type = request.form.get("import_type", "").strip()
    if import_type not in ("roster", "grades", "documents"):
        flash("Invalid import type.", "danger")
        return redirect(url_for("admin.bulk_import"))
    file = request.files.get("file")
    if not file or file.filename == "":
        flash("Please select a file to upload.", "danger")
        return redirect(url_for("admin.bulk_import"))
    preview_data, error = bi.preview_import(file, import_type)
    if error:
        flash(error, "danger")
        return redirect(url_for("admin.bulk_import"))
    return render_template("admin/bulk_preview.html", data=preview_data)

@admin_bp.route("/bulk-import/confirm", methods=["POST"])
@login_required
def bulk_import_confirm():
    import json
    raw = request.form.get("preview_json", "{}")
    try:
        preview_data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        flash("Invalid preview data. Please re-upload the file.", "danger")
        return redirect(url_for("admin.bulk_import"))
    result = bi.commit_import(preview_data)
    msg = f"Import complete: {result['created']} created, {result['skipped']} skipped."
    if result["errors"]:
        msg += f" {len(result['errors'])} errors."
        for err in result["errors"][:5]:
            flash(err, "warning")
    flash(msg, "success")
    return redirect(url_for("admin.bulk_import"))

from app.services.timetable_import import extract_timetable_from_pdf

@admin_bp.route("/audit-log")
@login_required
@admin_required
def audit_log():
    page = request.args.get("page", 1, type=int)
    sort = request.args.get("sort", "-timestamp")
    q = request.args.get("q", "").strip()
    base = AuditLog.query
    if q:
        base = base.join(User).filter(
            or_(User.name.ilike(f"%{q}%"),
                   AuditLog.action.ilike(f"%{q}%"),
                   AuditLog.target_type.ilike(f"%{q}%"))
        )
    if sort == "user":
        base = base.order_by(User.name, AuditLog.timestamp.desc())
    else:
        base = base.order_by(AuditLog.timestamp.desc())
    pagination = base.paginate(page=page, per_page=30, error_out=False)
    return render_template("admin/audit_log.html", pagination=pagination, q=q, sort=sort)

@admin_bp.route("/timetable/upload", methods=["GET", "POST"])
@login_required
def timetable_upload():
    if request.method == "POST":
        pdf_file = request.files.get("pdf_file")
        if not pdf_file or pdf_file.filename == "":
            flash("Please choose a PDF file to upload.", "danger")
            return redirect(url_for("admin.timetable_upload"))

        extraction = extract_timetable_from_pdf(pdf_file)
        if extraction["errors"]:
            for err in extraction["errors"]:
                flash(err, "danger")
            return redirect(url_for("admin.timetable_upload"))

        classes = SchoolClass.query.order_by(SchoolClass.program_id, SchoolClass.level, SchoolClass.section).all()
        courses = Course.query.order_by(Course.code).all()
        return render_template("admin/timetable_preview.html",
            extraction=extraction, classes=classes, courses=courses)

    return render_template("admin/timetable_upload.html")

@admin_bp.route("/timetable/upload/confirm", methods=["POST"])
@login_required
def timetable_upload_confirm():
    shared_class_id = request.form.get("shared_class_id", type=int)
    shared_academic_year = request.form.get("shared_academic_year", "").strip()
    shared_title = request.form.get("shared_title", "").strip()
    row_count = request.form.get("row_count", type=int) or 0

    created = 0
    skipped = 0
    for i in range(row_count):
        include = request.form.get(f"include_{i}")
        if not include:
            skipped += 1
            continue
        course_id = request.form.get(f"course_id_{i}", type=int)
        day = request.form.get(f"day_{i}", "").strip()
        start_time = request.form.get(f"start_time_{i}", "").strip()
        end_time = request.form.get(f"end_time_{i}", "").strip()
        room = request.form.get(f"room_{i}", "").strip()

        if not all([course_id, day, start_time, end_time, shared_class_id]):
            skipped += 1
            continue
        try:
            h1, m1 = map(int, start_time.split(":"))
            h2, m2 = map(int, end_time.split(":"))
        except Exception:
            skipped += 1
            continue

        entry = ScheduleEntry(
            title=shared_title or None,
            course_id=course_id,
            class_group_id=shared_class_id,
            day_of_week=day,
            start_time=dtime(h1, m1),
            end_time=dtime(h2, m2),
            room=room,
            academic_year=shared_academic_year,
            is_active=True
        )
        db.session.add(entry)
        created += 1

    db.session.commit()
    flash(f"Timetable import complete: {created} entries created, {skipped} rows skipped.", "success")
    return redirect(url_for("admin.timetable"))
