from flask import Blueprint, render_template, request, flash, redirect, url_for, send_file
from flask_login import login_required, current_user
from app.models import StudentProfile, AttendanceRecord, User, Assignment, Quiz, TeacherObservation
from app import db
from datetime import datetime

teacher_bp = Blueprint('teacher', __name__)

@teacher_bp.route('/dashboard')
@login_required
def dashboard():
    from app.models import ScheduleEntry
    students = StudentProfile.query.all()
    course_ids = [c.id for c in current_user.courses_taught]
    schedule = ScheduleEntry.query.filter(ScheduleEntry.course_id.in_(course_ids), ScheduleEntry.is_active==True).order_by(ScheduleEntry.day_of_week, ScheduleEntry.start_time).all() if course_ids else []
    return render_template('teacher/dashboard.html', students=students, schedule=schedule)

@teacher_bp.route('/attendance', methods=['GET', 'POST'])
@login_required
def attendance():
    from app.models import Course, SchoolClass
    from app.services.eri_engine import calculate_eri

    my_courses = Course.query.filter_by(teacher_id=current_user.id).order_by(Course.name).all()

    if request.method == 'POST':
        course_id = request.form.get('course_id', type=int)
        class_id = request.form.get('class_id', type=int)
        course = Course.query.get(course_id)
        cls = SchoolClass.query.get(class_id)
        if not course or not cls:
            flash('Invalid course or class selection.', 'danger')
            return redirect(url_for('teacher.attendance'))
        for student in cls.students:
            status = request.form.get(f'status_{student.id}', 'absent')
            record = AttendanceRecord(
                student_id=student.id,
                teacher_id=current_user.id,
                course=course.name,
                course_id=course.id,
                class_group_id=cls.id,
                status=status,
                date=datetime.utcnow()
            )
            db.session.add(record)
        db.session.commit()

        # Recalculate ERI for every affected student so attendance reflects immediately
        for student in cls.students:
            student.eri_score = calculate_eri(student)

        from app.services.audit_logger import log_action
        log_action("attendance_update", target_type="SchoolClass", target_id=cls.id,
                   old_value=None, new_value=f"Attendance recorded for {cls.display_name} ({course.name}) by {current_user.name}")

        db.session.commit()

        from app.services.notification_service import emit_notification
        for student in cls.students:
            status = request.form.get(f'status_{student.id}', 'absent')
            emit_notification(
                recipient_id=student.user_id,
                recipient_role="student",
                type_="attendance",
                title="Attendance Recorded",
                body=f"Your attendance for {course.name} ({cls.display_name}) was marked as {status}.",
                link="/student/dashboard",
            )
        db.session.commit()

        flash(f'Attendance saved for {cls.display_name} ({course.name}) - ERI scores updated!', 'success')
        return redirect(url_for('teacher.attendance', course_id=course.id, class_id=cls.id))

    course_id = request.args.get('course_id', type=int)
    class_id = request.args.get('class_id', type=int)
    selected_course = Course.query.get(course_id) if course_id else None
    available_classes = selected_course.classes if selected_course else []
    selected_class = SchoolClass.query.get(class_id) if class_id else None
    students = selected_class.students if selected_class else []

    return render_template('teacher/attendance.html',
        my_courses=my_courses, selected_course=selected_course,
        available_classes=available_classes, selected_class=selected_class,
        students=students)

from datetime import datetime as dt

@teacher_bp.route("/assignments", methods=["GET","POST"])
@login_required
def assignments():
    if request.method == "POST":
        a = Assignment(
            teacher_id=current_user.id,
            course=request.form.get("course","").strip(),
            title=request.form.get("title","").strip(),
            description=request.form.get("description","").strip(),
            due_date=datetime.strptime(request.form.get("due_date"),"%Y-%m-%d") if request.form.get("due_date") else None,
            max_score=float(request.form.get("max_score",20))
        )
        db.session.add(a)
        db.session.commit()
        flash("Assignment created!", "success")
        return redirect(url_for("teacher.assignments"))
    my_assignments = Assignment.query.filter_by(teacher_id=current_user.id).order_by(Assignment.created_at.desc()).all()
    return render_template("teacher/assignments.html", assignments=my_assignments)

