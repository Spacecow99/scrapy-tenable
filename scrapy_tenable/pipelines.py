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
    """
    Pipeline for storing Scrapy items in a MongoDB collection.

    Attributes:
        mongo_uri (str): MongoDB connection URI.
        mongo_db (str): Name of the MongoDB database.
        mongo_collection (str): Name of the MongoDB collection.

    Methods:
        from_crawler(crawler): Class method to create pipeline instance from Scrapy crawler settings.
        open_spider(spider): Initializes MongoDB client and collection when the spider opens.
        close_spider(spider): Closes the MongoDB client when the spider closes.
        process_item(item, spider): Upserts the item into the MongoDB collection using 'script_id' as the unique key.
    """
    def __init__(self, mongo_uri, mongo_db, mongo_collection):
        self.mongo_uri = mongo_uri
        self.mongo_db = mongo_db
        self.mongo_collection = mongo_collection

    @classmethod
    def from_crawler(cls, crawler):
        """
        Instantiates the pipeline using settings from the Scrapy crawler.

        Args:
            crawler (scrapy.crawler.Crawler): The Scrapy crawler instance containing project settings.

        Returns:
            An instance of the pipeline class initialized with MongoDB connection parameters:
                - mongo_uri: URI for MongoDB connection (default: 'mongodb://localhost:27017').
                - mongo_db: Name of the MongoDB database (default: 'tenable').
                - mongo_collection: Name of the MongoDB collection (default: 'plugins').
        """
        return cls(
            mongo_uri=crawler.settings.get('MONGO_URI', 'mongodb://localhost:27017'),
            mongo_db=crawler.settings.get('MONGO_DATABASE', 'tenable'),
            mongo_collection=crawler.settings.get('MONGO_COLLECTION', 'plugins')
        )

    def open_spider(self, spider):
        """
        Initializes the MongoDB client, database, and collection when the spider is opened.

        Args:
            spider (scrapy.Spider): The spider instance that is being opened.

        Side Effects:
            Sets up the MongoDB client connection and assigns the database and collection
            to instance variables for later use in the pipeline.
        """
        self.client = MongoClient(self.mongo_uri)
        self.db = self.client[self.mongo_db]
        self.collection = self.db[self.mongo_collection]

    def close_spider(self, spider):
        """
        Called when the spider is closed.

        This method closes the database or network client connection to ensure
        that all resources are properly released after the spider finishes crawling.

        Args:
            spider (scrapy.Spider): The spider instance that was closed.
        """
        self.client.close()

    def process_item(self, item, spider):
        """
        Processes a Scrapy item by upserting it into the MongoDB collection using 'script_id' as the unique key.

        Args:
            item (dict or Item): The scraped item to process.
            spider (Spider): The spider instance that scraped the item.

        Returns:
            dict or Item: The processed item.

        Logs:
            An error message if a PyMongoError occurs during the database operation.
        """
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