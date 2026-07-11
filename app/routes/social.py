from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.models import User, SocialPost, SocialLike, SocialComment, Follow
from app import db
from datetime import datetime

social_bp = Blueprint("social", __name__, url_prefix="/feed")

@social_bp.route("/")
@login_required
def feed():
    page = request.args.get("page", 1, type=int)
    filter_type = request.args.get("type", "all")

    query = SocialPost.query

    if filter_type == "network":
        followed_ids = [f.followed_id for f in Follow.query.filter_by(follower_id=current_user.id).all()]
        followed_ids.append(current_user.id)
        query = query.filter(SocialPost.user_id.in_(followed_ids))
    elif filter_type == "resources":
        query = query.filter(SocialPost.post_type == "resource")

    posts = query.order_by(SocialPost.created_at.desc()).paginate(page=page, per_page=10, error_out=False)

    for p in posts.items:
        p.is_liked = SocialLike.query.filter_by(post_id=p.id, user_id=current_user.id).first() is not None
        p.like_count = SocialLike.query.filter_by(post_id=p.id).count()
        p.comment_count = SocialComment.query.filter_by(post_id=p.id).count()
        p.comments_list = SocialComment.query.filter_by(post_id=p.id).order_by(SocialComment.created_at.asc()).limit(3).all()

    following_count = Follow.query.filter_by(follower_id=current_user.id).count()
    followers_count = Follow.query.filter_by(followed_id=current_user.id).count()

    suggested_users = User.query.filter(
        User.id != current_user.id,
        ~User.id.in_([f.followed_id for f in Follow.query.filter_by(follower_id=current_user.id).all()])
    ).limit(5).all()

    return render_template("social/feed.html", posts=posts, filter_type=filter_type,
        following_count=following_count, followers_count=followers_count,
        suggested_users=suggested_users)

@social_bp.route("/post", methods=["POST"])
@login_required
def create_post():
    content = request.form.get("content", "").strip()
    post_type = request.form.get("post_type", "post")
    resource_title = request.form.get("resource_title", "").strip()
    resource_url = request.form.get("resource_url", "").strip()

    if not content:
        flash("Post content cannot be empty.", "danger")
        return redirect(url_for("social.feed"))

    post = SocialPost(
        user_id=current_user.id,
        content=content,
        post_type=post_type,
        resource_title=resource_title if post_type == "resource" else None,
        resource_url=resource_url if post_type == "resource" else None
    )
    db.session.add(post)
    db.session.commit()
    flash("Post created!", "success")
    return redirect(url_for("social.feed"))

@social_bp.route("/like/<int:post_id>", methods=["POST"])
@login_required
def like_post(post_id):
    post = SocialPost.query.get_or_404(post_id)
    existing = SocialLike.query.filter_by(post_id=post_id, user_id=current_user.id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({"liked": False, "count": SocialLike.query.filter_by(post_id=post_id).count()})
    like = SocialLike(post_id=post_id, user_id=current_user.id)
    db.session.add(like)
    db.session.commit()
    return jsonify({"liked": True, "count": SocialLike.query.filter_by(post_id=post_id).count()})

@social_bp.route("/comment/<int:post_id>", methods=["POST"])
@login_required
def add_comment(post_id):
    post = SocialPost.query.get_or_404(post_id)
    content = request.form.get("content", "").strip()
    if not content:
        return jsonify({"error": "Comment cannot be empty"}), 400
    comment = SocialComment(post_id=post_id, user_id=current_user.id, content=content)
    db.session.add(comment)
    db.session.commit()
    return jsonify({
        "id": comment.id,
        "user": current_user.name,
        "user_role": current_user.role,
        "content": content,
        "time": comment.created_at.strftime("%d %b %Y"),
        "count": SocialComment.query.filter_by(post_id=post_id).count()
    })

@social_bp.route("/delete/<int:post_id>", methods=["POST"])
@login_required
def delete_post(post_id):
    post = SocialPost.query.get_or_404(post_id)
    if post.user_id != current_user.id:
        return jsonify({"error": "Forbidden"}), 403
    SocialLike.query.filter_by(post_id=post_id).delete()
    SocialComment.query.filter_by(post_id=post_id).delete()
    db.session.delete(post)
    db.session.commit()
    flash("Post deleted.", "success")
    return redirect(url_for("social.feed"))

@social_bp.route("/comments/<int:post_id>")
@login_required
def load_comments(post_id):
    comments = SocialComment.query.filter_by(post_id=post_id).order_by(SocialComment.created_at.asc()).all()
    return jsonify([{
        "id": c.id,
        "user": c.user.name,
        "user_role": c.user.role,
        "content": c.content,
        "time": c.created_at.strftime("%d %b %Y")
    } for c in comments])

@social_bp.route("/follow/<int:user_id>", methods=["POST"])
@login_required
def follow_user(user_id):
    if user_id == current_user.id:
        return jsonify({"error": "Cannot follow yourself"}), 400
    existing = Follow.query.filter_by(follower_id=current_user.id, followed_id=user_id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({"following": False})
    follow = Follow(follower_id=current_user.id, followed_id=user_id)
    db.session.add(follow)
    db.session.commit()
    return jsonify({"following": True})
