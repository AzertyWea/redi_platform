import sys
sys.path.insert(0, ".")
from app import create_app, db
from app.models import Department, Program, Course, User
from werkzeug.security import generate_password_hash
import random

app = create_app()
app.app_context().push()

first_names = ["Amina","Kevin","Pascal","Fatima","Jean","Marie","Eric","Sandra","Paul","Grace",
    "Boris","Christelle","Didier","Esther","Franck","Helene","Igor","Joelle","Karl","Laura"]
last_names = ["Kenfack","Mbarga","Nguemo","Dipende","Fouda","Nkomo","Biya","Atangana","Elong",
    "Manga","Onana","Essono","Mba","Nkoa","Tabi","Ngono"]

departments = Department.query.all()
if not departments:
    print("ERROR: run seed_iuc.py first")
    sys.exit(1)

teacher_counter = 2
teachers_by_dept = {}
for dept in departments:
    dept_teachers = []
    for i in range(3):
        mat = f"T{str(teacher_counter).zfill(3)}"
        teacher_counter += 1
        existing = User.query.filter_by(matricule=mat).first()
        if existing:
            dept_teachers.append(existing)
            continue
        t = User(matricule=mat, name=f"Dr. {random.choice(last_names)} {random.choice(first_names)}",
                 email=f"{mat.lower()}@iuc.edu", role="teacher", department=dept.name,
                 password_hash=generate_password_hash("demo1234"))
        db.session.add(t)
        db.session.flush()
        dept_teachers.append(t)
    teachers_by_dept[dept.id] = dept_teachers
db.session.commit()
print(f"Teachers ready: {sum(len(v) for v in teachers_by_dept.values())} total")

templates = ["Fundamentals","Practicum","Professional Skills","Research Methods","Advanced Topics","Capstone Project"]
courses_created = 0
for dept in departments:
    dept_teachers = teachers_by_dept[dept.id]
    programs = Program.query.filter_by(department_id=dept.id).all()
    t_idx = 0
    for prog in programs:
        prefix = "".join([w[0] for w in prog.name.split()])[:4].upper()
        for level in range(1, 4):
            for slot in range(2):
                semester_number = (level - 1) * 2 + slot + 1
                for idx in range(2):
                    title = f"{templates[(semester_number + idx) % len(templates)]} - {prog.name}"
                    code = f"{prefix}{semester_number}{idx}"
                    existing = Course.query.filter_by(code=code, program_id=prog.id).first()
                    if existing:
                        continue
                    teacher = dept_teachers[t_idx % len(dept_teachers)]
                    t_idx += 1
                    c = Course(name=title, code=code, program_id=prog.id,
                               teacher_id=teacher.id, semester_number=semester_number)
                    db.session.add(c)
                    courses_created += 1
db.session.commit()
print(f"Courses created: {courses_created}")
print("=== STRUCTURE SEED COMPLETE ===")
