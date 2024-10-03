# utils.py
import os
import subprocess
import io
import zipfile
from pathlib import Path
from flask import send_file
from python.config import Config, OUTPUT_DIR
import logging
from logging.handlers import RotatingFileHandler

# Configure logging for the utility module
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler('utils.log', maxBytes=5*1024*1024, backupCount=5)  # 5 MB per file, 5 backups
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

def is_7z_available():
    try:
        subprocess.run(['7z', '--help'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except FileNotFoundError:
        return False

def compress_directory(directory: Path, output_file: Path) -> tuple[Path, str]:
    """
    Compresses a directory using 7z if available, otherwise uses zip.
    Falls back to zip if 7z compression fails.

    Args:
        directory (Path): The directory to compress.
        output_file (Path): The path where the compressed file should be saved.

    Returns:
        tuple[Path, str]: The path to the compressed file and the mimetype.

    Raises:
        Exception: If both 7z and zip compression fail.
    """
    logger.debug(f"Compressing directory: {directory}")
    if is_7z_available():
        try:
            mimetype = 'application/x-7z-compressed'
            subprocess.run(['7z', 'a', str(output_file), str(directory)], check=True, capture_output=True, text=True)
            logger.debug(f"Directory compressed successfully with 7z: {output_file}")
            return output_file, mimetype
        except subprocess.CalledProcessError as e:
            logger.warning(f"7z compression failed, falling back to zip: {e.stderr}")
    
    # If 7z is not available or failed, use zip
    mimetype = 'application/zip'
    try:
        with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(directory):
                for file in files:
                    file_path = Path(root) / file
                    zipf.write(file_path, file_path.relative_to(directory))
        logger.debug(f"Directory compressed successfully with zip: {output_file}")
        return output_file, mimetype
    except Exception as e:
        logger.error(f"Error compressing directory with zip: {str(e)}")
        raise

def send_compressed(directory: Path, archive_name: str) -> send_file:
    """
    Sends a directory as a downloadable compressed archive to the client.

    Args:
        directory (Path): The directory to send.
        archive_name (str): The name of the archive file to be sent.

    Returns:
        Response: Flask response object containing the compressed file.

    Raises:
        HTTPException: 500 Internal Server Error if compression fails.
    """
    try:
        compressed_file, mimetype = compress_directory(directory)
        logger.info(f"Sending compressed archive: {archive_name}")
        return send_file(
            compressed_file,
            mimetype=mimetype,
            as_attachment=True,
            download_name=archive_name
        )
    except Exception as e:
        logger.exception(f"Error sending compressed archive for directory '{directory}': {e}")
        abort(500, description="Failed to create compressed archive.")

def extract_archive(archive_path: Path, extract_to: Path):
    """
    Extracts a 7z or zip archive to a specified directory.

    Args:
        archive_path (Path): The path to the archive.
        extract_to (Path): The directory to extract files into.

    Raises:
        subprocess.CalledProcessError: If extraction fails.
    """
    try:
        logger.debug(f"Extracting archive to: {extract_to}")
        if archive_path.suffix.lower() == '.7z' and is_7z_available():
            subprocess.run(['7z', 'x', str(archive_path), f'-o{extract_to}', '-y'], check=True, capture_output=True, text=True)
        else:
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(extract_to)
        logger.info(f"Archive extracted successfully to: {extract_to}")
    except (subprocess.CalledProcessError, zipfile.BadZipFile) as e:
        logger.error(f"Error extracting archive: {str(e)}")
        raise

def zip_directory(directory: Path) -> io.BytesIO:
    """
    Compresses a directory into a ZIP archive stored in memory.

    Args:
        directory (Path): The directory to compress.

    Returns:
        BytesIO: An in-memory bytes buffer containing the ZIP archive.
    """
    logger.debug(f"Zipping directory: {directory}")
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = Path(root) / file
                # Compute the relative path for the archive relative to 'directory'
                relative_path = file_path.relative_to(directory)
                logger.debug(f"Adding {file_path} as {relative_path} to ZIP")
                zip_file.write(file_path, arcname=relative_path)

    zip_buffer.seek(0)
    logger.debug(f"Directory zipped successfully: {directory}")
    return zip_buffer

def send_zip(directory: Path, archive_name: str = "archive.zip") -> send_file:
    """
    Sends a directory as a downloadable ZIP archive to the client.

    Args:
        directory (Path): The directory to send.
        archive_name (str): The name of the ZIP file to be sent.

    Returns:
        Response: Flask response object containing the ZIP file.

    Raises:
        HTTPException: 500 Internal Server Error if zipping fails.
    """
    try:
        zip_buffer = zip_directory(directory)
        logger.info(f"Sending ZIP archive: {archive_name}")
        return send_file(
            zip_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name=archive_name
        )
    except Exception as e:
        logger.exception(f"Error sending ZIP archive for directory '{directory}': {e}")
        abort(500, description="Failed to create ZIP archive.")

def unzip_file(zip_stream: io.BytesIO, extract_to: Path):
    """
    Extracts a ZIP archive from a bytes stream to a specified directory.

    Args:
        zip_stream (BytesIO): The bytes stream containing the ZIP archive.
        extract_to (Path): The directory to extract files into.

    Raises:
        HTTPException: 400 Bad Request if the ZIP file is invalid or extraction fails.
        HTTPException: 500 Internal Server Error for other exceptions.
    """
    try:
        logger.debug(f"Unzipping archive to: {extract_to}")
        with zipfile.ZipFile(zip_stream) as zip_file:
            # Prevent Zip Slip vulnerability
            for member in zip_file.namelist():
                member_path = (extract_to / member).resolve()
                if not member_path.is_relative_to(extract_to.resolve()):
                    logger.error(f"Attempted Zip Slip attack with member: {member}")
                    abort(400, description="Invalid ZIP file.")
            zip_file.extractall(extract_to)
        logger.info(f"ZIP archive extracted successfully to: {extract_to}")
    except zipfile.BadZipFile:
        logger.exception("Received a bad ZIP file.")
        abort(400, description="Invalid ZIP file.")
    except HTTPException:
        # Re-raise HTTP exceptions to be handled by Flask
        raise
    except Exception as e:
        logger.exception(f"Error extracting ZIP file: {e}")
        abort(500, description="Failed to extract ZIP archive.")

def create_logger(name: str = __name__) -> logging.Logger:
    """
    Creates a logger with the specified name and configures log rotation.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = RotatingFileHandler('utils.log', maxBytes=5*1024*1024, backupCount=5)  # 5 MB per file, 5 backups
        formatter = logging.Formatter('[%(asctime)s] %(levelname)s in %(module)s: %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger

def allowed_file(filename):
    """
    Check if the file extension is allowed.
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

# Additional utility functions can be added here as needed.