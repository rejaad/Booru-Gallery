import os
from settings import Settings

class Config:
    settings = Settings()
    
    # Base directory
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    
    # Static folder configuration
    STATIC_FOLDER = os.path.join(BASE_DIR, 'static')
    
    # Flask configuration
    SECRET_KEY = settings.get('server', 'secret_key')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        f"sqlite:///{os.path.join(BASE_DIR, settings.get('paths', 'database'))}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Server settings
    HOST = settings.get('server', 'host')
    PORT = settings.get('server', 'port')
    DEBUG = settings.get('server', 'debug')
    
    # Add static paths
    STATIC_FOLDER = settings.get('paths', 'static_folder')
    IMAGES_FOLDER = settings.get('paths', 'images_folder')
    THUMBNAILS_FOLDER = settings.get('paths', 'thumbnails_folder')
    
    # Add gallery settings
    IMAGES_PER_PAGE = settings.get('gallery', 'images_per_page')
    GALLERY_SORT_ORDER = settings.get('gallery', 'sort_order')
    GALLERY_SORT_BY = settings.get('gallery', 'sort_by')
    
    # Add processing settings
    BATCH_SIZE = settings.get('processing', 'batch_size')
    CPU_USAGE_PERCENT = settings.get('processing', 'cpu_usage_percent')
    
    # Add filter settings
    EXCLUDE_DELETED = settings.get('filters', 'exclude_deleted')
    EXCLUDE_BANNED = settings.get('filters', 'exclude_banned')
    ALLOWED_RATINGS = settings.get('filters', 'allowed_ratings')