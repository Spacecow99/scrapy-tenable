#!/usr/bin/env python3.9

"""
"""

import json
import urllib.parse
import gzip
from datetime import datetime, date, timedelta
from string import Template
from typing import Iterable

import requests
import xmltodict
import scrapy


NESSUS_FEED = "https://plugins.nessus.org/plugins_rba.xml.gz"
TENABLE_PLUGIN = Template("https://www.tenable.com/plugins/api/v1/nessus/${PLUGIN}")


class FullTenableSpider(scrapy.Spider):
    """
    scrapy crawl full_tenable_spider
    """
    name = "full_tenable_spider"
    plugin_ids = []

    def start_requests(self):
        # TODO: Make this in-memory then release
        feed_path = f"plugin_rba_{datetime.now().strftime('%d%M%y_%h%m%s')}.xml.gz"
        with requests.get(NESSUS_FEED, stream=True) as r:
            with open(feed_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=10*1024):
                    f.write(chunk)

        self.logger.info("Parsing plugin details XML file")
        xmltodict.parse(gzip.GzipFile(feed_path), item_depth=2, item_callback=self._extract_script_id)
        self.logger.info(f"Plugins XML parsing complete, {len(self.plugin_ids)} plugins found")
        for plugin_id in self.plugin_ids:
            # TODO: We should add support for a since_last_run parameter for limiting pulled information
            yield scrapy.Request(TENABLE_PLUGIN.substitute(PLUGIN=plugin_id), callback=self.parse_plugin)

    def _extract_script_id(self, _, nasl):
        """
        Takes a NASL xml block and extracts the script_id value to append to self.plugin_ids.
        """
        # If not dict then skip (should never occur)
        if type(nasl) is not dict:
            return True
        
        script_id = int(nasl["script_id"])
        # Skip plugins from the Tenable.OT platform (plugins >= 500k) as they all 404
        if (10001 <= script_id < 98000) or (99000 <= script_id < 112290) or (117291 <= script_id < 500000):
            self.plugin_ids.append(nasl["script_id"])
        return True

    def parse_plugin(self, response):
        """
        """
        j = json.loads(response.text)
        data = j["data"]["_source"]
        yield data


class SinceTenableSpider(scrapy.Spider):
    """
    scrapy crawl since_tenable_spider -a since_date=YYYY-MM-DD
    """
    name = "since_tenable_spider"

    def __init__(self, since_date: str, *args, **kwargs):
        """
        Initialize the spider with a since_date parameter.

        :param since_date: The date from which to start scraping, in YYYY-MM-DD format.
        """
        super(SinceTenableSpider, self).__init__(*args, **kwargs)
        # Start at the day following since_date
        self.start_date: date = date.fromisoformat(since_date) + timedelta(days=1)
        if self.start_date >= date.today():
            raise ValueError("since_date must be less than today")
        
        self.dates: list[date] = [
            self.start_date + timedelta(days=day)
            for day in range((date.today() - self.start_date).days + 1)
        ]

    def start_requests(self):
        """
        Queue up an initial page count scrape for each day since defined since_date
        """
        tenable_search = "https://www.tenable.com/plugins/api/v1/search?q=plugin_modification_date:({0})"
        for day in self.dates:
            yield scrapy.Request(
                tenable_search.format(day.strftime("%Y-%m-%d")),
                callback=self.scrape_all_pages
            )

    def scrape_all_pages(self, response):
        """
        Determine how many pages of results there are and queue them up for scraping
        """
        j = json.loads(response.text)
        total_results = int(j.get("data", {}).get("total"))
        pages = total_results // 50 + 1
        # We already have the first page so let's not waste it and have to force duplicate calls
        self.scape_page(response)
        for page in range(2, pages + 1):
            yield scrapy.Request(
                response.url + f"&page={page}",
                callback=self.scape_page
            )

    def scape_page(self, response):
        """
        Scrape the script_id value of all results from a given page
        """
        j = json.loads(response.text)
        for result in j.get("data", {}).get("hits", []):
            script_id = int(result.get("_source", {}).get("script_id"))
            if (10001 <= script_id < 98000) or (99000 <= script_id < 112290) or (117291 <= script_id < 500000):
                yield scrapy.Request(
                    f"https://www.tenable.com/plugins/api/v1/nessus/{script_id}",
                    callback=self.parse_plugin
                )

    def parse_plugin(self, response):
        """
        Extract the body of the plugin JSON output and send it to pipeline
        """
        j = json.loads(response.text)
        data = j["data"]["_source"]
        yield data

