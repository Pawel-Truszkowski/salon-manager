from .base import *

DEBUG = True

ALLOWED_HOSTS = ["*"]

SITE_URL = env("SITE_URL", default="http://localhost:8000")

INTERNAL_IPS = ["127.0.0.1"]

INSTALLED_APPS += ['debug_toolbar']

MIDDLEWARE = ['debug_toolbar.middleware.DebugToolbarMiddleware'] + MIDDLEWARE
