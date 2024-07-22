import re
from typing import Dict, Any, List

from flask import Flask, jsonify, request, Response
import logging
import os
import time
from bs4 import BeautifulSoup
from flasgger import Swagger
import requests

app = Flask(__name__)
swagger = Swagger(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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


def remove_strong_tag(question) -> str:
    strong_tag = question.find('strong')
    if strong_tag:
        strong_tag.decompose()
    return question.text.strip()


def extract_teach_block(soup: BeautifulSoup) -> Dict[str, Any]:
    teach_block_headline = ""
    teach_block_points = []

    teach_block = soup.find(id='tt16') or soup.select_one('.blockTeach')

    if teach_block:
        headline_element = teach_block.find('h2') or teach_block.select_one('.dc-ttClassStyle--unset h2')
        if headline_element:
            teach_block_headline = headline_element.text.strip()
        points_elements = teach_block.select('ul li p') or teach_block.select('.dc-ttClassStyle--unset ul li p')
        if points_elements:
            teach_block_points = [li.text.strip() for li in points_elements]

    return {
        'headline': teach_block_headline,
        'points': teach_block_points
    }


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


def extract_paragraph_numbers(question) -> List[int]:
    strong_tag = question.find('strong')
    if strong_tag:
        question_text = strong_tag.text.strip()
        numbers = re.findall(r'\d+', question_text)
        return [int(num) for num in numbers]
    return []


def extract_contents(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    contents = []
    questions = soup.find_all('p', class_='qu')
    for question in questions:
        p_numbers = extract_paragraph_numbers(question)
        q_text = remove_strong_tag(question)
        paragraphs = []

        data_pid = question.get('data-pid')
        related_paragraphs = soup.find_all('p', {'data-rel-pid': f'[{data_pid}]'})
        for para in related_paragraphs:
            paragraphs.append(para.text.strip())

        contents.append({
            'pNumbers': p_numbers,
            'question': q_text,
            'paragraphs': paragraphs
        })
    return contents


def parse_html_to_json(html: str) -> Dict[str, Any]:
    soup = BeautifulSoup(html, 'html5lib')

    article_number = soup.find('p', class_='contextTtl').strong.text.strip()
    article_title = soup.find('h1').strong.text.strip()
    article_topic = soup.find('p', class_='themeScrp').em.text.strip()

    contents = extract_contents(soup)
    teach_block = extract_teach_block(soup)

    json_data = {
        'articleNumber': article_number,
        'articleTitle': article_title,
        'articleTopic': article_topic,
        'contents': contents,
        'teachBlock': teach_block
    }

    return json_data


@app.route('/wol/fetch-landing-html', methods=['GET'])
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


@app.route('/wol/fetch-today-html', methods=['GET'])
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


@app.route('/pub-w/get-this-week-html', methods=['GET'])
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


@app.route('/pub-w/html-to-json', methods=['POST'])
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


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3001))
    logger.info(f'Starting Flask app on port {port}.')
    app.run(host='0.0.0.0', port=port)
