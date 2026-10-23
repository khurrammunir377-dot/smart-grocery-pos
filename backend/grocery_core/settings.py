from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-smart-grocery-pos-secret-key-counter'
DEBUG = True
ALLOWED_HOSTS = ['*']
CSRF_TRUSTED_ORIGINS = ['https://*.vercel.app', 'http://127.0.0.1', 'http://localhost']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'billing',
    'quickbill',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'grocery_core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# Database setup:
# 1. If DATABASE_URL is set (Neon / Supabase / Postgres / MySQL cloud), use it.
# 2. Otherwise on serverless (Linux/Vercel), use /tmp/db.sqlite3.
# 3. Otherwise locally, use BASE_DIR / db.sqlite3.
import sys
import shutil

database_url = os.environ.get('DATABASE_URL')
if database_url:
    try:
        import dj_database_url
        DATABASES = {
            'default': dj_database_url.parse(database_url, conn_max_age=600)
        }
    except ImportError:
        # Fallback to sqlite if dj_database_url not installed
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': Path('/tmp/db.sqlite3') if sys.platform != 'win32' else BASE_DIR / 'db.sqlite3',
            }
        }
else:
    if sys.platform != 'win32' or os.environ.get('VERCEL') or str(BASE_DIR).startswith('/var'):
        TMP_DB = Path('/tmp/db.sqlite3')
        SEED_DB = BASE_DIR / 'db.sqlite3'
        if not TMP_DB.exists():
            if SEED_DB.exists():
                try:
                    shutil.copyfile(str(SEED_DB), str(TMP_DB))
                    try:
                        os.chmod(str(TMP_DB), 0o666)
                    except Exception:
                        pass
                except Exception as e:
                    print("Failed to copyfile SEED_DB:", e)
        else:
            try:
                os.chmod(str(TMP_DB), 0o666)
            except Exception:
                pass
        DB_PATH = str(TMP_DB)
    else:
        DB_PATH = str(BASE_DIR / 'db.sqlite3')

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': DB_PATH,
        }
    }

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Dubai'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'



