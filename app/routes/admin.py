from flask import Blueprint, render_template, request, flash, redirect, url_for, send_file
from flask_login import login_required
from werkzeug.security import generate_password_hash
from app.models import User, StudentProfile, Document
from app import db

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

@admin_bp.route("/upload", methods=["GET","POST"])
@login_required
def upload():
    return redirect(url_for("admin.bulk_import"))

@admin_bp.route("/documents")
@login_required
def documents():
    docs = Document.query.all()
    return render_template("admin/documents.html", docs=docs)

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
