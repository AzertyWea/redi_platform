from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import (Course, CourseGrade, Enrollment, StudentProfile,
                        AcademicSemester, SchoolClass, AuditLog)
from app import db

unidy_lecturer_bp = Blueprint('unidy_lecturer', __name__, url_prefix='/unidy/lecturer')

def lecturer_required():
    if current_user.role not in ('teacher', 'lecturer', 'admin'):
        flash('Access denied.', 'danger')
        return False
    return True

@unidy_lecturer_bp.route('/dashboard')
@login_required
def dashboard():
    if not lecturer_required():
        return redirect(url_for('auth.login'))
    courses = Course.query.filter_by(teacher_id=current_user.id).all()
    current_sem = AcademicSemester.query.filter_by(is_current=True).first()
    grade_counts = {}
    for c in courses:
        enrolled = Enrollment.query.filter_by(course_id=c.id, semester_id=current_sem.id if current_sem else None).count() if current_sem else 0
        graded = CourseGrade.query.filter_by(course_id=c.id, semester_id=current_sem.id if current_sem else None).count() if current_sem else 0
        grade_counts[c.id] = {'enrolled': enrolled, 'graded': graded}
    return render_template('unidy/lecturer/dashboard.html',
                           courses=courses, current_sem=current_sem, grade_counts=grade_counts)

@unidy_lecturer_bp.route('/courses/<int:course_id>/grades', methods=['GET', 'POST'])
@login_required
def course_grades(course_id):
    if not lecturer_required():
        return redirect(url_for('auth.login'))
    course = Course.query.get_or_404(course_id)
    current_sem = AcademicSemester.query.filter_by(is_current=True).first()
    enrollments = Enrollment.query.filter_by(course_id=course_id).all()
    if request.method == 'POST':
        for e in enrollments:
            prefix = f'student_{e.student_id}'
            ca = request.form.get(f'{prefix}_ca', type=float) or 0
            exam = request.form.get(f'{prefix}_exam', type=float) or 0
            total = round(ca * 0.4 + exam * 0.6, 1)
            if total >= 70: grade_letter = 'A'
            elif total >= 60: grade_letter = 'B'
            elif total >= 50: grade_letter = 'C'
            elif total >= 40: grade_letter = 'D'
            else: grade_letter = 'F'
            gp = {'A': 4.0, 'B': 3.0, 'C': 2.0, 'D': 1.0, 'F': 0.0}.get(grade_letter, 0)
            existing = CourseGrade.query.filter_by(
                student_id=e.student_id, course_id=course_id,
                semester_id=current_sem.id if current_sem else None).first()
            if existing:
                existing.ca_score = ca
                existing.exam_score = exam
                existing.total_score = total
                existing.grade_letter = grade_letter
                existing.grade_points = gp
                existing.status = 'graded'
                existing.graded_by = current_user.id
            else:
                g = CourseGrade(student_id=e.student_id, course_id=course_id,
                               semester_id=current_sem.id if current_sem else None,
                               ca_score=ca, exam_score=exam, total_score=total,
                               grade_letter=grade_letter, grade_points=gp,
                               credits=3, status='graded', graded_by=current_user.id)
                db.session.add(g)
        log = AuditLog(user_id=current_user.id, role=current_user.role,
                      action='submit_grades', target_type='course', target_id=course_id)
        db.session.add(log)
        db.session.commit()
        flash('Grades submitted successfully.', 'success')
        return redirect(url_for('unidy_lecturer.course_grades', course_id=course_id))
    existing_grades = {}
    for e in enrollments:
        g = CourseGrade.query.filter_by(student_id=e.student_id, course_id=course_id,
                                        semester_id=current_sem.id if current_sem else None).first()
        if g:
            existing_grades[e.student_id] = g
    return render_template('unidy/lecturer/course_grades.html',
                           course=course, enrollments=enrollments,
                           existing_grades=existing_grades, current_sem=current_sem)

@unidy_lecturer_bp.route('/grades')
@login_required
def all_grades():
    if not lecturer_required():
        return redirect(url_for('auth.login'))
    current_sem = AcademicSemester.query.filter_by(is_current=True).first()
    courses = Course.query.filter_by(teacher_id=current_user.id).all()
    course_ids = [c.id for c in courses]
    grades = CourseGrade.query.filter(CourseGrade.course_id.in_(course_ids)).order_by(CourseGrade.created_at.desc()).all()
    return render_template('unidy/lecturer/all_grades.html',
                           grades=grades, courses=courses, current_sem=current_sem)
