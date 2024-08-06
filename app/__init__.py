from logging.config import dictConfig
from flask import Flask
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

    return app