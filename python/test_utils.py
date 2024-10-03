# test_utils.py
import unittest
from unittest import mock
from pathlib import Path
from python.utils import secure_path, allowed_file, zip_directory, unzip_file
from python.config import Config
import io
import zipfile
import tempfile
import os
from werkzeug.exceptions import HTTPException

class TestUtils(unittest.TestCase):
    def setUp(self):
        """
        Set up a temporary directory for testing and patch Config.UPLOAD_FOLDER.
        """
        # Create a temporary directory
        self.temp_dir = tempfile.TemporaryDirectory()
        self.upload_folder = Path(self.temp_dir.name)

        # Patch Config.UPLOAD_FOLDER to point to the temporary directory
        self.patcher = mock.patch.object(Config, 'UPLOAD_FOLDER', self.upload_folder)
        self.patcher.start()

        # Create sample files and directories
        (self.upload_folder / 'file1.txt').write_text('This is file1.')
        (self.upload_folder / 'file2.jpg').write_bytes(b'\xFF\xD8\xFF')  # JPEG header bytes
        subdir = self.upload_folder / 'subdir'
        subdir.mkdir()
        (subdir / 'file3.png').write_bytes(b'\x89PNG\r\n\x1a\n')  # PNG header bytes

    def tearDown(self):
        """
        Clean up the temporary directory after tests.
        """
        self.patcher.stop()
        self.temp_dir.cleanup()

    def test_secure_path_valid(self):
        """
        Test that secure_path correctly resolves a valid path within the upload directory.
        """
        # Valid relative path
        relative_path = 'subdir'
        expected_path = self.upload_folder / relative_path

        result = secure_path(relative_path)
        self.assertEqual(result, expected_path.resolve())

    def test_secure_path_invalid(self):
        """
        Test that secure_path aborts when attempting directory traversal.
        """
        # Create a temporary directory outside the upload_folder
        with tempfile.TemporaryDirectory() as outside_dir:
            outside_path = Path(outside_dir) / 'evil.txt'
            # Create the outside_path to make it exist
            outside_path.write_text('This should not be accessible.')

            # Compute relative path from upload_folder to outside_path
            relative_path = os.path.relpath(outside_path, self.upload_folder)

            # Now, call secure_path with the relative path
            with self.assertRaises(HTTPException) as cm:
                secure_path(relative_path)

            # Check that the HTTPException has code 403
            self.assertEqual(cm.exception.code, 403)
            self.assertEqual(cm.exception.description, "Unauthorized access.")

    def test_allowed_file_true(self):
        """
        Test that allowed_file returns True for allowed extensions.
        """
        self.assertTrue(allowed_file('test.pdf'))
        self.assertTrue(allowed_file('image.JPG'))  # Case-insensitive

    def test_allowed_file_false(self):
        """
        Test that allowed_file returns False for disallowed extensions.
        """
        self.assertFalse(allowed_file('test.exe'))
        self.assertFalse(allowed_file('script.sh'))

    def test_zip_directory(self):
        """
        Test that zip_directory correctly zips the specified directory.
        """
        # Zip the upload_folder
        zip_buffer = zip_directory(self.upload_folder)

        # Read the ZIP archive from the buffer
        with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
            zip_contents = zip_file.namelist()

            # Expected files in the ZIP archive
            expected_files = [
                'file1.txt',
                'file2.jpg',
                'subdir/file3.png'
            ]

            for file in expected_files:
                self.assertIn(file, zip_contents)

    def test_unzip_file(self):
        """
        Test that unzip_file correctly extracts a valid ZIP archive.
        """
        # Create a ZIP archive in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
            zip_file.writestr('unzipped_file.txt', 'This is an unzipped file.')
            zip_file.writestr('unzipped_subdir/file2.txt', 'This is another unzipped file.')

        zip_buffer.seek(0)

        # Directory to extract to
        extract_dir = self.upload_folder / 'extracted'
        extract_dir.mkdir()

        # Extract the ZIP archive
        unzip_file(zip_buffer, extract_dir)

        # Check that files were extracted correctly
        extracted_file1 = extract_dir / 'unzipped_file.txt'
        extracted_file2 = extract_dir / 'unzipped_subdir' / 'file2.txt'

        self.assertTrue(extracted_file1.exists())
        self.assertTrue(extracted_file2.exists())

        self.assertEqual(extracted_file1.read_text(), 'This is an unzipped file.')
        self.assertEqual(extracted_file2.read_text(), 'This is another unzipped file.')

    def test_unzip_file_bad_zip(self):
        """
        Test that unzip_file aborts when provided with a bad ZIP archive.
        """
        # Create a fake ZIP archive (invalid)
        bad_zip = io.BytesIO(b'This is not a valid ZIP file.')

        # Directory to extract to
        extract_dir = self.upload_folder / 'extracted_bad_zip'
        extract_dir.mkdir()

        with self.assertRaises(HTTPException) as cm:
            unzip_file(bad_zip, extract_dir)

        # Check that the HTTPException has code 400
        self.assertEqual(cm.exception.code, 400)
        self.assertEqual(cm.exception.description, "Invalid ZIP file.")

    def test_unzip_file_zip_slip(self):
        """
        Test that unzip_file prevents Zip Slip attacks by rejecting malicious archives.
        """
        # Create a ZIP archive attempting Zip Slip
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
            # Attempt to create a file outside the extract directory
            zip_file.writestr('../../evil.txt', 'Malicious content.')

        zip_buffer.seek(0)

        # Directory to extract to
        extract_dir = self.upload_folder / 'extracted_zip_slip'
        extract_dir.mkdir()

        with self.assertRaises(HTTPException) as cm:
            unzip_file(zip_buffer, extract_dir)

        # Check that the HTTPException has code 400
        self.assertEqual(cm.exception.code, 400)
        self.assertEqual(cm.exception.description, "Invalid ZIP file.")

    def test_create_logger(self):
        """
        Test that create_logger returns a logger instance.
        """
        from python.utils import create_logger
        logger = create_logger('test_logger')
        self.assertIsNotNone(logger)
        self.assertEqual(logger.name, 'test_logger')

if __name__ == '__main__':
    unittest.main()

