import logging
import time
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from app.services.constants import Constants

logger = logging.getLogger('fetch_content')


def get_html_content(url: str) -> tuple[str, int]:
    """
    Sends a GET request to the provided URL and returns the HTML content.

    Args:
    url (str): The URL to send the request to.

    Returns:
    tuple[str, int]: A tuple containing the HTML content and the HTTP status code.
    """
    start_time = time.time()

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:126.0) Gecko/20100101 Firefox/126.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'es-ES,es;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Referer': Constants.BASE_URL,
    }

    logger.debug(f"Sending GET request to {url} with headers: {headers}")

    try:
        response = requests.get(url, headers=headers, timeout=(6.05, 27))
        response.raise_for_status()
        elapsed_time = time.time() - start_time
        logger.info(f"Received HTML content from {url} with status code 200 in {elapsed_time:.2f} seconds")
        if elapsed_time > 10:
            logger.warning(f"Operation took {elapsed_time:.2f} seconds")
        return response.text, 200
    except requests.exceptions.HTTPError as e:
        elapsed_time = time.time() - start_time
        logger.error(f"HTTP error occurred: {e.response.status_code} - {e.response.reason} in {elapsed_time:.2f} seconds")
        if elapsed_time > 10:
            logger.warning(f"Operation took {elapsed_time:.2f} seconds")
        return f"HTTP error: {e.response.status_code} - {e.response.reason}", e.response.status_code
    except requests.exceptions.ConnectionError as e:
        elapsed_time = time.time() - start_time
        logger.warning(f"Connection error occurred: {e} in {elapsed_time:.2f} seconds")
        if elapsed_time > 10:
            logger.warning(f"Operation took {elapsed_time:.2f} seconds")
        return "Connection error occurred", 503
    except requests.exceptions.Timeout as e:
        elapsed_time = time.time() - start_time
        logger.warning(f"Timeout error occurred: {e} in {elapsed_time:.2f} seconds")
        if elapsed_time > 10:
            logger.warning(f"Operation took {elapsed_time:.2f} seconds")
        return "Timeout error occurred", 504
    except requests.exceptions.RequestException as e:
        elapsed_time = time.time() - start_time
        logger.error(f"Request error occurred: {e} in {elapsed_time:.2f} seconds")
        if elapsed_time > 10:
            logger.warning(f"Operation took {elapsed_time:.2f} seconds")
        logger.error(f"Request error occurred: {e}")
        return "Request error occurred", 500


def fetch_landing_html() -> tuple[str, int]:
    base_url = Constants.BASE_URL

    logger.info(f"Fetching landing HTML from {base_url}")
    html_content, status_code = get_html_content(base_url)
    logger.debug(f"Received HTML content with status code {status_code}")

    if status_code != 200:
        logger.error(f"Failed to fetch landing HTML: {html_content}")
        return html_content, status_code

    soup = BeautifulSoup(html_content, 'html5lib')
    href_lang_es = soup.select_one('link[hreflang="es"]')
    logger.debug(f"Found href_lang_es: {href_lang_es}")

    if not href_lang_es:
        logger.warning("No href found for hreflang='es'")
        return 'No href found for hreflang="es"', 404

    href_lang_es = href_lang_es['href']
    logger.info(f"Fetching HTML content from {base_url + href_lang_es}")
    html_content, status_code = get_html_content(base_url + href_lang_es)
    logger.debug(f"Received HTML content with status code {status_code}")

    return html_content, status_code


def fetch_today_html(base_html: str) -> tuple[str, int]:
    logger.debug("Parsing base HTML")
    soup = BeautifulSoup(base_html, 'html5lib')

    logger.debug("Selecting today's navigation link")
    today_nav = soup.select_one('#menuToday .todayNav')
    if not today_nav:
        logger.warning("No href found for #menuToday .todayNav")
        return 'No href found for #menuToday .todayNav', 404
    today_nav_href = today_nav['href']

    logger.info("Fetching today's HTML content from %s", Constants.BASE_URL + today_nav_href)
    html_content, status_code = get_html_content(Constants.BASE_URL + today_nav_href)
    logger.debug("Received HTML content with status code %s", status_code)

    return html_content, status_code


