from .base import *


DEBUG = True

ALLOWED_HOSTS = ["*"]

INTERNAL_IPS = ["127.0.0.1"]

INSTALLED_APPS += ['debug_toolbar']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
