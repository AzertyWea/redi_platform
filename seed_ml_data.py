"""Seed realistic BEng Computer Science Level 4 students (8 semesters) for ML training."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import create_app, db
from app.models import (
    User, StudentProfile, SemesterResult, AttendanceRecord,
    Internship, Certification, Project, Assignment, AssignmentSubmission,
    Quiz, QuizResult, Department, Program, Course, SchoolClass
)
from datetime import date, datetime

random.seed(42)

app = create_app()

with app.app_context():
    dept = Department.query.filter_by(name="Engineering").first()
    if not dept:
        dept = Department(name="Engineering")
        db.session.add(dept)
        db.session.flush()

    prog = Program.query.filter_by(name="BEng Computer Science").first()
    if not prog:
        prog = Program(name="BEng Computer Science", department_id=dept.id)
        db.session.add(prog)
        db.session.flush()

    school_class = SchoolClass.query.filter_by(
        program_id=prog.id, level=4, section="A"
    ).first()
    if not school_class:
        school_class = SchoolClass(
            name="BEng Computer Science - Level 4 (A)",
            program_id=prog.id, level=4, section="A",
            academic_year="2025/2026"
        )
        db.session.add(school_class)
        db.session.flush()

    teacher = User.query.filter_by(role="teacher").first()
    if not teacher:
        teacher = User(
            matricule="T002", name="Dr. Paul Biya",
            email="paul@redi.cm", role="teacher", department="Engineering"
        )
        teacher.set_password("demo1234")
        db.session.add(teacher)
        db.session.flush()

    courses_data = [
        ("CS401", "Advanced Algorithms", 5), ("CS402", "Machine Learning", 5),
        ("CS403", "Software Architecture", 5), ("CS404", "Compilers", 6),
        ("CS405", "Computer Networks", 6), ("CS406", "Operating Systems", 6),
        ("CS407", "Database Systems", 7), ("CS408", "Web Engineering", 7),
        ("CS409", "AI & Expert Systems", 7), ("CS410", "Final Year Project", 8),
        ("CS411", "Professional Ethics", 8), ("CS412", "Cloud Computing", 8),
    ]
    courses = {}
    for code, name, sem in courses_data:
        c = Course.query.filter_by(code=code).first()
        if not c:
            c = Course(name=name, code=code, program_id=prog.id,
                       teacher_id=teacher.id, semester_number=sem)
            db.session.add(c)
            db.session.flush()
        courses[name] = c

    for c in courses.values():
        if school_class not in c.classes:
            c.classes.append(school_class)

    existing = User.query.filter(User.matricule.like("ML%")).count()
    if existing > 0:
        print(f"Found {existing} ML seed students already. Skipping.")
        sys.exit(0)

    students_config = [
        ("ML001", "Alice Tchinda",     "alice@redi.cm",     85, "High", 8, 4),
        ("ML002", "Bob Nkwi",          "bob@redi.cm",       72, "High", 8, 4),
        ("ML003", "Claire Ebongue",    "claire@redi.cm",    68, "Mid",  8, 4),
        ("ML004", "David Mbah",        "david@redi.cm",     55, "Mid",  8, 4),
        ("ML005", "Esther Ngo",        "esther@redi.cm",    91, "High", 8, 4),
        ("ML006", "Frank Nyam",        "frank@redi.cm",     45, "Low",  8, 4),
        ("ML007", "Grace Ekwa",        "grace@redi.cm",     78, "High", 8, 4),
        ("ML008", "Herve Mouna",       "herve@redi.cm",     62, "Mid",  8, 4),
        ("ML009", "Irene Bibi",        "irene@redi.cm",     35, "Low",  8, 4),
        ("ML010", "Jean Mbida",        "jean@redi.cm",      88, "High", 8, 4),
        ("ML011", "Karine Olinga",     "karine@redi.cm",    50, "Low",  8, 4),
        ("ML012", "Leo Essono",        "leo@redi.cm",       74, "High", 8, 4),
    ]

    def gen_semester_scores(eri, perf_tier, sem):
        base = eri / 100.0
        if perf_tier == "High":
            noise = random.uniform(-0.1, 0.05)
            mult = 0.92 + sem * 0.005
        elif perf_tier == "Mid":
            noise = random.uniform(-0.08, 0.12)
            mult = 0.70 + sem * 0.01
        else:
            noise = random.uniform(-0.05, 0.2)
            mult = 0.50 + sem * 0.015
        avg = min(max(base * mult + noise, 0.15), 0.98)
        ca = round(random.uniform(avg - 0.15, avg + 0.10) * 100, 1)
        exam = round(random.uniform(avg - 0.10, avg + 0.15) * 100, 1)
        att = round(random.uniform(avg * 0.8, 1.0) * 100, 1)
        proj = round(random.uniform(avg - 0.1, avg + 0.2) * 100, 1)
        intern = round(random.uniform(0, avg) * 100, 1)
        ca = max(0, min(100, ca))
        exam = max(0, min(100, exam))
        att = max(0, min(100, att))
        proj = max(0, min(100, proj))
        intern = max(0, min(100, intern))
        overall = round(ca * 0.3 + exam * 0.5 + att * 0.05 + proj * 0.1 + intern * 0.05, 1)
        return ca, exam, att, proj, intern, overall

    created = 0
    for mat, name, email, eri, tier, sem, dur in students_config:
        user = User(matricule=mat, name=name, email=email,
                    role="student", department="Engineering")
        user.set_password("demo1234")
        db.session.add(user)
        db.session.flush()

        profile = StudentProfile(
            user_id=user.id, program="BEng Computer Science",
            current_semester=sem, duration_years=dur,
            eri_score=float(eri), class_group_id=school_class.id,
            skills="Python, Java, SQL, Machine Learning, Data Structures"
        )
        db.session.add(profile)
        db.session.flush()

        for s in range(1, 9):
            ca, exam, att, proj, intern, overall = gen_semester_scores(eri, tier, s)
            sr = SemesterResult(
                student_id=profile.id, semester_number=s,
                ca_score=ca, exam_score=exam, attendance=att,
                project_score=proj, internship_score=intern,
                overall_score=overall
            )
            db.session.add(sr)

        for _ in range(14):
            ar = AttendanceRecord(
                student_id=profile.id, teacher_id=teacher.id,
                course="CS401", status="present" if random.random() < (0.95 if tier == "High" else 0.80 if tier == "Mid" else 0.65) else "absent"
            )
            db.session.add(ar)

        if tier == "High":
            for comp in ["Google", "Microsoft", "TechLab"]:
                db.session.add(Internship(
                    student_id=profile.id, company_name=comp,
                    role_title="Software Engineer Intern",
                    start_date=date(2024, 6, 1), end_date=date(2024, 8, 31),
                    is_verified=True
                ))
            for cert, issuer in [("AWS Certified", "Amazon"), ("Python Pro", "Python Institute"), ("ML Specialist", "DeepLearning.AI")]:
                db.session.add(Certification(
                    student_id=profile.id, title=cert, issuer=issuer,
                    date_obtained=date(2025, 1, 15), is_verified=True
                ))
            for ptitle in ["AI Chatbot", "E-commerce Platform", "Network Analyzer"]:
                db.session.add(Project(
                    student_id=profile.id, title=ptitle,
                    description=f"A {ptitle} project built with modern tech stack.",
                    technologies="Python, React, PostgreSQL", project_url=f"https://github.com/{mat}/{ptitle.lower().replace(' ','-')}"
                ))
        elif tier == "Mid":
            db.session.add(Internship(student_id=profile.id, company_name="Local Startup", role_title="Dev Intern", start_date=date(2024, 6, 1), end_date=date(2024, 8, 31), is_verified=True))
            db.session.add(Certification(student_id=profile.id, title="Python Basics", issuer="Coursera", date_obtained=date(2024, 5, 1), is_verified=True))
            db.session.add(Project(student_id=profile.id, title="Portfolio Website", description="Personal portfolio", technologies="HTML, CSS, JS", project_url=f"https://github.com/{mat}/portfolio"))
        else:
            db.session.add(Certification(student_id=profile.id, title="Intro to Programming", issuer="Udemy", date_obtained=date(2024, 3, 1), is_verified=True))

        assign = Assignment.query.filter_by(course="CS401").first()
        if not assign:
            assign = Assignment(teacher_id=teacher.id, course="CS401",
                                title="ML Assignment", description="Build a classifier",
                                max_score=20)
            db.session.add(assign)
            db.session.flush()

        assign_score = random.uniform(12, 20) if tier == "High" else random.uniform(8, 16) if tier == "Mid" else random.uniform(4, 12)
        db.session.add(AssignmentSubmission(
            assignment_id=assign.id, student_id=profile.id,
            filename=f"{mat}_assignment.pdf", score=assign_score
        ))

        quiz = Quiz.query.filter_by(course="CS401").first()
        if not quiz:
            quiz = Quiz(teacher_id=teacher.id, course="CS401",
                        title="ML Quiz 1")
            db.session.add(quiz)
            db.session.flush()
        qscore = random.uniform(14, 20) if tier == "High" else random.uniform(8, 16) if tier == "Mid" else random.uniform(4, 12)
        db.session.add(QuizResult(
            quiz_id=quiz.id, student_id=profile.id,
            score=qscore, max_score=20
        ))

        created += 1

    db.session.commit()
    print(f"Created {created} BEng CS Level 4 students with 8 semesters each.")
