# -*- coding: utf-8 -*-
import scrapy
import logging
import emoji
import itertools
import functools
from pyquery import PyQuery as pq
from lxml.etree import XMLSyntaxError, ParseError
try:
    from urlparse import urljoin
except ImportError:
    from urllib.parse import urljoin
try:
    import ujson as json
except ImportError:
    import json
from .base_spider import BaseSpider


class ReviewSpider(BaseSpider):
    """ Crawl order:

    1. tags API for tagged_reviews
    2. shop all reviews:            /shop/75190365/review_all
    3. tagged_reviews
    """
    name = "review"
    TAGS_API_FMT = '/ajax/json/shopDynamic/allReview?shopId={shop_id}&cityId={city_id}&categoryURLName={category_url_name}&power=5&cityEnName={city_name}&shopType={category_id}'
    TAGGED_API_FMT = '/ajax/json/shopfood/wizard/getReviewListFPAjax?act=getreviewlist&tab=default&order=summary&summaryName={summary_name}&shopId={shop_id}'
    WORDS_MAP = {
        '口味': 'taste',
        '环境': 'environment',
        '服务': 'service',
    }
    logger = logging.getLogger(__name__)

    def init(self):
        super().init()
        self.shops_cursor = self.db['food'].find(no_cursor_timeout=True)

    def start_requests(self):
        self.init()

        def gen_tags_api_request(shop):
            # for getting tagged_reviews urls
            api_args = shop['meta']
            api_args['shop_id'] = shop['_id']
            url = self.add_host(self.TAGS_API_FMT.format(**api_args))

            request = scrapy.Request(url, self.parse, priority=100)
            request.meta['shop_id'] = shop['_id']
            request.meta['shop_url'] = shop['url']
            return self.delta.check_request(request)

        requests = map(gen_tags_api_request, self.shops_cursor)
        requests = itertools.chain(self.unfinished_requests, requests)
        return filter(bool, requests)

    # getting tagged_reviews urls
    def parse(self, response):
        obj = json.loads(response.text.encode('utf8'))
        shop_id = response.meta['shop_id']
        shop_url = response.meta['shop_url']

        item = {
            '_id': shop_id,
            'tags': [],
            'recommend_cuisines': obj['dishTagStrList'],
            'reviews': [],
            'tagged_reviews': [],
        }

        # tagged_reviews
        if obj['summarys']:
            for tag in obj['summarys']:
                name = tag['summaryName']
                value = tag['summaryCount']
                item['tags'].append((name, value))

        self.save_item_to_db(item)
        # all reviews
        url = urljoin(shop_url + '/', 'review_all')
        request = scrapy.Request(url, self.parse_review_all, priority=75)
        request.meta['shop_id'] = item['_id']
        request = self.delta.check_request(request)
        self.delta.mark_as_finished(response.request)
        return request

    # all reviews about a shop
    def parse_review_all(self, response):
        d = pq(emoji.demojize(response.text))
        shop_id = response.meta['shop_id']

        reviews = self.do_parse_reviews(d)
        self.extend_item_field_in_db(shop_id, 'reviews', reviews)

        # next page of all reviews
        next = d('.Pages .NextPage')
        if next:
            url = urljoin(response.request.url, next.attr('href'))
            request = scrapy.Request(url, self.parse_review_all, priority=50)
            request.meta['shop_id'] = shop_id
            request = self.delta.check_request(request)
            self.delta.mark_as_finished(response.request)
            yield request
        # if all reviews is crawled, then crawl tagged reviews
        else:
            requests = self.gen_tagged_review_requests(shop_id)
            requests = self.delta.check_requests(requests)
            self.delta.mark_as_finished(response.request)
            return requests

    def gen_tagged_review_requests(self, shop_id):
        cursor = self.db_collection.find(no_cursor_timeout=True)

        def gen_tagged_review_requests(item):
            for tag, _ in item['tags']:
                url = self.add_host(self.TAGGED_API_FMT.format(summary_name=tag,
                                                               shop_id=shop_id))
                request = scrapy.Request(url, self.parse_tagged_reviews)
                request.meta['tag'] = tag
                request.meta['shop_id'] = shop_id
                yield self.delta.check_request(request)

        list_of_requests = map(gen_tagged_review_requests, cursor)
        requests = functools.reduce(itertools.chain, list_of_requests)
        return filter(bool, requests)

    # tagged reviews
    def parse_tagged_reviews(self, response):
        html_content = json.loads(emoji.demojize(response.text))['msg']
        tag = response.meta['tag']
        shop_id = response.meta['shop_id']

        try:
            d = pq(html_content)
            tagged_reviews = self.do_parse_tagged_reviews(d, tag)
            self.extend_item_field_in_db(shop_id, 'tagged_reviews', tagged_reviews)
            self.delta.mark_as_finished(response.request)
        except (XMLSyntaxError, ParseError) as e:
            self.logger.warn('parse tagged review failed: %s', response.request.url)

    def do_parse_tagged_reviews(self, d, tag):
        score_classes = [
            '.sml-str0', '.sml-str10', '.sml-str20',
            '.sml-str30', '.sml-str40', '.sml-str50',
        ]
        comments = d('li.comment-item')
        reviews = []

        for li in comments:
            li = pq(li)

            id = int(li.attr('data-id'))
            user_id = int(li('a.avatar').attr('data-user-id'))
            average_score = self.find_classes_exists(li, score_classes)

            # score
            score_items = li('.shop-info .item')
            score = {}
            for item in score_items:
                name, value = item.text.split('：')
                key = self.WORDS_MAP[name]
                try:
                    score[key] = int(value)
                except ValueError:
                    self.logger.warning('cannot extract integer from "%s"', item.text)

            # date
            date = li('.time').text()
            date = self.text2date(date)

            description = li('.desc').text()
            tag_sentence = li('.desc span').text()

            review = {
                '_id': id,
                'user_id': user_id,
                'average_score': average_score,
                'date': date,
                'score': score,
                'description': description,
                'tag': tag,
                'tag_sentence': tag_sentence,
            }
            reviews.append(review)

        return reviews

    def do_parse_reviews(self, d):
        score_classes = [
            '.irr-star0', '.irr-star10', '.irr-star20',
            '.irr-star30', '.irr-star40', '.irr-star50',
        ]
        comments = d('.comment-list > ul > li')
        reviews = []

        for li in comments:
            li = pq(li)

            id = int(li.attr('data-id'))
            user_id = int(li('div.pic > a').attr('user-id'))
            user_info = li('div.content div.user-info')
            average_score = self.find_classes_exists(user_info, score_classes)

            # date
            date = li('div.content > div.misc-info > span.time').text()
            date = self.text2date(date)

            # score
            rsts = user_info('.rst')
            score = {}
            for rst in rsts:
                s = rst.text.strip()
                for w in self.WORDS_MAP.keys():
                    if s.startswith(w):
                        score[self.WORDS_MAP[w]] = self.extract_int(s)

            description = pq(li)('div.content > div.comment-txt > div').text()

            review = {
                '_id': id,
                'user_id': user_id,
                'average_score': average_score,
                'date': date,
                'score': score,
                'description': description,
            }
            reviews.append(review)

        return reviews
