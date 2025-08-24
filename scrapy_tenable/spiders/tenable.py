#!/usr/bin/env python3.9

import json
import urllib.parse
import gzip
from datetime import datetime, date, timedelta
from io import BytesIO
from string import Template
from typing import Iterable

import requests
import xmltodict
import scrapy


NESSUS_FEED = "https://plugins.nessus.org/plugins_rba.xml.gz"
TENABLE_PLUGIN = Template("https://www.tenable.com/plugins/api/v1/nessus/${PLUGIN}")


class FullTenableSpider(scrapy.Spider):
    """
    FullTenableSpider is a Scrapy spider designed to crawl and extract detailed information about Nessus plugins from the Tenable plugin feed.
    This spider performs the following tasks:
    - Downloads the Nessus plugin feed as a gzipped XML file via a streamed HTTP request.
    - Parses the XML file to extract plugin IDs that fall within specific ranges, excluding plugins from the Tenable.OT platform.
    - For each valid plugin ID, issues a Scrapy request to retrieve detailed plugin information from the Tenable API.
    - Parses the plugin details from the API response and yields the relevant data.
    Attributes:
        name (str): The name of the spider used for invocation.
        plugin_ids (list): A list to store discovered plugin IDs.
    Methods:
        start_requests():
            Initiates the crawling process by downloading and parsing the plugin feed, then yields requests for each plugin ID.
        _extract_script_id(_, nasl):
            Callback for XML parsing that extracts and filters plugin IDs based on defined ranges.
        parse_plugin(response):
            Parses the API response for a plugin and yields the extracted data.
    Usage:
        scrapy crawl full_tenable_spider
    """
    name = "full_tenable_spider"
    plugin_ids = []

    def start_requests(self):
        """
        Initiates the Scrapy spider by downloading the Nessus plugin feed, parsing the XML file for plugin details,
        and yielding requests for each discovered plugin ID.
        Downloads the Nessus plugin feed as a streamed HTTP request, writes the content to a BytesIO object,
        and parses the gzipped XML file to extract plugin IDs using a custom callback. For each plugin ID found,
        yields a Scrapy request to fetch detailed plugin information.
        Yields:
            scrapy.Request: A request for each plugin ID to retrieve its details.
        Logs:
            - Start and completion of XML parsing.
            - Number of plugins found after parsing.
        """
        with requests.get(NESSUS_FEED, stream=True) as r:
            file_obj = BytesIO()
            for chunk in r.iter_content(chunk_size=10*1024):
                file_obj.write(chunk)
            file_obj.seek(0)

        self.logger.info("Parsing plugin details XML file")
        xmltodict.parse(gzip.GzipFile(fileobj=file_obj), item_depth=2, item_callback=self._extract_script_id)
        file_obj.close()
        self.logger.info(f"Plugins XML parsing complete, {len(self.plugin_ids)} plugins found")
        
        for plugin_id in self.plugin_ids:
            # TODO: We should add support for a since_last_run parameter for limiting pulled information
            yield scrapy.Request(TENABLE_PLUGIN.substitute(PLUGIN=plugin_id), callback=self.parse_plugin)

    def _extract_script_id(self, _, nasl):
        """
        Extracts the script_id from a NASL XML block and appends it to self.plugin_ids if it falls within specific ranges.
        Args:
            _ (Any): Unused parameter.
            nasl (dict): A dictionary representing a NASL XML block.
        Returns:
            bool: Always returns True.
        Notes:
            - Only script_ids within the following ranges are appended:
                * 10001 <= script_id < 98000
                * 99000 <= script_id < 112290
                * 117291 <= script_id < 500000
            - Plugins from the Tenable.OT platform (script_id >= 500000) are skipped as they all return 404.
            - If nasl is not a dict, the function returns True without processing.
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
        Parses the plugin response from a Tenable API endpoint.

        Args:
            response (scrapy.http.Response): The HTTP response object containing the plugin data in JSON format.

        Yields:
            dict: The '_source' field from the 'data' section of the parsed JSON response.
        """
        j = json.loads(response.text)
        data = j["data"]["_source"]
        yield data


class SinceTenableSpider(scrapy.Spider):
    """
    SinceTenableSpider is a Scrapy spider designed to scrape Tenable plugin data modified since a specified date.

    Attributes:
        name (str): The name of the spider.
        start_date (date): The date from which to start scraping (exclusive of since_date).
        dates (list[date]): List of dates from start_date up to today.
    Methods:
        __init__(since_date: str, *args, **kwargs):
            Initializes the spider with a since_date parameter, validates it, and prepares the date range for scraping.
        start_requests():
            Generates initial requests for each date in the range, targeting Tenable's plugin search API.
        scrape_all_pages(response):
            Determines the total number of result pages for a given date and queues requests for each page.
        scape_page(response):
            Scrapes the script_id values from a page of results and queues requests for individual plugin details if they meet certain criteria.
        parse_plugin(response):
            Extracts plugin details from the API response and yields the data for further processing in the pipeline.
    Usage:
        scrapy crawl since_tenable_spider -a since_date=YYYY-MM-DD
    """
    name = "since_tenable_spider"

    def __init__(self, since_date: str, *args, **kwargs):
        """
        Initializes the SinceTenableSpider with a starting date.
        Args:
            since_date (str): The ISO format date string (YYYY-MM-DD) indicating the starting point (exclusive).
            *args: Additional positional arguments for the parent class.
            **kwargs: Additional keyword arguments for the parent class.
        Raises:
            ValueError: If since_date is today or in the future.
        Attributes:
            start_date (date): The date object representing the day after since_date.
            dates (list[date]): List of date objects from start_date up to and including today.
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
        Generates initial Scrapy requests for each date in self.dates to scrape plugin modification data from Tenable.

        For each day in the date range, constructs a search URL and yields a Scrapy Request to initiate scraping.
        The response for each request is handled by the scrape_all_pages callback.

        Yields:
            scrapy.Request: A request object for each date to fetch plugin modification data.
        """
        tenable_search = "https://www.tenable.com/plugins/api/v1/search?q=plugin_modification_date:({0})"
        for day in self.dates:
            yield scrapy.Request(
                tenable_search.format(day.strftime("%Y-%m-%d")),
                callback=self.scrape_all_pages
            )

    def scrape_all_pages(self, response):
        """
        Parses the initial response and initiates scraping of all paginated results.

        This method:
        - Loads the JSON data from the response.
        - Determines the total number of results and calculates the number of pages.
        - Processes the first page using `scape_page`.
        - Yields Scrapy requests for subsequent pages, invoking `scape_page` as the callback.

        Args:
            response (scrapy.http.Response): The response object containing the initial page data.

        Yields:
            scrapy.Request: Requests for each additional page to be scraped.
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
        Parses the response from a page, extracts plugin script IDs from the JSON data,
        and yields Scrapy requests for plugin details if the script ID falls within specified ranges.

        Args:
            response (scrapy.http.Response): The response object containing the page data.

        Yields:
            scrapy.Request: A request to fetch plugin details for each valid script ID.
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
        Parses the plugin response and yields the plugin data.

        Args:
            response (scrapy.http.Response): The HTTP response object containing the plugin data in JSON format.

        Yields:
            dict: The '_source' field from the 'data' object in the parsed JSON response.
        """
        j = json.loads(response.text)
        data = j["data"]["_source"]
        yield data

