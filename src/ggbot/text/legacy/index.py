from typing import Any, Optional, Iterable
from dataclasses import dataclass
import re

import Stemmer

__all__ = ["Entry", "Index"]


@dataclass
class Entry:
    __slots__ = "original", "document"

    original: str
    document: Any

    def __hash__(self):
        return hash(self.original)


_TOKEN_RE = re.compile(r"[\w\d]+")


def tokenize(text: str) -> Iterable[str]:
    matches = _TOKEN_RE.findall(text)
    for m in matches:
        yield m


def bigram_iter(collection: Iterable[str]):
    it = iter(collection)
    first = next(it)
    while True:
        try:
            yield first + next(it)
        except StopIteration:
            break


DEFAULT_ENGLISH_STOPWORDS = {
    "a",
    "in",
    "the",
    "be",
    "that",
    "i",
    "have",
    "in",
    "of",
    "to",
}


class Index:
    def __init__(
        self,
        stemmer: Stemmer.Stemmer = Stemmer.Stemmer("russian"),
        stopwords: Optional[set[str]] = None,
    ):
        self.stemmer = stemmer
        self.storage: dict[str, set[Entry]] = {}
        self.stopwords = (
            stopwords if stopwords is not None else DEFAULT_ENGLISH_STOPWORDS
        )

    def _iter_doc_keys(self, text: str, include_single_tokens: bool):
        if not text:
            return

        text = text.strip()
        yield text

        lowered = text.lower()
        yield lowered

        tokens = [t for t in tokenize(lowered) if t not in self.stopwords]
        tokens = self.stemmer.stemWords(tokens)

        if include_single_tokens:
            yield from tokens
        if len(tokens) > 1:
            yield from bigram_iter(tokens)

    def _add_to_storage(self, key: str, entry: Entry):
        if key in self.storage:
            self.storage[key].add(entry)
        else:
            self.storage[key] = {entry}

    def add(self, text: str, document: Any):
        entry = Entry(text, document)
        for key in self._iter_doc_keys(text, include_single_tokens=True):
            self._add_to_storage(key, entry)

    def search(self, text: str) -> Optional[Any]:
        if not text:
            return None

        hs = set()  # hypothesis
        for key in self._iter_doc_keys(text, include_single_tokens=False):
            if key in self.storage:
                print(key)
                hs.update(self.storage[key])

        for h in hs:
            print(h)

        return None
