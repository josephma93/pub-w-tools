import logging
import re
from typing import Dict, Any, List

from bs4 import BeautifulSoup

from app.services.constants import Constants
from app.services.fetch_content import get_html_content
from app.services.general_reference_parsers import (extract_nwtsty_text_stripping_notes)
from app.services.reference_link_parser import parse_reference_data_from_anchor

logger = logging.getLogger('pub_mwb_parser')


def parse_10min_talk_from_soup(soup: BeautifulSoup) -> Dict[str, Any]:
    scrape_div = soup.find(id=Constants.TEN_MIN_TALK_DIV_ID)
    if not scrape_div:
        logger.debug(f'Div not found: {Constants.TEN_MIN_TALK_DIV_ID}')
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

    # Process paragraphs with CSS selector `#{Constants.TT8} > div > p`
    paragraphs = soup.select(f'#{Constants.TEN_MIN_TALK_DIV_ID} > div > p')
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
            footnote_data = parse_reference_data_from_anchor(link)
            del footnote_data["rawData"]  # remove the rawData to cut on noise
            result["footnotes"][footnote_index] = footnote_data
            footnote_index += 1

        result["points"].append({
            "text": paragraph_text,
            "footnotes": footnotes
        })

    return result


def parse_10min_talk_to_json(html: str) -> Dict[str, Any]:
    soup = BeautifulSoup(html, 'html5lib')
    return parse_10min_talk_from_soup(soup)


def extract_book_name_from_tooltip_caption(caption):
    pattern = r'^(.*?)(?=\d+:)'
    match = re.search(pattern, caption)
    if match:
        return match.group(1).strip()
    else:
        return caption


def parse_weekly_bible_read_from_soup(soup: BeautifulSoup) -> Dict[str, Any]:
    result = {
        "bookName": "",
        "bookNumber": -1,
        "firstChapter": -1,
        "lastChapter": -1,
        "links": [],
    }
    logger.debug(f"Input soup: {soup}")

    reading_assignment = soup.find(id='p2')

    if not reading_assignment:
        logger.warning(f'The link with bible reading assignment was not found: {reading_assignment}')
        return result

    logger.debug(f"Found reading assignment: {reading_assignment}")

    read_ref_links = reading_assignment.find_all('a')

    if not read_ref_links:
        logger.warning(f'Bible reading link not found: {read_ref_links}')
        return result

    logger.debug(f"Found read reference links: {read_ref_links}")

    data_for_url_building = None

    for link in read_ref_links:
        reference_link_data = parse_reference_data_from_anchor(link)

        if not reference_link_data["isPubNwtsty"]:
            logger.warning('The reference data extracted do not point to the bible')
            continue

        raw_reference_data = reference_link_data["rawData"]

        if not data_for_url_building:
            data_for_url_building = (raw_reference_data["url"], reference_link_data['sourceHref'][0:3])

        logger.debug(f"Extracted data for URL building: {data_for_url_building}")

        if not result["bookName"]:
            result["bookName"] = extract_book_name_from_tooltip_caption(raw_reference_data["caption"])
            result["bookNumber"] = raw_reference_data["book"]

        if result["firstChapter"] == -1 or raw_reference_data["first_chapter"] < result["firstChapter"]:
            result["firstChapter"] = raw_reference_data["first_chapter"]

        if result["lastChapter"] == -1 or raw_reference_data["last_chapter"] > result["lastChapter"]:
            result["lastChapter"] = raw_reference_data["last_chapter"]

    logger.debug(f"Extracted book data: {result}")

    tooltip_url = data_for_url_building[0]
    base_url_parts = tooltip_url.split('#')[0].split('/')
    language_code = data_for_url_building[1]
    for chapter in range(result["firstChapter"], result["lastChapter"] + 1):
        link_parts = base_url_parts.copy()
        link_parts[-1] = str(chapter)
        joined_url = '/'.join(link_parts)
        result["links"].append(f"{Constants.BASE_URL}{language_code}{joined_url}")

    logger.info(f"Successfully extracted links: {result['links']}")

    return result


