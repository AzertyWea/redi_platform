import io
import pandas as pd
from werkzeug.security import generate_password_hash
from app import db
from app.models import (User, StudentProfile, Program, SchoolClass,
                        Enrollment, CourseGrade, AcademicSemester, AuditLog)


def import_students(file, program_id=None, class_id=None):
    filename = file.filename.lower() if hasattr(file, 'filename') and file.filename else ''
    if filename.endswith('.csv'):
        df = pd.read_csv(file)
    elif filename.endswith(('.xls', '.xlsx')):
        df = pd.read_excel(file, engine='openpyxl')
    else:
        return {'created': 0, 'skipped': 0, 'errors': ['Unsupported format. Use CSV or XLSX.']}
    if df.empty:
        return {'created': 0, 'skipped': 0, 'errors': ['File is empty.']}

    alias = {}
    for c in df.columns:
        cl = c.strip().lower()
        if cl in ('matricule', 'id', 'matr', 'student_id'):
            alias[c] = 'matricule'
        elif cl in ('name', 'full_name', 'nom', 'student_name'):
            alias[c] = 'name'
        elif cl in ('email', 'mail'):
            alias[c] = 'email'
        elif cl in ('department', 'dept', 'departement', 'filiere'):
            alias[c] = 'department'
        elif cl in ('program', 'programme'):
            alias[c] = 'program'
        elif cl in ('password', 'mot_de_passe'):
            alias[c] = 'password'
        elif cl in ('class', 'class_name', 'classe'):
            alias[c] = 'class_name'
        else:
            alias[c] = c
    df = df.rename(columns=alias)
    df = df.loc[:, ~df.columns.duplicated()]

    required = ['matricule', 'name']
    missing = [c for c in required if c not in df.columns]
    if missing:
        return {'created': 0, 'skipped': 0, 'errors': [f'Missing columns: {", ".join(missing)}']}

    created = 0
    skipped = 0
    errors = []
    prog = Program.query.get(program_id) if program_id else None
    cls = SchoolClass.query.get(class_id) if class_id else None

    for idx, row in df.iterrows():
        try:
            mat = str(row['matricule']).strip()
            name = str(row['name']).strip()
            if not mat or not name:
                skipped += 1
                continue
            existing = User.query.filter_by(matricule=mat).first()
            if existing:
                skipped += 1
                continue

            email = str(row.get('email', '')).strip() or f"{mat.lower()}@redi.local"
            dept = str(row.get('department', '')).strip() or (prog.department.name if prog and prog.department else '')
            prog_name = str(row.get('program', '')).strip() or (prog.name if prog else '')
            pwd = str(row.get('password', 'student123')).strip()

            user = User(matricule=mat, name=name, email=email,
                       role='student', department=dept)
            user.set_password(pwd)
            db.session.add(user)
            db.session.flush()

            profile = StudentProfile(user_id=user.id, eri_score=0.0,
                                    program=prog_name, filiere=prog_name,
                                    class_group_id=cls.id if cls else None)
            db.session.add(profile)
            created += 1
        except Exception as e:
            errors.append(f'Row {idx + 2}: {str(e)}')
            skipped += 1

    db.session.commit()
    log = AuditLog(user_id=None, role='admin',
                  action='unidy_bulk_import_students', target_type='student',
                  new_value=f'{created} created, {skipped} skipped')
    db.session.add(log)
    db.session.commit()
    return {'created': created, 'skipped': skipped, 'errors': errors}


