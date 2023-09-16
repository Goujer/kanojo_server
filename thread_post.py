#!/usr/bin/env python
# -*- coding: utf-8 -*-

__version__ = '0.01'
__author__ = 'Andrey Derevyagin'
__copyright__ = 'Copyright © 2013-2014'

import calendar
import time
import pytz

from datetime import datetime

class Post(object):
    """docstring for Post"""
    def __init__(self, post={}, timezone_string=None):
        super(Post, self).__init__()
        self.title = post.get('title', '')
        self.poster = post.get('poster', '')
        self.time = post.get('time', 0)     # unixtime
        self.post = post.get('post', None)
        self.thumb = post.get('thumb', None)
        self.img = post.get('image', None)
        self.id = post.get('pid', None)
        self.deleted = post.get('deleted', False)
        self.lxml_data = None
        self.timezone_string = timezone_string if timezone_string else 'Europe/Kiev'

        if post.get('image_attr'):
            tmp = post.get('image_attr')
            self.img_width = tmp[0]
            self.img_height = tmp[1]
            self.img_size = tmp[2]
        else:
            self.img_width = 0
            self.img_height = 0
            self.img_size = ''
        if post.get('thumb_attr'):
            tmp = post.get('thumb_attr')
            self.thumb_width = tmp[0]
            self.thumb_height = tmp[1]
        else:
            self.thumb_width = 0
            self.thumb_height = 0

    def __str__(self):
        return '%s %s %s'%(time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.localtime(self.time)),
                           self.title.encode('utf-8') if self.title else '', self.img)

    def dump(self):
        return '''
id: %d
date: %s
title: %s
poster: %s
image(%s): %s
thumb(%dx%d): %s
post(%d): %s'''%(self.id, self.date_string(), self.title, self.poster, self.img_info_str(), self.img,
            self.thumb_width, self.thumb_height, self.thumb, len(self.post) if self.post else 0, self.post if self.post else '')

    def date_string(self, timezone_string=None):
        if timezone_string is None:
            timezone_string = self.timezone_string
        tm = datetime.fromtimestamp(self.time, pytz.timezone(timezone_string))
        #tm = datetime.fromtimestamp(self.time, pytz.timezone('Europe/Kiev'))
        #tm = datetime.fromtimestamp(self.time, pytz.utc)
        #tm = time.gmtime(self.time).astimezone(pytz.timezone('Europe/Moscow'))
        m = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
        w = ['Пн','Вт','Ср','Чт','Пт','Сб','Вс']
        return '%s %02d %s %d %02d:%02d:%02d'%(w[tm.weekday()], tm.day, m[tm.month-1], tm.year, tm.hour, tm.minute, tm.second)
        #tm = time.localtime(self.time)
        #return '%s %02d %s %d %02d:%02d:%02d'%(w[tm.tm_wday], tm.tm_mday, m[tm.tm_mon-1], tm.tm_year, tm.tm_hour, tm.tm_min, tm.tm_sec)
        #return time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime(self.time))

    def img_info_str(self):
        if self.img_width and self.img_height:
            return '%s, %dx%d'%(self.img_size, self.img_width, self.img_height)
        return None

    def img_name(self):
        if self.img:
            return self.img.split('/')[-1]
        return None