def parse_weekly_bible_read(html: str) -> Dict[str, Any]:
    soup = BeautifulSoup(html, 'html5lib')
    return parse_weekly_bible_read_from_soup(soup)


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
            logger.info(f"Fetching reference link data for URL: {link.get('href')}")
            reference_link_data = parse_reference_data_from_anchor(link)

            if not reference_link_data['content']:
                logger.warning(f"Unable to load reference data from link: {reference_link_data['fetchUrl']}")
                ref_contents = 'UNABLE_TO_EXTRACT_REFERENCE'
            else:
                ref_contents = reference_link_data['parsedContent']

            mnemonic = link.get_text(strip=True).replace(',', '').replace(';', '')
            if ' ' not in mnemonic and prev_mnemonic:
                mnemonic = f"{prev_mnemonic.split(' ')[0]} {mnemonic}"

            logger.debug(f"Processed mnemonic: {mnemonic}")
            if mnemonic in seen_mnemonics:
                logger.debug(f"Mnemonic '{mnemonic}' already seen, updating count")
                seen_mnemonics[mnemonic]['count'] += 1
                references.append({
                    'mnemonic': mnemonic,
                    'refContents': f'SEE: sharedMnemonicReferences["{mnemonic}"]',
                })
                if seen_mnemonics[mnemonic].get('first_seen_ref'):
                    logger.debug(f"Updating first seen reference for mnemonic '{mnemonic}'")
                    seen_mnemonics[mnemonic]['first_seen_ref'][
                        'refContents'] = f'SEE: sharedMnemonicReferences["{mnemonic}"]'
                    del seen_mnemonics[mnemonic]['first_seen_ref']
            else:
                logger.debug(f"New mnemonic '{mnemonic}' seen, adding to references")
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
    logger.debug(f"Shared mnemonic references: {shared_mnemonic_references}")
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
            html_content, status_code = get_html_content(link)
            logger.debug(f"Received status code {status_code} for link {link}")

            if status_code != 200:
                error_msg = f'Failed to fetch content for link: {link}'
                logger.warning(error_msg)
                errors.append({'link': link, 'error': error_msg, 'status_code': status_code})
                continue

            parsed_reference = parse_bible_reference(html_content)
            logger.debug(f"Parsed reference for link {link}: {parsed_reference}")

            if parsed_reference:
                results.append({
                    'link': link,
                    'entries': parsed_reference['entries'],
                    'sharedMnemonicReferences': parsed_reference['sharedMnemonicReferences']
                })
        except Exception as e:
            error_msg = f'Error processing link {link}: {e}'
            logger.error(error_msg)
            errors.append({'link': link, 'error': error_msg})

    logger.info("Finished extracting references from links")
    return {
        'results': results,
        'errors': errors
    }


