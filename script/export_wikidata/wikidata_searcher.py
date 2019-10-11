#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
用于联网获取wikidata和wikipedia的数据，需要翻墙
"""


import asyncio
import pickle
import time
import traceback
from pathlib import Path
import os
import aiohttp
import async_timeout

from sekg.util.annotation import catch_exception
from sekg.wiki.WikiDataItem import WikiDataItem

# if sys.platform == 'win32':
#     loop = asyncio.ProactorEventLoop()
#     asyncio.set_event_loop(loop)

# import wikipedia
from definitions import WIKI_DIR


class AsyncWikiSearcher:
    API_URL = 'https://www.wikidata.org/w/api.php'
    WIKI_PEDIA_URL = 'https://en.wikipedia.org/w/api.php'

    def __init__(self, proxy_server=None, pool_size=10, stride=60):
        self.proxy_server = proxy_server
        self.semaphore = asyncio.Semaphore(pool_size)
        self.title_cache = {}
        self.item_cache = {}
        self.wikipedia_cache = {}
        self.stride = stride

    async def __fetch_titles(self, query, limit=5):
        if query in self.title_cache:
            return self.title_cache[query]
        params = {
            'action': 'query',
            'format': 'json',
            'list': 'search',
            'srprop': 'snippet',
            'srlimit': limit,
            'srsearch': query
        }
        try:
            async with self.semaphore:
                async with aiohttp.ClientSession() as session:
                    with async_timeout.timeout(10):
                        async with session.get(self.API_URL, params=params, proxy=self.proxy_server) as response:
                            json_data = await response.json()
                            result = [
                                {"pageid": item["pageid"], "title": item["title"], "snippet": item.get("snippet", "")}
                                for item in json_data["query"]["search"]]
                            if result:
                                self.title_cache[query] = result
                            else:
                                print(query, ", no search result")
                            return result
        except Exception:
            print("[Failed] query: {}".format(query))
            self.write_one_line_txt("search_error.txt", query)
            traceback.print_exc()
            return []

    async def __fetch_entity(self, title):
        if title in self.item_cache:
            return self.item_cache[title]
        params = {
            'ids': title,
            'format': 'json',
            'action': 'wbgetentities'
        }
        try:
            async with self.semaphore:
                async with aiohttp.ClientSession() as session:
                    with async_timeout.timeout(10):
                        async with session.get(self.API_URL, params=params, proxy=self.proxy_server) as response:
                            json_data = await response.json()
                            self.item_cache[title] = WikiDataItem(title,
                                                                  init_at_once=False).init_wikidata_item_from_json(
                                json_data)
                            print("[Done] title: {}".format(title))
                            return json_data
        except Exception:
            print("[Failed] title: {}".format(title))
            self.write_one_line_txt("fetch_entity_error.txt", title)
            traceback.print_exc()
            return {}

    async def __fetch_wikipedia(self, id, title):
        if id in self.wikipedia_cache:
            return self.wikipedia_cache[id]
        params = {
            'titles': title,
            'format': 'json',
            'action': 'query',
            'prop': 'extracts',
            'exintro': '',
            'explaintext': '',
            'redirects': 1
        }
        try:
            async with self.semaphore:
                async with aiohttp.ClientSession() as session:
                    with async_timeout.timeout(10):
                        async with session.get(self.WIKI_PEDIA_URL, params=params, proxy=self.proxy_server) as response:
                            json_data = await response.json()
                            result = [
                                {"pageid": item["pageid"], "title": item["title"], "context": item.get("extract", ""),
                                }
                                for index, item in json_data["query"]["pages"].items()]
                            if result:
                                self.wikipedia_cache[id] = result
                            else:
                                print(title, ", no wikipedia context")
                            print("[Done] title: {}".format(title))
                            return json_data
        except Exception:
            print("[Failed] title: {}".format(title))
            self.write_one_line_txt("fetch_wikipedia_error.txt", title)
            traceback.print_exc()
            return {}

    def save(self, title_save_path=None, item_save_path=None, wikipedia_save_path=None):
        print("Save...")
        if title_save_path is not None:
            with Path(title_save_path).open("wb") as f:
                pickle.dump(self.title_cache, f)
        if item_save_path is not None:
            with Path(item_save_path).open("wb") as f:
                pickle.dump(self.item_cache, f)
        if wikipedia_save_path is not None:
            with Path(wikipedia_save_path).open("wb") as f:
                pickle.dump(self.wikipedia_cache, f)

    def clear(self):
        del self.wikipedia_cache
        del self.item_cache
        del self.title_cache

        self.item_cache = {}
        self.title_cache = {}
        self.wikipedia_cache = {}

    def search_title(self, queries):
        loop = asyncio.get_event_loop()
        tasks = [self.__fetch_titles(q) for q in queries]
        loop.run_until_complete(asyncio.gather(*tasks))
        return self.title_cache

    def fetch_item(self, ids):
        loop = asyncio.get_event_loop()
        tasks = [self.__fetch_entity(_id) for _id in ids]
        loop.run_until_complete(asyncio.gather(*tasks))
        # for k, v in self.item_cache:
        #     self.item_cache[k] = WikiDataItem(k, init_at_once=False).init_wikidata_item_from_json(v)
        return self.item_cache

    def fetch_wikipedia_context(self, titles):
        loop = asyncio.get_event_loop()
        tasks = [self.__fetch_wikipedia(_id, _title) for _id, _title in titles]
        loop.run_until_complete(asyncio.gather(*tasks))
        # for k, v in self.item_cache:
        #     self.item_cache[k] = WikiDataItem(k, init_at_once=False).init_wikidata_item_from_json(v)
        return self.item_cache

    @catch_exception
    def init_from_cache(self, title_save_path=None, item_save_path=None, wikipedia_save_path=None):
        print("Init from cache...")
        if title_save_path is not None and Path(title_save_path).exists():
            with Path(title_save_path).open("rb") as f:
                title_cache = pickle.load(f)
                self.title_cache = dict(self.title_cache, **title_cache)
        if item_save_path is not None and Path(item_save_path).exists():
            with Path(item_save_path).open("rb") as f:
                item_cache = pickle.load(f)
                self.item_cache = dict(self.item_cache, **item_cache)
        if wikipedia_save_path is not None and Path(wikipedia_save_path).exists():
            with Path(wikipedia_save_path).open("rb") as f:
                wikipedia_cache = pickle.load(f)
                self.wikipedia_cache = dict(self.wikipedia_cache, **wikipedia_cache)

    def write_one_line_txt(self, path, line):
        if not os.path.exists(path):
            with open(path, "w", encoding='utf8') as f:
                print(f)
        try:
            with open(path, "a", encoding='utf8') as f:
                f.write(line + "\n")
        except Exception as e:
            print("exception:" + str(e))

    def item_cache_size(self):
        return len(self.item_cache)

    def title_cache_size(self):
        return len(self.title_cache)

    def wikipedia_cache_size(self):
        return len(self.wikipedia_cache)

    def get_item_cache(self):
        return self.item_cache

    def get_title_cache(self):
        return self.title_cache

    def get_wikipedia_cache(self):
        return self.wikipedia_cache

    def __repr__(self):
        return "<AsyncWikiSearcher title=%r item=%r wikipedia=%r>" % (
            self.title_cache_size(), self.item_cache_size(), self.wikipedia_cache_size())


if __name__ == '__main__':
    searcher = AsyncWikiSearcher(proxy_server="http://127.0.0.1:1080")
    wiki_dir = Path(WIKI_DIR)
    path_classification = str(wiki_dir / "WikidataClassification.pc")
    title_save_path = str(wiki_dir / "titles.bin")
    item_save_path = str(wiki_dir / "items.bin")
    wikipedia_save_path = str(wiki_dir / "wikipedia_context.bin")
    with Path(path_classification).open("rb") as f:
        data = pickle.load(f)
    terms = [item["url"].split("/")[-1] for item in data]
    ids = [item["wd_item_id"] for item in data]
    wiki = [(item["wd_item_id"], item["url"].split("/")[-1]) for item in data]
    # searcher.search_title(terms)
    # searcher.save(title_save_path=title_save_path)
    # searcher.fetch_item(ids)
    # searcher.save(item_save_path=item_save_path)
    searcher.fetch_wikipedia_context(wiki)
    searcher.save(wikipedia_save_path=wikipedia_save_path)
