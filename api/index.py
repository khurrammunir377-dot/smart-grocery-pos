import os
import sys
from pathlib import Path

# Add backend directory to sys.path so Django can locate grocery_core
ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / 'backend'

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'grocery_core.settings')

from django.core.wsgi import get_wsgi_application
app = get_wsgi_application()