def parse_spiritual_gems_from_soup(soup: BeautifulSoup) -> Dict[str, Any]:
    result = {
        "printedQuestion": {
            "scriptureMnemonic": Constants.UNABLE_TO_FIND,
            "scriptureContents": Constants.UNABLE_TO_FIND,
            "question": Constants.UNABLE_TO_FIND,
            "answerSources": [],
        },
        "openEndedQuestion": Constants.UNABLE_TO_FIND,
    }
    logger.debug("Starting to parse spiritual gems from soup")

    tt8_element = soup.find(id=Constants.TEN_MIN_TALK_DIV_ID)
    if not tt8_element:
        logger.warning(f"Could not find element with id '{Constants.TEN_MIN_TALK_DIV_ID}'")
        return result

    gems_content_div = tt8_element.find_next_siblings(limit=3)[1]
    if not gems_content_div:
        logger.warning(f"Could not find sibling element [1] of element with id '{Constants.TEN_MIN_TALK_DIV_ID}'")
        return result

    scripture_mnemonic_tag = gems_content_div.find('a', class_='b')
    if scripture_mnemonic_tag:
        logger.debug("Found scripture mnemonic tag")
        result['printedQuestion']['scriptureMnemonic'] = scripture_mnemonic_tag.text.strip()
        result['printedQuestion']['scriptureContents'] = parse_reference_data_from_anchor(scripture_mnemonic_tag)[
            'parsedContent']

    question_tag = scripture_mnemonic_tag.find_parent('p')
    if question_tag:
        logger.debug("Found question tag")
        full_text = question_tag.text.strip()
        mnemonic_text = scripture_mnemonic_tag.text.strip()
        start_index = full_text.find(mnemonic_text) + len(mnemonic_text)
        parenthesis_start_index = full_text.find('(')

        if parenthesis_start_index > start_index:
            question_text = full_text[start_index:parenthesis_start_index].strip()[2:]  # Skip the `. ` after the mnemonic
            result['printedQuestion']['question'] = question_text

        answer_source_anchors = question_tag.find_all('a')[1:]  # Skip the first <a> which is the scripture mnemonic
        for source_anchor in answer_source_anchors:
            result['printedQuestion']['answerSources'].append({
                "mnemonic": source_anchor.text.strip(),
                "contents": parse_reference_data_from_anchor(source_anchor)['parsedContent'],
            })

    open_ended_question_tag = soup.find('li', class_='du-margin-top--8').find('p')
    if open_ended_question_tag:
        logger.debug("Found open-ended question tag")
        result['openEndedQuestion'] = open_ended_question_tag.text.strip()

    logger.info("Finished parsing spiritual gems from soup")
    return result



def parse_time_from_text(text: str) -> int:
    time_match = re.search(r'\((\d+)\s*mins?\.\)', text)
    if time_match:
        return int(time_match.group(1))
    else:
        return 0


def parse_bible_read_from_soup(soup: BeautifulSoup) -> Dict[str, Any]:
    result = {
        "timebox": 0,
        "scripture": {
            "mnemonic": Constants.UNABLE_TO_FIND,
            "contents": Constants.UNABLE_TO_FIND,
        },
        "studyPoint": {
            "mnemonic": Constants.UNABLE_TO_FIND,
            "contents": Constants.UNABLE_TO_FIND,
        },
    }

    tt8_element = soup.find(id=Constants.TEN_MIN_TALK_DIV_ID)
    if not tt8_element:
        logger.warning(f"Could not find element with id '{Constants.TEN_MIN_TALK_DIV_ID}'")
        return result

    bible_read_div = tt8_element.find_next_siblings(limit=5)[3]
    if not bible_read_div:
        logger.warning(f"Could not find sibling element [3] of element with id '{Constants.TEN_MIN_TALK_DIV_ID}'")
        return result

    logger.debug("Extracting content from bible read div")
    content_tag = bible_read_div.find('p')
    if not content_tag:
        logger.warning("Unable to find content tag in bible read")
        return result

    content_text = content_tag.text.strip()
    logger.debug("Content text: {}".format(content_text))

    result['timebox'] = parse_time_from_text(content_text)
    logger.info(f"Parsed timebox: {result['timebox']}")

    logger.debug("Searching for bible read anchors")
    bible_read_anchors = content_tag.find_all('a')

    if len(bible_read_anchors) < 2:
        logger.warning("Unable to find bible read anchors in bible read")
        return result

    scripture_anchor = bible_read_anchors[0]
    result['scripture']['mnemonic'] = scripture_anchor.text.strip()
    result['scripture']['contents'] = parse_reference_data_from_anchor(scripture_anchor)['parsedContent']
    logger.info(f"Parsed scripture data: {result['scripture']}")

    study_point_anchor = bible_read_anchors[1]
    result['studyPoint']['mnemonic'] = study_point_anchor.text.strip()
    result['studyPoint']['contents'] = parse_reference_data_from_anchor(study_point_anchor)['parsedContent']
    logger.info(f"Parsed study point data: {result['studyPoint']}")

    return result


def contains_two_sets_of_parentheses(text):
    regex = r'\(.*?\).*?\(.*?\)'
    return bool(re.search(regex, text))


