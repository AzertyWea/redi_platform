from app.models import (
    SemesterResult, Internship, Certification, Project,
    AssignmentSubmission, QuizResult, TeacherObservation,
    AttendanceRecord, EmployerFeedback
)
def calculate_eri(student_profile):
    """
    11-parameter weighted Employability Readiness Index.
    Combines academic results with continuously generated platform data.
    """
    sid = student_profile.id
    # 1. Academic results (30%)
    results = SemesterResult.query.filter_by(student_id=sid).all()
    academic_score = sum(r.overall_score for r in results) / len(results) if results else 0
    # 2. Attendance (10%)
    records = AttendanceRecord.query.filter_by(student_id=sid).all()
    if records:
        present = sum(1 for r in records if r.status == "present")
        attendance_score = (present / len(records)) * 100
    else:
        attendance_score = 0
    # 3. Internships (15%)
    internships = Internship.query.filter_by(student_id=sid).count()
    internship_score = min(internships * 50, 100)
    # 4. Certifications (10%)
    certs = Certification.query.filter_by(student_id=sid).count()
    cert_score = min(certs * 25, 100)
    # 5. Projects (10%)
    projects = Project.query.filter_by(student_id=sid).count()
    project_score = min(projects * 20, 100)
    # 6. Assignments (8%)
    submissions = AssignmentSubmission.query.filter_by(student_id=sid).all()
    scored = [s for s in submissions if s.score is not None]
    assignment_score = (sum(s.score for s in scored) / len(scored)) * 5 if scored else 0
    # 7. Quizzes (7%)
    quiz_results = QuizResult.query.filter_by(student_id=sid).all()
    quiz_score = (sum(q.score / q.max_score for q in quiz_results) / len(quiz_results)) * 100 if quiz_results else 0
    # 8. Teacher observations / participation (5%)
    obs = TeacherObservation.query.filter_by(student_id=sid).all()
    obs_score = (sum(o.participation_score for o in obs) / len(obs)) * 5 if obs else 0
    # 9. Employer feedback (5%)
    feedback = EmployerFeedback.query.filter_by(student_id=sid).all()
    feedback_score = (sum(f.rating for f in feedback) / len(feedback)) * 20 if feedback else 0
    # Weighted sum
    eri = (
        academic_score * 0.30 +
        attendance_score * 0.10 +
        internship_score * 0.15 +
        cert_score * 0.10 +
        project_score * 0.10 +
        assignment_score * 0.08 +
        quiz_score * 0.07 +
        obs_score * 0.05 +
        feedback_score * 0.05
    )
    return round(min(eri, 100), 1)

def get_eri_breakdown(student_profile):
    """Returns individual component scores for transparency/explainability."""
    sid = student_profile.id
    results = SemesterResult.query.filter_by(student_id=sid).all()
    records = AttendanceRecord.query.filter_by(student_id=sid).all()
    return {
        "academic": round(sum(r.overall_score for r in results) / len(results), 1) if results else 0,
        "attendance": round((sum(1 for r in records if r.status == "present") / len(records)) * 100, 1) if records else 0,
        "internships": Internship.query.filter_by(student_id=sid).count(),
        "certifications": Certification.query.filter_by(student_id=sid).count(),
        "projects": Project.query.filter_by(student_id=sid).count(),
    }

