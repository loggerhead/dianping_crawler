# -*- coding: utf-8 -*-
import scrapy
import logging
import emoji
from datetime import datetime
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


class FoodSpider(scrapy.Spider):
    name = "food"
    CATEGORY_ID = 10
    WORDS_MAP = {
        '口味': 'taste',
        '环境': 'environment',
        '服务': 'service',
    }

    def start_requests(self):
        index_fmt = self.add_host('/search/category/{}/{}')

        for city_id, city_name in self.settings['CITY_IDS']:
            url = index_fmt.format(city_id, self.CATEGORY_ID)
            request = scrapy.Request(url, self.parse)
            request.meta['city_id'] = city_id
            request.meta['city_name'] = city_name
            yield request

    # http://www.dianping.com/search/category/2/10/
    def parse(self, response):
        city_id = response.meta['city_id']
        d = pq(response.text)
        classfy_aa = d('#classfy a')
        area_aa = d('#J_nt_items a')
        prefix = '/search/category'

        # <a href="/search/category/2/10/g26483">...</a>
        # g26483
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

        requests = []
        for c in classfies:
            for a in areas:
                path = '{}/{}/{}/{}{}'.format(prefix, city_id, self.CATEGORY_ID, c, a)
                url = self.add_host(path)
                request = scrapy.Request(url, self.index)
                request.meta.update(response.meta)
                requests.append(request)

        return requests

    def index(self, response):
        d = pq(response.text)
        aa = d('#shop-all-list .pic > a')
        urls = self.aa2urls(aa)

        for url in urls:
            url = self.add_host(url)
            shop_id = url.rsplit('/', 1)[-1]
            request = scrapy.Request(url, self.detail)
            request.meta.update(response.meta)
            request.meta['shop_id'] = shop_id
            yield request

        next_aa = d('.next')
        if next_aa:
            url = self.add_host(self.aa2urls(next_aa)[0])
            request = scrapy.Request(url, self.index)
            request.meta.update(response.meta)
            yield request

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
                logging.warning('cannot extract float from "{}"'.format(item.text))

        shop_id = response.meta['shop_id']
        city_id = response.meta['city_id']
        city_name = response.meta['city_name']

        item = {
            '_id': shop_id,
            'name': shop_name,
            'address': address,
            'telephones': telephones,
            # 人均
            'average_price': average_price,
            # 红色方块
            'average_score': average_score,
            # 满分 10
            'score': score,
            # need request API
            'recommend_cuisines': [],
            'tags': [],
            'reviews': [],
            'tagged_reviews': []
        }

        tags_api_fmt = '/ajax/json/shopDynamic/allReview?shopId={shop_id}&cityId={city_id}&categoryURLName={name}&power=5&cityEnName={city_name}&shopType={category_id}'
        tags_api_url = self.add_host(tags_api_fmt.format(shop_id=shop_id,
                                                         city_id=city_id,
                                                         city_name=city_name,
                                                         name=self.name,
                                                         category_id=self.CATEGORY_ID))
        request = scrapy.Request(tags_api_url, self.parse_tags_api)
        request.meta.update(response.meta)
        request.meta['item'] = item
        request.meta['url'] = response.request.url
        return request

    def parse_tags_api(self, response):
        obj = json.loads(response.text.encode('utf8'))
        shop_id = response.meta['shop_id']
        item = response.meta['item']

        # tagged_reviews
        tagged_api_fmt = self.add_host('/ajax/json/shopfood/wizard/getReviewListFPAjax?act=getreviewlist&tab=default&order=summary&summaryName={}&shopId={}')
        item['_requests'] = []

        if obj['summarys']:
            for tag in obj['summarys']:
                name = tag['summaryName']
                value = tag['summaryCount']
                item['tags'].append((name, value))

                url = tagged_api_fmt.format(name, shop_id)
                request = scrapy.Request(url, self.parse_tagged_reviews)
                request.meta.update(response.meta)
                request.meta['tag'] = name
                item['_requests'].append(request)

        item['recommend_cuisines'] = obj['dishTagStrList']

        # reviews
        url = urljoin(response.meta['url'] + '/', 'review_all')
        request = scrapy.Request(url, self.parse_review_all)
        request.meta.update(response.meta)
        return request

    def parse_review_all(self, response):
        d = pq(emoji.demojize(response.text))
        item = response.meta['item']
        request_url = response.request.url

        reviews = self.do_parse_reviews(d)
        item['reviews'].extend(reviews)

        next = d('.Pages .NextPage')
        if next:
            url = urljoin(request_url, next.attr('href'))
            request = scrapy.Request(url, self.parse_review_all)
            request.meta['item'] = item
            yield request
        elif len(item['_requests']) > 0:
            request = item['_requests'].pop()
            yield request

    def parse_tagged_reviews(self, response):
        html_content = json.loads(emoji.demojize(response.text))['msg']
        item = response.meta['item']

        try:
            d = pq(html_content)
            tag = response.meta['tag']
            tagged_reviews = self.do_parse_tagged_reviews(d, tag)
            item['tagged_reviews'].extend(tagged_reviews)
        except (XMLSyntaxError, ParseError):
            pass

        if len(item['_requests']) > 0:
            return item['_requests'].pop()
        else:
            del item['_requests']
            return item

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
                    logging.warning('cannot extract integer from "{}"'.format(item.text))

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
            logging.warning('cannot extract integer from "{}"'.format(text))
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
            logging.warning('not a valid date: "{}"'.format(date))
            date = None
        return date
