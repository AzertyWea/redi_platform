from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import (StudentProfile, FeeStructure, FeePayment,
                        AcademicYear, AuditLog, User)
from app import db

unidy_finance_bp = Blueprint('unidy_finance', __name__, url_prefix='/unidy/finance')

def finance_required():
    if current_user.role not in ('finance_officer', 'admin'):
        flash('Access denied.', 'danger')
        return False
    return True

@unidy_finance_bp.route('/dashboard')
@login_required
def dashboard():
    if not finance_required():
        return redirect(url_for('auth.login'))
    stats = {
        'total_payments': FeePayment.query.count(),
        'total_collected': db.session.query(db.func.sum(FeePayment.amount)).scalar() or 0,
        'students_with_balance': 0,
    }
    current_ay = AcademicYear.query.filter_by(is_current=True).first()
    recent_payments = FeePayment.query.order_by(FeePayment.created_at.desc()).limit(10).all()
    return render_template('unidy/finance/dashboard.html',
                           stats=stats, current_ay=current_ay, recent_payments=recent_payments)

@unidy_finance_bp.route('/payments', methods=['GET', 'POST'])
@login_required
def payments():
    if not finance_required():
        return redirect(url_for('auth.login'))
    if request.method == 'POST':
        student_id = request.form.get('student_id', type=int)
        amount = request.form.get('amount', type=float)
        method = request.form.get('payment_method', 'cash')
        ref = request.form.get('reference', '').strip()
        sem_num = request.form.get('semester_number', type=int)
        notes = request.form.get('notes', '').strip()
        if student_id and amount and amount > 0:
            p = FeePayment(student_id=student_id, amount=amount, payment_method=method,
                          reference=ref, semester_number=sem_num, notes=notes,
                          recorded_by=current_user.id, payment_date=db.func.current_date(),
                          academic_year='2025-2026')
            db.session.add(p)
            log = AuditLog(user_id=current_user.id, role=current_user.role,
                          action='record_payment', target_type='fee_payment')
            db.session.add(log)
            db.session.commit()
            flash(f'Payment of {amount:,.0f} FCFA recorded.', 'success')
        return redirect(url_for('unidy_finance.payments'))
    students = StudentProfile.query.join(User).order_by(User.name).all()
    payments = FeePayment.query.order_by(FeePayment.created_at.desc()).limit(50).all()
    return render_template('unidy/finance/payments.html', payments=payments, students=students)

@unidy_finance_bp.route('/structures', methods=['GET', 'POST'])
@login_required
def structures():
    if not finance_required():
        return redirect(url_for('auth.login'))
    if request.method == 'POST':
        prog_id = request.form.get('program_id', type=int)
        level = request.form.get('level', type=int)
        sem = request.form.get('semester_number', type=int)
        amount = request.form.get('amount', type=float)
        desc = request.form.get('description', '').strip()
        if prog_id and level and sem and amount:
            fs = FeeStructure(program_id=prog_id, level=level, semester_number=sem,
                             amount=amount, description=desc, academic_year='2025-2026')
            db.session.add(fs)
            db.session.commit()
            flash('Fee structure created.', 'success')
        return redirect(url_for('unidy_finance.structures'))
    structures = FeeStructure.query.order_by(FeeStructure.program_id, FeeStructure.level).all()
    from app.models import Program
    programs = Program.query.all()
    return render_template('unidy/finance/structures.html', structures=structures, programs=programs)

@unidy_finance_bp.route('/receipts')
@login_required
def receipts():
    if not finance_required():
        return redirect(url_for('auth.login'))
    payments = FeePayment.query.order_by(FeePayment.created_at.desc()).all()
    return render_template('unidy/finance/receipts.html', payments=payments)
