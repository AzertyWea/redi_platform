import sys
import os

path = os.path.dirname(os.path.abspath(__file__))
if path not in sys.path:
    sys.path.insert(0, path)

os.environ['FLASK_ENV'] = 'production'
os.environ['WTF_CSRF_ENABLED'] = 'True'

from app import create_app, db
from run import migrate_schema, seed_data

application = create_app()
with application.app_context():
    db.create_all()
    migrate_schema()
    seed_data()
