import json, os, pickle
import numpy as np
from collections import defaultdict
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, StratifiedKFold, GridSearchCV
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
from app.models import StudentProfile, SemesterResult, AttendanceRecord, Internship, Certification, Project, AssignmentSubmission, QuizResult, TeacherObservation, EmployerFeedback, PredictionResult
from app import db

MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "ml_models")
os.makedirs(MODEL_DIR, exist_ok=True)
MODEL_PATH = os.path.join(MODEL_DIR, "redi_classifier.pkl")
SCALER_PATH = os.path.join(MODEL_DIR, "redi_scaler.pkl")

REDI_THRESHOLD = 70

FEATURE_NAMES = [
    "Academic Avg", "Academic Std", "Grade Trend", "CA Average", "Exam Average",
    "Attendance Rate", "Internships", "Certifications",
    "Projects", "Assignment Score", "Assignment Count", "Quiz Score",
    "Teacher Observation", "Employer Feedback", "Skills Count", "Semester Progress"
]

_model_instance = None
_scaler_instance = None

def _batch_features(student_ids):
    if not student_ids:
        return defaultdict(lambda: [0]*16)
    ids_set = set(student_ids)
    sid_list = list(ids_set)

    sp_map = {s.id: (s.duration_years or 2, s.current_semester or 1, s.skills or "")
              for s in StudentProfile.query.filter(StudentProfile.id.in_(sid_list)).all()}

    sem_rows = SemesterResult.query.filter(SemesterResult.student_id.in_(sid_list)).all()
    acad_map = defaultdict(list)
    ca_map = defaultdict(list)
    exam_map = defaultdict(list)
    for r in sem_rows:
        acad_map[r.student_id].append((r.semester_number or 0, r.overall_score or 0))
        ca_map[r.student_id].append(r.ca_score or 0)
        exam_map[r.student_id].append(r.exam_score or 0)

    att_rows = db.session.query(
        AttendanceRecord.student_id, AttendanceRecord.status
    ).filter(AttendanceRecord.student_id.in_(sid_list)).all()
    att_map = defaultdict(lambda: {"total": 0, "present": 0})
    for sid, status in att_rows:
        att_map[sid]["total"] += 1
        if status == "present":
            att_map[sid]["present"] += 1

    intern_counts = dict(db.session.query(Internship.student_id, db.func.count()).filter(
        Internship.student_id.in_(sid_list)).group_by(Internship.student_id).all())
    cert_counts = dict(db.session.query(Certification.student_id, db.func.count()).filter(
        Certification.student_id.in_(sid_list)).group_by(Certification.student_id).all())
    proj_counts = dict(db.session.query(Project.student_id, db.func.count()).filter(
        Project.student_id.in_(sid_list)).group_by(Project.student_id).all())

    sub_rows = AssignmentSubmission.query.filter(
        AssignmentSubmission.student_id.in_(sid_list),
        AssignmentSubmission.score.isnot(None)
    ).all()
    assign_map = defaultdict(list)
    for r in sub_rows:
        assign_map[r.student_id].append(r.score)

    qz_rows = QuizResult.query.filter(QuizResult.student_id.in_(sid_list)).all()
    quiz_map = defaultdict(list)
    for r in qz_rows:
        quiz_map[r.student_id].append(r.score / r.max_score if r.max_score else 0)

    obs_rows = TeacherObservation.query.filter(
        TeacherObservation.student_id.in_(sid_list)
    ).all()
    obs_map = defaultdict(list)
    for r in obs_rows:
        obs_map[r.student_id].append(r.participation_score)

    fb_rows = EmployerFeedback.query.filter(
        EmployerFeedback.student_id.in_(sid_list)
    ).all()
    fb_map = defaultdict(list)
    for r in fb_rows:
        fb_map[r.student_id].append(r.rating)

    features = {}
    for sid in ids_set:
        dur, cur_sem, skills_str = sp_map.get(sid, (2, 1, ""))

        sem_scores = acad_map.get(sid, [])
        scores_only = [s for _, s in sem_scores]
        academic = sum(scores_only) / len(scores_only) if scores_only else 0
        academic_std = float(np.std(scores_only)) if len(scores_only) > 1 else 0

        sorted_sems = sorted(sem_scores, key=lambda x: x[0])
        if len(sorted_sems) >= 2:
            x_vals = np.array([s[0] for s in sorted_sems], dtype=float)
            y_vals = np.array([s[1] for s in sorted_sems], dtype=float)
            slope = np.polyfit(x_vals, y_vals, 1)[0]
        else:
            slope = 0

        ca_scores = ca_map.get(sid, [])
        ca_avg = sum(ca_scores) / len(ca_scores) if ca_scores else 0

        exam_scores = exam_map.get(sid, [])
        exam_avg = sum(exam_scores) / len(exam_scores) if exam_scores else 0

        att = att_map.get(sid, {"total": 0, "present": 0})
        att_rate = (att["present"] / att["total"] * 100) if att["total"] else 0

        n_internships = intern_counts.get(sid, 0)
        n_certs = cert_counts.get(sid, 0)
        n_projects = proj_counts.get(sid, 0)

        sc = assign_map.get(sid, [])
        assign_score = sum(sc) / len(sc) if sc else 0
        n_assignments = len(sc)

        qz = quiz_map.get(sid, [])
        quiz_score = (sum(qz) / len(qz) * 100) if qz else 0

        obs_scores = obs_map.get(sid, [])
        obs_avg = sum(obs_scores) / len(obs_scores) if obs_scores else 0

        fb_scores = fb_map.get(sid, [])
        fb_avg = sum(fb_scores) / len(fb_scores) if fb_scores else 0

        n_skills = len([s for s in skills_str.split(",") if s.strip()]) if skills_str else 0

        total_sems = dur * 2
        sem_progress = cur_sem / total_sems

        features[sid] = [academic, academic_std, slope, ca_avg, exam_avg,
                         att_rate, n_internships, n_certs, n_projects,
                         assign_score, n_assignments, quiz_score,
                         obs_avg, fb_avg, n_skills, sem_progress]

    return features

