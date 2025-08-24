# scrapy-tenable

Scrapy spiders for interacting with Tenable public APIs and storing plugin data in MongoDB.

## Overview

This project provides Scrapy spiders to collect vulnerability plugin data from Tenable's public APIs. Scraped data is automatically stored in a MongoDB collection for further analysis or integration.

## Features

- **Full Plugin Scrape:** Download and parse the entire Nessus plugin feed.
- **Incremental Scrape:** Scrape plugins modified since a given date.
- **MongoDB Integration:** Scraped items are upserted into a MongoDB collection using `script_id` as the unique key.
- **Configurable Settings:** Easily adjust MongoDB connection details and Scrapy behavior via `settings.py`.

## Requirements

- Python 3.9+
- Scrapy
- pymongo
- requests
- xmltodict

Install dependencies:
```bash
pip install scrapy pymongo requests xmltodict
```

## Usage

### Full Plugin Scrape

Scrapes all plugins from the Nessus feed.

```bash
scrapy crawl full_tenable_spider
```

### Incremental Plugin Scrape

Scrapes plugins modified since a specific date.

```bash
scrapy crawl since_tenable_spider -a since_date=YYYY-MM-DD
```

Replace `YYYY-MM-DD` with the desired start date.

## MongoDB Configuration

By default, the pipeline connects to MongoDB at `mongodb://localhost:27017`, database `tenable`, collection `plugins`.  
You can override these settings in `scrapy_tenable/settings.py`:

```python
MONGO_URI = 'mongodb://localhost:27017'
MONGO_DATABASE = 'tenable'
MONGO_COLLECTION = 'plugins'
```

## Output

Each plugin is upserted into MongoDB using its `script_id` as the unique key. If a plugin already exists, its data is updated.

## Logging

Scrapy logs are written to a timestamped log file in the project directory.

## Author

``scrapy-tenable`` was written by ``Jacques Pharand`` <cow@space.eu>.