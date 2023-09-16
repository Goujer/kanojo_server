#!/usr/bin/env python
# -*- coding: utf-8 -*-

__version__ = '0.1'
__author__ = 'Andrey Derevyagin'
__copyright__ = 'Copyright © 2014'

import hashlib
import json
import time
import urllib.request, urllib.error, urllib.parse

#from config import GEOIP_SECRET1, GEOIP_SECRET2, GEOIP_SECRET3

GEOIP_CACHE_ONLY = 0
GEOIP_WEB_SERVICE = 1


class GeoIP(object):
    """docstring for GeoIP"""
    def __init__(self, db=None, secret1='', secret2='', secret3=''):
        super(GeoIP, self).__init__()
        self.db = db
        self.cache = self.read_cache()
        self.secret1 = secret1
        self.secret2 = secret2
        self.secret3 = secret3

    def read_cache(self):
        cache = {}
        if self.db is not None:
            for row in self.db.geoip.find():
                if row.get('key'):
                    val = {
                        'tz': row.get('tz'),
                        'update': row.get('update'),
                    }
                    cache[row.get('key')] = val
        return cache

    def geo_key(self, ip):
        ipIndex = len(ip)//2
        tmp = ('%s%s%s%s%s'%(self.secret1, ip[:ipIndex], self.secret2, ip[ipIndex:], self.secret3)).encode('utf-8')
        #print tmp, ip
        return hashlib.md5(tmp).hexdigest()

    def ip2timezone(self, ip, service_type=GEOIP_CACHE_ONLY):
        key = self.geo_key(ip)
        if key in self.cache:
            self.cache.get(key)['update'] = int(time.time())
            return self.cache.get(key).get('tz')
        if service_type == GEOIP_WEB_SERVICE:
            tz_string = None
            req = urllib.request.Request('https://freegeoip.net/json/'+ip)
            try:
                urlObject = urllib.request.urlopen(req, timeout=5)
                tmp = json.loads(urlObject.read())
                tz_string = tmp.get('time_zone')
            except:
                pass
            self.cache[key] = {
                'tz': tz_string,
                'update': int(time.time()),
            }
            if tz_string and self.db:
                val = self.cache[key].copy()
                val['key'] = key
                self.db.geoip.insert(val)
            return tz_string


if __name__ == "__main__":
    geoIP = GeoIP()
    print(geoIP.ip2timezone('8.8.8.8', service_type=GEOIP_WEB_SERVICE))
    print(geoIP.ip2timezone('31.13.144.31', service_type=GEOIP_WEB_SERVICE))
    print(geoIP.ip2timezone('8.8.8.8'))
    print(geoIP.cache)