def extract_features(student_profile):
    feats = _batch_features([student_profile.id])
    return np.array([feats[student_profile.id]])

def build_training_data():
    students = StudentProfile.query.all()
    sids = [s.id for s in students]
    feat_map = _batch_features(sids)
    semester_has = set(r.student_id for r in SemesterResult.query.filter(
        SemesterResult.student_id.in_(sids)).all())
    X, y = [], []
    for s in students:
        if s.id not in semester_has:
            continue
        label = 1 if (s.eri_score or 0) >= REDI_THRESHOLD else 0
        X.append(feat_map.get(s.id, [0]*16))
        y.append(label)
    return np.array(X), np.array(y)

def train():
    X, y = build_training_data()
    if len(X) < 5:
        return {"error": "Not enough students with data. Need at least 5."}

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    n_folds = min(5, np.bincount(y).min())
    if n_folds < 2:
        n_folds = 2

    cv = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=42)

    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42, stratify=y)

    param_grid = {
        "n_estimators": [100, 200, 300],
        "max_depth": [10, 15, None],
        "min_samples_split": [2, 5, 10],
        "min_samples_leaf": [1, 2, 4]
    }

    base_model = RandomForestClassifier(random_state=42, class_weight="balanced")
    grid = GridSearchCV(
        base_model, param_grid, cv=cv, scoring="f1", n_jobs=-1, verbose=0
    )
    grid.fit(X_train, y_train)

    model = grid.best_estimator_

    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
    with open(SCALER_PATH, "wb") as f:
        pickle.dump(scaler, f)

    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]

    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, zero_division=0)
    rec = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)

    try:
        auc = roc_auc_score(y_test, y_prob)
    except Exception:
        auc = 0

    importances = model.feature_importances_
    top_idx = np.argsort(importances)[::-1][:3]
    top_features = [{"feature": FEATURE_NAMES[i], "weight": round(float(importances[i]), 3)} for i in top_idx]

    train_acc = accuracy_score(y_train, model.predict(X_train))

    cv_results = grid.cv_results_
    cv_acc = float(np.mean([cv_results[f"split{i}_test_score"][grid.best_index_] for i in range(n_folds)]))

    return {
        "accuracy": round(acc, 3),
        "precision": round(prec, 3),
        "recall": round(rec, 3),
        "f1_score": round(f1, 3),
        "auc": round(auc, 3),
        "train_samples": int(len(X_train)),
        "test_samples": int(len(X_test)),
        "class_0": int(np.sum(y == 0)),
        "class_1": int(np.sum(y == 1)),
        "top_features": top_features,
        "train_accuracy": round(train_acc, 3),
        "cv_f1": round(float(grid.best_score_), 3),
        "best_params": grid.best_params_,
        "model_version": "v3",
        "n_features": 16
    }

