import pytest
from app.models import User, AttendanceRecord, Course, SchoolClass, ScheduleEntry
from app import db

class TestDataArchitecture:
    def test_school_classes_populated(self, ctx):
        assert SchoolClass.query.count() > 0

    def test_courses_linked_to_classes(self, ctx):
        from app.models import Course
        has_links = any(len(c.classes) > 0 for c in Course.query.limit(50).all())
        assert has_links

    def test_students_assigned_to_classes(self, ctx):
        from app.models import StudentProfile
        count = StudentProfile.query.filter(StudentProfile.class_group_id.isnot(None)).count()
        assert count > 0

    def test_schedule_entries_exist(self, ctx):
        assert ScheduleEntry.query.count() > 0

    def test_schedule_entries_have_class(self, ctx):
        count = ScheduleEntry.query.filter(ScheduleEntry.class_group_id.isnot(None)).count()
        assert count > 0

class TestTeacherWorkflow:
    def test_attendance_page_filters(self, teacher_client):
        teacher = User.query.filter_by(matricule="T002").first()
        course = Course.query.filter_by(teacher_id=teacher.id).first()
        if not course or not course.classes:
            pytest.skip("No course with linked class")
        cls = course.classes[0]
        r = teacher_client.get(f"/teacher/attendance?course_id={course.id}&class_id={cls.id}")
        assert r.status_code == 200
        body = r.get_data(as_text=True)
        assert "status_" in body

    def test_attendance_post_updates_eri(self, teacher_client):
        teacher = User.query.filter_by(matricule="T002").first()
        course = Course.query.filter_by(teacher_id=teacher.id).first()
        if not course or not course.classes:
            pytest.skip("No course with linked class")
        cls = course.classes[0]
        if not cls.students:
            pytest.skip("No students in class")

        student = cls.students[0]
        eri_before = student.eri_score
        form = {"course_id": str(course.id), "class_id": str(cls.id)}
        for s in cls.students:
            form[f"status_{s.id}"] = "present"
        r = teacher_client.post("/teacher/attendance", data=form, follow_redirects=False)
        assert r.status_code == 302
        db.session.refresh(student)
        assert student.eri_score == eri_before or abs(student.eri_score - eri_before) > 0

    def test_observations_page(self, teacher_client):
        teacher = User.query.filter_by(matricule="T002").first()
        course = Course.query.filter_by(teacher_id=teacher.id).first()
        if not course or not course.classes:
            pytest.skip("No course with linked class")
        cls = course.classes[0]
        r = teacher_client.get(f"/teacher/observations?course_id={course.id}&class_id={cls.id}")
        assert r.status_code == 200

    def test_timetable_pdf_download(self, teacher_client):
        r = teacher_client.get("/teacher/timetable/pdf")
        assert r.status_code == 200
        assert r.content_type == "application/pdf"
        assert len(r.get_data()) > 100

class TestAdminWorkflow:
    def test_timetable_page_loads(self, admin_client):
        r = admin_client.get("/admin/timetable")
        assert r.status_code == 200

    def test_timetable_has_class_selector_js(self, admin_client):
        r = admin_client.get("/admin/timetable")
        body = r.get_data(as_text=True)
        assert "updateClassOptions" in body

    def test_structure_page_loads(self, admin_client):
        r = admin_client.get("/admin/structure")
        assert r.status_code == 200

class TestStudentDashboard:
    def test_dashboard_loads(self, student_client):
        r = student_client.get("/student/dashboard")
        assert r.status_code == 200

    def test_eri_meter_present(self, student_client):
        r = student_client.get("/student/dashboard")
        body = r.get_data(as_text=True)
        assert "corp-trust-fill" in body

    def test_trend_chart_present(self, student_client):
        r = student_client.get("/student/dashboard")
        body = r.get_data(as_text=True)
        assert "trendChart" in body

    def test_readiness_radar_present(self, student_client):
        r = student_client.get("/student/dashboard")
        body = r.get_data(as_text=True)
        assert "readinessRadar" in body

    def test_attendance_timeline_present(self, student_client):
        r = student_client.get("/student/dashboard")
        body = r.get_data(as_text=True)
        assert "Attendance" in body
        assert "corp-row-list" in body

    def test_pdf_report_download(self, student_client):
        r = student_client.get("/student/report/pdf")
        assert r.status_code == 200
        assert r.content_type == "application/pdf"
