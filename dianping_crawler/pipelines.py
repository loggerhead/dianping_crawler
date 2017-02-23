# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html
import pymongo


class DianpingCrawlerPipeline(object):
    # http://www.dianping.com/shop/38230595
    item = {
        '_id': 38230595,
        'name': '靓码头重庆火锅',
        'address': '后沙峪中粮祥云小镇安泰大街9号院19号楼104',
        'telephones': [
            '010-80470966',
            '13810211746',
        ],
        # 人均
        'average_price': 91,
        # 红色方块
        'average_score': 4,
        # 满分 10
        'score': {
            'taste': 8.3,
            'environment': 8.5,
            'service': 8.1,
        },
        # 推荐
        'recommendation': {
            # 菜
            'cuisines': [
                ('苏尼特草原羔羊肉', 16),
                ('农家小酥肉，重庆贡菜', 13),
            ],
            # 页面右侧的「你可能会喜欢」
            'asides': [
                59127154,
                24870072,
            ]
        },
        'tags': [
            ('回头客_1', 3),
            ('干净卫生_1', 8),
        ],
        'reviews': [
            {
                # review id
                '_id': 333523022,
                'user_id': 11149581,
                'average_score': 4,
                'date': '2016-01-02',
                # 满分 5
                'score': {
                    'taste': 3,
                    'environment': 3,
                    'service': 3,
                },
                'description': '骨灰级的火锅热爱者...',
            },
        ],
        'tagged_reviews': [
            {
                '_id': 333523022,
                'user_id': 986721191,
                'average_score': 4,
                'date': '2016-01-02',
                # 满分 5
                'score': {
                    'taste': 3,
                    'environment': 3,
                    'service': 3,
                },
                'description': '就点评找到的这里。整体感觉还不错...',
                'tag': '体验好_1',
                'tag_sentence': '整体感觉还不错',
            },
        ]
    }

    def __init__(self, mongo_uri, mongo_db):
        self.mongo_uri = mongo_uri
        self.mongo_db = mongo_db

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            mongo_uri=crawler.settings.get('MONGO_URI'),
            mongo_db=crawler.settings.get('MONGO_DATABASE', 'dianping')
        )

    def open_spider(self, _spider):
        self.client = pymongo.MongoClient(self.mongo_uri)
        self.db = self.client[self.mongo_db]

    def close_spider(self, _spider):
        self.client.close()

    def process_item(self, item, spider):
        if spider.name == 'food':
            return self.process_food_item(item, spider)
        if spider.name == 'user':
            return self.process_user_item(item, spider)

    def process_food_item(self, item, _spider):
        try:
            self.db['food'].insert_one(item)
        except Exception as e:
            print(e)
        return item

    def process_user_item(self, item, _spider):
        try:
            self.db['user'].insert_one(item)
        except Exception as e:
            print(e)
        return item
