from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User
from app import db

ROLE_DASHBOARDS = {
    'student': 'student.dashboard',
    'teacher': 'teacher.dashboard',
    'admin': 'admin.dashboard',
    'employer': 'employer.dashboard',
    'registrar': 'unidy_registrar.dashboard',
    'finance_officer': 'unidy_finance.dashboard',
    'lecturer': 'unidy_lecturer.dashboard',
    'academic_admin': 'unidy_admin.dashboard',
}

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
def welcome():
    if current_user.is_authenticated:
        route = ROLE_DASHBOARDS.get(current_user.role, 'auth.login')
        return redirect(url_for(route))
    return render_template('welcome.html', open_login=False)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        matricule = request.form.get('matricule')
        password = request.form.get('password')
        user = User.query.filter_by(matricule=matricule).first()
        if user and user.check_password(password):
            login_user(user)
            route = ROLE_DASHBOARDS.get(user.role, 'auth.login')
            return redirect(url_for(route))
        flash('Invalid credentials. Please try again.', 'danger')
        return render_template('welcome.html', open_login=True)
    return render_template('welcome.html', open_login=True)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('auth.login'))
