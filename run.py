from app import create_app, db
from app.models import User, StudentProfile, SemesterResult, Document, Notification

app = create_app()

def seed_data():
    if User.query.first():
        return
    users = [
        {'matricule':'S001','name':'Amina Kenfack','email':'amina@redi.cm','role':'student','dept':'Computer Science'},
        {'matricule':'S041','name':'Kevin Mbarga','email':'kevin@redi.cm','role':'student','dept':'Business Management'},
        {'matricule':'S131','name':'Pascal Nguemo','email':'pascal@redi.cm','role':'student','dept':'Computer Science'},
        {'matricule':'T001','name':'Dr. Marie Dipene','email':'marie@redi.cm','role':'teacher','dept':'Computer Science'},
        {'matricule':'ADMIN01','name':'Admin REDI','email':'admin@redi.cm','role':'admin','dept':'Administration'},
        {'matricule':'E001','name':'TechCorp HR','email':'hr@techcorp.cm','role':'employer','dept':'Industry'},
    ]
    for u in users:
        user = User(matricule=u['matricule'], name=u['name'], email=u['email'],
                    role=u['role'], department=u['dept'])
        pwd = 'admin1234' if u['role'] == 'admin' else 'demo1234'
        user.set_password(pwd)
        db.session.add(user)
    db.session.commit()

    profiles = [
        {'mat':'S001','program':'HND Software Engineering','eri':84.0,'sem':3},
        {'mat':'S041','program':'HND Business Management','eri':67.0,'sem':2},
        {'mat':'S131','program':'BEng Computer Science','eri':91.0,'sem':4},
    ]
    for p in profiles:
        user = User.query.filter_by(matricule=p['mat']).first()
        profile = StudentProfile(user_id=user.id, program=p['program'],
                                 eri_score=p['eri'], current_semester=p['sem'],
                                 duration_years=2)
        db.session.add(profile)
    db.session.commit()

    results_data = [
        ('S001',1,72,65,85,78,0),
        ('S001',2,78,74,90,85,82),
        ('S041',1,65,60,78,70,0),
        ('S041',2,70,68,82,74,75),
        ('S131',1,85,88,95,90,0),
        ('S131',2,88,90,92,88,85),
    ]
    for mat,sem,ca,exam,att,proj,intern in results_data:
        user = User.query.filter_by(matricule=mat).first()
        profile = StudentProfile.query.filter_by(user_id=user.id).first()
        overall = round((ca*0.3 + exam*0.5 + att*0.05 + proj*0.1 + intern*0.05), 1)
        r = SemesterResult(student_id=profile.id, semester_number=sem,
            ca_score=ca, exam_score=exam, attendance=att,
            project_score=proj, internship_score=intern, overall_score=overall)
        db.session.add(r)

    docs_data = [
        ('S001','CA Results S1','ca_s1_amina.pdf',True),
        ('S001','Transcript S2','transcript_s2_amina.pdf',True),
        ('S131','CA Results S1','ca_s1_pascal.pdf',True),
    ]
    for mat,dtype,fname,verified in docs_data:
        user = User.query.filter_by(matricule=mat).first()
        profile = StudentProfile.query.filter_by(user_id=user.id).first()
        doc = Document(student_id=profile.id, doc_type=dtype,
                       filename=fname, is_verified=verified, qr_hash='abc123')
        db.session.add(doc)

    notifs = [
        ('S001','ERI Score Updated','Your ERI score increased to 84% after completing your internship!'),
        ('S001','New Document','Your Semester 2 transcript has been uploaded.'),
        ('S131','Top Performer','You are in the top 5% of your department. Congratulations!'),
    ]
    for mat,title,msg in notifs:
        user = User.query.filter_by(matricule=mat).first()
        n = Notification(user_id=user.id, title=title, message=msg)
        db.session.add(n)

    db.session.commit()
    print('Seed data loaded.')

with app.app_context():
    db.create_all()
    seed_data()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
