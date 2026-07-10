from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Notification, mark_as_read

notifications_bp = Blueprint("notifications", __name__)

@notifications_bp.route("/notifications")
@login_required
def list_notifications():
    page = request.args.get("page", 1, type=int)
    pagination = Notification.query.filter_by(recipient_id=current_user.id)\
        .order_by(Notification.created_at.desc())\
        .paginate(page=page, per_page=20, error_out=False)
    return render_template("notifications.html", pagination=pagination)

@notifications_bp.route("/notifications/unread-count")
@login_required
def unread_count():
    from app.models import get_unread_count
    return jsonify({"count": get_unread_count(current_user.id)})

@notifications_bp.route("/notifications/<int:notification_id>/read", methods=["POST"])
@login_required
def mark_read(notification_id):
    n = Notification.query.get_or_404(notification_id)
    if n.recipient_id != current_user.id:
        return jsonify({"error": "Forbidden"}), 403
    mark_as_read(notification_id)
    db.session.commit()
    return jsonify({"success": True})
