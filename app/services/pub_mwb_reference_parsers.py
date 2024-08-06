from abc import ABC, abstractmethod
from bs4 import BeautifulSoup, Tag


# Strategy Interface
class ContentParserStrategy(ABC):
    @abstractmethod
    def parse(self, content: str) -> str:
        pass


# Concrete Strategy for PubW
class PubWParserStrategy(ContentParserStrategy):
    def parse(self, content: str):
        soup = BeautifulSoup(content, 'html5lib')
        return '\n'.join([p.text.strip() for p in soup.select('p.sb')])


def extract_nwtsty_text_stripping_notes(soup: BeautifulSoup | Tag) -> str:
    anchors = soup.select('a.fn, a.b')
    if anchors:
        for anchor in anchors:
            anchor.decompose()
    return soup.get_text(" ", strip=True)


# Concrete Strategy for PubNwtsty
class PubNwtstyParserStrategy(ContentParserStrategy):
    def parse(self, content: str):
        soup = BeautifulSoup(content, 'html5lib')
        return extract_nwtsty_text_stripping_notes(soup)


# Default Strategy
class DefaultParserStrategy(ContentParserStrategy):
    def parse(self, content: str):
        soup = BeautifulSoup(content, 'html5lib')
        return soup.get_text()


# Context Class
class ContentParser:
    def __init__(self, strategy: ContentParserStrategy):
        self._strategy = strategy

    def set_strategy(self, strategy: ContentParserStrategy):
        self._strategy = strategy

    def parse_content(self, content: str):
        return self._strategy.parse(content)
