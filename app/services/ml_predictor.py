import json, os, pickle
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
from app.models import StudentProfile, SemesterResult, AttendanceRecord, Internship, Certification, Project, AssignmentSubmission, QuizResult, TeacherObservation, EmployerFeedback, PredictionResult
from app import db

MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "ml_models")
os.makedirs(MODEL_DIR, exist_ok=True)
MODEL_PATH = os.path.join(MODEL_DIR, "redi_classifier.pkl")
SCALER_PATH = os.path.join(MODEL_DIR, "redi_scaler.pkl")

REDI_THRESHOLD = 70

def extract_features(student_profile):
    """Build a feature vector for a student: 8 numeric features."""
    sid = student_profile.id
    eri = student_profile.eri_score or 0

    results = SemesterResult.query.filter_by(student_id=sid).all()
    academic = sum(r.overall_score for r in results) / len(results) if results else 0

    records = AttendanceRecord.query.filter_by(student_id=sid).all()
    att_rate = (sum(1 for r in records if r.status == "present") / len(records) * 100) if records else 0

    n_internships = Internship.query.filter_by(student_id=sid).count()
    n_certs = Certification.query.filter_by(student_id=sid).count()
    n_projects = Project.query.filter_by(student_id=sid).count()

    submissions = AssignmentSubmission.query.filter_by(student_id=sid).all()
    scored = [s for s in submissions if s.score is not None]
    assign_score = (sum(s.score for s in scored) / len(scored)) if scored else 0

    q_results = QuizResult.query.filter_by(student_id=sid).all()
    quiz_score = (sum(q.score / q.max_score for q in q_results) / len(q_results) * 100) if q_results else 0

    total_sems = (student_profile.duration_years or 2) * 2
    sem_progress = (student_profile.current_semester or 1) / total_sems

    return np.array([[eri, academic, att_rate, n_internships, n_certs, n_projects, assign_score, sem_progress]])

FEATURE_NAMES = ["ERI Score", "Academic Avg", "Attendance Rate", "Internships", "Certifications", "Projects", "Assignment Score", "Semester Progress"]

def build_training_data():
    """Build X (feature matrix) and y (labels) from all students."""
    students = StudentProfile.query.all()
    X, y = [], []
    for s in students:
        results = SemesterResult.query.filter_by(student_id=s.id).order_by(SemesterResult.semester_number.desc()).first()
        if not results:
            continue
        label = 1 if (s.eri_score or 0) >= REDI_THRESHOLD else 0
        feats = extract_features(s)
        X.append(feats[0])
        y.append(label)
    return np.array(X), np.array(y)

def train():
    """Train a LogisticRegression model on all available student data. Returns metrics dict."""
    X, y = build_training_data()
    if len(X) < 5:
        return {"error": "Not enough students with data. Need at least 5."}

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42, stratify=y)

    model = LogisticRegression(max_iter=1000, random_state=42, class_weight="balanced")
    model.fit(X_train, y_train)

    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
    with open(SCALER_PATH, "wb") as f:
        pickle.dump(scaler, f)

    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1] if hasattr(model, "predict_proba") else y_pred

    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, zero_division=0)
    rec = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)

    try:
        auc = roc_auc_score(y_test, y_prob)
    except Exception:
        auc = 0

    coef = model.coef_[0]
    top_idx = np.argsort(np.abs(coef))[::-1][:3]
    top_features = [{"feature": FEATURE_NAMES[i], "weight": round(coef[i], 3)} for i in top_idx]

    train_acc = accuracy_score(y_train, model.predict(X_train))

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
        "model_version": "v1"
    }

def predict(student_profile, model_version="v1"):
    """Predict REDI readiness for a single student. Returns dict with probability, decision, top factors."""
    if not os.path.exists(MODEL_PATH):
        return {"probability": 0, "prediction": False, "error": "Model not trained yet"}

    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)
    with open(SCALER_PATH, "rb") as f:
        scaler = pickle.load(f)

    feats = extract_features(student_profile)
    feats_scaled = scaler.transform(feats)
    prob = model.predict_proba(feats_scaled)[0, 1]
    pred = bool(model.predict(feats_scaled)[0])

    coef = model.coef_[0]
    top_idx = np.argsort(np.abs(coef))[::-1][:3]
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
    """Run prediction for every student with data. Returns count."""
    students = StudentProfile.query.all()
    if not os.path.exists(MODEL_PATH):
        return 0
    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)
    with open(SCALER_PATH, "rb") as f:
        scaler = pickle.load(f)
    count = 0
    for s in students:
        try:
            feats = extract_features(s)
            feats_scaled = scaler.transform(feats)
            prob = model.predict_proba(feats_scaled)[0, 1]
            pred = bool(model.predict(feats_scaled)[0])
            coef = model.coef_[0]
            top_idx = np.argsort(np.abs(coef))[::-1][:3]
            top_factors = [FEATURE_NAMES[i] for i in top_idx]
            _save_prediction(s, prob, pred, "v1", feats[0].tolist(), top_factors)
            count += 1
        except Exception:
            continue
    return count

def get_stats():
    """Return summary stats about predictions."""
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
