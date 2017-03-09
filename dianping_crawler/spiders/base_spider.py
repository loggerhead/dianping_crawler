# -*- coding: utf-8 -*-
import scrapy
import logging
import pymongo
from datetime import datetime
try:
    from urlparse import urljoin
except ImportError:
    from urllib.parse import urljoin
from .delta_helper import DeltaHelper


class BaseSpider(scrapy.Spider):
    # need overwrite in subclass
    logger = logging.getLogger(__name__)

    def init(self):
        self.delta = DeltaHelper(self)
        self.delta.connect_db()
        self.db_name = self.settings.get('MONGO_DATABASE', 'dianping')
        self.db = self.delta.db_client[self.db_name]
        self.db_collection = self.db[self.name]
        self.unfinished_requests = self.delta.fetch_unfinished_requests()

    def extract_int(self, text):
        i = -1
        for i in range(len(text)):
            if text[i].isdigit():
                break
        j = len(text) if i >= 0 else -1
        for j in range(i + 1, len(text)):
            if not text[j].isdigit():
                break
        try:
            return int(text[i:j])
        except ValueError:
            self.logger.warning('cannot extract integer from "%s"', text)
            return None

    def aa2urls(self, aa):
        urls = []
        for a in aa:
            urls.append(a.attrib['href'])
        return urls

    def add_host(self, s):
        return urljoin(self.settings['HOST'], s)

    # return index of the first exists class
    def find_classes_exists(self, d, classes):
        for i in range(len(classes)):
            if d(classes[i]):
                return i
        return None

    def text2date(self, date):
        if date.count('-') == 1:
            date = '{}-{}'.format(datetime.now().year % 100, date)
        try:
            date = datetime.strptime(date, '%y-%m-%d')
        except ValueError:
            self.logger.warning('not a valid date: "%s"', date)
            date = None
        return date

    def save_item_to_db(self, item):
        try:
            self.db_collection.insert_one(item)
        except pymongo.errors.DuplicateKeyError as e:
            self.logger.warn(e)
        except Exception as e:
            raise e

    def extend_item_field_in_db(self, shop_id, field_name, values):
        try:
            cond = {'_id': shop_id}
            update = {'$push': {field_name: {'$each': values}}}
            self.db_collection.update_one(cond, update)
        except Exception as e:
            raise e
