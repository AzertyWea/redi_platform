"""
Prepares the REDI platform for a live demo.
"""
import sys
sys.path.insert(0, ".")
from app import create_app, db
from app.models import *
from app.services.eri_engine import calculate_eri
from datetime import date, datetime, time, timedelta
import random

app = create_app()
with app.app_context():
    print("=" * 60)
    print("PREPARING REDI DEMO ENVIRONMENT")
    print("=" * 60)

    print("\n[1/7] Standardizing demo passwords...")
    for role, pw in [("admin","admin123"),("teacher","teacher123"),("student","student123"),("employer","employer123")]:
        for user in User.query.filter_by(role=role).all():
            user.set_password(pw)
    db.session.commit()
    print("  Done.")

    print("\n[2/7] Recalculating ERI scores...")
    all_students = StudentProfile.query.all()
    count = len(all_students)
    for idx, s in enumerate(all_students):
        s.eri_score = calculate_eri(s)
        if (idx + 1) % 200 == 0:
            db.session.commit()
            print(f"  ... {idx+1}/{count}")
    db.session.commit()

    for i, s in enumerate(all_students):
        if i < 30:
            s.eri_score = min(100, s.eri_score + random.uniform(10, 30))
        elif i > count - 50:
            s.eri_score = s.eri_score * random.uniform(0.3, 0.6)
    db.session.commit()

    top = StudentProfile.query.order_by(StudentProfile.eri_score.desc()).limit(5).all()
    print(f"  Top ERI: {', '.join(f'{s.user.name} ({s.eri_score:.1f}%)' for s in top)}")

    print("\n[3/7] Creating documents...")
    doc_types = ["Semester 1 Transcript","Semester 2 Transcript","CA Results","Exam Results","Internship Certificate","Project Report"]
    doc_count = 0
    for s in all_students[:300]:
        for dt in random.sample(doc_types, random.randint(1, 3)):
            if not Document.query.filter_by(student_id=s.id, doc_type=dt).first():
                db.session.add(Document(student_id=s.id, doc_type=dt,
                    filename=f"{dt.lower().replace(' ','_')}_{s.user.matricule.lower()}.pdf",
                    is_verified=random.random() > 0.3, qr_hash=f"qr_{s.user.matricule}_{random.randint(1000,9999)}",
                    uploaded_at=datetime.utcnow() - timedelta(days=random.randint(1, 180))))
                doc_count += 1
        if doc_count % 200 == 0 and doc_count > 0:
            db.session.commit()
    db.session.commit()
    print(f"  Created {doc_count} documents")

    print("\n[4/7] Creating assignments and submissions...")
    teachers = User.query.filter_by(role="teacher").all()
    courses = Course.query.all()
    a_count = s_count = 0
    for teacher in teachers[:10]:
        for course in (Course.query.filter_by(teacher_id=teacher.id).all() or courses[:2])[:2]:
            for week in range(1, 4):
                title = f"{course.name} Week {week}"
                if Assignment.query.filter_by(teacher_id=teacher.id, title=title).first():
                    continue
                a = Assignment(teacher_id=teacher.id, course=course.name, title=title,
                    description=f"Week {week} assignment for {course.name}.",
                    due_date=datetime.utcnow() + timedelta(days=random.randint(-20, 20)), max_score=20.0)
                db.session.add(a)
                db.session.flush()
                a_count += 1
                for student in StudentProfile.query.filter(StudentProfile.class_group_id.isnot(None)).limit(25).all():
                    db.session.add(AssignmentSubmission(assignment_id=a.id, student_id=student.id,
                        filename=f"sub_{student.user.matricule}_w{week}.pdf",
                        score=round(random.uniform(10, 20), 1),
                        feedback=random.choice(["Good work!","Needs improvement.","Excellent.","Keep it up."]),
                        submitted_at=datetime.utcnow() - timedelta(days=random.randint(1, 14))))
                    s_count += 1
    db.session.commit()
    print(f"  Created {a_count} assignments, {s_count} submissions")

    print("\n[5/7] Creating quizzes and results...")
    q_count = r_count = 0
    for teacher in teachers[:8]:
        for course in (Course.query.filter_by(teacher_id=teacher.id).all() or courses[:2])[:2]:
            for qnum in range(1, 3):
                qtitle = f"{course.name} Quiz {qnum}"
                if Quiz.query.filter_by(teacher_id=teacher.id, title=qtitle).first():
                    continue
                q = Quiz(teacher_id=teacher.id, course=course.name, title=qtitle)
                db.session.add(q)
                db.session.flush()
                q_count += 1
                for student in StudentProfile.query.limit(30).all():
                    db.session.add(QuizResult(quiz_id=q.id, student_id=student.id,
                        score=round(random.uniform(8, 20), 1), max_score=20.0,
                        completed_at=datetime.utcnow() - timedelta(days=random.randint(1, 20))))
                    r_count += 1
    db.session.commit()
    print(f"  Created {q_count} quizzes, {r_count} results")

    print("\n[6/7] Creating observations and employer feedback...")
    teachers = User.query.filter_by(role="teacher").all()
    employers = User.query.filter_by(role="employer").all()
    obs_count = fb_count = 0
    sample = StudentProfile.query.limit(80).all()
    for t in teachers[:5]:
        for s in random.sample(sample, min(10, len(sample))):
            if not TeacherObservation.query.filter_by(student_id=s.id, teacher_id=t.id).first():
                db.session.add(TeacherObservation(student_id=s.id, teacher_id=t.id, course=random.choice(courses).name if courses else "General",
                    note=random.choice(["Active participant.","Good work.","Needs improvement.","Excellent student.","Shows leadership."]),
                    participation_score=round(random.uniform(10, 20), 1)))
                obs_count += 1
    for e in employers:
        for s in random.sample(sample, min(8, len(sample))):
            if not EmployerFeedback.query.filter_by(student_id=s.id, employer_id=e.id).first():
                db.session.add(EmployerFeedback(student_id=s.id, employer_id=e.id,
                    rating=round(random.uniform(2.5, 5.0), 1),
                    comment=random.choice(["Great candidate.","Good potential.","Recommended.","Strong profile.","Hireable."])))
                fb_count += 1
    db.session.commit()
    print(f"  Created {obs_count} observations, {fb_count} feedbacks")

    print("\n[7/7] Final ERI pass...")
    for idx, s in enumerate(all_students):
        s.eri_score = calculate_eri(s)
        if (idx + 1) % 300 == 0:
            db.session.commit()
    db.session.commit()
    scores = [s.eri_score for s in all_students]
    print(f"  Range: {min(scores):.1f}% - {max(scores):.1f}%, Avg: {sum(scores)/len(scores):.1f}%")

    print("\n" + "=" * 60)
    print("DEMO CREDENTIALS")
    print("=" * 60)
    print("  Admin:    ADMIN01 / admin123")
    print("  Teacher:  T002    / teacher123")
    print("  Student:  S0010  / student123")
    print("  Employer: E002   / employer123")
    print("\n" + "=" * 60)
    print("DEMO ENVIRONMENT READY")
    print("=" * 60)
