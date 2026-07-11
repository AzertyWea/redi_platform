"""Generate realistic synthetic student data with varied ERI scores (15-98)."""
import sys, os, random
import math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import create_app, db
from app.models import (
    User, StudentProfile, SemesterResult, AttendanceRecord,
    Internship, Certification, Project, Assignment, AssignmentSubmission,
    Quiz, QuizResult, Department, Program, Course, SchoolClass,
    TeacherObservation, EmployerFeedback, EmployerFeedback, Notification
)
from datetime import date, datetime, timedelta

random.seed(123)

app = create_app()

with app.app_context():
    existing_students = User.query.filter(User.matricule.like("SYNTH%")).count()
    if existing_students > 200:
        print(f"Found {existing_students} synthetic students already. Skipping.")
        sys.exit(0)

    admin = User.query.filter_by(role="admin").first()
    if not admin:
        admin = User(matricule="ADMIN01", name="Admin REDI", email="admin@redi.cm", role="admin")
        admin.set_password("admin1234")
        db.session.add(admin)

    departments_data = {
        "Engineering": ["BEng Computer Science", "BEng Software Engineering", "BEng Data Science"],
        "Business": ["BBA Management", "BBA Finance", "BBA Marketing"],
        "Health Sciences": ["BSc Nursing", "BSc Public Health", "BSc Medical Lab"],
        "Arts & Humanities": ["BA English", "BA Communications", "BA Graphic Design"],
    }

    dept_objs = {}
    prog_objs = {}
    for dname, progs in departments_data.items():
        dept = Department.query.filter_by(name=dname).first()
        if not dept:
            dept = Department(name=dname)
            db.session.add(dept)
            db.session.flush()
        dept_objs[dname] = dept
        for pname in progs:
            prog = Program.query.filter_by(name=pname, department_id=dept.id).first()
            if not prog:
                prog = Program(name=pname, department_id=dept.id)
                db.session.add(prog)
                db.session.flush()
            prog_objs[pname] = prog

    teacher = User.query.filter_by(role="teacher").first()
    if not teacher:
        teacher = User(matricule="T001", name="Dr. Teacher", email="teacher@redi.cm", role="teacher", department="Engineering")
        teacher.set_password("demo1234")
        db.session.add(teacher)
        db.session.flush()

    classes_created = {}
    for pname in prog_objs:
        for level in range(1, 5):
            for section in ["A", "B"]:
                existing = SchoolClass.query.filter_by(
                    program_id=prog_objs[pname].id, level=level, section=section
                ).first()
                if not existing:
                    existing = SchoolClass(
                        name=f"{pname} - Level {level} ({section})",
                        program_id=prog_objs[pname].id, level=level, section=section,
                        academic_year="2025/2026"
                    )
                    db.session.add(existing)
                    db.session.flush()
                classes_created[(pname, level, section)] = existing

    semester_names = ["Algorithms & Data Structures", "Calculus & Linear Algebra", "Programming Paradigms", 
                      "Database Systems", "Software Engineering", "Computer Networks",
                      "Machine Learning", "Capstone Project"]
    course_names = {
        "Sem 1": ["CS101", "CS102", "CS103", "MA101"],
        "Sem 2": ["CS201", "CS202", "CS203", "MA201"],
        "Sem 3": ["CS301", "CS302", "CS303", "CS304"],
        "Sem 4": ["CS401", "CS402", "CS403", "CS404"],
        "Sem 5": ["CS501", "CS502", "CS503", "CS504"],
        "Sem 6": ["CS601", "CS602", "CS603", "CS604"],
        "Sem 7": ["CS701", "CS702", "CS703", "CS704"],
        "Sem 8": ["CS801", "CS802", "CS803", "CS804"],
    }

    all_courses = {}
    for sem_key, codes in course_names.items():
        for code in codes:
            c = Course.query.filter_by(code=code).first()
            if not c:
                c = Course(name=f"Course {code}", code=code, program_id=prog_objs["BEng Computer Science"].id,
                           teacher_id=teacher.id, semester_number=int(sem_key.split()[1]))
                db.session.add(c)
                db.session.flush()
            all_courses[code] = c

    configs = []
    for pname in prog_objs:
        n_students = random.randint(10, 18)
        for i in range(n_students):
            eri_target = random.choice([random.randint(15, 40), random.randint(41, 69), random.randint(70, 98)])
            configs.append((pname, eri_target))

    def perf_tier(eri):
        if eri >= 70: return "High"
        if eri >= 40: return "Mid"
        return "Low"

    def gen_academic_scores(eri, sem, total_sems):
        base = eri / 100.0
        tier = perf_tier(eri)
        if tier == "High":
            variance = random.uniform(-0.08, 0.05)
            trajectory = 0.92 + (sem / total_sems) * 0.08
        elif tier == "Mid":
            variance = random.uniform(-0.10, 0.12)
            trajectory = 0.65 + (sem / total_sems) * 0.12
        else:
            variance = random.uniform(-0.08, 0.20)
            trajectory = 0.35 + (sem / total_sems) * 0.15
            trajectory = min(trajectory, 0.65)

        avg = max(0.10, min(0.98, base * trajectory + variance))
        ca = round(random.uniform(max(0, avg - 0.20), min(1.0, avg + 0.10)) * 100, 1)
        exam = round(random.uniform(max(0, avg - 0.15), min(1.0, avg + 0.15)) * 100, 1)
        att = round(random.uniform(max(0, avg * 0.7), 1.0) * 100, 1)
        proj = round(random.uniform(max(0, avg - 0.15), min(1.0, avg + 0.20)) * 100, 1)
        intern = round(random.uniform(0, min(1.0, avg + 0.10)) * 100, 1)
        overall = round(ca * 0.30 + exam * 0.50 + att * 0.05 + proj * 0.10 + intern * 0.05, 1)
        return min(100, max(0, ca)), min(100, max(0, exam)), min(100, max(0, att)), \
               min(100, max(0, proj)), min(100, max(0, intern)), min(100, max(0, overall))

    created = 0
    mat_counter = 1000
    for pname, eri in configs:
        tier = perf_tier(eri)
        total_sems = random.randint(4, 8)
        cur_sem = total_sems
        dur = math.ceil(total_sems / 2)

        mat_counter += 1
        mat = f"SYNTH{mat_counter:04d}"
        name = f"Student {mat_counter}"
        email = f"student{mat_counter}@redi.cm"

        user = User(matricule=mat, name=name, email=email, role="student", department=pname.split()[-1])
        user.set_password("demo1234")
        db.session.add(user)
        db.session.flush()

        n_skills = random.randint(2, 8)
        skill_pool = ["Python", "Java", "JavaScript", "SQL", "HTML/CSS", "React", "Node.js",
                      "Django", "Flask", "Git", "Linux", "Docker", "AWS", "Machine Learning",
                      "Data Analysis", "Communication", "Teamwork", "Problem Solving",
                      "Critical Thinking", "Public Speaking", "Leadership", "Project Management"]
        skills = ", ".join(random.sample(skill_pool, n_skills))

        prog = prog_objs[pname]
        sclass = classes_created.get((pname, min(cur_sem, 4), random.choice(["A", "B"])))
        if not sclass:
            sclass = list(classes_created.values())[0]

        profile = StudentProfile(
            user_id=user.id, program=pname, current_semester=cur_sem,
            duration_years=dur, eri_score=float(eri),
            class_group_id=sclass.id, skills=skills,
            bio=f"I am a {tier.lower()} performing student in {pname}.",
            is_public=random.random() > 0.2
        )
        db.session.add(profile)
        db.session.flush()

        for sem in range(1, total_sems + 1):
            ca, exam, att, proj, intern, overall = gen_academic_scores(eri, sem, total_sems)
            sr = SemesterResult(
                student_id=profile.id, semester_number=sem,
                ca_score=ca, exam_score=exam, attendance=att,
                project_score=proj, internship_score=intern,
                overall_score=overall
            )
            db.session.add(sr)

        n_att_records = random.randint(20, 50)
        present_rate = 0.95 if tier == "High" else 0.80 if tier == "Mid" else 0.55
        for _ in range(n_att_records):
            status = "present" if random.random() < present_rate else "absent"
            ar = AttendanceRecord(
                student_id=profile.id, teacher_id=teacher.id,
                course="General", status=status,
                date=datetime.now() - timedelta(days=random.randint(1, 365))
            )
            db.session.add(ar)

        n_internships = 0
        if tier == "High":
            n_internships = random.randint(2, 4)
        elif tier == "Mid":
            n_internships = random.randint(0, 2)
        else:
            n_internships = 0 if random.random() < 0.5 else 1

        companies = ["Google", "Microsoft", "Meta", "Amazon", "Apple", "Local Startup",
                     "Tech Hub", "Orange", "MTN", "Afriland", "BGFI Bank"]
        for _ in range(n_internships):
            db.session.add(Internship(
                student_id=profile.id,
                company_name=random.choice(companies),
                role_title=random.choice(["Software Intern", "Data Analyst", "DevOps Intern", "IT Support"]),
                start_date=date(2024, random.randint(1, 12), random.randint(1, 28)),
                end_date=date(2024, random.randint(6, 12), random.randint(1, 28)),
                is_verified=random.random() > 0.3
            ))

        n_certs = 0
        if tier == "High":
            n_certs = random.randint(2, 5)
        elif tier == "Mid":
            n_certs = random.randint(0, 2)
        else:
            n_certs = 0 if random.random() < 0.4 else 1

        cert_titles = ["Python Pro", "AWS Certified", "ML Specialist", "Data Science 101",
                       "Web Developer", "Network Basics", "Cybersecurity Intro", "Agile Scrum"]
        for _ in range(n_certs):
            db.session.add(Certification(
                student_id=profile.id,
                title=random.choice(cert_titles),
                issuer=random.choice(["Coursera", "Udemy", "Amazon", "Python Institute", "Google"]),
                date_obtained=date(2025, random.randint(1, 6), random.randint(1, 28)),
                is_verified=random.random() > 0.2
            ))

        n_projects = 0
        if tier == "High":
            n_projects = random.randint(2, 4)
        elif tier == "Mid":
            n_projects = random.randint(0, 2)
        else:
            n_projects = 0 if random.random() < 0.6 else 1

        for _ in range(n_projects):
            db.session.add(Project(
                student_id=profile.id,
                title=random.choice(["AI Chatbot", "E-commerce Platform", "Portfolio Site",
                                     "Mobile App", "Data Dashboard", "API Gateway"]),
                technologies=random.choice(["Python, React, SQL", "JavaScript, Node, MongoDB",
                                           "Python, TensorFlow", "Java, Spring, PostgreSQL"]),
                description=f"A project demonstrating technical skills.",
                project_url=f"https://github.com/{mat}/project"
            ))

        assign = Assignment.query.filter_by(course="General").first()
        if not assign:
            assign = Assignment(teacher_id=teacher.id, course="General",
                                title="General Assignment", description="Course assignment",
                                max_score=20)
            db.session.add(assign)
            db.session.flush()

        n_assignments = random.randint(1, 8)
        for _ in range(n_assignments):
            score = random.uniform(10, 20) if tier == "High" else random.uniform(6, 16) if tier == "Mid" else random.uniform(2, 12)
            db.session.add(AssignmentSubmission(
                assignment_id=assign.id, student_id=profile.id,
                filename=f"{mat}_assignment.pdf", score=score
            ))

        quiz = Quiz.query.filter_by(course="General").first()
        if not quiz:
            quiz = Quiz(teacher_id=teacher.id, course="General", title="General Quiz")
            db.session.add(quiz)
            db.session.flush()

        n_quizzes = random.randint(1, 6)
        for _ in range(n_quizzes):
            qscore = random.uniform(12, 20) if tier == "High" else random.uniform(6, 16) if tier == "Mid" else random.uniform(2, 12)
            db.session.add(QuizResult(
                quiz_id=quiz.id, student_id=profile.id,
                score=qscore, max_score=20
            ))

        n_obs = random.randint(0, 5) if tier == "Mid" else random.randint(1, 3) if tier == "High" else 0
        for _ in range(n_obs):
            db.session.add(TeacherObservation(
                student_id=profile.id, teacher_id=teacher.id,
                course="General",
                participation_score=random.uniform(50, 100) if tier == "High" else random.uniform(30, 70) if tier == "Mid" else random.uniform(10, 40)
            ))

        n_feedback = random.randint(0, 3)
        for _ in range(n_feedback):
            db.session.add(EmployerFeedback(
                student_id=profile.id, employer_id=teacher.id,
                rating=random.uniform(3.0, 5.0) if tier == "High" else random.uniform(1.0, 4.0)
            ))

        for code in random.sample(list(all_courses.keys()), min(4, len(all_courses))):
            if sclass and all_courses[code] not in sclass.courses:
                sclass.courses.append(all_courses[code])

        created += 1
        if created % 50 == 0:
            print(f"  Created {created} students...")
            db.session.commit()

    db.session.commit()
    print(f"Done! Created {created} synthetic students across {len(prog_objs)} programs.")
    print(f"ERI distribution:")
    eri_vals = [c[1] for c in configs[:created]]
    print(f"  0-39: {sum(1 for e in eri_vals if e < 40)}")
    print(f"  40-69: {sum(1 for e in eri_vals if 40 <= e < 70)}")
    print(f"  70-100: {sum(1 for e in eri_vals if e >= 70)}")
