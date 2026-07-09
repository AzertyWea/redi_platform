import pytest

ROLE_ROUTES = {
    "admin": [
        "/admin/dashboard", "/admin/bulk-import", "/admin/documents",
        "/admin/users", "/admin/structure", "/admin/timetable",
        "/admin/bulk-import/template/roster",
        "/admin/bulk-import/template/grades",
        "/admin/bulk-import/template/documents",
    ],
    "teacher": [
        "/teacher/dashboard", "/teacher/attendance",
        "/teacher/assignments", "/teacher/quizzes", "/teacher/observations",
    ],
    "student": [
        "/student/dashboard", "/student/results", "/student/documents",
        "/student/coach", "/student/profile", "/student/career-data",
    ],
    "employer": [
        "/employer/dashboard", "/employer/search",
    ],
}

class TestAdminRoutes:
    def test_all_return_200(self, admin_client):
        for route in ROLE_ROUTES["admin"]:
            r = admin_client.get(route, follow_redirects=False)
            assert r.status_code == 200, f"{route} returned {r.status_code}"

class TestTeacherRoutes:
    def test_all_return_200(self, teacher_client):
        for route in ROLE_ROUTES["teacher"]:
            r = teacher_client.get(route, follow_redirects=False)
            assert r.status_code == 200, f"{route} returned {r.status_code}"

class TestStudentRoutes:
    def test_all_return_200(self, student_client):
        for route in ROLE_ROUTES["student"]:
            r = student_client.get(route, follow_redirects=False)
            assert r.status_code == 200, f"{route} returned {r.status_code}"

class TestEmployerRoutes:
    def test_all_return_200(self, employer_client):
        for route in ROLE_ROUTES["employer"]:
            r = employer_client.get(route, follow_redirects=False)
            assert r.status_code == 200, f"{route} returned {r.status_code}"
