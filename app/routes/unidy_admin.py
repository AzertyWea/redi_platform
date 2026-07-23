import json
from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file
from flask_login import login_required, current_user
from app.models import (User, StudentProfile, Department, Program, SchoolClass,
                        AcademicYear, AcademicSemester, AuditLog, Enrollment, CourseGrade)
from app import db

unidy_admin_bp = Blueprint('unidy_admin', __name__, url_prefix='/unidy/admin')

def admin_required():
    if current_user.role not in ('admin', 'academic_admin'):
        flash('Access denied.', 'danger')
        return False
    return True

@unidy_admin_bp.route('/dashboard')
@login_required
def dashboard():
    if not admin_required():
        return redirect(url_for('auth.login'))
    stats = {
        'total_students': StudentProfile.query.count(),
        'total_teachers': User.query.filter_by(role='teacher').count(),
        'total_departments': Department.query.count(),
        'total_programs': Program.query.count(),
        'total_classes': SchoolClass.query.count(),
    }
    current_ay = AcademicYear.query.filter_by(is_current=True).first()
    current_sem = AcademicSemester.query.filter_by(is_current=True).first() if current_ay else None
    departments = Department.query.all()
    programs = Program.query.all()
    classes = SchoolClass.query.order_by(SchoolClass.level, SchoolClass.section).all()
    return render_template('unidy/admin/dashboard.html',
                           stats=stats, current_ay=current_ay, current_sem=current_sem,
                           departments=departments, programs=programs, classes=classes)

@unidy_admin_bp.route('/departments', methods=['GET', 'POST'])
@login_required
def departments():
    if not admin_required():
        return redirect(url_for('auth.login'))
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        if name:
            d = Department(name=name)
            db.session.add(d)
            log = AuditLog(user_id=current_user.id, role=current_user.role,
                          action='create_department', target_type='department', new_value=name)
            db.session.add(log)
            db.session.commit()
            flash(f'Department "{name}" created.', 'success')
        return redirect(url_for('unidy_admin.departments'))
    depts = Department.query.all()
    return render_template('unidy/admin/departments.html', departments=depts)

@unidy_admin_bp.route('/programs', methods=['GET', 'POST'])
@login_required
def programs():
    if not admin_required():
        return redirect(url_for('auth.login'))
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        dept_id = request.form.get('department_id', type=int)
        if name:
            p = Program(name=name, department_id=dept_id)
            db.session.add(p)
            log = AuditLog(user_id=current_user.id, role=current_user.role,
                          action='create_program', target_type='program', new_value=name)
            db.session.add(log)
            db.session.commit()
            flash(f'Program "{name}" created.', 'success')
        return redirect(url_for('unidy_admin.programs'))
    depts = Department.query.all()
    progs = Program.query.all()
    return render_template('unidy/admin/programs.html', programs=progs, departments=depts)

@unidy_admin_bp.route('/classes', methods=['GET', 'POST'])
@login_required
def classes():
    if not admin_required():
        return redirect(url_for('auth.login'))
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        prog_id = request.form.get('program_id', type=int)
        level = request.form.get('level', type=int)
        section = request.form.get('section', '').strip() or None
        if name and prog_id and level:
            c = SchoolClass(name=name, program_id=prog_id, level=level, section=section,
                           academic_year='2025-2026')
            db.session.add(c)
            log = AuditLog(user_id=current_user.id, role=current_user.role,
                          action='create_class', target_type='school_class', new_value=name)
            db.session.add(log)
            db.session.commit()
            flash(f'Class "{name}" created.', 'success')
        return redirect(url_for('unidy_admin.classes'))
    progs = Program.query.all()
    classes = SchoolClass.query.order_by(SchoolClass.level).all()
    return render_template('unidy/admin/classes.html', programs=progs, classes=classes)

@unidy_admin_bp.route('/users', methods=['GET', 'POST'])
@login_required
def users():
    if not admin_required():
        return redirect(url_for('auth.login'))
    if request.method == 'POST':
        matricule = request.form.get('matricule', '').strip()
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        role = request.form.get('role', 'student')
        dept = request.form.get('department', '').strip()
        password = request.form.get('password', 'demo1234')
        if matricule and name and email:
            u = User(matricule=matricule, name=name, email=email, role=role, department=dept)
            u.set_password(password)
            db.session.add(u)
            log = AuditLog(user_id=current_user.id, role=current_user.role,
                          action='create_user', target_type='user', new_value=name)
            db.session.add(log)
            db.session.commit()
            flash(f'User "{name}" created ({role}).', 'success')
        return redirect(url_for('unidy_admin.users'))
    role_filter = request.args.get('role', '')
    q = User.query
    if role_filter:
        q = q.filter_by(role=role_filter)
    users = q.order_by(User.role, User.name).all()
    return render_template('unidy/admin/users.html', users=users, role_filter=role_filter)

