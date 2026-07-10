from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import User, StudentProfile, Conversation, Message, Document

employer_bp = Blueprint("employer", __name__)

@employer_bp.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    if request.method == "POST":
        program = request.form.get("program", "").strip()
        skills = request.form.get("skills", "").strip()
        eri_min = request.form.get("eri_min", 0, type=int)
        dept = request.form.get("dept", "").strip()

        query = StudentProfile.query.join(User)
        if program:
            query = query.filter(StudentProfile.program.ilike(f"%{program}%"))
        if dept:
            query = query.filter(User.department.ilike(f"%{dept}%"))
        if eri_min > 0:
            query = query.filter(StudentProfile.eri_score >= eri_min)
        if skills:
            skill_list = [s.strip() for s in skills.split(",")]
            for sk in skill_list:
                query = query.filter(StudentProfile.skills.ilike(f"%{sk}%"))
        students = query.order_by(StudentProfile.eri_score.desc()).all()
        return render_template("employer/results.html", students=students,
                               program=program, skills=skills, eri_min=eri_min, dept=dept)

    total = StudentProfile.query.count()
    top = StudentProfile.query.filter(StudentProfile.eri_score >= 80).count()
    top_students = StudentProfile.query.order_by(StudentProfile.eri_score.desc()).limit(6).all()
    unread = Message.query.filter_by(sender_id=User.id).join(Conversation).filter(
        Conversation.employer_id == current_user.id, Message.is_read == False
    ).count() if False else 0
    convos = Conversation.query.filter_by(employer_id=current_user.id)\
        .order_by(Conversation.created_at.desc()).limit(5).all()
    return render_template("employer/dashboard.html",
        total=total, top=top, top_students=top_students,
        unread=unread, convos=convos)

@employer_bp.route("/search")
@login_required
def search():
    q = request.args.get("q", "").strip()
    program = request.args.get("program", "").strip()
    eri_min = request.args.get("eri_min", 0, type=int)
    query = StudentProfile.query.join(User)
    if q:
        query = query.filter(User.name.ilike(f"%{q}%"))
    if program:
        query = query.filter(StudentProfile.program.ilike(f"%{program}%"))
    if eri_min > 0:
        query = query.filter(StudentProfile.eri_score >= eri_min)
    students = query.order_by(StudentProfile.eri_score.desc()).all()
    return render_template("employer/results.html", students=students,
                           q=q, program=program, eri_min=eri_min)

@employer_bp.route("/student/<int:profile_id>")
@login_required
def view_student(profile_id):
    p = StudentProfile.query.get_or_404(profile_id)
    docs = Document.query.filter_by(student_id=p.id, is_verified=True).all()
    return render_template("employer/student_profile.html", p=p, docs=docs)

@employer_bp.route("/chat")
@login_required
def chat_list():
    convos = Conversation.query.filter_by(employer_id=current_user.id)\
        .order_by(Conversation.created_at.desc()).all()
    return render_template("employer/chat_list.html", convos=convos)

@employer_bp.route("/chat/<int:student_id>")
@login_required
def chat_with_student(student_id):
    student = User.query.get_or_404(student_id)
    if student.role != "student":
        flash("Invalid user.", "danger")
        return redirect(url_for("employer.dashboard"))
    convo = Conversation.query.filter_by(employer_id=current_user.id, student_id=student_id).first()
    if not convo:
        convo = Conversation(employer_id=current_user.id, student_id=student_id)
        db.session.add(convo)
        db.session.commit()
    return render_template("employer/chat.html", convo=convo, student=student)

@employer_bp.route("/chat/<int:conversation_id>/messages")
@login_required
def get_messages(conversation_id):
    convo = Conversation.query.get_or_404(conversation_id)
    if convo.employer_id != current_user.id and convo.student_id != current_user.id:
        return jsonify({"error": "Forbidden"}), 403
    Message.query.filter_by(conversation_id=convo.id, is_read=False)\
        .filter(Message.sender_id != current_user.id)\
        .update({"is_read": True})
    db.session.commit()
    messages = Message.query.filter_by(conversation_id=convo.id)\
        .order_by(Message.created_at.asc()).all()
    return jsonify([{
        "id": m.id,
        "sender_id": m.sender_id,
        "content": m.content,
        "is_mine": m.sender_id == current_user.id,
        "created_at": m.created_at.strftime("%d %b %Y %H:%M") if m.created_at else "",
    } for m in messages])

@employer_bp.route("/chat/<int:conversation_id>/send", methods=["POST"])
@login_required
def send_message(conversation_id):
    convo = Conversation.query.get_or_404(conversation_id)
    if convo.employer_id != current_user.id and convo.student_id != current_user.id:
        return jsonify({"error": "Forbidden"}), 403
    content = request.form.get("content", "").strip()
    if not content:
        return jsonify({"error": "Empty message"}), 400
    msg = Message(conversation_id=convo.id, sender_id=current_user.id, content=content)
    db.session.add(msg)

    recipient_id = convo.student_id if current_user.id == convo.employer_id else convo.employer_id
    recipient_role = "student" if recipient_id == convo.student_id else "employer"
    from app.services.notification_service import emit_notification
    emit_notification(
        recipient_id=recipient_id, recipient_role=recipient_role,
        type_="message", title="New Message",
        body=f"{current_user.name}: {content[:80]}",
        link="/messages",
    )
    db.session.commit()
    return jsonify({"success": True, "message_id": msg.id})
