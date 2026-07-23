from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import (User, StudentProfile, Admission, Enrollment, AcademicYear,
                        AcademicSemester, Department, Program, AuditLog, SchoolClass)
from app import db

unidy_registrar_bp = Blueprint('unidy_registrar', __name__, url_prefix='/unidy/registrar')

def registrar_required():
    if current_user.role not in ('registrar', 'admin'):
        flash('Access denied.', 'danger')
        return False
    return True

@unidy_registrar_bp.route('/dashboard')
@login_required
def dashboard():
    if not registrar_required():
        return redirect(url_for('auth.login'))
    stats = {
        'total_students': StudentProfile.query.count(),
        'pending_admissions': Admission.query.filter_by(status='pending').count(),
        'approved_admissions': Admission.query.filter_by(status='approved').count(),
        'total_enrollments': Enrollment.query.count(),
    }
    current_ay = AcademicYear.query.filter_by(is_current=True).first()
    current_sem = AcademicSemester.query.filter_by(is_current=True).first() if current_ay else None
    pending = Admission.query.filter_by(status='pending').order_by(Admission.created_at.desc()).limit(10).all()
    return render_template('unidy/registrar/dashboard.html',
                           stats=stats, current_ay=current_ay, current_sem=current_sem,
                           pending=pending)

@unidy_registrar_bp.route('/admissions')
@login_required
def admissions():
    if not registrar_required():
        return redirect(url_for('auth.login'))
    status_filter = request.args.get('status', '')
    q = Admission.query
    if status_filter:
        q = q.filter_by(status=status_filter)
    admissions = q.order_by(Admission.created_at.desc()).all()
    return render_template('unidy/registrar/admissions.html', admissions=admissions, status_filter=status_filter)

@unidy_registrar_bp.route('/admissions/<int:id>/approve', methods=['POST'])
@login_required
def approve_admission(id):
    if not registrar_required():
        return redirect(url_for('auth.login'))
    a = Admission.query.get_or_404(id)
    a.status = 'approved'
    a.reviewed_by = current_user.id
    a.reviewed_at = db.func.now()
    log = AuditLog(user_id=current_user.id, role=current_user.role,
                  action='approve_admission', target_type='admission', target_id=id)
    db.session.add(log)
    db.session.commit()
    flash(f'Admission approved for {a.student.name if a.student else "Unknown"}.', 'success')
    return redirect(url_for('unidy_registrar.admissions'))

@unidy_registrar_bp.route('/admissions/<int:id>/reject', methods=['POST'])
@login_required
def reject_admission(id):
    if not registrar_required():
        return redirect(url_for('auth.login'))
    a = Admission.query.get_or_404(id)
    a.status = 'rejected'
    a.reviewed_by = current_user.id
    a.reviewed_at = db.func.now()
    log = AuditLog(user_id=current_user.id, role=current_user.role,
                  action='reject_admission', target_type='admission', target_id=id)
    db.session.add(log)
    db.session.commit()
    flash(f'Admission rejected for {a.student.name if a.student else "Unknown"}.', 'warning')
    return redirect(url_for('unidy_registrar.admissions'))

@unidy_registrar_bp.route('/enrollments', methods=['GET', 'POST'])
@login_required
def enrollments():
    if not registrar_required():
        return redirect(url_for('auth.login'))
    if request.method == 'POST':
        student_id = request.form.get('student_id', type=int)
        course_id = request.form.get('course_id', type=int)
        sem_id = request.form.get('semester_id', type=int)
        if student_id and course_id:
            existing = Enrollment.query.filter_by(student_id=student_id, course_id=course_id, semester_id=sem_id).first()
            if existing:
                flash('Student already enrolled in this course.', 'warning')
            else:
                e = Enrollment(student_id=student_id, course_id=course_id,
                              semester_id=sem_id, enrolled_by=current_user.id)
                db.session.add(e)
                log = AuditLog(user_id=current_user.id, role=current_user.role,
                              action='create_enrollment', target_type='enrollment')
                db.session.add(log)
                db.session.commit()
                flash('Enrollment created.', 'success')
        return redirect(url_for('unidy_registrar.enrollments'))
    enrollments = Enrollment.query.order_by(Enrollment.created_at.desc()).all()
    students = StudentProfile.query.all()
    current_sem = AcademicSemester.query.filter_by(is_current=True).first()
    from app.models import Course
    courses = Course.query.all()
    return render_template('unidy/registrar/enrollments.html',
                           enrollments=enrollments, students=students,
                           courses=courses, current_sem=current_sem)

@unidy_registrar_bp.route('/students')
@login_required
def students():
    if not registrar_required():
        return redirect(url_for('auth.login'))
    students = StudentProfile.query.join(User).order_by(User.name).all()
    return render_template('unidy/registrar/students.html', students=students)

@unidy_registrar_bp.route('/students/<int:id>')
@login_required
def student_detail(id):
    if not registrar_required():
        return redirect(url_for('auth.login'))
    profile = StudentProfile.query.get_or_404(id)
    enrollments = Enrollment.query.filter_by(student_id=id).all()
    from app.models import CourseGrade
    grades = CourseGrade.query.filter_by(student_id=id).all()
    return render_template('unidy/registrar/student_detail.html',
                           profile=profile, enrollments=enrollments, grades=grades)
