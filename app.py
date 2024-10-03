# app.py

#!/usr/bin/env python3

import logging
from flask import Flask, Request, abort, request
from routes import main_bp
from config import Config, FLASK_PORT
from werkzeug.serving import run_simple
from werkzeug.debug import DebuggedApplication

# Set up root logger
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.StreamHandler()])

logger = logging.getLogger(__name__)

class LargeFileRequest(Request):
    max_content_length = Config.MAX_CONTENT_LENGTH

def create_app():
    logger.info("Creating Flask application")
    app = Flask(__name__)
    app.config.from_object(Config)
    app.request_class = LargeFileRequest

    logger.debug(f"Application configuration: {app.config}")

    # Ensure SESSION_COOKIE_SECURE is False for development (HTTP)
    app.config['SESSION_COOKIE_SECURE'] = False
    
    # Set SameSite attribute for cookies
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['REMEMBER_COOKIE_SAMESITE'] = 'Lax'

    logger.info("Registering blueprints")
    app.register_blueprint(main_bp)

    @app.context_processor
    def inject_output_dir():
        logger.debug(f"Injecting output_dir: {Config.UPLOAD_FOLDER}")
        return {'output_dir': Config.UPLOAD_FOLDER}

    @app.before_request
    def limit_remote_addr():
        allowed_ips = app.config['ALLOWED_IP'].union({'127.0.0.1', 'localhost'})
        logger.debug(f"Checking remote address: {request.remote_addr}")
        if request.remote_addr not in allowed_ips:
            logger.warning(f"Forbidden access attempt from IP: {request.remote_addr}")
            abort(403, description="Forbidden: Your IP is not allowed to access this resource.")

    # Set logging level to DEBUG for detailed logs
    app.logger.setLevel(logging.DEBUG)

    logger.info("Flask application created successfully")
    return app

if __name__ == '__main__':
    logger.info("Starting Flask application")
    app = create_app()
    
    # Disable reloader and debugger
    logger.info(f"Running Flask app on port {FLASK_PORT}")
    app.run(host='0.0.0.0', port=int(FLASK_PORT), debug=True, use_reloader=False)