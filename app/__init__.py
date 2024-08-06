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
        logger.error(f"An unexpected error occurred: {str(e)}")
        response = {
            "message": "An unexpected error occurred.",
            "error": str(e)
        }
        return jsonify(response), 500

    return app
