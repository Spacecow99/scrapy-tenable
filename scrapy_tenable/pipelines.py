# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
from pymongo import MongoClient, errors

class ScrapyTenablePipeline:
    def process_item(self, item, spider):
        return item

class MongoDBPipeline:
    def __init__(self, mongo_uri, mongo_db, mongo_collection):
        self.mongo_uri = mongo_uri
        self.mongo_db = mongo_db
        self.mongo_collection = mongo_collection

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            mongo_uri=crawler.settings.get('MONGO_URI', 'mongodb://172.24.80.1:27017'),
            mongo_db=crawler.settings.get('MONGO_DATABASE', 'tenable'),
            mongo_collection=crawler.settings.get('MONGO_COLLECTION', 'plugins')
        )

    def open_spider(self, spider):
        self.client = MongoClient(self.mongo_uri)
        self.db = self.client[self.mongo_db]
        self.collection = self.db[self.mongo_collection]

    def close_spider(self, spider):
        self.client.close()

    def process_item(self, item, spider):
        data = dict(item)
        try:
            # Use 'script_id' as the unique key for upsert
            self.collection.update_one(
                {'script_id': data.get('script_id')},
                {'$set': data},
                upsert=True
            )
        except errors.PyMongoError as e:
            spider.logger.error(f"Error processing item {data.get('script_id')}: {e}")
        return item