@unidy_admin_bp.route('/academic-year', methods=['GET', 'POST'])
@login_required
def academic_year():
    if not admin_required():
        return redirect(url_for('auth.login'))
    current_ay = AcademicYear.query.filter_by(is_current=True).first()
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        start = request.form.get('start_date')
        end = request.form.get('end_date')
        if name and start and end:
            ay = AcademicYear(name=name, start_date=start, end_date=end, is_current=True)
            db.session.add(ay)
            db.session.flush()
            s1 = AcademicSemester(academic_year_id=ay.id, name='Semester 1', number=1,
                                 start_date=start, end_date=end, is_current=True)
            s2 = AcademicSemester(academic_year_id=ay.id, name='Semester 2', number=2,
                                 start_date=start, end_date=end)
            db.session.add_all([s1, s2])
            log = AuditLog(user_id=current_user.id, role=current_user.role,
                          action='create_academic_year', target_type='academic_year', new_value=name)
            db.session.add(log)
            db.session.commit()
            flash(f'Academic year "{name}" created with semesters.', 'success')
        return redirect(url_for('unidy_admin.academic_year'))
    years = AcademicYear.query.order_by(AcademicYear.start_date.desc()).all()
    return render_template('unidy/admin/academic_year.html', current_ay=current_ay, years=years)

@unidy_admin_bp.route('/bulk-import', methods=['GET'])
@login_required
def bulk_import():
    if not admin_required():
        return redirect(url_for('auth.login'))
    programs = Program.query.all()
    classes = SchoolClass.query.all()
    current_sem = AcademicSemester.query.filter_by(is_current=True).first()
    from app.models import Course
    courses = Course.query.all()
    return render_template('unidy/admin/bulk_import.html',
                           programs=programs, classes=classes,
                           courses=courses, current_sem=current_sem)

@unidy_admin_bp.route('/bulk-import/preview', methods=['POST'])
@login_required
def bulk_import_preview():
    if not admin_required():
        return redirect(url_for('auth.login'))
    import_type = request.form.get('import_type', '').strip()
    program_id = request.form.get('program_id', type=int)
    class_id = request.form.get('class_id', type=int)
    course_id = request.form.get('course_id', type=int)
    sem_id = request.form.get('semester_id', type=int)
    file = request.files.get('file')
    if not file or file.filename == '':
        flash('Please select a file to upload.', 'danger')
        return redirect(url_for('unidy_admin.bulk_import'))

    from app.services.unidy_import import import_students, import_enrollments, import_grades
    if import_type == 'students':
        result = import_students(file, program_id=program_id, class_id=class_id)
    elif import_type == 'enrollments':
        result = import_enrollments(file, semester_id=sem_id)
    elif import_type == 'grades':
        result = import_grades(file, course_id=course_id, semester_id=sem_id)
    else:
        flash('Invalid import type.', 'danger')
        return redirect(url_for('unidy_admin.bulk_import'))

    if result['errors']:
        for err in result['errors'][:5]:
            flash(err, 'warning')
    flash(f'Import complete: {result["created"]} created, {result["skipped"]} skipped.', 'success')
    return redirect(url_for('unidy_admin.bulk_import'))

@unidy_admin_bp.route('/bulk-import/template/<import_type>')
@login_required
def bulk_import_template(import_type):
    if not admin_required():
        return redirect(url_for('auth.login'))
    import io
    import pandas as pd
    output = io.BytesIO()
    if import_type == 'students':
        df = pd.DataFrame(columns=['matricule', 'name', 'email', 'program', 'department', 'password'])
        df.loc[0] = ['STU001', 'John Doe', 'john@redi.cm', 'HND Software Engineering', 'Computer Science', 'student123']
    elif import_type == 'enrollments':
        df = pd.DataFrame(columns=['matricule', 'course'])
        df.loc[0] = ['STU001', 'Introduction to Programming']
    elif import_type == 'grades':
        df = pd.DataFrame(columns=['matricule', 'ca_score', 'exam_score', 'course'])
        df.loc[0] = ['STU001', 16.5, 14.0, 'Introduction to Programming']
    else:
        flash('Invalid template type.', 'danger')
        return redirect(url_for('unidy_admin.bulk_import'))
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='data')
    output.seek(0)
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     download_name=f'unidy_{import_type}_template.xlsx', as_attachment=True)