def extract_between_parentheses(text):
    extract_regex = r"(?<=\)\s)\s*(.*?)\s*(?=\s\()"
    match = re.search(extract_regex, text)
    if match:
        return match.group(1)
    return text


def parse_field_ministry_from_soup(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    result = []

    tt8_element = soup.find(id=Constants.TEN_MIN_TALK_DIV_ID)
    if not tt8_element:
        logger.warning(f"Could not find element with id '{Constants.TEN_MIN_TALK_DIV_ID}'")
        return result

    siblings = tt8_element.find_next_siblings()
    siblings = list(siblings)[5:]  # Skip 5 siblings (Spiritual Gems and Bible Reading)

    field_ministry_parts = []
    for i, sibling in enumerate(siblings):
        if sibling.name == 'h3':
            field_ministry_parts.append({
                'headline': sibling,
            })
            continue
        if sibling.name == 'div':
            if 'dc-icon--sheep' in sibling.get('class', []):
                break
            field_ministry_parts[-1].update({
                'content': sibling,
            })
    logger.debug(f"Found {len(field_ministry_parts)} field ministry parts")

    for field_ministry_part in field_ministry_parts:
        headline = field_ministry_part['headline']
        content = field_ministry_part['content']
        content_text = content.text.strip()

        timebox = parse_time_from_text(content_text)
        seems_to_be_student_assignment = contains_two_sets_of_parentheses(content_text)

        study_point_mnemonic = Constants.UNABLE_TO_FIND
        study_point_contents = Constants.UNABLE_TO_FIND
        if seems_to_be_student_assignment:
            study_point_anchor = content.find_all('a')[-1]
            study_point_mnemonic = study_point_anchor.text.strip()
            study_point_contents = parse_reference_data_from_anchor(study_point_anchor)['parsedContent'].strip()
        logger.info(f"Parsed field ministry part: {headline.text.strip()}")

        result.append({
            'headline': headline.text.strip(),
            "timebox": timebox,
            "isStudentTask": seems_to_be_student_assignment,
            "studyPoint": {
                "mnemonic": study_point_mnemonic,
                "contents": study_point_contents,
            },
            "contents": extract_between_parentheses(content_text) if seems_to_be_student_assignment else content_text,
        })

    logger.info(f"Parsed {len(result)} field ministry parts")
    return result


def parse_christian_living_from_soup(soup: BeautifulSoup) -> Dict[str, Any]:
    result = {
        "others": [],
        "bibleStudy": {},
    }

    return result


def parse_meeting_workbook_to_json(html: str) -> Dict[str, Any]:
    logger.debug(f"Parsing HTML: {html}")
    soup = BeautifulSoup(html, 'html5lib')
    logger.info("Parsed HTML into soup")

    bible_study = parse_weekly_bible_read_from_soup(soup)
    ten_min_talk = parse_10min_talk_from_soup(soup)
    spiritual_gems = parse_spiritual_gems_from_soup(soup)
    bible_read = parse_bible_read_from_soup(soup)
    field_ministry = parse_field_ministry_from_soup(soup)
    christian_living = parse_christian_living_from_soup(soup)

    logger.debug(
        "Parsed components: bible_study, ten_min_talk, spiritual_gems, bible_read, field_ministry, christian_living")

    # Remove some noise from ten_min_talk
    for i, entry in ten_min_talk['footnotes'].items():
        ten_min_talk['footnotes'][i].pop('content', None)
        ten_min_talk['footnotes'][i].pop('articleClasses', None)
    logger.info("Removed noise from ten_min_talk")

    result = {
        "weekDateSpan": soup.find(id='p1').text.strip().lower(),
        "bibleStudy": bible_study,
        "godTreasures": {
            "tenMinTalk": ten_min_talk,
            "spiritualGems": spiritual_gems,
            "bibleRead": bible_read,
        },
        "fieldMinistry": field_ministry,
        "christianLiving": christian_living,
    }

    logger.info("Constructed result dictionary")
    return result
