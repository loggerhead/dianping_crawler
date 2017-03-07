# -*- coding: utf-8 -*-
import scrapy
import logging
import itertools
from pyquery import PyQuery as pq
from .base_spider import BaseSpider


class FoodSpider(BaseSpider):
    """ Crawl order:

    1. city: http://www.dianping.com/search/category/2/10/
    2. specific region of the city: /search/category/2/10/g110r2580
    3. shop detail:                 /shop/75190365
    """
    name = "food"
    CATEGORY_ID = 10
    WORDS_MAP = {
        '口味': 'taste',
        '环境': 'environment',
        '服务': 'service',
    }
    logger = logging.getLogger(__name__)

    def start_requests(self):
        self.init()

        def start_requests_generator():
            index_fmt = self.add_host('/search/category/{}/{}')

            for city_id, city_name in self.settings['CITY_IDS']:
                url = index_fmt.format(city_id, self.CATEGORY_ID)
                request = scrapy.Request(url, self.parse, priority=100)
                request.meta['city_id'] = city_id
                request.meta['city_name'] = city_name
                yield request

        unfinished = self.delta.fetch_unfinished_requests()
        starts = start_requests_generator()
        requests = itertools.chain(unfinished, starts)
        return requests

    # http://www.dianping.com/search/category/2/10/
    def parse(self, response):
        city_id = response.meta['city_id']
        d = pq(response.text)
        classfy_aa = d('#classfy a')
        area_aa = d('#J_nt_items a')
        prefix = '/search/category'

        # input: <a href="/search/category/2/10/g26483"></a>
        # output: g26483
        def aa2suffix(aa):
            suffixes = []
            urls = self.aa2urls(aa)
            for url in urls:
                if url.startswith(prefix):
                    suffix = url.rsplit('/', 1)[-1]
                    suffixes.append(suffix)
            return suffixes

        classfies = aa2suffix(classfy_aa)
        areas = aa2suffix(area_aa)

        def region_requests_generator():
            for c in classfies:
                for a in areas:
                    path = '{}/{}/{}/{}{}'.format(prefix, city_id, self.CATEGORY_ID, c, a)
                    # /search/category/2/10/g110r2580
                    url = self.add_host(path)
                    request = scrapy.Request(url, self.index, priority=75)
                    request.meta.update(response.meta)
                    yield request

        requests = region_requests_generator()
        requests = self.delta.check_requests(requests, hurry=True)
        self.delta.mark_as_finished(response.request)
        return requests

    # /search/category/2/10/g110r2580
    def index(self, response):
        d = pq(response.text)
        # /search/category/2/10/g110r2580p2
        next_aa = d('.next')
        requests = []

        if next_aa:
            url = self.add_host(self.aa2urls(next_aa)[0])
            request = scrapy.Request(url, self.index, priority=50)
            request.meta.update(response.meta)
            requests.append(request)

        # /shop/75190365
        aa = d('#shop-all-list .pic > a')
        urls = self.aa2urls(aa)

        for url in urls:
            url = self.add_host(url)
            shop_id = url.rsplit('/', 1)[-1]
            request = scrapy.Request(url, self.detail, priority=0)
            request.meta.update(response.meta)
            request.meta['shop_id'] = shop_id
            requests.append(request)

        requests = self.delta.check_requests(requests, hurry=True)
        self.delta.mark_as_finished(response.request)
        return requests

    # /shop/75190365
    def detail(self, response):
        d = pq(response.text)
        basic_info = d('#basic-info')
        brief_info = basic_info('.brief-info')

        shop_name = basic_info('.shop-name').clone().children().remove().end().text().strip()
        address = basic_info('.address .item').text().strip()
        telephones = [span.text for span in basic_info('.tel .item')]

        # average_price
        average_price = brief_info('#avgPriceTitle').text()
        average_price = self.extract_int(average_price)

        # average_score
        score_classes = [
            '.mid-str0', '.mid-str10', '.mid-str20',
            '.mid-str30', '.mid-str40', '.mid-str50',
        ]
        average_score = self.find_classes_exists(brief_info, score_classes)

        # score
        score_items = brief_info('#comment_score .item')
        score = {}
        for item in score_items:
            name, value = item.text.split('：')
            key = self.WORDS_MAP[name]
            try:
                score[key] = float(value)
            except ValueError:
                self.logger.warning('cannot extract float from "%s"', item.text)

        shop_id = response.meta['shop_id']
        city_id = response.meta['city_id']
        city_name = response.meta['city_name']

        item = {
            '_id': shop_id,
            'url': response.request.url,
            'name': shop_name,
            'address': address,
            'telephones': telephones,
            # 人均
            'average_price': average_price,
            # 红色方块
            'average_score': average_score,
            # 满分 10
            'score': score,
            'meta': {
                'city_id': city_id,
                'city_name': city_name,
                'category_id': self.CATEGORY_ID,
                'category_url_name': self.name,
            }
        }
        self.delta.mark_as_finished(response.request)
        return item
