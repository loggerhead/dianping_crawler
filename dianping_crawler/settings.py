# -*- coding: utf-8 -*-

# Scrapy settings for dianping_crawler project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     http://doc.scrapy.org/en/latest/topics/settings.html
#     http://scrapy.readthedocs.org/en/latest/topics/downloader-middleware.html
#     http://scrapy.readthedocs.org/en/latest/topics/spider-middleware.html
HOST = 'http://www.dianping.com'

CITY_IDS = [
    (2, 'beijing'),
]

# only need '_hc.v'
COOKIES = 'showNav=#nav-tab|0|0; navCtgScroll=0; navCtgScroll=0; _hc.v=a38e4721-eee7-9167-2f73-d0ce0182365d.1486954839; PHOENIX_ID=0a010444-15a68e17bd2-25c5754a; __utma=205923334.1798401956.1487817449.1487817449.1487817449.1; __utmc=205923334; __utmz=205923334.1487817449.1.1.utmcsr=(direct)|utmccn=(direct)|utmcmd=(none); default_ab=shopreviewlist%3AA%3A1; __mta=171228447.1487818368557.1487925211991.1487925530915.6; s_ViewType=10; JSESSIONID=BB36B3E0304AE3DD14BCCDF129EB2521; aburl=1; cy=2; cye=beijing'
# convert cookies string to dict
COOKIES = dict([tuple(p.strip().split('=', 1)) for p in COOKIES.split(';')])

PROXIES = [
    # spec https://github.com/constverum/ProxyBroker
    'http://127.0.0.1:8888',
]

BOT_NAME = 'dianping_crawler'
MONGO_DATABASE = 'dianping'

SPIDER_MODULES = ['dianping_crawler.spiders']
NEWSPIDER_MODULE = 'dianping_crawler.spiders'

# Crawl responsibly by identifying yourself (and your website) on the user-agent
#USER_AGENT = 'dianping_crawler (+http://www.yourdomain.com)'

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# Configure maximum concurrent requests performed by Scrapy (default: 16)
CONCURRENT_REQUESTS = 2

# Configure a delay for requests for the same website (default: 0)
# See http://scrapy.readthedocs.org/en/latest/topics/settings.html#download-delay
# See also autothrottle settings and docs
DOWNLOAD_DELAY = 1
# The download delay setting will honor only one of:
#CONCURRENT_REQUESTS_PER_DOMAIN = 16
#CONCURRENT_REQUESTS_PER_IP = 16

# Disable cookies (enabled by default)
COOKIES_ENABLED = False

# Disable Telnet Console (enabled by default)
#TELNETCONSOLE_ENABLED = False

# Override the default request headers:
DEFAULT_REQUEST_HEADERS = {
#   'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
#   'Accept-Language': 'en',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.95 Safari/537.36',
}

# DELTAFETCH_ENABLED = True

# Enable or disable spider middlewares
# See http://scrapy.readthedocs.org/en/latest/topics/spider-middleware.html
SPIDER_MIDDLEWARES = {
    # 'dianping_crawler.middlewares.DianpingCrawlerSpiderMiddleware': 543,
    # 'dianping_crawler.middlewares.DeltaSpiderMiddleware': 543,
}

# Enable or disable downloader middlewares
# See http://scrapy.readthedocs.org/en/latest/topics/downloader-middleware.html
DOWNLOADER_MIDDLEWARES = {
    # 'scrapy.downloadermiddlewares.retry.RetryMiddleware': 80,
    # 'dianping_crawler.middlewares.DeltaSpiderMiddleware': 543,
    # 'scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware': 750,
}

# Configure item pipelines
# See http://scrapy.readthedocs.org/en/latest/topics/item-pipeline.html
ITEM_PIPELINES = {
   'dianping_crawler.pipelines.DianpingCrawlerPipeline': 300,
}

# Enable or disable extensions
# See http://scrapy.readthedocs.org/en/latest/topics/extensions.html
EXTENSIONS = {
   'scrapy.extensions.telnet.TelnetConsole': None,
}

# Enable and configure the AutoThrottle extension (disabled by default)
# See http://doc.scrapy.org/en/latest/topics/autothrottle.html
#AUTOTHROTTLE_ENABLED = True
# The initial download delay
#AUTOTHROTTLE_START_DELAY = 5
# The maximum download delay to be set in case of high latencies
#AUTOTHROTTLE_MAX_DELAY = 60
# The average number of requests Scrapy should be sending in parallel to
# each remote server
#AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
# Enable showing throttling stats for every response received:
#AUTOTHROTTLE_DEBUG = False

# Enable and configure HTTP caching (disabled by default)
# See http://scrapy.readthedocs.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
#HTTPCACHE_ENABLED = True
#HTTPCACHE_EXPIRATION_SECS = 0
#HTTPCACHE_DIR = 'httpcache'
#HTTPCACHE_IGNORE_HTTP_CODES = []
#HTTPCACHE_STORAGE = 'scrapy.extensions.httpcache.FilesystemCacheStorage'
