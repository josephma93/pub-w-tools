import logging
import os
import re
import time
from typing import Any, Dict, List
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_paragraph_numbers(question) -> List[int]:
    strong_tag = question.find('strong')
    if strong_tag:
        question_text = strong_tag.text.strip()
        numbers = re.findall(r'\d+', question_text)
        return [int(num) for num in numbers]
    return []


def remove_strong_tag(question) -> str:
    strong_tag = question.find('strong')
    if strong_tag:
        strong_tag.decompose()
    return question.text.strip()


def parse_html_to_json(html: str) -> Dict[str, Any]:
    soup = BeautifulSoup(html, 'html5lib')

    # Extract article number, title, and topic
    article_number = soup.find('p', class_='contextTtl').strong.text.strip()
    article_title = soup.find('h1').strong.text.strip()
    article_topic = soup.find('p', class_='themeScrp').em.text.strip()

    contents = []
    questions = soup.find_all('p', class_='qu')
    for question in questions:
        p_numbers = extract_paragraph_numbers(question)
        q_text = remove_strong_tag(question)  # Remove the paragraph number and following space
        paragraphs = []

        # Get related paragraphs using data-pid and data-rel-pid
        data_pid = question.get('data-pid')
        related_paragraphs = soup.find_all('p', {'data-rel-pid': f'[{data_pid}]'})
        for para in related_paragraphs:
            paragraphs.append(para.text.strip())

        contents.append({
            'pNumbers': p_numbers,
            'question': q_text,
            'paragraphs': paragraphs
        })

    teach_block = soup.find(id='tt16')
    if teach_block:
        teach_block_headline = teach_block.find('h2').text.strip()
        teach_block_points = [li.text.strip() for li in teach_block.select('ul li p')]
    else:
        teach_block_headline = ""
        teach_block_points = []

    json_data = {
        'articleNumber': article_number,
        'articleTitle': article_title,
        'articleTopic': article_topic,
        'contents': contents,
        'teachBlock': {
            'headline': teach_block_headline,
            'points': teach_block_points
        }
    }

    return json_data


def get_html_content(url: str) -> (str, int):
    try:
        response = requests.get(url)
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


@app.route('/pub-w', methods=['POST'])
def parse_pub_w():
    input_html = request.form.get('html')
    if not input_html:
        logger.error('Invalid input: No HTML content provided.')
        return 'Invalid input', 400
    logger.info('Processing HTML content.')
    json_data = parse_html_to_json(input_html)
    logger.info('Successfully parsed HTML to JSON.')
    return jsonify(json_data), 200


@app.route('/get-article', methods=['GET'])
def get_article():
    try:
        start_time = time.time()

        # Step 1: Request to https://wol.jw.org
        base_url = 'https://wol.jw.org'
        logger.info('Step 1: Requesting base URL')
        html_content, status_code = get_html_content(base_url)
        if status_code != 200:
            return jsonify({'error': html_content}), status_code
        soup = BeautifulSoup(html_content, 'html5lib')
        logger.info(f'Step 1 completed in {time.time() - start_time:.2f} seconds')

        # Step 2: Extract href from link[hreflang="es"]
        step_start_time = time.time()
        href_lang_es = soup.select_one('link[hreflang="es"]')
        if not href_lang_es:
            return jsonify({'error': 'No href found for hreflang="es"'}), 404
        href_lang_es = href_lang_es['href']
        logger.info(f'Step 2 completed in {time.time() - step_start_time:.2f} seconds')

        # Step 3: Request to the extracted href
        step_start_time = time.time()
        html_content, status_code = get_html_content(base_url + href_lang_es)
        if status_code != 200:
            return jsonify({'error': html_content}), status_code
        soup = BeautifulSoup(html_content, 'html5lib')
        logger.info(f'Step 3 completed in {time.time() - step_start_time:.2f} seconds')

        # Step 4: Extract href from #menuToday .todayNav
        step_start_time = time.time()
        today_nav = soup.select_one('#menuToday .todayNav')
        if not today_nav:
            return jsonify({'error': 'No href found for #menuToday .todayNav'}), 404
        today_nav_href = today_nav['href']
        logger.info(f'Step 4 completed in {time.time() - step_start_time:.2f} seconds')

        # Step 5: Request to the extracted href
        step_start_time = time.time()
        html_content, status_code = get_html_content(base_url + today_nav_href)
        if status_code != 200:
            return jsonify({'error': html_content}), status_code
        soup = BeautifulSoup(html_content, 'html5lib')
        logger.info(f'Step 5 completed in {time.time() - step_start_time:.2f} seconds')

        # Step 6: Extract href from .todayItem.pub-w:nth-child(2) .itemData a
        step_start_time = time.time()
        pub_w_item = soup.select_one('.todayItem.pub-w:nth-child(2) .itemData a')
        if not pub_w_item:
            return jsonify({'error': 'No href found for .todayItem.pub-w:nth-child(2) .itemData a'}), 404
        pub_w_item_href = pub_w_item['href']
        logger.info(f'Step 6 completed in {time.time() - step_start_time:.2f} seconds')

        # Step 7: Request to the extracted href
        step_start_time = time.time()
        html_content, status_code = get_html_content(base_url + pub_w_item_href)
        if status_code != 200:
            return jsonify({'error': html_content}), status_code
        soup = BeautifulSoup(html_content, 'html5lib')
        logger.info(f'Step 7 completed in {time.time() - step_start_time:.2f} seconds')

        # Step 8: Extract and return the HTML of the element with id="article"
        step_start_time = time.time()
        article_element = soup.find(id='article')
        if not article_element:
            return jsonify({'error': 'No element found with id="article"'}), 404
        logger.info(f'Step 8 completed in {time.time() - step_start_time:.2f} seconds')

        total_time = time.time() - start_time
        logger.info(f'Total time for get_article: {total_time:.2f} seconds')

        return str(article_element), 200

    except Exception as e:
        logger.error(f'Error in get_article endpoint: {e}')
        return jsonify({'error': 'An error occurred while processing your request'}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3001))
    logger.info(f'Starting Flask app on port {port}.')
    app.run(host='0.0.0.0', port=port)
