# -*- coding: utf-8 -*-

# Define here the models for your spider middleware
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/spider-middleware.html


class DianpingCrawlerSpiderMiddleware(object):
    def process_request(self, request, spider):
        cookies = spider.settings.get('COOKIES', {})
        request.cookies.update(cookies)
