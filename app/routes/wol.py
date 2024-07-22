import logging
import time

from flask import Blueprint, Response, jsonify

from app.services.fetch_content import fetch_landing_html, fetch_today_html

wol_bp = Blueprint('wol', __name__)
logger = logging.getLogger('pub_w')


@wol_bp.route('/fetch-landing-html', methods=['GET'])
def fetch_landing() -> tuple[Response, int] | tuple[str, int]:
    """
    Fetch the landing HTML from WOL
    ---
    responses:
      200:
        description: The HTML content of the landing page
      404:
        description: Resource not found
    """
    start_time = time.time()
    html_content, status_code = fetch_landing_html()
    logger.info(f'fetch_landing_html completed in {time.time() - start_time:.2f} seconds')
    if status_code != 200:
        return jsonify({'error': html_content}), status_code
    return html_content, status_code


@wol_bp.route('/fetch-today-html', methods=['GET'])
def fetch_today() -> tuple[Response, int] | tuple[str, int]:
    """
    Fetch today's HTML from WOL
    ---
    responses:
      200:
        description: The HTML content of today's page
      404:
        description: Resource not found
    """
    start_time = time.time()
    html_content, status_code = fetch_landing_html()
    if status_code != 200:
        return jsonify({'error': html_content}), status_code
    today_html_content, status_code = fetch_today_html(html_content)
    logger.info(f'fetch_today_html completed in {time.time() - start_time:.2f} seconds')
    if status_code != 200:
        return jsonify({'error': today_html_content}), status_code
    return today_html_content, status_code