def calculate_eri_trend(student_profile):
    """
    Reconstructs a semester-by-semester ERI trajectory using the same weighted
    formula as calculate_eri(). Academic performance (30% of the score) is 100%
    accurate per semester, since SemesterResult is already tagged by semester_number.
    The remaining cumulative components (internships, certifications, projects,
    attendance, assignments, quizzes, observations, employer feedback) are NOT
    individually timestamped by semester in the current schema, so they are
    scaled proportionally to how far along the student's timeline each semester
    falls. This is a standard reconstruction technique for cumulative data
    without per-event semester tags, and is noted here explicitly for transparency
    in academic reporting - a future enhancement would be to tag each activity
    with its semester_number at creation time for fully precise historical ERI.
    """
    sid = student_profile.id
    results = SemesterResult.query.filter_by(student_id=sid).order_by(SemesterResult.semester_number).all()
    if not results:
        return []
    max_sem = max(r.semester_number for r in results)

    total_internships = Internship.query.filter_by(student_id=sid).count()
    total_certs = Certification.query.filter_by(student_id=sid).count()
    total_projects = Project.query.filter_by(student_id=sid).count()
    all_attendance = AttendanceRecord.query.filter_by(student_id=sid).all()
    total_att_present = sum(1 for r in all_attendance if r.status == "present")
    total_att = len(all_attendance)
    submissions = AssignmentSubmission.query.filter_by(student_id=sid).all()
    scored = [s for s in submissions if s.score is not None]
    quiz_results = QuizResult.query.filter_by(student_id=sid).all()
    obs = TeacherObservation.query.filter_by(student_id=sid).all()
    feedback = EmployerFeedback.query.filter_by(student_id=sid).all()

    trend = []
    for r in results:
        sem = r.semester_number
        progress = sem / max_sem if max_sem else 1

        sem_results = [x for x in results if x.semester_number <= sem]
        academic_score = sum(x.overall_score for x in sem_results) / len(sem_results)

        est_internships = round(total_internships * progress)
        est_certs = round(total_certs * progress)
        est_projects = round(total_projects * progress)
        internship_score = min(est_internships * 50, 100)
        cert_score = min(est_certs * 25, 100)
        project_score = min(est_projects * 20, 100)

        est_att_total = max(round(total_att * progress), 1) if total_att else 0
        est_att_present = round(total_att_present * progress)
        attendance_score = (est_att_present / est_att_total * 100) if est_att_total else 0

        n_scored = max(round(len(scored) * progress), 0)
        est_scored = scored[:n_scored]
        assignment_score = (sum(s.score for s in est_scored) / len(est_scored)) * 5 if est_scored else 0

        n_quiz = max(round(len(quiz_results) * progress), 0)
        est_quiz = quiz_results[:n_quiz]
        quiz_score = (sum(q.score / q.max_score for q in est_quiz) / len(est_quiz)) * 100 if est_quiz else 0

        n_obs = max(round(len(obs) * progress), 0)
        est_obs = obs[:n_obs]
        obs_score = (sum(o.participation_score for o in est_obs) / len(est_obs)) * 5 if est_obs else 0

        n_fb = max(round(len(feedback) * progress), 0)
        est_fb = feedback[:n_fb]
        feedback_score = (sum(f.rating for f in est_fb) / len(est_fb)) * 20 if est_fb else 0

        eri = (
            academic_score * 0.30 + attendance_score * 0.10 + internship_score * 0.15 +
            cert_score * 0.10 + project_score * 0.10 + assignment_score * 0.08 +
            quiz_score * 0.07 + obs_score * 0.05 + feedback_score * 0.05
        )
        trend.append({
            "semester": sem,
            "eri": round(min(eri, 100), 1),
            "academic": round(academic_score, 1),
            "ca": round(r.ca_score, 1),
            "exam": round(r.exam_score, 1),
            "attendance": round(r.attendance, 1),
            "project": round(r.project_score, 1),
        })
    return trend

def calculate_class_eri_trend(school_class):
    """Average ERI trend across every student in a class, semester by semester."""
    students = school_class.students
    sids = [s.id for s in students]
    if not sids:
        return []

    results = SemesterResult.query.filter(SemesterResult.student_id.in_(sids)).order_by(SemesterResult.semester_number).all()
    by_student = {}
    for r in results:
        by_student.setdefault(r.student_id, []).append(r)

    by_sem = {}
    for sid in sids:
        s_results = by_student.get(sid, [])
        if not s_results:
            continue
        max_sem = max(r.semester_number for r in s_results)
        for r in s_results:
            sem = r.semester_number
            sem_results = [x for x in s_results if x.semester_number <= sem]
            academic_score = sum(x.overall_score for x in sem_results) / len(sem_results)
            progress = sem / max_sem if max_sem else 1
            estimated_eri = academic_score * 0.30
            by_sem.setdefault(sem, []).append(min(estimated_eri, 100))
    return [{"semester": sem, "avg_eri": round(sum(v) / len(v), 1)} for sem, v in sorted(by_sem.items())]

def predict_next_eri(trend):
    """Simple linear projection from the last two trend points."""
    if len(trend) < 2:
        return trend[-1]["eri"] if trend else 0
    last = trend[-1]["eri"]
    prev = trend[-2]["eri"]
    delta = last - prev
    return round(max(0, min(100, last + delta)), 1)
