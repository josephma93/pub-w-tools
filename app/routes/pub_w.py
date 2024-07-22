import logging
import time

from flask import Blueprint, Response, jsonify, request

from app.services.fetch_content import fetch_landing_html, fetch_today_html, fetch_weekly_html
from app.services.pub_w_parser import parse_html_to_json

pub_w_bp = Blueprint('pub_w', __name__)
logger = logging.getLogger('pub_w')


@pub_w_bp.route('/get-this-week-html', methods=['GET'])
def get_this_week_html() -> tuple[Response, int] | tuple[str, int]:
    """
    Fetch this week's HTML from WOL
    ---
    responses:
      200:
        description: The HTML content of this week's publication
      404:
        description: Resource not found
    """
    start_time = time.time()
    html_content, status_code = fetch_landing_html()
    if status_code != 200:
        return jsonify({'error': html_content}), status_code
    today_html_content, status_code = fetch_today_html(html_content)
    if status_code != 200:
        return jsonify({'error': today_html_content}), status_code
    weekly_html_content, status_code = fetch_weekly_html(today_html_content)
    logger.info(f'fetch_weekly_html completed in {time.time() - start_time:.2f} seconds')
    if status_code != 200:
        return jsonify({'error': weekly_html_content}), status_code
    return weekly_html_content, status_code


@pub_w_bp.route('/html-to-json', methods=['POST'])
def parse_pub_w() -> tuple[Response, int] | tuple[str, int]:
    """
    Parse HTML to JSON
    ---
    parameters:
      - name: html
        in: formData
        type: string
        required: True
        description: The HTML content to be parsed, expected to contain the output of GET /pub-w/get-this-week-html.
    responses:
      200:
        description: The parsed JSON content
      400:
        description: Invalid input
    """
    input_html = request.form.get('html')
    if not input_html:
        logger.error('Invalid input: No HTML content provided.')
        return 'Invalid input', 400
    logger.info('Processing HTML content.')
    json_data = parse_html_to_json(input_html)
    logger.info('Successfully parsed HTML to JSON.')
    return jsonify(json_data), 200
