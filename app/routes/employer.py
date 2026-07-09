from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from app.models import User, StudentProfile

employer_bp = Blueprint("employer", __name__)

@employer_bp.route("/dashboard")
@login_required
def dashboard():
    total = StudentProfile.query.count()
    top = StudentProfile.query.filter(StudentProfile.eri_score >= 80).count()
    students = StudentProfile.query.order_by(StudentProfile.eri_score.desc()).limit(5).all()
    return render_template("employer/dashboard.html", total=total, top=top, students=students)

@employer_bp.route("/search")
@login_required
def search():
    q         = request.args.get("q","").strip()
    filiere   = request.args.get("filiere","").strip()
    dept      = request.args.get("dept","").strip()
    eri_min   = request.args.get("eri_min", 0, type=int)

    query = StudentProfile.query
    if filiere:
        query = query.filter(StudentProfile.filiere == filiere)
    if dept:
        query = query.join(User).filter(User.department == dept)
    if q:
        query = query.join(User).filter(User.name.ilike(f"%{q}%"))
    students = query.filter(StudentProfile.eri_score >= eri_min).order_by(StudentProfile.eri_score.desc()).all()
    return render_template("employer/search.html", students=students, q=q, filiere=filiere, dept=dept, eri_min=eri_min)

@employer_bp.route("/student/<int:profile_id>")
@login_required
def view_student(profile_id):
    p = StudentProfile.query.get_or_404(profile_id)
    return render_template("employer/student_view.html", p=p)
