from app import db, login_manager
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    matricule = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    role = db.Column(db.String(20), default='student')
    department = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class StudentProfile(db.Model):
    __tablename__ = 'student_profiles'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    program = db.Column(db.String(100))
    duration_years = db.Column(db.Integer, default=2)
    current_semester = db.Column(db.Integer, default=1)
    eri_score = db.Column(db.Float, default=0.0, index=True)
    photo_filename = db.Column(db.String(200))
    bio = db.Column(db.Text)
    skills = db.Column(db.String(500))
    linkedin_url = db.Column(db.String(200))
    filiere = db.Column(db.String(100))
    availability = db.Column(db.String(30), default="available_now")
    cv_file = db.Column(db.String(300))
    is_public = db.Column(db.Boolean, default=False, index=True)
    class_group_id = db.Column(db.Integer, db.ForeignKey('school_classes.id'), index=True)
    user = db.relationship('User', backref=db.backref('profile', uselist=False))
    school_class = db.relationship('SchoolClass', backref='students')

class SemesterResult(db.Model):
    __tablename__ = 'semester_results'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student_profiles.id'), index=True)
    semester_number = db.Column(db.Integer)
    ca_score = db.Column(db.Float, default=0)
    exam_score = db.Column(db.Float, default=0)
    attendance = db.Column(db.Float, default=0)
    project_score = db.Column(db.Float, default=0)
    internship_score = db.Column(db.Float, default=0)
    overall_score = db.Column(db.Float, default=0)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    student = db.relationship('StudentProfile', backref='results')

class Document(db.Model):
    __tablename__ = 'documents'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student_profiles.id'))
    doc_type = db.Column(db.String(50))
    filename = db.Column(db.String(200))
    qr_hash = db.Column(db.String(64))
    is_verified = db.Column(db.Boolean, default=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

class AttendanceRecord(db.Model):
    __tablename__ = 'attendance_records'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student_profiles.id'), index=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    course = db.Column(db.String(100))
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), index=True)
    class_group_id = db.Column(db.Integer, db.ForeignKey('school_classes.id'), index=True)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(10), default='present', index=True)

class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    recipient_role = db.Column(db.String(20))
    type = db.Column(db.String(50))
    title = db.Column(db.String(200))
    body = db.Column(db.Text)
    link = db.Column(db.String(500))
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    recipient = db.relationship("User", backref="notifications")

def create_notification(recipient_id, recipient_role, type_, title, body, link=None):
    n = Notification(
        recipient_id=recipient_id,
        recipient_role=recipient_role,
        type=type_,
        title=title,
        body=body,
        link=link,
    )
    db.session.add(n)
    db.session.flush()
    return n

def get_unread_count(user_id):
    return Notification.query.filter_by(recipient_id=user_id, is_read=False).count()

def mark_as_read(notification_id):
    n = Notification.query.get(notification_id)
    if n:
        n.is_read = True
        return True
    return False

class Internship(db.Model):
    __tablename__ = "internships"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student_profiles.id"))
    company_name = db.Column(db.String(150))
    role_title = db.Column(db.String(150))
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    description = db.Column(db.Text)
    is_verified = db.Column(db.Boolean, default=False)
    proof_filename = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    student = db.relationship("StudentProfile", backref="internships")

class Certification(db.Model):
    __tablename__ = "certifications"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student_profiles.id"))
    title = db.Column(db.String(150))
    issuer = db.Column(db.String(150))
    date_obtained = db.Column(db.Date)
    proof_filename = db.Column(db.String(200))
    is_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    student = db.relationship("StudentProfile", backref="certifications")

class Project(db.Model):
    __tablename__ = "projects"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student_profiles.id"))
    title = db.Column(db.String(150))
    description = db.Column(db.Text)
    technologies = db.Column(db.String(300))
    project_url = db.Column(db.String(300))
    course_related = db.Column(db.String(150))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    student = db.relationship("StudentProfile", backref="projects")

