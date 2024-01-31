from typing import Optional, Mapping, Any
import json
import os
import aiohttp
import hashlib
import time
import logging
from contextlib import contextmanager

import yaml


__all__ = [
    "get_url_json_with_file_cache",
    "benchmark",
    "load_yamls",
    "local_time_cache",
    "get_item_from_dict",
    "require_item_from_dict_or_env",
]

_logger = logging.getLogger(__name__)


async def get_url_json_with_file_cache(
    url: str,
    method: str = "GET",
    cached_file_path: Optional[str] = None,
    lifetime: float = 24 * 60 * 60,
    encoding: str = "utf-8",
    session: aiohttp.ClientSession = None,
    cache_dir: str = ".cache",
    **kwargs,
):
    key = f"{method}:{url}"
    if cached_file_path is None:
        filename = hashlib.md5(key.encode()).hexdigest()[:8] + ".json"
        cached_file_path = os.path.abspath(os.path.join(cache_dir, filename))

    if os.path.exists(cached_file_path):
        mtime = os.path.getmtime(cached_file_path)
        now = time.time()

        if now - mtime < lifetime:
            _logger.debug(f"Loading data from cache ({cached_file_path}) for url={url}")
            with open(cached_file_path, "r", encoding=encoding) as fp:
                return json.load(fp)

    if session is None:
        session = aiohttp.ClientSession()
    async with session as session:
        _logger.debug(f"Requesting: {url}")
        resp = await session.get(url, **kwargs)
        if resp.status != 200:
            raise ValueError(f"Failed to get data from url: {url}")
        data = await resp.read()
        _logger.debug(f"Saving response data to cache ({cached_file_path})")
        os.makedirs(cache_dir, exist_ok=True)
        with open(cached_file_path, "wb") as fp:
            fp.write(data)
        print(data)
        return json.loads(data)


@contextmanager
def benchmark(name: str):
    started = time.time()
    yield
    delta = time.time() - started
    if delta > 0:
        print(f"{name}: {delta:.3f} seconds ({1 / delta:.1f} calls per second)")
    else:
        print(f"{name}: {delta:.3f} seconds")


def load_yamls(*paths: str) -> dict:
    result = {}
    for p in paths:
        with open(p, "r", encoding="utf-8") as fp:
            for doc in yaml.full_load_all(fp):
                result.update(doc)
    return result


def local_time_cache(seconds: float):
    def _decorator(fn):
        # Variable per decorator usage
        last_accessed = 0
        cache = None

        def _inner(*args, **kwargs):
            nonlocal last_accessed
            nonlocal cache

            time_since_last_access = time.time() - last_accessed

            # Cache miss
            if time_since_last_access > seconds:
                cache = fn(*args, **kwargs)
                last_accessed = time.time()

            # Cache hit
            return cache

        return _inner

    return _decorator


def get_item_from_dict(data: Mapping[str, Any], path: str):
    obj = data
    for key in path.split("."):
        obj = obj.get(key)
        if obj is None:
            return None
    return obj


def require_item_from_dict_or_env(
    data: Mapping[str, Any], path: str, env_var: Optional[str] = None
):
    if not env_var:
        env_var = path.replace(".", "_").upper()

    obj = os.environ.get(env_var)

    if obj is None:
        obj = get_item_from_dict(data, path)

    if obj is None:
        raise KeyError(f"Missing value for key {path} or env variable {env_var}")

    return obj
