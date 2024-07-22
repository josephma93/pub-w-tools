import logging
import time

from flask import Blueprint, Response, jsonify, request

from app.routes.wol import fetch_today
from app.services.pub_mwb_parser import parse_10min_talk_to_json

pub_mwb = Blueprint('pub_mwb', __name__)
logger = logging.getLogger('pub_mwb')


@pub_mwb.route('/get-this-week-10min-talk-json', methods=['GET'])
def get_this_week_html() -> tuple[Response, int] | tuple[str, int]:
    """
    Parce this week's 10min talk in WOL to JSON
    ---
    responses:
      200:
        description: The JSON content of this week's 10min talk
      404:
        description: Resource not found
    """
    today_html_content, status_code = fetch_today()
    if status_code != 200:
        return jsonify({'error': today_html_content}), status_code

    logger.info('Processing HTML content.')
    json_data = parse_10min_talk_to_json(today_html_content)
    logger.info('Successfully parsed HTML to JSON.')

    return jsonify(json_data), 200
