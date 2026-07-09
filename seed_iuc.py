from app import create_app, db
from app.models import Department, Program

app = create_app()
app.app_context().push()

schools = {
    "ICIA - Institute of Commerce and Business Engineering": [
        "Accounting and Finance",
        "Banking and Finance",
        "Human Resources Management",
        "Marketing and Sales",
        "Business Management",
        "Transport and Logistics",
        "Audit and Control",
        "Quality Management",
        "Business Computing",
        "Corporate Communication"
    ],
    "3IAC - Institute of Computer Engineering of Central Africa": [
        "Web and Application Development",
        "Networks and Telecommunications",
        "Information Security",
        "Artificial Intelligence / Data Science",
        "Software Engineering",
        "Industrial Computing",
        "IT Systems Maintenance"
    ],
    "ISTDI - Institute of Technology and Industrial Design": [
        "Electrical Engineering",
        "Mechanical Engineering",
        "Civil Engineering",
        "Automation and Industrial Computing",
        "Industrial Design / Architecture",
        "Mechatronics",
        "Industrial Systems Maintenance"
    ],
    "SEAS - School of Engineering and Applied Sciences": [
        "Applied Engineering"
    ],
    "ESTA - School of Agro-Industrial Sciences": [
        "Plant Production",
        "Animal Production",
        "Food Processing"
    ],
    "ISSA - Institute of Health Sciences": [
        "Nursing Care",
        "Laboratory Techniques",
        "Physiotherapy"
    ]
}

created_depts = 0
created_progs = 0

for school_name, programs in schools.items():
    dept = Department.query.filter_by(name=school_name).first()
    if not dept:
        dept = Department(name=school_name)
        db.session.add(dept)
        db.session.flush()
        created_depts += 1

    for prog_name in programs:
        existing = Program.query.filter_by(name=prog_name, department_id=dept.id).first()
        if not existing:
            db.session.add(Program(name=prog_name, department_id=dept.id))
            created_progs += 1

db.session.commit()
print(f"Seeded {created_depts} schools and {created_progs} programs")
