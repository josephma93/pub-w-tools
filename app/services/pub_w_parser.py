import re
from typing import Dict, Any, List

from bs4 import BeautifulSoup


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
    article_theme_scripture = soup.find('p', class_='themeScrp').text.strip()
    article_topic = soup.select_one('#tt9 p:nth-of-type(2)').text.strip()

    contents = extract_contents(soup)
    teach_block = extract_teach_block(soup)

    json_data = {
        'articleNumber': article_number,
        'articleTitle': article_title,
        'articleThemeScrp': article_theme_scripture,
        'articleTopic': article_topic,
        'contents': contents,
        'teachBlock': teach_block
    }

    return json_data
