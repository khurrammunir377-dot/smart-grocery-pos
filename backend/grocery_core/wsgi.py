import os
import sys
import shutil
from pathlib import Path

# Ensure backend directory is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# On Vercel / Serverless, copy database and run migrations to /tmp if needed
IS_SERVERLESS = bool(
    os.environ.get('VERCEL')
    or os.environ.get('AWS_LAMBDA_FUNCTION_NAME')
    or str(BASE_DIR).startswith('/var/task')
    or os.path.exists('/var/task')
)

if IS_SERVERLESS:
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

# Ensure migrations are applied on /tmp
if IS_SERVERLESS:
    try:
        from django.core.management import call_command
        call_command('migrate', interactive=False)
    except Exception as e:
        print("Auto-migration in wsgi:", e)

app = application
