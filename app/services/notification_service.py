from flask import request
from flask_login import current_user
from flask_socketio import emit, join_room, leave_room
from app import db, socketio
from app.models import create_notification, get_unread_count

@socketio.on("connect")
def handle_connect():
    if current_user.is_authenticated:
        room = f"user_{current_user.id}"
        join_room(room)

@socketio.on("disconnect")
def handle_disconnect():
    if current_user.is_authenticated:
        room = f"user_{current_user.id}"
        leave_room(room)

@socketio.on("join")
def handle_join(data):
    if current_user.is_authenticated:
        join_room(f"user_{current_user.id}")

def emit_notification(recipient_id, recipient_role, type_, title, body, link=None):
    n = create_notification(
        recipient_id=recipient_id,
        recipient_role=recipient_role,
        type_=type_,
        title=title,
        body=body,
        link=link,
    )
    unread_count = get_unread_count(recipient_id)
    payload = {
        "id": n.id,
        "type": type_,
        "title": title,
        "body": body,
        "link": link,
        "is_read": False,
        "created_at": n.created_at.isoformat() if n.created_at else None,
        "unread_count": unread_count,
    }
    socketio.emit("new_notification", payload, room=f"user_{recipient_id}")
    return n
