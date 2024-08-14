import json
import logging
import re
from typing import Dict, Any

from bs4 import BeautifulSoup, Tag

from app.services.constants import Constants
from app.services.fetch_content import get_html_content
from app.services.general_reference_parsers import PubWParserStrategy, PubNwtstyParserStrategy, DefaultParserStrategy, \
    ContentParser

logger = logging.getLogger('general_parser')


def validate_and_parse_potential_reference_json(json_string):
    try:
        # Parse the JSON string
        data = json.loads(json_string)

        if not isinstance(data.get('items'), list) or len(data['items']) < 1:
            return "Error: .items must be an array with at least 1 item"

        if not isinstance(data['items'][0].get('content'), str) or not data['items'][0]['content']:
            return "Error: .items[0].content must be a non-empty string"

        if not isinstance(data['items'][0].get('articleClasses'), str) or not data['items'][0]['articleClasses']:
            return "Error: .items[0].articleClasses must be a non-empty string"

        content = data['items'][0]['content']
        article_classes = data['items'][0]['articleClasses']

        is_pub_w = bool(re.search(rf'\b{Constants.PUB_CODE_WATCHTOWER}\b', article_classes, re.IGNORECASE))
        is_pub_nwtsty = bool(re.search(rf'\b{Constants.PUB_CODE_BIBLE}\b', article_classes, re.IGNORECASE))

        return {
            "content": content,
            "articleClasses": article_classes,
            "isPubW": is_pub_w,
            "isPubNwtsty": is_pub_nwtsty,
            "rawData": data["items"][0],
        }
    except json.JSONDecodeError:
        return "Error: Invalid JSON"


def apply_specific_reference_data_parsing(parsed_json):
    content = parsed_json.get("content")
    is_pub_w = parsed_json.get("isPubW", False)
    is_pub_nwtsty = parsed_json.get("isPubNwtsty", False)

    # Choose the appropriate strategy
    if is_pub_w:
        parser_strategy = PubWParserStrategy()
    elif is_pub_nwtsty:
        parser_strategy = PubNwtstyParserStrategy()
    else:
        parser_strategy = DefaultParserStrategy()

    # Use the context class to parse the content
    content_parser = ContentParser(parser_strategy)
    parsed_content = content_parser.parse_content(content)

    return {
        "parsedContent": parsed_content,
    }


"""
Parses reference data from an anchor element.

Args:
    anchor_element (BeautifulSoup): The anchor element from which to extract the reference data.

Returns:
    Dict[str, Any]: A dictionary containing the parsed reference data, including:
        - 'sourceHref' (str): The source href extracted from the anchor element.
        - 'fetchUrl' (str): The fetch URL constructed from the source href.
        - 'content' (str): The content extracted from the parsed JSON data.
        - 'articleClasses' (str): The article classes extracted from the parsed JSON data.
        - 'isPubW' (bool): Whether the article is a Watchtower publication.
        - 'isPubNwtsty' (bool): Whether the article is a New World Translation study publication.
        - 'rawData' (dict): The raw data extracted from the parsed JSON data.
        - 'parsedContent' (str): The parsed content extracted from the parsed JSON data using the apply_specific_reference_data_parsing function.
            For details on the parsing strategy and output format, see the general_reference_parsers file.

Raises:
    None
"""
def parse_reference_data_from_anchor(anchor_element: BeautifulSoup | Tag) -> Dict[str, Any]:
    source_href = anchor_element.get('href')
    fetch_url = f"https://wol.jw.org{source_href[3:]}"
    result = {
        "sourceHref": source_href,
        "fetchUrl": fetch_url,
        'content': None,
    }

    potential_json_content, status_code = get_html_content(fetch_url)
    if status_code != 200:
        logger.warning(f'Unable to load reference data from link: {fetch_url}')
        return result

    maybe_json = validate_and_parse_potential_reference_json(potential_json_content)
    if isinstance(maybe_json, str):
        logger.warning('Unable to parse reference data to JSON')
        return result

    confirmed_json: dict = maybe_json
    result.update(confirmed_json)
    result.update(apply_specific_reference_data_parsing(confirmed_json))

    return result
