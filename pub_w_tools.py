import logging
import os
import re
from typing import Any, Dict, List
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify

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


def get_question_text_clean(question) -> str:
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
        q_text = get_question_text_clean(question)
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


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3001))
    logger.info(f'Starting Flask app on port {port}.')
    app.run(host='0.0.0.0', port=port)
