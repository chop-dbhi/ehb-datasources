import os

SECRET_KEY = 'test'

BASE_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'redcap', 'templates')
TEMPLATE_DEBUG = False
