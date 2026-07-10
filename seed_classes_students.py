import sys, random
sys.path.insert(0, ".")
from app import create_app, db
from app.models import (Department, Program, Course, SchoolClass, User, StudentProfile,
    SemesterResult, AttendanceRecord, Internship, Certification, Project, Notification)
from werkzeug.security import generate_password_hash
from datetime import date

app = create_app()
app.app_context().push()

first_names = ["Amina","Kevin","Pascal","Fatima","Jean","Marie","Eric","Sandra","Paul","Grace",
    "Boris","Christelle","Didier","Esther","Franck","Helene","Igor","Joelle","Karl","Laura",
    "Marc","Nadia","Oscar","Patricia","Quentin","Rachel","Samuel","Therese","Ulrich","Valerie",
    "Willy","Xanthe","Yannick","Zoe","Andre","Beatrice","Cedric","Diane","Emmanuel","Florence"]
last_names = ["Kenfack","Mbarga","Nguemo","Dipende","Fouda","Nkomo","Biya","Atangana","Elong",
    "Manga","Onana","Essono","Mba","Nkoa","Tabi","Ngono","Abena","Belinga","Chouaibou","Djouda"]

programs = Program.query.all()
if not programs:
    print("ERROR: run seed_iuc.py and seed_structure.py first")
    sys.exit(1)

# --- 1. CREATE CLASSES (one per program x level) ---
classes_created = 0
for prog in programs:
    for level in range(1, 4):
        existing = SchoolClass.query.filter_by(program_id=prog.id, level=level, section="A").first()
        if existing:
            continue
        c = SchoolClass(name=f"{prog.name} - Level {level} (A)", department_id=prog.department_id,
                         program_id=prog.id, level=level, section="A", academic_year="2026-2027")
        db.session.add(c)
        classes_created += 1
db.session.commit()
print(f"Classes created: {classes_created}")

# --- 2. LINK COURSES TO THEIR MATCHING CLASS ---
links_created = 0
courses = Course.query.all()
for course in courses:
    level = (course.semester_number + 1) // 2 if course.semester_number else 1
    cls = SchoolClass.query.filter_by(program_id=course.program_id, level=level, section="A").first()
    if cls and cls not in course.classes:
        course.classes.append(cls)
        links_created += 1
db.session.commit()
print(f"Course-class links created: {links_created}")

# --- 3. CREATE STUDENTS, ONE COHORT PER CLASS ---
classes = SchoolClass.query.all()
mat_counter = 10
students_created = 0
companies = ["Orange Cameroun","MTN Cameroon","Afriland First Bank","Bollore Africa Logistics",
    "Total Energies Cameroun","Societe Generale","Camtel","CAMAIR-Co","SCDP","Groupe La Falaise",
    "Tractafric Motors","CBC Bank"]
certs_list = [("Google Digital Garage","Google"),("Cisco CCNA","Cisco"),("Microsoft Azure","Microsoft"),
    ("AWS Cloud Practitioner","Amazon"),("Coursera Python","Coursera"),("HubSpot Marketing","HubSpot")]
projects_list = [("Student Management System","Python,Flask,SQLite"),("E-commerce Website","HTML,CSS,JavaScript"),
    ("Data Analysis Dashboard","Python,Pandas,Plotly"),("Mobile Banking App","Java,Android"),
    ("Network Security Tool","Python,Scapy"),("Inventory Management","PHP,MySQL")]
skills_pool = ["Python,Excel,Communication","Java,SQL,Teamwork","Marketing,PowerPoint,English",
    "AutoCAD,Project Management,French","Networking,Linux,Cybersecurity","Accounting,SAP,Analysis"]

