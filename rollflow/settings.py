"""Development foundation; production configuration is supplied by school ICT."""
import os
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
DEBUG = os.environ.get("ROLLFLOW_DEBUG") == "1"
ROLLFLOW_SCHOOL_MODE = os.environ.get("ROLLFLOW_SCHOOL_MODE") == "1"
SECRET_KEY = os.environ.get("ROLLFLOW_SECRET_KEY", "")
if not SECRET_KEY and not DEBUG:
    raise ImproperlyConfigured("Set ROLLFLOW_SECRET_KEY before starting the server.")
if not SECRET_KEY:
    SECRET_KEY = "local-development-only-not-for-production"
ALLOWED_HOSTS = [h.strip() for h in os.environ.get("ROLLFLOW_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]" if DEBUG else "").split(",") if h.strip()]
if not DEBUG and (not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS):
    raise ImproperlyConfigured("Configure specific ROLLFLOW_ALLOWED_HOSTS.")
ROOT_URLCONF = "rollflow.urls"
WSGI_APPLICATION = "rollflow.wsgi.application"
INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
    "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles",
    "accounts",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "rollflow.school_security.LocalOnlyResourcesMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]
if os.environ.get("ROLLFLOW_DB_NAME"):
    DATABASES = {"default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ["ROLLFLOW_DB_NAME"],
        "USER": os.environ["ROLLFLOW_DB_USER"],
        "PASSWORD": os.environ["ROLLFLOW_DB_PASSWORD"],
        "HOST": os.environ.get("ROLLFLOW_DB_HOST", "localhost"),
        "PORT": os.environ.get("ROLLFLOW_DB_PORT", "5432"),
    }}
elif DEBUG:
    data_dir = Path(os.environ.get("ROLLFLOW_DATA_DIR", BASE_DIR / ".local-data"))
    data_dir.mkdir(parents=True, exist_ok=True)
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": data_dir / "rollflow.sqlite3"}}
else:
    raise ImproperlyConfigured("Configure PostgreSQL for non-development installations.")
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]
LANGUAGE_CODE = "en-au"
TIME_ZONE = "Australia/Brisbane"
USE_I18N = True
USE_TZ = True
STATIC_URL = "/static/"
STATIC_ROOT = Path(os.environ.get("ROLLFLOW_STATIC_ROOT", BASE_DIR / ".collected-static"))
# Original OneSchool exports live under private instance state, never STATIC_ROOT.
ROLLFLOW_ARCHIVE_STATE_DIR = Path(os.environ.get("ROLLFLOW_DATA_DIR", BASE_DIR / ".local-data")).resolve()
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "/login/"
SESSION_COOKIE_NAME = "rollflow_session"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 8 * 60 * 60
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_SSL_REDIRECT = not DEBUG
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
# Set ONLY behind a trusted proxy that strips incoming forwarded headers.
if os.environ.get("ROLLFLOW_TRUST_HTTPS_PROXY") == "1":
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Only enable on an approved, private school-hosted timetable installation.
ROLLFLOW_LIVE_TIMETABLE = os.environ.get("ROLLFLOW_LIVE_TIMETABLE") == "1"
if ROLLFLOW_LIVE_TIMETABLE and (DEBUG or DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql" or len(SECRET_KEY) < 50):
    raise ImproperlyConfigured("Live timetable requires DEBUG off, PostgreSQL and a secret key of at least 50 characters.")

# Uploaded source files may contain identities: use a private temporary directory
# even before they are encrypted into the offline archive.
if os.environ.get("ROLLFLOW_DATA_DIR"):
    private_uploads = Path(os.environ["ROLLFLOW_DATA_DIR"]) / "uploads"
    private_uploads.mkdir(mode=0o700, parents=True, exist_ok=True)
    FILE_UPLOAD_TEMP_DIR = str(private_uploads)

# A school installation must never silently fall back to sample attendance or SQLite.
if ROLLFLOW_SCHOOL_MODE:
    if DEBUG or not ROLLFLOW_LIVE_TIMETABLE or len(SECRET_KEY) < 50:
        raise ImproperlyConfigured("School mode requires DEBUG off, live timetable mode and a strong secret.")
    if any(h.startswith(".") or "*" in h for h in ALLOWED_HOSTS):
        raise ImproperlyConfigured("School mode requires exact approved hostnames.")
    if not os.environ.get("ROLLFLOW_DATA_DIR") or not os.environ.get("ROLLFLOW_STATIC_ROOT"):
        raise ImproperlyConfigured("School mode requires explicit private state and static directories.")
    if os.environ.get("ROLLFLOW_TRUST_HTTPS_PROXY") != "1":
        raise ImproperlyConfigured("School mode requires an approved local HTTPS gateway.")
    FILE_UPLOAD_TEMP_DIR = str(Path(os.environ["ROLLFLOW_DATA_DIR"]) / "uploads")
    Path(FILE_UPLOAD_TEMP_DIR).mkdir(parents=True, exist_ok=True)
    # Apply HSTS to this host only; ICT owns policy for its parent domain.
