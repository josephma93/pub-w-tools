from typing import Dict

from bs4 import PageElement



def build_reference_link_data(link: PageElement) -> Dict[str, str]:
    source_href = link.get('href')
    return {
        "sourceHref": source_href,
        "fetchUrl": f"https://wol.jw.org{source_href[3:]}",
    }

def parse_link_with_tooltip_reference(link: PageElement) -> Dict[str, Any]:
    footnote_data = build_reference_link_data(link)
    footnote_data.update({
        "content": "",
        "articleClasses": "",
        "isPubW": False,
        "isPubNwtsty": False,
    })
    potential_json_content, status_code = get_html_content(fn["fetchUrl"])
    if status_code != 200:
        continue

    maybe_json = parse_reference_json_if_possible(potential_json_content)
    if isinstance(maybe_json, dict):
        del maybe_json["rawData"]
        fn.update(maybe_json)
        fn.update(apply_parsing_logic(maybe_json))