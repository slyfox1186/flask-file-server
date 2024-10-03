# Best Local Web Server

A Flask-based web application for managing and sharing files locally.

## Features

- Browse and manage files and directories
- Upload files and folders
- Create new folders
- Download files and folders as ZIP archives
- Remove files and folders
- Secure access with IP restrictions

## Requirements

- Python 3.7+
- Flask
- Werkzeug

For a complete list of dependencies, see `requirements.txt`.

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/best-local-web-server.git
   cd best-local-web-server
   ```

2. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

**IMPORTANT**: Before running the server, you must configure the variables in the `config.py` file correctly. This step is crucial for the proper and secure functioning of the application.

1. Open `config.py` and adjust the following settings:
   - `FLASK_PORT`: The port on which the server will run (default is 5000)
   - `OUTPUT_DIR`: The directory where uploaded files will be stored
   - `ALLOWED_IP`: Set of IP addresses allowed to access the server
   - `ALLOWED_EXTENSIONS`: File extensions that are allowed to be uploaded
   - `SECRET_KEY`: A secret key for the application (for security, use a strong, random key)
   - `MAX_CONTENT_LENGTH`: Maximum allowed file size for uploads

Example configuration:

```python
FLASK_PORT = '5000'
OUTPUT_DIR = Path(os.path.expanduser("~/uploads"))
ALLOWED_IP = {'127.0.0.1', '192.168.1.100'}  # Add your IP addresses here
SECRET_KEY = 'your_secret_key
```

## Running the Server

1. Start the server:
   ```bash
   python app.py
   ```

2. Open a web browser and navigate to `http://localhost:5000` (or the port specified in your configuration).

## Usage

- Use the web interface to browse, upload, download, and manage files.
- Create new folders using the "Create New Folder" form.
- Upload files by dragging and dropping them onto the page or using the file input.
- Download folders as ZIP archives by clicking the "Download" button next to a folder.
- Remove files or folders by clicking the "Remove" button next to an item.

## Security Notes

- This server is intended for local use only. Do not expose it to the public internet without proper security measures.
- The server restricts access to specified IP addresses. Make sure to configure `ALLOWED_IP` in `config.py`.
- Always keep your system and dependencies up to date.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License. See the LICENSE file for details.
