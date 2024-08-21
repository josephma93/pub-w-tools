import logging

from flask import Blueprint, Response, jsonify, request

from app.routes.wol import fetch_today
from app.services.fetch_content import is_valid_wol_bible_book_url, is_url_str_in_wol_jw_org, get_html_content
from app.services.pub_mwb_parser import parse_10min_talk_to_json, parse_weekly_bible_read, \
    extract_references_from_links, parse_meeting_workbook_to_json

pub_mwb_bp = Blueprint('pub_mwb', __name__)
logger = logging.getLogger('pub_mwb')


@pub_mwb_bp.route('/get-this-week-10min-talk-json', methods=['GET'])
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


@pub_mwb_bp.route('/get-week-program-json', methods=['GET'])
def get_this_week_json() -> tuple[Response, int] | tuple[str, int]:
    """
    Fetch this week's data from WOL and returns it as JSON.
    ---
    parameters:
      - name: url
        in: query
        type: string
        required: false
        description: The URL to fetch data from. If not provided, today's data will be fetched.

    responses:
      200:
        description: The JSON content of this week's data
      404:
        description: Resource not found
    """
    url = request.args.get('url')
    logger.debug('URL parameter: %s', url)

    if is_url_str_in_wol_jw_org(url):
        logger.info('Fetching HTML content from provided URL')
        html_content, status_code = get_html_content(url)
    else:
        logger.info('Fetching today\'s data')
        html_content, status_code = fetch_today()

    if status_code != 200:
        logger.error('Failed to fetch data with status code %s', status_code)
        return jsonify({'error': html_content}), status_code

    logger.info('Parsing JSON data')
    json_data = parse_meeting_workbook_to_json(html_content)
    logger.info('Successfully parsed JSON data')
    return jsonify(json_data), 200


def fetch_weekly_bible_reading_info() -> tuple[dict, int]:
    today_html_content, status_code = fetch_today()
    if status_code != 200:
        return {'error': today_html_content}, status_code

    logger.info('Processing HTML content.')
    json_data = parse_weekly_bible_read(today_html_content)
    logger.info('Successfully parsed HTML to JSON.')

    return json_data, 200


@pub_mwb_bp.route('/weekly-scripture-read', methods=['GET'])
def get_weekly_bible_reading_info() -> tuple[Response, int]:
    """
    Parce this week's program to fetch information about the assigned biblical reading
    ---
    responses:
      200:
        description: The JSON content of this week's reading assignment
      404:
        description: Resource not found
    """
    json_data, status_code = fetch_weekly_bible_reading_info()
    return jsonify(json_data), status_code


@pub_mwb_bp.route('/scripture-read-references', methods=['GET'])
def get_bible_references_as_json() -> tuple[Response, int] | tuple[str, int]:
    """
    Extract all references found on the bible using the given links to the books to process and return them as JSON.
    If no links are provided, the links will be fetched from the weekly Bible reading assignment.

    Example of valid links:
    - https://wol.jw.org/es/wol/b/r4/lp-s/nwtsty/19/70
    - https://wol.jw.org/en/wol/b/r1/lp-e/nwtsty/19/70
    - https://wol.jw.org/en/wol/b/r1/lp-e/nwtsty/2/1

    The URL must meet the following criteria:
    - The domain must be 'wol.jw.org'.
    - The path must consist of 9 parts when split by '/'.
    - The first part must be empty.
    - The second part must be a string of length 2 (language code).
    - The sixth part (index -4) must start with 'lp'.
    - The seventh part (index -3) must be 'nwtsty'.
    - The eighth and ninth parts (index -2 and -1) must be numbers.
    ---
    parameters:
      - in: query
        name: links
        required: false
        type: array
        items:
          type: string
        collectionFormat: multi
        example: ["https://wol.jw.org/es/wol/b/r4/lp-s/nwtsty/19/70", "https://wol.jw.org/es/wol/b/r4/lp-s/nwtsty/19/71"]
    responses:
      200:
        description: The JSON content of the Bible references
      400:
        description: Invalid input
      404:
        description: Resource not found
    """
    links = request.args.getlist('links')

    logger.debug(f'Incoming links: {links}')

    if not links:
        response, status_code = fetch_weekly_bible_reading_info()
        if status_code != 200:
            return jsonify({'error': 'Failed to fetch weekly scripture reading links'}), status_code
        links = response.get('links', [])

    invalid_links = [link for link in links if not is_valid_wol_bible_book_url(link)]
    if invalid_links:
        return jsonify({'error': 'Some links are invalid', 'invalid_links': invalid_links}), 400

    bible_references = extract_references_from_links(links)

    return jsonify(bible_references), 200
