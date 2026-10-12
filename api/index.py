import os
import sys
from pathlib import Path

# Add backend directory to sys.path so Django can locate grocery_core
CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CURRENT_DIR / 'backend'
sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'grocery_core.settings')

from django.core.wsgi import get_wsgi_application
app = get_wsgi_application()