def import_enrollments(file, semester_id=None):
    filename = file.filename.lower() if hasattr(file, 'filename') and file.filename else ''
    if filename.endswith('.csv'):
        df = pd.read_csv(file)
    elif filename.endswith(('.xls', '.xlsx')):
        df = pd.read_excel(file, engine='openpyxl')
    else:
        return {'created': 0, 'skipped': 0, 'errors': ['Unsupported format.']}

    alias = {}
    for c in df.columns:
        cl = c.strip().lower()
        if cl in ('matricule', 'student_id', 'student'):
            alias[c] = 'matricule'
        elif cl in ('course', 'course_name', 'course_id'):
            alias[c] = 'course'
        else:
            alias[c] = c
    df = df.rename(columns=alias)
    df = df.loc[:, ~df.columns.duplicated()]

    required = ['matricule', 'course']
    missing = [c for c in required if c not in df.columns]
    if missing:
        return {'created': 0, 'skipped': 0, 'errors': [f'Missing columns: {", ".join(missing)}']}

    created = 0
    skipped = 0
    errors = []
    from app.models import Course

    for idx, row in df.iterrows():
        try:
            mat = str(row['matricule']).strip()
            course_name = str(row['course']).strip()
            user = User.query.filter_by(matricule=mat).first()
            if not user:
                skipped += 1
                continue
            profile = StudentProfile.query.filter_by(user_id=user.id).first()
            if not profile:
                skipped += 1
                continue
            course = Course.query.filter(Course.name.ilike(course_name)).first()
            if not course:
                course = Course.query.filter(Course.code.ilike(course_name)).first()
            if not course:
                skipped += 1
                errors.append(f'Row {idx + 2}: Course "{course_name}" not found')
                continue
            existing = Enrollment.query.filter_by(
                student_id=profile.id, course_id=course.id,
                semester_id=semester_id).first()
            if existing:
                skipped += 1
                continue
            e = Enrollment(student_id=profile.id, course_id=course.id,
                          semester_id=semester_id, status='active')
            db.session.add(e)
            created += 1
        except Exception as e2:
            errors.append(f'Row {idx + 2}: {str(e2)}')
            skipped += 1

    db.session.commit()
    return {'created': created, 'skipped': skipped, 'errors': errors}


def import_grades(file, course_id=None, semester_id=None):
    filename = file.filename.lower() if hasattr(file, 'filename') and file.filename else ''
    if filename.endswith('.csv'):
        df = pd.read_csv(file)
    elif filename.endswith(('.xls', '.xlsx')):
        df = pd.read_excel(file, engine='openpyxl')
    else:
        return {'created': 0, 'skipped': 0, 'errors': ['Unsupported format.']}

    alias = {}
    for c in df.columns:
        cl = c.strip().lower()
        if cl in ('matricule', 'student_id', 'student'):
            alias[c] = 'matricule'
        elif cl in ('ca_score', 'ca', 'cc', 'continuous_assessment'):
            alias[c] = 'ca_score'
        elif cl in ('exam_score', 'exam', 'examen'):
            alias[c] = 'exam_score'
        elif cl in ('course', 'course_name', 'course_id'):
            alias[c] = 'course'
        else:
            alias[c] = c
    df = df.rename(columns=alias)
    df = df.loc[:, ~df.columns.duplicated()]

    required = ['matricule', 'ca_score', 'exam_score']
    missing = [c for c in required if c not in df.columns]
    if missing:
        return {'created': 0, 'skipped': 0, 'errors': [f'Missing columns: {", ".join(missing)}']}

    created = 0
    skipped = 0
    errors = []
    from app.models import Course

    for idx, row in df.iterrows():
        try:
            mat = str(row['matricule']).strip()
            ca = float(row.get('ca_score', 0) or 0)
            exam = float(row.get('exam_score', 0) or 0)
            total = round(ca * 0.4 + exam * 0.6, 1)
            if total >= 70: gl = 'A'
            elif total >= 60: gl = 'B'
            elif total >= 50: gl = 'C'
            elif total >= 40: gl = 'D'
            else: gl = 'F'
            gp = {'A': 4.0, 'B': 3.0, 'C': 2.0, 'D': 1.0, 'F': 0.0}.get(gl, 0)

            user = User.query.filter_by(matricule=mat).first()
            if not user:
                skipped += 1
                continue
            profile = StudentProfile.query.filter_by(user_id=user.id).first()
            if not profile:
                skipped += 1
                continue

            cid = course_id
            if 'course' in row and not cid:
                cname = str(row['course']).strip()
                course = Course.query.filter(Course.name.ilike(cname)).first()
                if course:
                    cid = course.id
            if not cid:
                skipped += 1
                continue

            existing = CourseGrade.query.filter_by(
                student_id=profile.id, course_id=cid,
                semester_id=semester_id).first()
            if existing:
                existing.ca_score = ca
                existing.exam_score = exam
                existing.total_score = total
                existing.grade_letter = gl
                existing.grade_points = gp
                existing.status = 'graded'
            else:
                g = CourseGrade(student_id=profile.id, course_id=cid,
                               semester_id=semester_id,
                               ca_score=ca, exam_score=exam,
                               total_score=total, grade_letter=gl,
                               grade_points=gp, credits=3,
                               status='graded')
                db.session.add(g)
            created += 1
        except Exception as e3:
            errors.append(f'Row {idx + 2}: {str(e3)}')
            skipped += 1

    db.session.commit()
    return {'created': created, 'skipped': skipped, 'errors': errors}
