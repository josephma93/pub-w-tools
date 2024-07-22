from typing import Dict, Any

from bs4 import BeautifulSoup


def parse_10min_talk_to_json(html: str) -> Dict[str, Any]:
    soup = BeautifulSoup(html, 'html5lib')

    soup.find(id='tt8')

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