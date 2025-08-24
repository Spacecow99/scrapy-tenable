#!/usr/bin/env python

# Stolen from https://gitlab.com/mshepherd/scrapy-extensions/-/blob/master/scrapy_extensions/loggers.py?ref_type=heads

from scrapy.logformatter import LogFormatter


class QuietLogFormatter(LogFormatter):
    """
    A custom log formatter that conditionally logs scraped items based on the
    'LOG_SCRAPED_ITEMS' setting.
    
    If 'LOG_SCRAPED_ITEMS' is set to True in the spider's settings, this formatter
    behaves like the default LogFormatter and logs scraped items. Otherwise, it
    suppresses logging for scraped items.
    
    Methods:
        scraped(item, response, spider):
            Returns the default log message for scraped items if logging is 
            enabled; otherwise, returns None to suppress the log entry.
    """
    def scraped(self, item, response, spider):
        return (
            super().scraped(item, response, spider)
            if spider.settings.getbool("LOG_SCRAPED_ITEMS")
            else None
        )