@teacher_bp.route("/quizzes", methods=["GET","POST"])
@login_required
def quizzes():
    if request.method == "POST":
        q = Quiz(teacher_id=current_user.id, course=request.form.get("course","").strip(), title=request.form.get("title","").strip())
        db.session.add(q)
        db.session.commit()
        flash("Quiz created!", "success")
        return redirect(url_for("teacher.quizzes"))
    my_quizzes = Quiz.query.filter_by(teacher_id=current_user.id).order_by(Quiz.created_at.desc()).all()
    return render_template("teacher/quizzes.html", quizzes=my_quizzes)

@teacher_bp.route("/observations", methods=["GET","POST"])
@login_required
def observations():
    from app.models import Course, SchoolClass

    my_courses = Course.query.filter_by(teacher_id=current_user.id).order_by(Course.name).all()

    if request.method == "POST":
        course_id = request.form.get("course_id", type=int)
        class_id = request.form.get("class_id", type=int)
        course = Course.query.get(course_id) if course_id else None
        o = TeacherObservation(
            student_id=request.form.get("student_id", type=int),
            teacher_id=current_user.id,
            course=course.name if course else request.form.get("course","").strip(),
            course_id=course_id,
            class_group_id=class_id,
            note=request.form.get("note","").strip(),
            participation_score=float(request.form.get("participation_score",0) or 0)
        )
        db.session.add(o)
        db.session.commit()
        flash("Observation recorded!", "success")
        return redirect(url_for("teacher.observations", course_id=course_id, class_id=class_id))

    course_id = request.args.get('course_id', type=int)
    class_id = request.args.get('class_id', type=int)
    selected_course = Course.query.get(course_id) if course_id else None
    available_classes = selected_course.classes if selected_course else []
    selected_class = SchoolClass.query.get(class_id) if class_id else None
    students = selected_class.students if selected_class else StudentProfile.query.all()

    my_obs = TeacherObservation.query.filter_by(teacher_id=current_user.id).order_by(TeacherObservation.created_at.desc()).limit(20).all()
    return render_template("teacher/observations.html",
        students=students, observations=my_obs, my_courses=my_courses,
        selected_course=selected_course, available_classes=available_classes, selected_class=selected_class)

@teacher_bp.route("/timetable/pdf")
@login_required
def timetable_pdf():
    from app.models import ScheduleEntry
    from io import BytesIO
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet

    course_ids = [c.id for c in current_user.courses_taught]
    schedule = ScheduleEntry.query.filter(
        ScheduleEntry.course_id.in_(course_ids), ScheduleEntry.is_active == True
    ).order_by(ScheduleEntry.day_of_week, ScheduleEntry.start_time).all() if course_ids else []

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles = getSampleStyleSheet()
    elements = [
        Paragraph(f"Weekly Timetable — {current_user.name}", styles['Title']),
        Spacer(1, 12),
    ]

    data = [["Day", "Time", "Course", "Class", "Room"]]
    for e in schedule:
        data.append([
            e.day_of_week,
            f"{e.start_time.strftime('%H:%M')} - {e.end_time.strftime('%H:%M')}",
            f"{e.course.code} - {e.course.name}",
            e.school_class.display_name if e.school_class else "-",
            e.room or "-"
        ])
    if len(data) == 1:
        data.append(["No scheduled sessions found.", "", "", "", ""])

    table = Table(data, colWidths=[3*cm, 4*cm, 9*cm, 7*cm, 3*cm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#7B0D1E")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#DDDDDD")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#F8F5F5")]),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return send_file(buffer, mimetype="application/pdf",
                      download_name=f"timetable_{current_user.matricule}.pdf",
                      as_attachment=True)
