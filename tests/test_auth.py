import pytest

class TestAuth:
    def test_welcome_page(self, client):
        r = client.get("/", follow_redirects=True)
        assert r.status_code == 200
        body = r.get_data(as_text=True)
        assert len(body) > 200

    def test_login_page(self, client):
        r = client.get("/login", follow_redirects=False)
        assert r.status_code == 200
        body = r.get_data(as_text=True).lower()
        assert "matricule" in body
        assert "password" in body

    def test_admin_login(self, client):
        r = client.post("/login", data={"matricule": "ADMIN01", "password": "admin123"}, follow_redirects=False)
        assert r.status_code == 302
        assert "/admin/dashboard" in r.headers.get("Location", "")

    def test_teacher_login(self, client):
        r = client.post("/login", data={"matricule": "T002", "password": "teacher123"}, follow_redirects=False)
        assert r.status_code == 302
        assert "/teacher/dashboard" in r.headers.get("Location", "")

    def test_student_login(self, client):
        from app.models import User
        student = User.query.filter_by(role="student").first()
        r = client.post("/login", data={"matricule": student.matricule, "password": "student123"}, follow_redirects=False)
        assert r.status_code == 302
        assert "/student/dashboard" in r.headers.get("Location", "")

    def test_employer_login(self, client):
        r = client.post("/login", data={"matricule": "E002", "password": "employer123"}, follow_redirects=False)
        assert r.status_code == 302
        assert "/employer/dashboard" in r.headers.get("Location", "")

    def test_logout(self, client):
        client.post("/login", data={"matricule": "ADMIN01", "password": "admin123"}, follow_redirects=False)
        r = client.get("/logout", follow_redirects=False)
        assert r.status_code == 302
        assert "/login" in r.headers.get("Location", "")

    def test_invalid_login(self, client):
        r = client.post("/login", data={"matricule": "FAKE", "password": "wrong"}, follow_redirects=False)
        assert r.status_code == 200
