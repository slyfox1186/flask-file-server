# routes.py

import logging
import os
import tempfile
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_file, jsonify
from flask.views import MethodView
from python.file_manager import list_directory, save_file, download_file, remove_file
from python.utils import allowed_file, extract_archive, create_logger, send_compressed, is_7z_available, compress_directory
from werkzeug.utils import secure_filename
from pathlib import Path
from python.config import Config
import subprocess
import zipfile
import shutil

def get_masked_path(full_path):
    home_dir = os.path.expanduser("~")
    if full_path.startswith(home_dir):
        return f"~/...{full_path[len(home_dir):]}"
    return full_path

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

main_bp = Blueprint('main', __name__)

class FileSystemView(MethodView):
    def get(self, req_path=''):
        logger.debug(f"GET request received for path: {req_path}")
        try:
            logger.info(f"Accessing path: {req_path}")
            abs_path = Path(Config.OUTPUT_DIR) / req_path
            logger.info(f"Absolute path: {abs_path}")
            
            if abs_path.is_file():
                logger.info(f"Downloading file: {abs_path}")
                return send_file(abs_path, as_attachment=True)
            
            contents = list_directory(req_path)
            logger.info(f"Directory contents: {contents}")
            current_path = req_path.strip('/')
            parent_path = str(Path(current_path).parent)
            
            masked_path = get_masked_path(str(abs_path))
            
            logger.debug("Rendering index.html template")
            return render_template('index.html', 
                                   contents=contents, 
                                   current_path=current_path, 
                                   parent_path=parent_path,
                                   masked_path=masked_path)
        except Exception as e:
            logger.exception(f"Error in GET method: {str(e)}")
            flash(str(e), 'danger')
            return redirect(url_for('main.file_system'))

    def post(self, req_path=''):
        logger.debug(f"POST request received for path: {req_path}")
        action = request.form.get('action')
        logger.info(f"Action requested: {action}")
        
        if action == 'upload_file':
            return self.upload_file(req_path)
        elif action == 'upload_folder':
            return self.upload_folder(req_path)
        elif action == 'create_folder':
            return self.create_folder(req_path)
        elif action == 'upload_zip':
            return self.upload_zip(req_path)
        elif action == 'download_folder':
            return self.download_folder(req_path)
        elif action == 'remove':
            return self.remove_file(req_path)
        else:
            logger.warning(f"Invalid action requested: {action}")
            flash('Invalid action', 'danger')
            return redirect(url_for('main.file_system', req_path=req_path))

    def upload_file(self, req_path):
        try:
            abs_path = Path(Config.OUTPUT_DIR) / req_path
            logger.debug(f"Upload destination for file: {abs_path}")
            if not abs_path.is_dir():
                logger.error(f"Upload destination is not a directory: {abs_path}")
                return jsonify({'status': 'error', 'message': "Upload destination is not a directory."}), 400

            files = request.files.getlist('files[]')
            logger.debug(f"Number of files received: {len(files)}")

            uploaded_count = 0
            uploaded_files = []

            for file in files:
                if file and file.filename:
                    logger.debug(f"Processing file: {file.filename}")
                    filename = secure_filename(file.filename)
                    file_path = abs_path / filename
                    logger.debug(f"File will be saved to: {file_path}")
                    
                    if allowed_file(filename):
                        file.save(file_path)
                        uploaded_count += 1
                        uploaded_files.append(str(file_path.relative_to(abs_path)))
                    else:
                        logger.warning(f"File type not allowed: {filename}")

            if not uploaded_files:
                logger.warning("No files uploaded")
                return jsonify({'status': 'error', 'message': 'No files processed'}), 400

            message = f'{uploaded_count} file(s) uploaded successfully'
            logger.info(message)
            return jsonify({
                'status': 'success',
                'message': message,
                'uploaded_files': uploaded_files
            }), 200
        except Exception as e:
            logger.exception(f"Error uploading files: {str(e)}")
            return jsonify({'status': 'error', 'message': f'Error uploading files: {str(e)}'}), 500

    def upload_folder(self, req_path):
        try:
            abs_path = Path(Config.OUTPUT_DIR) / req_path
            logger.debug(f"Upload destination for folder: {abs_path}")
            if not abs_path.is_dir():
                logger.error(f"Upload destination is not a directory: {abs_path}")
                return jsonify({'status': 'error', 'message': "Upload destination is not a directory."}), 400

            files = request.files.getlist('files[]')
            logger.debug(f"Number of files received in folder: {len(files)}")

            uploaded_count = 0
            uploaded_files = []

            for file in files:
                if file and file.filename:
                    logger.debug(f"Processing file in folder: {file.filename}")
                    relative_path = file.filename
                    file_path = abs_path / relative_path
                    logger.debug(f"File will be saved to: {file_path}")
                    file_path.parent.mkdir(parents=True, exist_ok=True)  # Create subdirectories if needed
                    
                    if allowed_file(file.filename):
                        file.save(file_path)
                        uploaded_count += 1
                        uploaded_files.append(str(file_path.relative_to(abs_path)))
                    else:
                        logger.warning(f"File type not allowed: {file.filename}")

            # Handle folder creation for empty folders
            folders = request.form.getlist('folders[]')
            logger.debug(f"Folders to create: {folders}")
            created_folders = []
            for folder in folders:
                folder_path = abs_path / folder
                logger.debug(f"Creating folder: {folder_path}")
                folder_path.mkdir(parents=True, exist_ok=True)
                created_folders.append(str(folder_path.relative_to(abs_path)))

            if not uploaded_files and not created_folders:
                logger.warning("No files uploaded and no folders created")
                return jsonify({'status': 'error', 'message': 'No files or folders processed'}), 400

            message = f'{uploaded_count} file(s) uploaded successfully'
            if created_folders:
                message += f' and {len(created_folders)} folder(s) created successfully'
            logger.info(message)
            return jsonify({
                'status': 'success',
                'message': message,
                'uploaded_files': uploaded_files,
                'created_folders': created_folders
            }), 200
        except Exception as e:
            logger.exception(f"Error uploading folder: {str(e)}")
            return jsonify({'status': 'error', 'message': f'Error uploading folder: {str(e)}'}), 500

    def create_folder(self, req_path):
        logger.info(f"Create folder route accessed with req_path: {req_path}")
        try:
            logger.info(f"Creating folder in path: {req_path}")
            abs_path = Path(Config.OUTPUT_DIR) / req_path
            logger.info(f"Absolute path: {abs_path}")
            folder_name = request.form.get('folder_name')
            logger.info(f"Folder name: {folder_name}")
            
            if folder_name:
                new_folder_path = abs_path / secure_filename(folder_name)
                logger.info(f"New folder path: {new_folder_path}")
                os.makedirs(new_folder_path, exist_ok=True)
                flash(f'Folder "{folder_name}" created successfully', 'success')
            else:
                flash('Folder name cannot be empty', 'danger')
        except Exception as e:
            logger.exception(f"Error creating folder: {str(e)}")
            flash(f'Error creating folder: {str(e)}', 'danger')
        
        return redirect(url_for('main.file_system', req_path=req_path))

    def upload_zip(self, req_path):
        temp_dir = None
        try:
            abs_path = Path(Config.OUTPUT_DIR) / req_path
            if not abs_path.is_dir():
                flash("Upload destination is not a directory.", "danger")
                return redirect(url_for('main.file_system', req_path=req_path))
            
            if 'archive_file' not in request.files:
                flash('No archive file part', 'danger')
                return redirect(url_for('main.file_system', req_path=req_path))
            
            archive_file = request.files['archive_file']
            
            if archive_file.filename == '':
                flash('No selected archive file', 'danger')
                return redirect(url_for('main.file_system', req_path=req_path))
            
            if archive_file.filename.lower().endswith('.7z') and not is_7z_available():
                flash('7z archives are not supported on this server. Please use ZIP instead.', 'danger')
                return redirect(url_for('main.file_system', req_path=req_path))
            
            # Create a temporary directory
            temp_dir = tempfile.mkdtemp(dir=abs_path)
            temp_archive_path = Path(temp_dir) / secure_filename(archive_file.filename)
            archive_file.save(temp_archive_path)
            
            try:
                extract_archive(temp_archive_path, abs_path)
                flash('Archive uploaded and extracted successfully', 'success')
            except (subprocess.CalledProcessError, zipfile.BadZipFile):
                flash('Failed to extract the archive', 'danger')
        except Exception as e:
            flash(str(e), 'danger')
        finally:
            # Clean up temporary files
            if temp_dir:
                for root, dirs, files in os.walk(temp_dir, topdown=False):
                    for name in files:
                        os.remove(os.path.join(root, name))
                    for name in dirs:
                        os.rmdir(os.path.join(root, name))
                os.rmdir(temp_dir)
        
        return redirect(url_for('main.file_system', req_path=req_path))

    def download_folder(self, req_path):
        temp_file = None
        try:
            abs_path = Path(Config.OUTPUT_DIR) / req_path
            if not abs_path.is_dir():
                flash("Download path is not a directory.", "danger")
                return redirect(url_for('main.file_system', req_path=req_path))
            
            archive_name = f"{abs_path.name}.zip"  # Always use .zip extension
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
            temp_file.close()
            
            compressed_file, mimetype = compress_directory(abs_path, Path(temp_file.name))
            
            return send_file(
                compressed_file,
                mimetype=mimetype,
                as_attachment=True,
                download_name=archive_name
            )
        except Exception as e:
            logger.exception(f"Error downloading folder: {str(e)}")
            flash(f'Error downloading folder: {str(e)}', 'danger')
            return redirect(url_for('main.file_system', req_path=req_path))
        finally:
            if temp_file:
                os.unlink(temp_file.name)

    def remove_file(self, req_path):
        try:
            file_to_remove = request.form.get('file_path')
            if not file_to_remove:
                logger.warning("No item specified for removal.")
                return jsonify({'status': 'error', 'message': 'No item specified for removal.'}), 400
            
            abs_path = Path(Config.OUTPUT_DIR) / file_to_remove.lstrip('/')
            logger.info(f"Attempting to remove item: {abs_path}")
            
            if not abs_path.exists():
                logger.warning(f"Item does not exist: {abs_path}")
                return jsonify({'status': 'error', 'message': 'Item does not exist.'}), 404
            
            if abs_path.is_file():
                abs_path.unlink()  # Delete the file
                logger.info(f"Removed file: {abs_path}")
            elif abs_path.is_dir():
                shutil.rmtree(abs_path)  # Delete the directory and its contents
                logger.info(f"Removed directory: {abs_path}")
            
            return jsonify({'status': 'success', 'message': f'Item "{abs_path.name}" removed successfully.'}), 200
        except PermissionError as e:
            logger.error(f"Permission error removing item: {str(e)}")
            return jsonify({'status': 'error', 'message': 'Permission denied when trying to remove the item.'}), 403
        except Exception as e:
            logger.exception(f"Error removing item: {str(e)}")
            return jsonify({'status': 'error', 'message': f'Error removing item: {str(e)}'}), 500

file_system_view = FileSystemView.as_view('file_system')
main_bp.add_url_rule('/', view_func=file_system_view, methods=['GET', 'POST'])
main_bp.add_url_rule('/<path:req_path>', view_func=file_system_view, methods=['GET', 'POST'])

