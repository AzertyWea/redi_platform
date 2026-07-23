from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import (StudentProfile, CourseGrade, Enrollment, Transcript,
                        TranscriptItem, FeePayment, AcademicSemester)
from app import db

unidy_student_bp = Blueprint('unidy_student', __name__, url_prefix='/unidy/student')

@unidy_student_bp.route('/dashboard')
@login_required
def dashboard():
    profile = StudentProfile.query.filter_by(user_id=current_user.id).first()
    if not profile:
        flash('No student profile found.', 'warning')
        return redirect(url_for('auth.login'))
    current_sem = AcademicSemester.query.filter_by(is_current=True).first()
    enrollments = Enrollment.query.filter_by(student_id=profile.id).all()
    grades = CourseGrade.query.filter_by(student_id=profile.id).order_by(CourseGrade.created_at.desc()).all()
    payments = FeePayment.query.filter_by(student_id=profile.id).order_by(FeePayment.created_at.desc()).all()
    transcripts = Transcript.query.filter_by(student_id=profile.id).order_by(Transcript.created_at.desc()).all()
    total_paid = db.session.query(db.func.sum(FeePayment.amount)).filter_by(student_id=profile.id).scalar() or 0
    total_fees = 300000
    balance = total_fees - total_paid
    return render_template('unidy/student/dashboard.html',
                           profile=profile, current_sem=current_sem,
                           enrollments=enrollments, grades=grades,
                           payments=payments, transcripts=transcripts,
                           total_paid=total_paid, balance=balance)

@unidy_student_bp.route('/grades')
@login_required
def my_grades():
    profile = StudentProfile.query.filter_by(user_id=current_user.id).first()
    if not profile:
        return redirect(url_for('auth.login'))
    grades = CourseGrade.query.filter_by(student_id=profile.id).order_by(CourseGrade.created_at.desc()).all()
    return render_template('unidy/student/grades.html', grades=grades, profile=profile)

@unidy_student_bp.route('/payments')
@login_required
def my_payments():
    profile = StudentProfile.query.filter_by(user_id=current_user.id).first()
    if not profile:
        return redirect(url_for('auth.login'))
    payments = FeePayment.query.filter_by(student_id=profile.id).order_by(FeePayment.created_at.desc()).all()
    total_paid = db.session.query(db.func.sum(FeePayment.amount)).filter_by(student_id=profile.id).scalar() or 0
    return render_template('unidy/student/payments.html',
                           payments=payments, total_paid=total_paid, profile=profile)

@unidy_student_bp.route('/transcripts')
@login_required
def my_transcripts():
    profile = StudentProfile.query.filter_by(user_id=current_user.id).first()
    if not profile:
        return redirect(url_for('auth.login'))
    transcripts = Transcript.query.filter_by(student_id=profile.id).order_by(Transcript.created_at.desc()).all()
    return render_template('unidy/student/transcripts.html', transcripts=transcripts, profile=profile)
