import sys
sys.path.insert(0, ".")
from app import create_app, db
from app.models import *
from werkzeug.security import generate_password_hash
from datetime import date, datetime, time
import random

app = create_app()
app.app_context().push()

# --- CAMEROONIAN NAMES ---
first_names = ["Amina","Kevin","Pascal","Fatima","Jean","Marie","Eric","Sandra","Paul","Grace",
    "Boris","Christelle","Didier","Esther","Franck","Helene","Igor","Joelle","Karl","Laura",
    "Marc","Nadia","Oscar","Patricia","Quentin","Rachel","Samuel","Therese","Ulrich","Valerie",
    "Willy","Xanthe","Yannick","Zoe","Andre","Beatrice","Cedric","Diane","Emmanuel","Florence",
    "Georges","Henriette","Ivan","Josephine","Koffi","Laure","Michel","Nadege","Olivier","Prisca"]

last_names = ["Kenfack","Mbarga","Nguemo","Dipende","Fouda","Nkomo","Biya","Atangana","Elong",
    "Manga","Onana","Essono","Mba","Nkoa","Tabi","Ngono","Abena","Belinga","Chouaibou","Djouda",
    "Ekambi","Fopa","Guimdo","Hamidou","Itoua","Kameni","Lekene","Moukam","Nana","Owona",
    "Penda","Quentin","Ringo","Samba","Talla","Umba","Vega","Wamba","Yemdji","Zanga"]

schools = Department.query.all()
programs = Program.query.all()
courses = Course.query.all()

if not schools:
    print("ERROR: Run the IUC seed script first (seed_iuc.py)")
    sys.exit(1)

print(f"Found {len(schools)} schools, {len(programs)} programs, {len(courses)} courses")

# --- CREATE TEACHERS (one per school) ---
teachers_created = []
for i, school in enumerate(schools[:6]):
    mat = f"T{str(i+2).zfill(3)}"
    if not User.query.filter_by(matricule=mat).first():
        t = User(matricule=mat, name=f"Dr. {random.choice(last_names)} {random.choice(first_names)}",
            email=f"{mat.lower()}@iuc.edu", role="teacher",
            department=school.name, password_hash=generate_password_hash("demo1234"))
        db.session.add(t)
        teachers_created.append(t)
db.session.flush()

teachers = User.query.filter_by(role="teacher").all()

for i, course in enumerate(courses):
    if not course.teacher_id and teachers:
        course.teacher_id = teachers[i % len(teachers)].id
db.session.flush()