def fetch_weekly_html(today_html: str) -> tuple[str, int]:
    logger.debug("Parsing today's HTML")
    soup = BeautifulSoup(today_html, 'html5lib')

    pub_w_item = soup.select_one('.todayItem.pub-w:nth-child(2) .itemData a')
    if not pub_w_item:
        logger.warning("No href found for .todayItem.pub-w:nth-child(2) .itemData a")
        return 'No href found for .todayItem.pub-w:nth-child(2) .itemData a', 404
    pub_w_item_href = pub_w_item['href']

    logger.info(f"Fetching weekly HTML content from {Constants.BASE_URL + pub_w_item_href}")
    html_content, status_code = get_html_content(Constants.BASE_URL + pub_w_item_href)
    if status_code != 200:
        logger.error(f"Failed to fetch weekly HTML: {html_content}")
        return html_content, status_code

    logger.debug("Parsing weekly HTML")
    soup = BeautifulSoup(html_content, 'html5lib')
    article_element = soup.find(id='article')
    if not article_element:
        logger.error("No element found with id='article'")
        return 'No element found with id="article"', 404

    logger.info("Weekly HTML fetched successfully")
    return str(article_element), 200



def parse_url(url: str) -> dict | None:
    logger.debug(f"Parsing URL: {url}")
    try:
        parsed_url = urlparse(url)
        logger.debug(f"Parsed URL: {parsed_url}")
        return {
            'netloc': parsed_url.netloc,
            'path_parts': parsed_url.path.split('/')
        }
    except Exception as e:
        logger.error(f"Error parsing URL: {url} - {e}")
        return None



def is_wol_jw_org(parsed_url: dict) -> bool:
    return parsed_url.get('netloc') == 'wol.jw.org'


def is_url_str_in_wol_jw_org(url: str) -> bool:
    parsed_url = parse_url(url)
    if not parsed_url:
        return False
    return is_wol_jw_org(parsed_url)


def is_valid_wol_bible_book_url(url: str) -> bool:
    logger.debug(f"Checking if URL is a valid WOL Bible book URL: {url}")
    parsed_url = parse_url(url)
    if not parsed_url:
        logger.warning(f"Failed to parse URL: {url}")
        return False
    if not is_wol_jw_org(parsed_url):
        logger.debug(f"URL is from wol.jw.org, skipping: {url}")
        return False
    path_parts = parsed_url['path_parts']
    logger.debug(f"Parsed URL path parts: {path_parts}")
    if len(path_parts) != 9:
        logger.warning(f"Invalid URL path parts length: {len(path_parts)} (expected 9)")
        return False
    if path_parts[0] != '':
        logger.warning(f"Invalid URL path parts first element: {path_parts[0]} (expected empty string)")
        return False
    if len(path_parts[1]) != 2:
        logger.warning(f"Invalid URL path parts second element length: {len(path_parts[1])} (expected 2)")
        return False
    if not path_parts[-4].startswith('lp'):
        logger.warning(f"Invalid URL path parts fourth element from end: {path_parts[-4]} (expected to start with 'lp')")
        return False
    if path_parts[-3] != 'nwtsty':
        logger.warning(f"Invalid URL path parts third element from end: {path_parts[-3]} (expected 'nwtsty')")
        return False
    if not path_parts[-2].isdigit():
        logger.warning(f"Invalid URL path parts second element from end: {path_parts[-2]} (expected digit)")
        return False
    if not path_parts[-1].isdigit():
        logger.warning(f"Invalid URL path parts last element: {path_parts[-1]} (expected digit)")
        return False

    logger.info(f"URL is a valid WOL Bible book URL: {url}")
    return True

