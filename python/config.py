# config.py

import os
from pathlib import Path

FLASK_PORT = os.environ.get('FLASK_PORT', '5000')

# Define the output directory
OUTPUT_DIR = Path(os.path.expanduser("~/uploads"))

# Create the output directory if it doesn't exist
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_IP = {'127.0.0.1'}

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', os.urandom(32))
    UPLOAD_FOLDER = str(OUTPUT_DIR)
    OUTPUT_DIR = OUTPUT_DIR  # Add this line
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024 * 1024  # 10 GB
    ALLOWED_EXTENSIONS = {
        # Documents
        'txt', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'odt', 'ods', 'odp',
        'rtf', 'tex', 'wpd', 'csv', 'md', 'json', 'xml',
        
        # Images
        'jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg', 'webp', 'tiff', 'ico',
        
        # Audio
        'mp3', 'wav', 'ogg', 'flac', 'm4a', 'aac', 'wma',
        
        # Video
        'mp4', 'avi', 'mov', 'wmv', 'flv', 'mkv', 'webm', 'm4v',
        
        # Archives
        'zip', 'rar', '7z', 'tar', 'gz', 'bz2',
        
        # Programming
        'py', 'js', 'html', 'css', 'java', 'c', 'cpp', 'h', 'hpp', 'php', 'rb', 'go', 'rs',
        'swift', 'kt', 'ts', 'sql', 'sh', 'bat', 'ps1',
        
        # Other
        'log', 'ini', 'cfg', 'conf', 'yaml', 'yml', 'toml', 'db', 'sqlite', 'exe', 'dll',
        'iso', 'bin', 'dat'
    }