def _load_model():
    global _model_instance, _scaler_instance
    if _model_instance is None or _scaler_instance is None:
        if not os.path.exists(MODEL_PATH):
            return None, None
        with open(MODEL_PATH, "rb") as f:
            _model_instance = pickle.load(f)
        with open(SCALER_PATH, "rb") as f:
            _scaler_instance = pickle.load(f)
    return _model_instance, _scaler_instance

def predict(student_profile, model_version="v3"):
    model, scaler = _load_model()
    if model is None:
        return {"probability": 0, "prediction": False, "error": "Model not trained yet"}

    feats = extract_features(student_profile)
    feats_scaled = scaler.transform(feats)
    prob = model.predict_proba(feats_scaled)[0, 1]
    pred = bool(model.predict(feats_scaled)[0])

    importances = model.feature_importances_
    top_idx = np.argsort(importances)[::-1][:3]
    top_factors = [FEATURE_NAMES[i] for i in top_idx]

    _save_prediction(student_profile, prob, pred, model_version, feats[0].tolist(), top_factors)

    return {"probability": round(float(prob) * 100, 1), "prediction": pred, "top_factors": top_factors}

def _save_prediction(student_profile, probability, prediction, model_version, features_list, top_factors):
    existing = PredictionResult.query.filter_by(student_id=student_profile.id).first()
    if existing:
        existing.probability = round(float(probability), 4)
        existing.prediction = prediction
        existing.model_version = model_version
        existing.features_json = json.dumps(features_list)
        existing.top_factors = ", ".join(top_factors)
    else:
        pr = PredictionResult(
            student_id=student_profile.id,
            probability=round(float(probability), 4),
            prediction=prediction,
            model_version=model_version,
            features_json=json.dumps(features_list),
            top_factors=", ".join(top_factors)
        )
        db.session.add(pr)
    db.session.commit()

def predict_all():
    students = StudentProfile.query.all()
    sids = [s.id for s in students]
    feat_map = _batch_features(sids)
    model, scaler = _load_model()
    if model is None:
        return 0

    importances = model.feature_importances_
    top_idx = np.argsort(importances)[::-1][:3]
    top_factors = [FEATURE_NAMES[i] for i in top_idx]
    count = 0
    feat_array = np.array([feat_map.get(sid, [0]*16) for sid in sids])
    if len(feat_array) == 0:
        return 0
    feat_scaled = scaler.transform(feat_array)
    probs = model.predict_proba(feat_scaled)[:, 1]
    preds = model.predict(feat_scaled)

    for s, prob, pred in zip(students, probs, preds):
        try:
            _save_prediction(s, prob, bool(pred), "v3",
                             feat_map.get(s.id, [0]*16), top_factors)
            count += 1
        except Exception:
            continue
    return count

def get_stats():
    total = PredictionResult.query.count()
    ready = PredictionResult.query.filter_by(prediction=True).count()
    not_ready = PredictionResult.query.filter_by(prediction=False).count()
    avg_prob = db.session.query(db.func.avg(PredictionResult.probability)).scalar() or 0
    return {
        "total_predictions": total,
        "predicted_ready": ready,
        "predicted_not_ready": not_ready,
        "avg_probability": round(float(avg_prob) * 100, 1)
    }
