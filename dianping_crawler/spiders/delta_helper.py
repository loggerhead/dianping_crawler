# -*- coding: utf-8 -*-

# Define here the models for your spider middleware
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/spider-middleware.html
import bson
import scrapy
import pymongo
import logging


class DeltaHelper(object):
    item = {
        "_id": "GET https://example.com",
        "finished": True,
        # request fields
        "url": "https://example.com",
        "method": "GET",
        "callback": "self.func_name",
        "errback": "self.func_name",
        "meta": {},
    }
    logger = logging.getLogger(__name__)

    def __init__(self, spider):
        self.spider = spider
        # connect to mongodb
        self.mongo_uri = spider.settings.get('MONGO_URI')
        self.db_name = spider.settings.get('MONGO_DATABASE', 'delta')

    def connect_db(self):
        self.db_collection_name = '{}_delta'.format(self.spider.name)
        self.db_client = pymongo.MongoClient(self.mongo_uri)
        self.db_collection = self.db_client[self.db_name][self.db_collection_name]

    def fetch_unfinished_requests(self):
        cond = {'finished': False}
        entries = self.db_collection.find(cond)

        def gen_request(serialized):
            if serialized:
                self.logger.debug("Add %s", serialized['url'])
                return self.request_deserialize(self.spider, serialized)
            else:
                return None

        return filter(bool, map(gen_request, entries))

    def check_request(self, request):
        serialized = self.request_serialize(request)
        serialized['finished'] = False
        cond = {'_id': self.serialized_request_id(serialized)}
        result = self.db_collection.find_one(cond)

        if result:
            if result['finished']:
                self.logger.debug("Ignore %s", request.url)
                return None
            else:
                return request
        else:
            try:
                self.db_collection.insert_one(serialized)
                return request
            except Exception as e:
                raise e
                self.logger.error('%s', serialized)

    def check_requests(self, requests, hurry=False):
        checked = filter(bool, map(self.check_request, requests))
        if hurry:
            return list(checked)
        else:
            return checked

    def mark_as_finished(self, request):
        if not request:
            return
        serialized = self.request_serialize(request)
        serialized['finished'] = True
        del serialized['_id']
        cond = {'_id': self.serialized_request_id(serialized)}
        value = {'$set': serialized}
        self.db_collection.update_one(cond, value)

    @classmethod
    def serialized_request_id(cls, serialized):
        return '{} {}'.format(serialized['method'], serialized['url'])

    # modify obj
    @classmethod
    def object_serialize(cls, obj):
        if isinstance(obj, scrapy.http.Request):
            obj = cls.request_serialize(obj)
        if isinstance(obj, scrapy.http.Headers):
            obj = dict(obj)

        if isinstance(obj, dict):
            for k in obj.keys():
                v = cls.object_serialize(obj.pop(k))
                if isinstance(k, bytes):
                    k = str(k, 'utf-8')
                obj[k] = v
        elif isinstance(obj, list):
            for i in range(len(obj)):
                obj[i] = cls.object_serialize(obj[i])
        elif isinstance(obj, bytes):
            return bson.Binary(obj)

        return obj

    @classmethod
    def request_serialize(cls, request):
        serialized = {}

        for k, v in request.__dict__.items():
            if k.startswith('_'):
                k = k.lstrip('_')
            if callable(v):
                v = v.__name__
            serialized[k] = v

        serialized['_id'] = cls.serialized_request_id(serialized)
        serialized['headers'] = cls.object_serialize(serialized['headers'])

        return serialized

    @classmethod
    def request_deserialize(cls, spider, serialized):
        serialized = dict(serialized)

        def safe_set_value(key):
            if serialized.get(key) is not None:
                serialized[key] = spider.__getattribute__(serialized[key])

        def safe_del_key(key):
            if serialized.get(key) is not None:
                del serialized[key]

        safe_set_value('callback')
        safe_set_value('errback')
        safe_del_key('_id')
        safe_del_key('finished')

        return scrapy.Request(**serialized)
