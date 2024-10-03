# file_manager.py

import logging
import os
from flask import send_from_directory, abort, jsonify, request
from werkzeug.utils import secure_filename
from python.config import Config
from python.utils import allowed_file, send_zip, create_logger
from pathlib import Path

logger = create_logger('file_manager')
logger.setLevel(logging.DEBUG)

def list_directory(path):
    try:
        logger.info(f"Listing directory: {path}")
        dir_path = Path(Config.OUTPUT_DIR) / path
        logger.info(f"Directory path: {dir_path}")
        
        if not dir_path.exists():
            logger.info(f"Creating directory: {dir_path}")
            os.makedirs(dir_path, exist_ok=True)
        
        items = os.listdir(dir_path)
        logger.info(f"Items in directory: {items}")
        
        files = []
        folders = []
        for item in items:
            full_path = dir_path / item
            if full_path.is_dir():
                folders.append(item)
            else:
                files.append(item)
        
        logger.info(f"Folders: {folders}")
        logger.info(f"Files: {files}")
        
        return {'folders': folders, 'files': files}
    except Exception as e:
        logger.exception(f"Error accessing directory {path}: {e}")
        return {'folders': [], 'files': []}

def save_file(file_storage, destination):
    if not allowed_file(file_storage.filename):
        return None
    filename = secure_filename(file_storage.filename)
    file_path = destination / filename
    try:
        file_storage.save(file_path)
        return filename
    except Exception as e:
        print(f"Error saving file {filename}: {e}")
        return None

def download_file(path):
    """
    Handles file or directory download. If path is a file, it sends the file.
    If it's a directory, it sends a ZIP archive of the directory.
    """
    try:
        target_path = Path(Config.OUTPUT_DIR) / path
        if target_path.is_file():
            return send_from_directory(target_path.parent, target_path.name, as_attachment=True)
        elif target_path.is_dir():
            archive_name = f"{target_path.name}.zip"
            return send_zip(target_path, archive_name)
        else:
            abort(404, description="File or directory not found.")
    except Exception as e:
        print(f"Error downloading {path}: {e}")
        abort(500, description="Internal Server Error.")

def remove_file(path):
    """
    Removes a file from the specified path.
    """
    try:
        file_to_remove = request.form.get('file_path')
        if not file_to_remove:
            return jsonify({'status': 'error', 'message': 'No file specified for removal.'}), 400
        
        abs_path = Path(Config.OUTPUT_DIR) / file_to_remove
        
        if not abs_path.is_file():
            return jsonify({'status': 'error', 'message': 'File does not exist.'}), 404
        
        abs_path.unlink()  # Delete the file
        logger.info(f"Removed file: {abs_path}")
        
        return jsonify({'status': 'success', 'message': f'File "{abs_path.name}" removed successfully.'}), 200
    except Exception as e:
        logger.exception(f"Error removing file: {e}")
        return jsonify({'status': 'error', 'message': f'Error removing file: {e}'}), 500

