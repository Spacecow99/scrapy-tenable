#!/usr/bin/env python

# Stolen from https://gitlab.com/mshepherd/scrapy-extensions/-/blob/master/scrapy_extensions/loggers.py?ref_type=heads

from scrapy.logformatter import LogFormatter


class QuietLogFormatter(LogFormatter):
    """Be quieter about scraped items."""

    def scraped(self, item, response, spider):
        return (
            super().scraped(item, response, spider)
            if spider.settings.getbool("LOG_SCRAPED_ITEMS")
            else None
        )
