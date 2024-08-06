import json
import logging
import re
from typing import Dict, Any

from bs4 import BeautifulSoup

from app.services.fetch_content import get_html_content
from app.services.pub_mwb_reference_parsers import (PubWParserStrategy,
                                                    PubNwtstyParserStrategy,
                                                    DefaultParserStrategy,
                                                    ContentParser,
                                                    extract_nwtsty_text_stripping_notes)

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
            "isPubNwtsty": is_pub_nwtsty,
            "rawData": data["items"][0],
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


def build_reference_link_data(link) -> Dict[str, str]:
    source_href = link.get('href')
    return {
        "sourceHref": source_href,
        "fetchUrl": f"https://wol.jw.org{source_href[3:]}",
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
            result["footnotes"][footnote_index] = build_reference_link_data(link).update({
                "content": "",
                "articleClasses": "",
                "isPubW": False,
                "isPubNwtsty": False,
            })
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
            del maybe_json["rawData"]
            fn.update(maybe_json)
            fn.update(apply_parsing_logic(maybe_json))

    return result


def extract_book_name_from_tooltip_caption(caption):
    pattern = r'^(.*?)(?=\d+:)'
    match = re.search(pattern, caption)
    if match:
        return match.group(1).strip()
    else:
        return caption


def parse_weekly_bible_read(html: str) -> Dict[str, Any]:
    result = {
        "bookName": "",
        "bookNumber": -1,
        "firstChapter": -1,
        "lastChapter": -1,
        "links": [],
    }
    # logger.debug(html)
    soup = BeautifulSoup(html, 'html5lib')
    reading_assignment = soup.find(id='p2')

    if not reading_assignment:
        logger.warning(f'The link with bible reading assignment was not found: {reading_assignment}')
        return result

    read_ref_link = reading_assignment.find('a')

    if not read_ref_link:
        logger.warning(f'Bible reading link not found: {read_ref_link}')
        return result

    reference_link_data = build_reference_link_data(read_ref_link)

    potential_json_content, status_code = get_html_content(reference_link_data["fetchUrl"])
    if status_code != 200:
        logger.warning(f'Unable to load reference data from link: {reference_link_data["fetchUrl"]}')
        return result

    maybe_json = parse_reference_json_if_possible(potential_json_content)
    if isinstance(maybe_json, str):
        logger.warning('Unable to parse reference data to JSON')
        return result

    if not maybe_json["isPubNwtsty"]:
        logger.warning('The reference data extracted do not point to the bible')
        return result

    json_content = maybe_json["rawData"]

    result["bookName"] = extract_book_name_from_tooltip_caption(json_content["caption"])
    result["bookNumber"] = json_content["book"]
    result["firstChapter"] = json_content["first_chapter"]
    result["lastChapter"] = json_content["last_chapter"]

    tooltip_url: str = json_content["url"]
    language_code = reference_link_data['sourceHref'][0:3]
    base_url_parts = tooltip_url.split('#')[0].split('/')
    for chapter in range(json_content["first_chapter"], json_content["last_chapter"] + 1):
        link_parts = base_url_parts.copy()
        link_parts[-1] = str(chapter)
        joined_url = '/'.join(link_parts)
        result["links"].append(f"https://wol.jw.org{language_code}{joined_url}")

    return result


def parse_bible_reference(html: str) -> dict:
    logger.info("Starting to parse Bible reference")
    soup = BeautifulSoup(html, 'html5lib')

    sections = soup.select('.section:not(:nth-child(1))')
    entries = []
    seen_mnemonics = {}

    logger.debug(f"Found {len(sections)} sections to process")
    for section in sections:
        references = []
        key = section['data-key']
        prev_mnemonic = None

        logger.debug(f"Processing section with key: {key}")
        for link in section.select('.group.index.collapsible .sx a'):
            reference_link_data = build_reference_link_data(link)

            logger.info(f"Fetching content from URL: {reference_link_data['fetchUrl']}")
            potential_json_content, status_code = get_html_content(reference_link_data["fetchUrl"])
            if status_code != 200:
                logger.warning(f"Unable to load reference data from link: {reference_link_data['fetchUrl']}")
                ref_contents = 'UNABLE_TO_EXTRACT_REFERENCE'
            else:
                maybe_json = parse_reference_json_if_possible(potential_json_content)
                if isinstance(maybe_json, str):
                    logger.warning("Unable to parse reference data to JSON")
                    ref_contents = 'UNABLE_TO_EXTRACT_REFERENCE'
                else:
                    ref_contents = apply_parsing_logic(maybe_json)

            mnemonic = link.get_text(strip=True).replace(',', '').replace(';', '')
            if ' ' not in mnemonic and prev_mnemonic:
                mnemonic = f"{prev_mnemonic.split(' ')[0]} {mnemonic}"

            logger.debug(f"Processed mnemonic: {mnemonic}")
            if mnemonic in seen_mnemonics:
                seen_mnemonics[mnemonic]['count'] += 1
                references.append({
                    'mnemonic': mnemonic,
                    'refContents': f'SEE: sharedMnemonicReferences["{mnemonic}"]',
                })
                if seen_mnemonics[mnemonic].get('first_seen_ref'):
                    seen_mnemonics[mnemonic]['first_seen_ref'][
                        'refContents'] = f'SEE: sharedMnemonicReferences["{mnemonic}"]'
                    del seen_mnemonics[mnemonic]['first_seen_ref']
            else:
                ref_dict = {
                    'mnemonic': mnemonic,
                    'refContents': ref_contents
                }
                references.append(ref_dict)
                seen_mnemonics[mnemonic] = {
                    'count': 1,
                    'refContents': ref_contents,
                    'first_seen_ref': ref_dict,
                }

            prev_mnemonic = mnemonic

        citation = section.select_one('h3.title').get_text(strip=True)

        scripture = ' '.join(
            extract_nwtsty_text_stripping_notes(e)
            for e in soup.select(f'[id*="{key}"]')
        ).strip()

        logger.info(f"Processed citation: {citation}")
        entries.append({
            'citation': citation,
            'scripture': scripture,
            'references': references,
        })

    shared_mnemonic_references = {mnemonic: data['refContents'] for mnemonic, data in seen_mnemonics.items() if
                                  data['count'] > 1}

    logger.info("Finished parsing Bible reference")
    return {
        'entries': entries,
        'sharedMnemonicReferences': shared_mnemonic_references,
    }


def extract_references_from_links(links: list[str]) -> dict:
    logger.info("Starting to extract references from links")
    results = []
    errors = []

    for link in links:
        try:
            logger.info(f"Fetching content for link: {link}")
            html_content, status_code = get_html_content(link)
            if status_code != 200:
                error_msg = f'Failed to fetch content for link: {link}'
                logger.warning(error_msg)
                errors.append({'link': link, 'error': error_msg, 'status_code': status_code})
                continue

            logger.info(f"Parsing references for book with URL: {link}")
            parsed_reference = parse_bible_reference(html_content)
            if parsed_reference:
                results.append({
                    'link': link,
                    'entries': parsed_reference['entries'],
                    'sharedMnemonicReferences': parsed_reference['sharedMnemonicReferences']
                })
        except Exception as e:
            error_msg = f'Error processing link {link}: {e}'
            logger.warning(error_msg)
            errors.append({'link': link, 'error': error_msg})

    logger.info("Finished extracting references from links")
    return {
        'results': results,
        'errors': errors
    }
