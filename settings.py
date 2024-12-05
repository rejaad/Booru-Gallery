import json
import os
from pathlib import Path

class Settings:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Settings, cls).__new__(cls)
            cls._instance._load_settings()
        return cls._instance
    
    def _load_settings(self):
        settings_path = Path('settings.json')
        
        # Create default settings if file doesn't exist
        if not settings_path.exists():
            self._create_default_settings()
        
        try:
            with open(settings_path, 'r') as f:
                self._settings = json.load(f)
        except Exception as e:
            print(f"Error loading settings: {e}")
            self._create_default_settings()
    
    def _create_default_settings(self):
        default_settings = {
            "paths": {
                "source_images": "D:\\Downloads\\gdl\\gallery-dl\\atfbooru\\id꞉1..10000",
                "database": "booru.db"
            },
            "thumbnails": {
                "width": 128,
                "quality": 85,
                "compression_level": 7
            },
            "gallery": {
                "images_per_page": 24,
                "sort_order": "desc",
                "sort_by": "id"
            },
            "server": {
                "host": "localhost",
                "port": 5000,
                "debug": True
            },
            "processing": {
                "batch_size": 1000,
                "cpu_usage_percent": 75
            },
            "filters": {
                "exclude_deleted": True,
                "exclude_banned": True,
                "allowed_ratings": ["s", "q", "e"]
            }
        }
        
        with open('settings.json', 'w') as f:
            json.dump(default_settings, f, indent=4)
        
        self._settings = default_settings
    
    def save(self):
        """Save current settings to file"""
        with open('settings.json', 'w') as f:
            json.dump(self._settings, f, indent=4)
    
    def get(self, *keys):
        """Get a setting value using dot notation"""
        value = self._settings
        for key in keys:
            value = value.get(key)
            if value is None:
                return None
        return value
    
    def set(self, value, *keys):
        """Set a setting value using dot notation"""
        settings = self._settings
        for key in keys[:-1]:
            settings = settings.setdefault(key, {})
        settings[keys[-1]] = value
        self.save()
    
    def update(self, new_settings):
        """Update multiple settings at once"""
        self._settings.update(new_settings)
        self.save()

# Example usage:
# settings = Settings()
# source_path = settings.get('paths', 'source_images')
# settings.set('new_path', 'paths', 'source_images')