students_created = 0
for i in range(100):
    mat = f"S{str(i+10).zfill(3)}"
    if User.query.filter_by(matricule=mat).first():
        continue
    prog = random.choice(programs)
    school = prog.department
    fn = random.choice(first_names)
    ln = random.choice(last_names)
    u = User(matricule=mat, name=f"{fn} {ln}", email=f"{mat.lower()}@iuc.edu",
        role="student", department=school.name,
        password_hash=generate_password_hash("demo1234"))
    db.session.add(u)
    db.session.flush()

    eri = round(random.uniform(35, 96), 1)
    p = StudentProfile(user_id=u.id, eri_score=eri, program=prog.name,
        filiere=prog.name, current_semester=random.randint(1,4),
        bio=f"Student at IUC Douala in {prog.name}. Passionate about my field and eager to grow professionally.",
        skills=random.choice(["Python,Excel,Communication","Java,SQL,Teamwork",
            "Marketing,PowerPoint,English","AutoCAD,Project Management,French",
            "Networking,Linux,Cybersecurity","Accounting,SAP,Analysis"]),
        linkedin_url="")
    db.session.add(p)
    db.session.flush()

    for sem in range(1, random.randint(3,5)):
        ca = round(random.uniform(8, 18), 1)
        ex = round(random.uniform(8, 18), 1)
        att = round(random.uniform(55, 98), 1)
        proj = round(random.uniform(10, 19), 1)
        overall = round((ca*0.3 + ex*0.4 + att*0.15 + proj*0.15), 1)
        r = SemesterResult(student_id=p.id, semester_number=sem,
            ca_score=ca, exam_score=ex, attendance=att,
            project_score=proj, overall_score=overall)
        db.session.add(r)

    for _ in range(random.randint(10,30)):
        status = "present" if random.random() > 0.2 else "absent"
        a = AttendanceRecord(student_id=p.id, teacher_id=random.choice(teachers).id,
            course=prog.name, status=status)
        db.session.add(a)

    companies = ["Orange Cameroun","MTN Cameroon","Afriland First Bank",
        "Bollore Africa Logistics","Total Energies Cameroun","Societe Generale",
        "Camtel","CAMAIR-Co","SCDP","Groupe La Falaise","Tractafric Motors","CBC Bank"]
    for _ in range(random.randint(0,2)):
        start = date(2024, random.randint(1,6), 1)
        end = date(2025, random.randint(1,6), 28)
        intern = Internship(student_id=p.id, company_name=random.choice(companies),
            role_title=random.choice(["IT Intern","Finance Intern","Marketing Intern",
                "Engineering Intern","Network Intern","Accounting Intern"]),
            start_date=start, end_date=end,
            description="Gained practical experience in a professional environment.")
        db.session.add(intern)

    certs_list = [("Google Digital Garage","Google"),("Cisco CCNA","Cisco"),
        ("Microsoft Azure","Microsoft"),("AWS Cloud Practitioner","Amazon"),
        ("Coursera Python","Coursera"),("HubSpot Marketing","HubSpot")]
    for cert_title, issuer in random.sample(certs_list, random.randint(0,3)):
        c = Certification(student_id=p.id, title=cert_title, issuer=issuer,
            date_obtained=date(2024, random.randint(1,12), 1))
        db.session.add(c)

    projects_list = [("Student Management System","Python,Flask,SQLite"),
        ("E-commerce Website","HTML,CSS,JavaScript"),("Data Analysis Dashboard","Python,Pandas,Plotly"),
        ("Mobile Banking App","Java,Android"),("Network Security Tool","Python,Scapy"),
        ("Inventory Management","PHP,MySQL")]
    for ptitle, ptech in random.sample(projects_list, random.randint(0,3)):
        pr = Project(student_id=p.id, title=ptitle, technologies=ptech,
            description=f"Developed {ptitle} as part of academic and personal development.",
            course_related=prog.name)
        db.session.add(pr)

    notif_msgs = [("ERI Updated","Your ERI score has been recalculated."),
        ("New Assignment","A new assignment has been posted."),
        ("Exam Results","Your semester results are now available."),
        ("Schedule Update","Your timetable has been updated.")]
    for ntitle, nmsg in random.sample(notif_msgs, random.randint(1,3)):
        db.session.add(Notification(user_id=u.id, title=ntitle, message=nmsg))

    students_created += 1

db.session.commit()
print(f"Seeded {students_created} students with full data")

employer_companies = ["Orange Cameroun HR","MTN Cameroon Recruitment","Afriland First Bank HR",
    "Bollore Africa Logistics","Total Energies Cameroun"]
emp_created = 0
for i, company in enumerate(employer_companies):
    mat = f"E{str(i+2).zfill(3)}"
    if not User.query.filter_by(matricule=mat).first():
        e = User(matricule=mat, name=company, email=f"{mat.lower()}@corp.cm",
            role="employer", department="Corporate",
            password_hash=generate_password_hash("demo1234"))
        db.session.add(e)
        emp_created += 1
db.session.commit()
print(f"Seeded {emp_created} employers")

from app.services.eri_engine import calculate_eri
students_all = StudentProfile.query.all()
for s in students_all:
    s.eri_score = calculate_eri(s)
db.session.commit()
print(f"ERI recalculated for {len(students_all)} students")
print("=== SEED COMPLETE ===")
