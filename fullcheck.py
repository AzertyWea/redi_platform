import sys
sys.path.insert(0, ".")
from app import create_app, db
from app.models import User

app = create_app()
app.config["TESTING"] = True
app.config["WTF_CSRF_ENABLED"] = False
app.app_context().push()

def check_html(resp, label):
    body = resp.get_data(as_text=True)
    problems = []
    if resp.status_code >= 500:
        problems.append(f"HTTP {resp.status_code} SERVER ERROR")
    if "Traceback" in body or "Internal Server Error" in body:
        problems.append("Traceback/error text found in body")
    if resp.status_code == 200 and len(body) < 200:
        problems.append(f"Suspiciously short body ({len(body)} chars) - possible broken render")
    status = "OK" if not problems else " / ".join(problems)
    print(f"  {label}: HTTP {resp.status_code} -- {status}")
    return not problems

print("=== STEP 1: WELCOME PAGE (fresh, no session) ===")
client = app.test_client()
r = client.get("/", follow_redirects=False)
print(f"  GET / : {r.status_code} -> redirects to: {r.headers.get('Location','')}")
r2 = client.get("/", follow_redirects=True)
check_html(r2, "GET / (following redirects)")

print("\n=== STEP 2: DIRECT LOGIN PAGE ACCESS ===")
client2 = app.test_client()
r = client2.get("/login", follow_redirects=False)
check_html(r, "GET /login (should show real login form, not redirect)")
body = r.get_data(as_text=True)
has_form = "matricule" in body.lower() and "password" in body.lower()
print(f"  Contains login form fields: {has_form}")

print("\n=== STEP 3: LOGIN + DASHBOARD PER ROLE ===")
role_creds = {
    "admin": ("ADMIN01", "admin123"),
    "teacher": ("T002", "teacher123"),
    "student": (User.query.filter_by(role='student').first().matricule, "student123"),
    "employer": ("E002", "employer123"),
}
role_dashboard = {
    "admin": "/admin/dashboard",
    "teacher": "/teacher/dashboard",
    "student": "/student/dashboard",
    "employer": "/employer/dashboard",
}
role_sidebar_markers = {
    "admin": ["Timetable","Structure","Users"],
    "teacher": ["Take Attendance","Dashboard"],
    "student": ["Results","Documents"],
    "employer": ["Search"],
}

for role, (mat, pw) in role_creds.items():
    c = app.test_client()
    lr = c.post("/login", data={"matricule": mat, "password": pw}, follow_redirects=False)
    print(f"\n[{role.upper()}] login {mat}: {lr.status_code} -> {lr.headers.get('Location','xxx')}")
    if lr.status_code != 302:
        print(f"  !! LOGIN FAILED - body snippet: {lr.get_data(as_text=True)[:200].encode('ascii','ignore').decode()}")
        continue
    dr = c.get(role_dashboard[role], follow_redirects=False)
    ok = check_html(dr, f"GET {role_dashboard[role]}")
    if ok:
        body = dr.get_data(as_text=True)
        for marker in role_sidebar_markers[role]:
            found = marker in body
            print(f"    sidebar contains '{marker}': {found}")
    lo = c.get("/logout", follow_redirects=False)
    print(f"  logout: {lo.status_code} -> {lo.headers.get('Location','')}")

print("\n=== STEP 4: WELCOME.HTML DIRECT RENDER TEST ===")
c3 = app.test_client()
r = c3.get("/", follow_redirects=False)
check_html(r, "GET / (should show welcome.html when not authenticated)")

print("\n=== DONE ===")