class CourseMaterial(db.Model):
    __tablename__ = "course_materials"
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    course = db.Column(db.String(150))
    title = db.Column(db.String(200))
    filename = db.Column(db.String(200))
    publish_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Assignment(db.Model):
    __tablename__ = "assignments"
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    course = db.Column(db.String(150))
    title = db.Column(db.String(200))
    description = db.Column(db.Text)
    due_date = db.Column(db.DateTime)
    max_score = db.Column(db.Float, default=20)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AssignmentSubmission(db.Model):
    __tablename__ = "assignment_submissions"
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey("assignments.id"))
    student_id = db.Column(db.Integer, db.ForeignKey("student_profiles.id"))
    filename = db.Column(db.String(200))
    score = db.Column(db.Float)
    feedback = db.Column(db.Text)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    assignment = db.relationship("Assignment", backref="submissions")
    student = db.relationship("StudentProfile", backref="submissions")

class Quiz(db.Model):
    __tablename__ = "quizzes"
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    course = db.Column(db.String(150))
    title = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class QuizResult(db.Model):
    __tablename__ = "quiz_results"
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey("quizzes.id"))
    student_id = db.Column(db.Integer, db.ForeignKey("student_profiles.id"))
    score = db.Column(db.Float)
    max_score = db.Column(db.Float, default=20)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)
    quiz = db.relationship("Quiz", backref="results")
    student = db.relationship("StudentProfile", backref="quiz_results")

class TeacherObservation(db.Model):
    __tablename__ = "teacher_observations"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student_profiles.id"))
    teacher_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    course = db.Column(db.String(150))
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"))
    class_group_id = db.Column(db.Integer, db.ForeignKey("school_classes.id"))
    note = db.Column(db.Text)
    participation_score = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    student = db.relationship("StudentProfile", backref="observations")

class EmployerFeedback(db.Model):
    __tablename__ = "employer_feedback"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student_profiles.id"))
    employer_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    rating = db.Column(db.Float)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    student = db.relationship("StudentProfile", backref="employer_feedbacks")

class Department(db.Model):
    __tablename__ = "departments"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

class Program(db.Model):
    __tablename__ = "programs"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"))
    department = db.relationship("Department", backref="programs")

class Course(db.Model):
    __tablename__ = "courses"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    code = db.Column(db.String(20))
    program_id = db.Column(db.Integer, db.ForeignKey("programs.id"))
    teacher_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    semester_number = db.Column(db.Integer)
    program = db.relationship("Program", backref="courses")
    teacher = db.relationship("User", backref="courses_taught")

class SchoolClass(db.Model):
    __tablename__ = "school_classes"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"))
    program_id = db.Column(db.Integer, db.ForeignKey("programs.id"), nullable=False)
    level = db.Column(db.Integer, nullable=False)
    section = db.Column(db.String(10))
    academic_year = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    department = db.relationship("Department", backref="school_classes")
    program = db.relationship("Program", backref="school_classes")

    @property
    def display_name(self):
        base = f"{self.program.name} - Level {self.level}"
        if self.section:
            base += f" ({self.section})"
        return base

course_classes = db.Table(
    "course_classes",
    db.Column("course_id", db.Integer, db.ForeignKey("courses.id"), primary_key=True),
    db.Column("class_id", db.Integer, db.ForeignKey("school_classes.id"), primary_key=True),
)

Course.classes = db.relationship("SchoolClass", secondary=course_classes, backref="courses")

class AuditLog(db.Model):
    __tablename__ = "audit_logs"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    role = db.Column(db.String(20))
    action = db.Column(db.String(50), nullable=False)
    target_type = db.Column(db.String(50))
    target_id = db.Column(db.Integer)
    old_value = db.Column(db.Text)
    new_value = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship("User", backref="audit_logs")

class Conversation(db.Model):
    __tablename__ = "conversations"
    id = db.Column(db.Integer, primary_key=True)
    employer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    employer = db.relationship("User", foreign_keys=[employer_id], backref="employer_conversations")
    student = db.relationship("User", foreign_keys=[student_id], backref="student_conversations")

