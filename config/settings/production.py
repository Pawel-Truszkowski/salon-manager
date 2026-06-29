from .base import *

DEBUG = False

USE_X_FORWARDED_HOST = True

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
CSRF_TRUSTED_ORIGINS = [
    'https://royalbeauty-studiourody.pl', 
    'https://www.royalbeauty-studiourody.pl'
]
