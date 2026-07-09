from flask import Blueprint, render_template, request
from flask_login import login_required
from app.models import StudentProfile, User

employer_bp = Blueprint('employer', __name__)

@employer_bp.route('/dashboard')
@login_required
def dashboard():
    students = StudentProfile.query.filter(StudentProfile.eri_score >= 70).all()
    return render_template('employer/dashboard.html', students=students)

@employer_bp.route('/search')
@login_required
def search():
    min_eri = request.args.get('min_eri', 0, type=float)
    department = request.args.get('department', '')
    query = StudentProfile.query
    if min_eri:
        query = query.filter(StudentProfile.eri_score >= min_eri)
    if department:
        query = query.join(User).filter(User.department == department)
    students = query.all()
    return render_template('employer/search.html', students=students)
