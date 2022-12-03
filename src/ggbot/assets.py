from typing import Dict, Any, Mapping, Iterable, TypeVar, Generic
import os
import pathlib
import aiohttp
import uuid
import time
import json
import yaml
import hashlib
import logging
import requests
from dataclasses import dataclass, field


from aiohttp.typedefs import StrOrURL


__all__ = [
    "Source",
    "FileSource",
    "UrlSource",
    "Cached",
    "TextAsset",
    "DictAsset",
    "JsonAsset",
    "YamlDictAsset",
    "IndexedCollection",
    "yaml_dict_from_file",
]


_logger = logging.getLogger(__name__)


class Source:
    def get_uri(self) -> str:
        raise NotImplementedError

    def get_as_binary(self) -> bytes:
        raise NotImplementedError

    def get_as_text(self, encoding: str = "utf-8") -> str:
        raise NotImplementedError

    async def get_as_binary_async(self) -> bytes:
        return self.get_as_binary()

    async def get_as_text_async(self, encoding: str = "utf-8") -> str:
        return self.get_as_text(encoding)


@dataclass
class FileSource(Source):
    path: pathlib.Path

    def get_uri(self) -> str:
        return str(self.path.absolute())

    def get_as_binary(self) -> bytes:
        return self.path.open("rb").read()

    def get_as_text(self, encoding: str = "utf-8") -> str:
        return self.path.open("r", encoding=encoding).read()

    def __repr__(self):
        return f"{self.__class__.__name__}({self.path})>"


@dataclass
class UrlSource(Source):
    url: StrOrURL
    method: str = "GET"
    request_kwargs: Dict[str, Any] = field(default_factory=dict)

    def get_uri(self) -> str:
        return str(self.url)

    def get_as_binary(self) -> bytes:
        response = requests.request(self.method, str(self.url), **self.request_kwargs)
        return response.content

    def get_as_text(self, encoding: str = "utf-8") -> str:
        return self.get_as_binary().decode(encoding)

    async def request(self, session: aiohttp.ClientSession):
        _logger.debug(f"Performing {self.method} to {self.url}")
        return await session.request(
            method=self.method, url=self.url, **self.request_kwargs
        )

    async def get_as_binary_async(self) -> bytes:
        async with aiohttp.ClientSession() as session:
            response = await self.request(session)
            return await response.read()

    async def get_as_text_async(self, encoding: str = "utf-8") -> str:
        async with aiohttp.ClientSession() as session:
            response = await self.request(session)
            return await response.text(encoding)

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.url}>"


def generate_id() -> str:
    return str(uuid.uuid4()[:8])


@dataclass
class Cached(Source):
    source: Source
    cache_dir: str = ".cache"
    lifetime_seconds: float = 24 * 60 * 60

    _cache_path: pathlib.Path = None

    def __post_init__(self):
        filename = hashlib.md5(self.source.get_uri().encode()).hexdigest()[:8]
        self._cache_path = pathlib.Path(self.cache_dir, f"{filename}.dat")
        os.makedirs(self.cache_dir, exist_ok=True)

    def get_uri(self) -> str:
        return str(self._cache_path.absolute())

    @property
    def valid_cache_exists(self) -> bool:
        if not self._cache_path.exists():
            return False

        modified_time = os.path.getmtime(self._cache_path.absolute())
        now = time.time()
        return now - modified_time < self.lifetime_seconds

    def invalidate_cache(self):
        if self._cache_path.exists():
            os.remove(self._cache_path.absolute())

    def get_as_binary(self) -> bytes:
        if self.valid_cache_exists:
            return self._cache_path.read_bytes()

        contents = self.source.get_as_binary()
        self._cache_path.write_bytes(contents)
        return contents

    def get_as_text(self, encoding: str = "utf-8") -> str:
        if self.valid_cache_exists:
            return self._cache_path.read_text(encoding=encoding)

        contents = self.source.get_as_text()
        self._cache_path.write_text(contents, encoding)
        return contents

    async def get_as_binary_async(self) -> bytes:
        if self.valid_cache_exists:
            return self._cache_path.read_bytes()

        contents = await self.source.get_as_binary_async()
        self._cache_path.write_bytes(contents)
        return contents

    async def get_as_text_async(self, encoding: str = "utf-8") -> str:
        if self.valid_cache_exists:
            return self._cache_path.read_text(encoding=encoding)

        contents = await self.source.get_as_text_async(encoding)
        self._cache_path.write_text(contents, encoding)
        return contents

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.source!r}>"


@dataclass
class TextAsset:
    source: Source
    encoding: str = "utf-8"

    def get_content(self) -> str:
        return self.source.get_as_text(self.encoding)


class DictAsset(Mapping[str, Any]):
    def get_data(self) -> Mapping[str, Any]:
        raise NotImplementedError

    @property
    def data(self) -> Mapping[str, Any]:
        return self.get_data()

    def values(self):
        return self.data.values()

    def items(self):
        return self.data.items()

    def keys(self):
        return self.data.keys()

    def __len__(self):
        return len(self.data)

    def __contains__(self, item):
        return len(self.data)

    def __iter__(self):
        return iter(self.data)

    def __getitem__(self, item):
        return self.data.__getitem__(item)

    def get(self, default=None):
        return self.data.get(default)

    def __str__(self):
        return str(self.data)

    def __hash__(self):
        return hash(self.data)


@dataclass
class JsonAsset:
    source: Source
    encoding: str = "utf-8"

    def get_data(self) -> Dict[str, Any]:
        return json.loads(self.source.get_as_text(self.encoding))


@dataclass
class YamlDictAsset(DictAsset):
    source: Source
    encoding: str = "utf-8"

    def get_data(self) -> Dict[str, Any]:
        return yaml.full_load(self.source.get_as_text(self.encoding))


T = TypeVar("T")


class IndexedCollection(Generic[T]):
    def iter_items(self) -> Iterable[T]:
        raise NotImplementedError

    def get_item_by_index(self, index) -> T:
        raise NotImplementedError

    def __iter__(self) -> Iterable[T]:
        return self.iter_items()

    def __getitem__(self, item) -> T:
        return self.get_item_by_index(item)

    def __len__(self):
        raise NotImplementedError


def yaml_dict_from_file(path: str) -> YamlDictAsset:
    return YamlDictAsset(FileSource(pathlib.Path(path)))
