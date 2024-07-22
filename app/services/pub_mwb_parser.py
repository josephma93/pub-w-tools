import json
import logging
import re
from typing import Dict, Any

from bs4 import BeautifulSoup

from app.services.fetch_content import get_html_content
from app.services.pub_mwb_reference_parsers import PubWParserStrategy, PubNwtstyParserStrategy, DefaultParserStrategy, \
    ContentParser

logger = logging.getLogger('pub_mwb_parser')


def parse_reference_json_if_possible(json_string):
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

        is_pub_w = bool(re.search(r'\bpub-w\b', article_classes, re.IGNORECASE))
        is_pub_nwtsty = bool(re.search(r'\bpub-nwtsty\b', article_classes, re.IGNORECASE))

        return {
            "content": content,
            "articleClasses": article_classes,
            "isPubW": is_pub_w,
            "isPubNwtsty": is_pub_nwtsty
        }
    except json.JSONDecodeError:
        return "Error: Invalid JSON"


def apply_parsing_logic(parsed_json):
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


def parse_10min_talk_to_json(html: str) -> Dict[str, Any]:
    scrape_div_id = 'tt8'
    soup = BeautifulSoup(html, 'html5lib')

    # Locate the scrape div
    scrape_div = soup.find(id=scrape_div_id)
    if not scrape_div:
        logger.debug(f'Div not found: {scrape_div_id}')
        scrape_div = soup.find('article')
        if not scrape_div:
            logger.debug('Article tag not found either.')
            return {"heading": "", "points": [], "footnotes": {}}

    result = {
        "heading": "",
        "points": [],
        "footnotes": {}
    }
    footnote_index = 1

    # Process heading (only the first h3)
    heading = scrape_div.find('h3')
    if heading:
        result["heading"] = heading.get_text(strip=True)

    logger.debug(result["heading"])

    # Process paragraphs with CSS selector `#tt8 > div > p`
    paragraphs = soup.select(f'#{scrape_div_id} > div > p')
    for paragraph in paragraphs:
        paragraph_text = paragraph.get_text(strip=True)
        logger.debug(paragraph_text)
        links = paragraph.find_all('a')
        footnotes = []
        logger.debug(links)

        for link in links:
            link_text = link.get_text(strip=True)
            paragraph_text = paragraph_text.replace(link_text, f"{link_text}[^{footnote_index}]")
            footnotes.append(footnote_index)
            result["footnotes"][footnote_index] = {
                "sourceHref": link.get('href'),
                "fetchUrl": f"https://wol.jw.org{link.get('href')[3:]}",
                "content": "",
                "articleClasses": "",
                "isPubW": False,
                "isPubNwtsty": False,
            }
            footnote_index += 1

        result["points"].append({
            "text": paragraph_text,
            "footnotes": footnotes
        })

    logger.debug(result["footnotes"])

    for fn_index in result["footnotes"]:
        logger.debug(fn_index)
        fn = result["footnotes"][fn_index]
        logger.debug(fn)

        potential_json_content, status_code = get_html_content(fn["fetchUrl"])
        if status_code != 200:
            continue

        maybe_json = parse_reference_json_if_possible(potential_json_content)
        if isinstance(maybe_json, dict):
            fn.update(maybe_json)
            fn.update(apply_parsing_logic(maybe_json))

    return result