class Message(db.Model):
    __tablename__ = "messages"
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey("conversations.id"), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    conversation = db.relationship("Conversation", backref="messages")
    sender = db.relationship("User", backref="sent_messages")

class PredictionResult(db.Model):
    __tablename__ = "predictions"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student_profiles.id"), nullable=False)
    probability = db.Column(db.Float, default=0.0)
    prediction = db.Column(db.Boolean, default=False)
    model_version = db.Column(db.String(20), default="v1")
    features_json = db.Column(db.Text)
    top_factors = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    student = db.relationship("StudentProfile", backref="prediction")

class SocialPost(db.Model):
    __tablename__ = "social_posts"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    media_url = db.Column(db.String(500))
    post_type = db.Column(db.String(20), default="post")
    resource_title = db.Column(db.String(200))
    resource_url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship("User", backref="social_posts")

class SocialLike(db.Model):
    __tablename__ = "social_likes"
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("social_posts.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    post = db.relationship("SocialPost", backref="likes")
    user = db.relationship("User", backref="social_likes")
    __table_args__ = (db.UniqueConstraint("post_id", "user_id"),)

class SocialComment(db.Model):
    __tablename__ = "social_comments"
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("social_posts.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    post = db.relationship("SocialPost", backref="comments")
    user = db.relationship("User", backref="social_comments")

class Follow(db.Model):
    __tablename__ = "follows"
    id = db.Column(db.Integer, primary_key=True)
    follower_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    followed_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    follower = db.relationship("User", foreign_keys=[follower_id], backref="following")
    followed = db.relationship("User", foreign_keys=[followed_id], backref="followers")


class ScheduleEntry(db.Model):
    __tablename__ = "schedule_entries"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    class_group_id = db.Column(db.Integer, db.ForeignKey("school_classes.id"))
    day_of_week = db.Column(db.String(10))
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    room = db.Column(db.String(50))
    academic_year = db.Column(db.String(20))
    semester_number = db.Column(db.Integer)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    course = db.relationship("Course", backref="schedule_entries")
    school_class = db.relationship("SchoolClass", backref="schedule_entries")


# ═══════════════════════════════════════════
# UNIDY MODELS — University Digital Management
# ═══════════════════════════════════════════

class AcademicYear(db.Model):
    __tablename__ = "academic_years"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), unique=True, nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    is_current = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    semesters = db.relationship("AcademicSemester", backref="academic_year", cascade="all, delete-orphan")

    @property
    def duration_months(self):
        delta = self.end_date - self.start_date
        return max(1, delta.days // 30)

class AcademicSemester(db.Model):
    __tablename__ = "academic_semesters"
    id = db.Column(db.Integer, primary_key=True)
    academic_year_id = db.Column(db.Integer, db.ForeignKey("academic_years.id"), nullable=False, index=True)
    name = db.Column(db.String(50), nullable=False)
    number = db.Column(db.Integer, nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    is_current = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Admission(db.Model):
    __tablename__ = "admissions"
    id = db.Column(db.Integer, primary_key=True)
    student_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    academic_year_id = db.Column(db.Integer, db.ForeignKey("academic_years.id"), index=True)
    program_id = db.Column(db.Integer, db.ForeignKey("programs.id"))
    status = db.Column(db.String(20), default="pending")
    notes = db.Column(db.Text)
    reviewed_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime)
    student = db.relationship("User", foreign_keys=[student_user_id], backref="admissions")
    reviewer = db.relationship("User", foreign_keys=[reviewed_by])
    academic_year = db.relationship("AcademicYear", backref="admissions")
    program = db.relationship("Program", backref="admissions")

class Enrollment(db.Model):
    __tablename__ = "enrollments"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student_profiles.id"), nullable=False, index=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False, index=True)
    semester_id = db.Column(db.Integer, db.ForeignKey("academic_semesters.id"), index=True)
    academic_year = db.Column(db.String(20))
    status = db.Column(db.String(20), default="active")
    enrolled_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    student_profile = db.relationship("StudentProfile", backref="enrollments")
    course = db.relationship("Course", backref="enrollments")
    semester = db.relationship("AcademicSemester", backref="enrollments")
    __table_args__ = (db.UniqueConstraint("student_id", "course_id", "semester_id"),)

class FeeStructure(db.Model):
    __tablename__ = "fee_structures"
    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(db.Integer, db.ForeignKey("programs.id"), index=True)
    level = db.Column(db.Integer, nullable=False)
    semester_number = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200))
    academic_year = db.Column(db.String(20))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    program = db.relationship("Program", backref="fee_structures")

