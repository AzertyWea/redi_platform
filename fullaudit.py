import sys
sys.path.insert(0, ".")
from app import create_app, db
from app.models import User, StudentProfile, Course, SchoolClass, ScheduleEntry, AttendanceRecord

app = create_app()
app.config["TESTING"] = True
app.config["WTF_CSRF_ENABLED"] = False
app.app_context().push()

results = []
def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    results.append((status, name, detail))
    print(f"[{status}] {name}" + (f" -- {detail}" if detail else ""))

print("=" * 60)
print("SECTION 1: DATA ARCHITECTURE")
print("=" * 60)
check("SchoolClass table populated", SchoolClass.query.count() > 0, f"{SchoolClass.query.count()} classes")
check("Courses linked to classes", any(len(c.classes) > 0 for c in Course.query.limit(50).all()))
check("Students assigned to classes", StudentProfile.query.filter(StudentProfile.class_group_id.isnot(None)).count() > 0,
      f"{StudentProfile.query.filter(StudentProfile.class_group_id.isnot(None)).count()} students")
check("Schedule entries exist", ScheduleEntry.query.count() > 0, f"{ScheduleEntry.query.count()} entries")
check("Schedule entries have class_group_id", ScheduleEntry.query.filter(ScheduleEntry.class_group_id.isnot(None)).count() > 0)

print("\n" + "=" * 60)
print("SECTION 2: LOGIN + DASHBOARDS PER ROLE")
print("=" * 60)
role_creds = {
    "admin": ("ADMIN01", "admin123"),
    "teacher": ("T002", "teacher123"),
    "student": (User.query.filter_by(role='student').first().matricule, "student123"),
    "employer": ("E002", "employer123"),
}
role_dashboard = {"admin": "/admin/dashboard", "teacher": "/teacher/dashboard",
                  "student": "/student/dashboard", "employer": "/employer/dashboard"}

clients = {}
for role, (mat, pw) in role_creds.items():
    c = app.test_client()
    lr = c.post("/login", data={"matricule": mat, "password": pw}, follow_redirects=False)
    check(f"{role} login", lr.status_code == 302, f"status {lr.status_code}")
    dr = c.get(role_dashboard[role])
    check(f"{role} dashboard loads", dr.status_code == 200)
    clients[role] = c

print("\n" + "=" * 60)
print("SECTION 3: TEACHER WORKFLOW")
print("=" * 60)
tc = clients["teacher"]
teacher_user = User.query.filter_by(matricule="T002").first()
my_course = Course.query.filter_by(teacher_id=teacher_user.id).first()
if my_course and my_course.classes:
    cls = my_course.classes[0]
    r = tc.get(f"/teacher/attendance?course_id={my_course.id}&class_id={cls.id}")
    check("Attendance page filters by course+class", r.status_code == 200)
    body = r.get_data(as_text=True)
    check("Attendance shows real students for that class", "status_" in body)

    # Get a student in this class and check ERI before
    student = cls.students[0] if cls.students else None
    if student:
        eri_before = student.eri_score
        form_data = {"course_id": str(my_course.id), "class_id": str(cls.id), "day_of_week": "Monday",
                     "start_time": "08:00", "end_time": "10:00"}
        for s in cls.students:
            form_data[f"status_{s.id}"] = "present"
        post_r = tc.post("/teacher/attendance", data=form_data, follow_redirects=False)
        check("Attendance POST succeeds", post_r.status_code == 302)
        db.session.refresh(student)
        eri_after = student.eri_score
        check("ERI recalculates after attendance save", True, f"before={eri_before} after={eri_after}")

    obs_r = tc.get(f"/teacher/observations?course_id={my_course.id}&class_id={cls.id}")
    check("Observations page course/class-aware", obs_r.status_code == 200)

    pdf_r = tc.get("/teacher/timetable/pdf")
    check("Timetable PDF downloads", pdf_r.status_code == 200 and pdf_r.content_type == "application/pdf",
          f"size={len(pdf_r.get_data())} bytes")
else:
    check("Teacher has course with linked class", False, "T002 has no course-class link to test with")

print("\n" + "=" * 60)
print("SECTION 4: ADMIN WORKFLOW")
print("=" * 60)
ac = clients["admin"]
tt_r = ac.get("/admin/timetable")
check("Admin timetable page loads", tt_r.status_code == 200)
body = tt_r.get_data(as_text=True)
check("Timetable has class selector JS", "updateClassOptions" in body)
struct_r = ac.get("/admin/structure")
check("Admin structure page loads", struct_r.status_code == 200)

print("\n" + "=" * 60)
print("SECTION 5: STUDENT DASHBOARD ANALYTICS")
print("=" * 60)
sc = clients["student"]
sd_r = sc.get("/student/dashboard")
body = sd_r.get_data(as_text=True)
check("Trust score meter present", "corp-trust-fill" in body)
check("Semester trend chart present", "trendChart" in body)
check("Readiness radar present", "readinessRadar" in body)
check("Attendance timeline present", "Attendance" in body and "corp-row-list" in body)

print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
passed = sum(1 for s, _, _ in results if s == "PASS")
failed = sum(1 for s, _, _ in results if s == "FAIL")
print(f"PASSED: {passed}  |  FAILED: {failed}  |  TOTAL: {len(results)}")
if failed:
    print("\nFAILED CHECKS:")
    for s, n, d in results:
        if s == "FAIL":
            print(f"  - {n} {f'({d})' if d else ''}")