for cls in classes:
    class_courses = cls.courses
    class_size = random.randint(8, 16)
    for _ in range(class_size):
        mat = f"S{str(mat_counter).zfill(4)}"
        mat_counter += 1
        fn = random.choice(first_names)
        ln = random.choice(last_names)
        u = User(matricule=mat, name=f"{fn} {ln}", email=f"{mat.lower()}@iuc.edu",
                 role="student", department=cls.department.name,
                 password_hash=generate_password_hash("demo1234"))
        db.session.add(u)
        db.session.flush()

        semester_in_level = random.choice([2*cls.level - 1, 2*cls.level])
        eri = round(random.uniform(35, 96), 1)
        p = StudentProfile(user_id=u.id, eri_score=eri, program=cls.program.name,
            filiere=cls.program.name, current_semester=semester_in_level, class_group_id=cls.id,
            bio=f"Student at IUC Douala in {cls.program.name}. Motivated and growth-oriented.",
            skills=random.choice(skills_pool), linkedin_url="")
        db.session.add(p)
        db.session.flush()

        for sem in range(1, semester_in_level + 1):
            ca = round(random.uniform(8, 18), 1)
            ex = round(random.uniform(8, 18), 1)
            att = round(random.uniform(55, 98), 1)
            proj = round(random.uniform(10, 19), 1)
            overall = round((ca*0.3 + ex*0.4 + att*0.15 + proj*0.15), 1)
            db.session.add(SemesterResult(student_id=p.id, semester_number=sem, ca_score=ca,
                exam_score=ex, attendance=att, project_score=proj, overall_score=overall))

        # attendance tied to REAL courses of this class
        for course in class_courses:
            for _ in range(random.randint(4, 10)):
                status = "present" if random.random() > 0.18 else "absent"
                db.session.add(AttendanceRecord(student_id=p.id, teacher_id=course.teacher_id,
                    course=course.name, course_id=course.id, class_group_id=cls.id, status=status))

        for _ in range(random.randint(0, 2)):
            start = date(2024, random.randint(1,6), 1)
            end = date(2025, random.randint(1,6), 28)
            db.session.add(Internship(student_id=p.id, company_name=random.choice(companies),
                role_title=random.choice(["IT Intern","Finance Intern","Marketing Intern",
                    "Engineering Intern","Network Intern","Accounting Intern"]),
                start_date=start, end_date=end,
                description="Gained practical experience in a professional environment."))

        for cert_title, issuer in random.sample(certs_list, random.randint(0,3)):
            db.session.add(Certification(student_id=p.id, title=cert_title, issuer=issuer,
                date_obtained=date(2024, random.randint(1,12), 1)))

        for ptitle, ptech in random.sample(projects_list, random.randint(0,3)):
            db.session.add(Project(student_id=p.id, title=ptitle, technologies=ptech,
                description=f"Developed {ptitle} as part of academic and personal development.",
                course_related=cls.program.name))

        notif_msgs = [("ERI Updated","Your ERI score has been recalculated."),
            ("New Assignment","A new assignment has been posted."),
            ("Exam Results","Your semester results are now available."),
            ("Schedule Update","Your timetable has been updated.")]
        for ntitle, nmsg in random.sample(notif_msgs, random.randint(1,3)):
            db.session.add(Notification(recipient_id=u.id, recipient_role="student", type="announcement", title=ntitle, body=nmsg))

        students_created += 1
    db.session.commit()

print(f"Students created: {students_created}")

# --- 4. EMPLOYERS ---
employer_companies = ["Orange Cameroun HR","MTN Cameroon Recruitment","Afriland First Bank HR",
    "Bollore Africa Logistics","Total Energies Cameroun"]
emp_created = 0
for i, company in enumerate(employer_companies):
    mat = f"E{str(i+2).zfill(3)}"
    if not User.query.filter_by(matricule=mat).first():
        db.session.add(User(matricule=mat, name=company, email=f"{mat.lower()}@corp.cm",
            role="employer", department="Corporate", password_hash=generate_password_hash("demo1234")))
        emp_created += 1
db.session.commit()
print(f"Employers created: {emp_created}")

# --- 5. ADMIN ---
if not User.query.filter_by(matricule="A001").first():
    db.session.add(User(matricule="A001", name="System Administrator", email="admin@iuc.edu",
        role="admin", department="Administration", password_hash=generate_password_hash("demo1234")))
    db.session.commit()
    print("Admin account created (A001 / demo1234)")

# --- 6. RECALCULATE ERI ---
from app.services.eri_engine import calculate_eri
students_all = StudentProfile.query.all()
for s in students_all:
    s.eri_score = calculate_eri(s)
db.session.commit()
print(f"ERI recalculated for {len(students_all)} students")
print("=== FULL RESEED COMPLETE ===")
