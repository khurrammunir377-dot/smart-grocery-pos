import os
import sys
import shutil
from pathlib import Path

# Ensure backend directory is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# On Vercel, copy database and run migrations to /tmp if needed
if os.environ.get('VERCEL'):
    tmp_db = Path('/tmp/db.sqlite3')
    seed_db = BASE_DIR / 'db.sqlite3'
    if not tmp_db.exists() and seed_db.exists():
        try:
            shutil.copy2(seed_db, tmp_db)
        except Exception as e:
            print("Failed to copy seed db:", e)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'grocery_core.settings')

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Ensure migrations are applied on /tmp if seed was empty
if os.environ.get('VERCEL'):
    try:
        from django.core.management import call_command
        call_command('migrate', interactive=False)
    except Exception as e:
        print("Auto-migration in wsgi:", e)

app = application
