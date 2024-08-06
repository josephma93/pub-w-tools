import logging
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger('fetch_content')


def get_html_content(url: str) -> tuple[str, int]:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:126.0) Gecko/20100101 Firefox/126.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'es-ES,es;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Referer': 'https://wol.jw.org/'
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.text, 200
    except requests.exceptions.HTTPError as e:
        logger.error(f'HTTP error occurred: {e.response.status_code} - {e.response.reason}')
        return f'HTTP error: {e.response.status_code} - {e.response.reason}', e.response.status_code
    except requests.exceptions.ConnectionError as e:
        logger.error(f'Connection error occurred: {e}')
        return 'Connection error occurred', 503
    except requests.exceptions.Timeout as e:
        logger.error(f'Timeout error occurred: {e}')
        return 'Timeout error occurred', 504
    except requests.exceptions.RequestException as e:
        logger.error(f'Request error occurred: {e}')
        return 'Request error occurred', 500


def fetch_landing_html() -> tuple[str, int]:
    base_url = 'https://wol.jw.org'
    logger.info('Step 1: Requesting base URL')
    html_content, status_code = get_html_content(base_url)
    if status_code != 200:
        return html_content, status_code
    soup = BeautifulSoup(html_content, 'html5lib')

    logger.info('Step 2: Extracting href from link[hreflang="es"]')
    href_lang_es = soup.select_one('link[hreflang="es"]')
    if not href_lang_es:
        return 'No href found for hreflang="es"', 404
    href_lang_es = href_lang_es['href']

    logger.info('Step 3: Requesting the extracted href')
    html_content, status_code = get_html_content(base_url + href_lang_es)
    return html_content, status_code


def fetch_today_html(base_html: str) -> tuple[str, int]:
    soup = BeautifulSoup(base_html, 'html5lib')

    logger.info('Step 4: Extracting href from #menuToday .todayNav')
    today_nav = soup.select_one('#menuToday .todayNav')
    if not today_nav:
        return 'No href found for #menuToday .todayNav', 404
    today_nav_href = today_nav['href']

    logger.info('Step 5: Requesting the extracted href')
    base_url = 'https://wol.jw.org'
    html_content, status_code = get_html_content(base_url + today_nav_href)
    return html_content, status_code


def fetch_weekly_html(today_html: str) -> tuple[str, int]:
    soup = BeautifulSoup(today_html, 'html5lib')

    logger.info('Step 6: Extracting href from .todayItem.pub-w:nth-child(2) .itemData a')
    pub_w_item = soup.select_one('.todayItem.pub-w:nth-child(2) .itemData a')
    if not pub_w_item:
        return 'No href found for .todayItem.pub-w:nth-child(2) .itemData a', 404
    pub_w_item_href = pub_w_item['href']

    logger.info('Step 7: Requesting the extracted href')
    base_url = 'https://wol.jw.org'
    html_content, status_code = get_html_content(base_url + pub_w_item_href)
    if status_code != 200:
        return html_content, status_code

    logger.info('Step 8: Extracting the HTML of the element with id="article"')
    soup = BeautifulSoup(html_content, 'html5lib')
    article_element = soup.find(id='article')
    if not article_element:
        return 'No element found with id="article"', 404

    return str(article_element), 200


def is_valid_wol_bible_book_url(url: str) -> bool:
    try:
        parsed_url = urlparse(url)
        if parsed_url.netloc != 'wol.jw.org':
            return False
        path_parts = parsed_url.path.split('/')
        if len(path_parts) != 9:
            return False
        if path_parts[0] != '':
            return False
        if len(path_parts[1]) != 2:
            return False
        if not path_parts[-4].startswith('lp'):
            return False
        if path_parts[-3] != 'nwtsty':
            return False
        if not path_parts[-2].isdigit():
            return False
        if not path_parts[-1].isdigit():
            return False
        return True
    except Exception as e:
        return False
