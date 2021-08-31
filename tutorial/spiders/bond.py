# !/usr/bin/env python3
# -*- coding : utf-8 -*-
"""
Created on Tue Mar 12 15:37:47 2019

@author: python
"""
import scrapy, json
from scrapy.loader import ItemLoader
from urllib.parse import urlencode, quote
from tutorial.items import BondItem
from tutorial.utils import params2url, parse_kline
# from . import Routers, params_url, parse_kline


class Bond(scrapy.Spider):
    """
        回售最后2年70% ，赎回130%  type=KZZ_HSSH
    """
    name = 'bond'
    allowed_domains = ['dcfm.eastmoney.com', 'push2his.eastmoney.com']

    # custom_settings = {
    #     'SOME_SETTING': 'some value',
    # }

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(Bond, cls).from_crawler(crawler, *args, **kwargs)
        routers = crawler.settings.get(
            'FILES_URLS_FIELD')
        spider.routers = routers
        return spider

    def start_requests(self):
        params = {'type': 'KZZ_MX',
                  'token': '894050c76af8597a853f5b408b759f5d'}
        # bond_url = Routers['bond'] + urlencode(params, quote_via=quote)
        bond_url = self.routers['bond'] + urlencode(params, quote_via=quote)
        yield scrapy.Request(bond_url, callback=self.parse, dont_filter=True)

    def parse(self, response, **kwargs):
        # load json
        content = json.loads(response.text)
        meta = response.meta
        meta['owner'] = 'bond'
        # bond loader
        bond = ItemLoader(item=BondItem())
        # bond.add_value('owner', 'bond')
        bond.add_value('owner', meta['owner'])
        # load assets
        for item in content:
            bond.add_value('sid', item['BONDCODE'])
            bond.add_value('name', item['SNAME'])
            bond.add_value('swap_code', item['SWAPSCODE'])
            bond.add_value('swap_price', item['SWAPPRICE'])
            bond.add_value('swap_sdate', item['SWAPSDATE'])
            bond.add_value('swap_edate', item['SWAPEDATE'])
        items = bond.load_item()
        yield items
        # load kline
        for symbol in items['sid']:
            url_kline = params2url(symbol)
            meta['sid'] = symbol
            yield scrapy.Request(url_kline, meta=meta, callback=parse_kline, dont_filter=True)
