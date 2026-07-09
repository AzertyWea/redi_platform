import sys; sys.path.insert(0, ".")
import pytest
from app import create_app, db as _db
from app.models import User, StudentProfile, Course, SchoolClass, ScheduleEntry

@pytest.fixture(scope="session")
def app():
    app = create_app()
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    return app

@pytest.fixture(scope="function")
def client(app):
    with app.app_context():
        with app.test_client() as c:
            yield c

@pytest.fixture(scope="function")
def ctx(app):
    with app.app_context():
        yield

@pytest.fixture(scope="function")
def admin_client(client):
    r = client.post("/login", data={"matricule": "ADMIN01", "password": "admin123"}, follow_redirects=False)
    assert r.status_code == 302
    return client

@pytest.fixture(scope="function")
def teacher_client(client):
    r = client.post("/login", data={"matricule": "T002", "password": "teacher123"}, follow_redirects=False)
    assert r.status_code == 302
    return client

@pytest.fixture(scope="function")
def student_client(client):
    student = User.query.filter_by(role="student").first()
    assert student, "No student found in database"
    r = client.post("/login", data={"matricule": student.matricule, "password": "student123"}, follow_redirects=False)
    assert r.status_code == 302
    return client

@pytest.fixture(scope="function")
def employer_client(client):
    r = client.post("/login", data={"matricule": "E002", "password": "employer123"}, follow_redirects=False)
    assert r.status_code == 302
    return client
