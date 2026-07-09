import sys
import os

path = os.path.dirname(os.path.abspath(__file__))
if path not in sys.path:
    sys.path.insert(0, path)

os.environ['FLASK_ENV'] = 'production'
os.environ['WTF_CSRF_ENABLED'] = 'True'

from run import app as application