class FeePayment(db.Model):
    __tablename__ = "fee_payments"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student_profiles.id"), nullable=False, index=True)
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(30), default="cash")
    reference = db.Column(db.String(100))
    receipt_number = db.Column(db.String(50))
    notes = db.Column(db.Text)
    recorded_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    payment_date = db.Column(db.Date, nullable=False)
    academic_year = db.Column(db.String(20))
    semester_number = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    student_profile = db.relationship("StudentProfile", backref="payments")
    recorder = db.relationship("User", backref="recorded_payments")

class CourseGrade(db.Model):
    __tablename__ = "course_grades"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student_profiles.id"), nullable=False, index=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False, index=True)
    semester_id = db.Column(db.Integer, db.ForeignKey("academic_semesters.id"), index=True)
    ca_score = db.Column(db.Float, default=0)
    exam_score = db.Column(db.Float, default=0)
    total_score = db.Column(db.Float, default=0)
    grade_letter = db.Column(db.String(2))
    grade_points = db.Column(db.Float, default=0)
    credits = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default="draft")
    graded_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    locked = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    student_profile = db.relationship("StudentProfile", backref="course_grades")
    course = db.relationship("Course", backref="course_grades")
    semester = db.relationship("AcademicSemester", backref="course_grades")
    grader = db.relationship("User", backref="graded_courses")
    __table_args__ = (db.UniqueConstraint("student_id", "course_id", "semester_id"),)

class Transcript(db.Model):
    __tablename__ = "transcripts"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student_profiles.id"), nullable=False, index=True)
    academic_year = db.Column(db.String(20))
    semester_number = db.Column(db.Integer)
    semester_gpa = db.Column(db.Float, default=0)
    cumulative_gpa = db.Column(db.Float, default=0)
    total_credits = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default="draft")
    generated_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    pdf_filename = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    student_profile = db.relationship("StudentProfile", backref="transcripts")
    generator = db.relationship("User", backref="generated_transcripts")

class TranscriptItem(db.Model):
    __tablename__ = "transcript_items"
    id = db.Column(db.Integer, primary_key=True)
    transcript_id = db.Column(db.Integer, db.ForeignKey("transcripts.id"), nullable=False, index=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"))
    course_name = db.Column(db.String(150))
    course_code = db.Column(db.String(20))
    ca_score = db.Column(db.Float, default=0)
    exam_score = db.Column(db.Float, default=0)
    total_score = db.Column(db.Float, default=0)
    grade_letter = db.Column(db.String(2))
    grade_points = db.Column(db.Float, default=0)
    credits = db.Column(db.Integer, default=0)
    transcript = db.relationship("Transcript", backref="items")
    course = db.relationship("Course")

class AdmissionApplication(db.Model):
    __tablename__ = "admission_applications"
    id = db.Column(db.Integer, primary_key=True)
    applicant_name = db.Column(db.String(120), nullable=False)
    applicant_email = db.Column(db.String(120))
    applicant_phone = db.Column(db.String(30))
    program_id = db.Column(db.Integer, db.ForeignKey("programs.id"))
    academic_year_id = db.Column(db.Integer, db.ForeignKey("academic_years.id"))
    status = db.Column(db.String(20), default="pending")
    documents_json = db.Column(db.Text)
    notes = db.Column(db.Text)
    reviewed_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime)
    program = db.relationship("Program", backref="applications")
    academic_year = db.relationship("AcademicYear", backref="applications")
    reviewer = db.relationship("User", foreign_keys=[reviewed_by])
