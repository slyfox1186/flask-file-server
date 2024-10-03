# app.py

#!/usr/bin/env python3

import logging
from flask import Flask, Request, abort, request
from routes import main_bp
from config import Config

# Set up root logger
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.StreamHandler()])

logger = logging.getLogger(__name__)

class LargeFileRequest(Request):
    max_content_length = Config.MAX_CONTENT_LENGTH

def create_app():
    app = Flask(__name__, static_folder='static')
    app.config.from_object(Config)
    
    app.register_blueprint(main_bp)
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=Config.FLASK_PORT, debug=True)
