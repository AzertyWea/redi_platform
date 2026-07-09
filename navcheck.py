import sys
sys.path.insert(0, ".")
from app import create_app, db
from app.models import User

app = create_app()
app.config["TESTING"] = True
app.config["WTF_CSRF_ENABLED"] = False
app.app_context().push()

accounts = {
    "admin": "ADMIN01",
    "teacher": "T002",
    "student": None,
    "employer": "E002",
}
s = User.query.filter_by(role="student").first()
if s:
    accounts["student"] = s.matricule

role_routes = {
    "admin": ["/admin/dashboard","/admin/bulk-import","/admin/documents","/admin/users",
              "/admin/structure","/admin/timetable","/admin/bulk-import/template/roster",
              "/admin/bulk-import/template/grades","/admin/bulk-import/template/documents"],
    "teacher": ["/teacher/dashboard","/teacher/attendance","/teacher/assignments",
                "/teacher/quizzes","/teacher/observations"],
    "student": ["/student/dashboard","/student/results","/student/documents",
                "/student/coach","/student/profile","/student/career-data"],
    "employer": ["/employer/dashboard","/employer/search"],
}

print("=== NAVIGATION CHECK ===\n")
for role, matricule in accounts.items():
    if not matricule:
        print(f"[{role.upper()}] SKIPPED - no account found")
        continue
    client = app.test_client()
    password = "admin123" if role == "admin" else "teacher123" if role == "teacher" else "student123" if role == "student" else "employer123"
    login_resp = client.post("/login", data={"matricule": matricule, "password": password}, follow_redirects=False)
    print(f"[{role.upper()}] login as {matricule}: status {login_resp.status_code} -> {login_resp.headers.get('Location','')}")
    if login_resp.status_code != 302:
        print(f"  !! LOGIN FAILED for {role}")
        continue
    for route in role_routes[role]:
        r = client.get(route, follow_redirects=False)
        flag = "" if r.status_code in (200,) else "  <-- CHECK THIS"
        print(f"  GET {route}: {r.status_code}{flag}")
    client.get("/logout", follow_redirects=False)
    print()

print("=== BASE.HTML SIDEBAR CHECK (raw file scan) ===")
import re
with open("app/templates/base.html", encoding="utf-8") as f:
    content = f.read()
print(f"base.html length: {len(content)} chars")
blocks = re.findall(r"{% block (\w+) %}", content)
print(f"Blocks defined in base.html: {blocks}")

print("\n=== DONE ===")
