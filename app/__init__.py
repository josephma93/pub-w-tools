import traceback

from flask import Flask, jsonify
from flasgger import Swagger
from app.routes.wol import wol_bp
from app.routes.pub_w import pub_w_bp
from app.routes.pub_mwb import pub_mwb
import logging
import os


def create_app():
    app = Flask(__name__)
    Swagger(app)

    app.register_blueprint(wol_bp, url_prefix='/wol')
    app.register_blueprint(pub_w_bp, url_prefix='/pub-w')
    app.register_blueprint(pub_mwb, url_prefix='/pub-mwb')

    log_level = os.getenv('LOGGING_LEVEL', 'INFO').upper()
    numeric_level = getattr(logging, log_level, logging.INFO)
    logging.basicConfig(level=numeric_level)
    logger = logging.getLogger(__name__)
    logger.info('Flask app initialized')

    @app.errorhandler(Exception)
    def handle_exception(e):
        error_msg = "An unexpected error occurred: {}"
        if app.debug:
            error_msg += "\nTraceback:\n{}"
        logger.error(error_msg, str(e))
        response = {
            "message": "An unexpected error occurred.",
            "error": str(e),
            "traceback": traceback.format_exc() if app.debug else None
        }
        return jsonify(response), 500

    return app
