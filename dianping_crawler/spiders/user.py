# -*- coding: utf-8 -*-
import scrapy
import logging
import emoji
import itertools
import functools
from pyquery import PyQuery as pq
try:
    from urlparse import urljoin
except ImportError:
    from urllib.parse import urljoin
from .base_spider import BaseSpider


class UserSpider(BaseSpider):
    """ Crawl order:

    1. user detail: http://www.dianping.com/member/24903566
    2. followees: /member/24903566/follows
    3. followers: /member/24903566/fans
    4. collections: /member/24903566/wishlists
    """
    name = "user"
    logger = logging.getLogger(__name__)
    USER_URL_FMT = "http://www.dianping.com/member/{user_id}"
    # field name in db => url suffix
    FIELD_SUFFIX_MAP = {
        'followees': 'follows',
        'followers': 'fans',
        'collections': 'wishlists',
    }

    def init(self):
        super().init()
        self.reviews_cursor = self.db['review'].find()

    def start_requests(self):
        self.init()

        def gen_user_requests(shop_review):
            for review in shop_review['reviews']:
                user_id = review['user_id']
                url = self.USER_URL_FMT.format(user_id=user_id)
                request = scrapy.Request(url, self.parse, priority=100)
                request.meta['user_id'] = user_id
                yield self.delta.check_request(request)

        list_of_requests = map(gen_user_requests, self.reviews_cursor)
        requests = functools.reduce(itertools.chain, list_of_requests)
        requests = itertools.chain(self.unfinished_requests, requests)
        return filter(bool, requests)

    # getting tagged_reviews urls
    def parse(self, response):
        d = pq(emoji.demojize(response.text))
        user_id = response.meta['user_id']

        name = d('.tit > .name').text()
        gender = d('.user-info > .user-groun > i').attr('class')
        address = d('.user-info > .user-groun').text()
        contribution = self.extract_int(d('#J_col_exp').text())

        item = {
            '_id': user_id,
            'name': name,
            'gender': gender,
            'address': address,
            'contribution': contribution,
            'followees': [],
            'followers': [],
            'collections': [],
        }
        self.save_item_to_db(item)

        requests = [
            self.create_request(user_id, 'followees', 75),
            self.create_request(user_id, 'followers', 50),
            self.create_request(user_id, 'collections', 25),
        ]
        self.delta.mark_as_finished(response.request)
        return filter(bool, requests)

    def create_request(self, user_id, field_name, priority=0, suffix=None):
        if not suffix:
            suffix = self.FIELD_SUFFIX_MAP[field_name]
        callback = getattr(self, 'parse_{}'.format(field_name))
        url = urljoin(self.USER_URL_FMT.format(user_id=user_id) + '/', suffix)

        request = scrapy.Request(url, callback, priority=priority)
        request.meta['user_id'] = user_id
        return self.delta.check_request(request)

    def parse_followees(self, response):
        return self.do_parse_user_page(response,
                                       'followees',
                                       '.fllow-list .pic-txt li div.tit a',
                                       lambda a: a.attrib['user-id'])

    def parse_followers(self, response):
        return self.do_parse_user_page(response,
                                       'followers',
                                       '.fllow-list .pic-txt li div.tit a',
                                       lambda a: a.attrib['user-id'])

    def parse_collections(self, response):
        return self.do_parse_user_page(response,
                                       'collections',
                                       '.favor-list li div.tit a',
                                       lambda a: a.attrib['href'].rsplit('/', 1)[-1])

    def do_parse_user_page(self, response, field_name, aa_selector, id_extract_func):
        d = pq(emoji.demojize(response.text))

        # user id or shop id
        ids = []
        aa = d(aa_selector)
        for a in aa:
            id = id_extract_func(a)
            id = self.extract_int(id)
            ids.append(id)

        user_id = response.meta['user_id']
        self.extend_item_field_in_db(user_id, field_name, ids)

        next_page = d('.pages-num > a.page-next')
        if next_page:
            url_path = next_page.attr('href')
            suffix = '{}{}'.format(self.FIELD_SUFFIX_MAP[field_name], url_path)
            request = self.create_request(user_id, field_name, suffix=suffix)
            self.delta.mark_as_finished(response.request)
            yield request
