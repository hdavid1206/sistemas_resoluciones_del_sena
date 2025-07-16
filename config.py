import os
from datetime import timedelta


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'sena_centro_minero_2023_resoluciones'
    
UPLOAD_FOLDER = 'uploads'
GENERATED_FOLDER = 'generated'
MAX_CONTENT_LENGTH = 16 * 1024 * 1024
ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}

PERMANENT_SESSION_LIFETIME = timedelta(hours=2)

MYSQL_HOST = os.environ.get('MYSQL_HOST') or 'localhost'
MYSQL_DATABASE = os.environ.get('MYSQL_DATABASE') or 'sena_bienestar'
MYSQL_USER = os.environ.get('MYSQL_USER') or 'root'
MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD') or ''

MYSQL_PORT = int(os.environ.get('MYSQL_PORT',3306))

CENTRO_NOMBRE = "Centro Minero"
Regional_NOMBRE = "SENA Regional Boyacá"
CIUDAD = "Sogamoso"
SUBDIRECTOR_NOMBRE = "Harvey Yadiver Dimaté Rodríguez"
SUBDIRECTOR_CARGO = "Subdirector (E) Centro Minero"

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

