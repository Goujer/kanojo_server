#!/usr/bin/env python
# -*- coding: utf-8 -*-

__version__ = '0.1'
__author__ = 'Andrey Derevyagin'
__copyright__ = 'Copyright © 2014'

import copy
import unittest

from store import StoreManager, KANOJO_OWNER, KANOJO_FRIEND, KANOJO_OTHER

class StoreTest(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(StoreTest, self).__init__(*args, **kwargs)
        self.sm = StoreManager()
        self.user = {"facebook_connect": False,
			"money": 0,
			"sex": "male",
			"create_time": 1413019326, "likes": [],
			"id": 1, "description": None,
			"uuid": ["test_uuid"],
			"stamina": 100,
			"kanojos": [1, 368],
			"email": None,
			"twitter_connect": False,
			"generate_count": 0,
			"profile_image_url": "http://www.deviantsart.com/2oo69ib.jpg",
			"birthday": 1413025200, "enemies": [],
			"password": None,
			"friends": [231, 31, 149, 333, 335, 336, 337, 339, 30, 220, 361],
			"tickets": 20,
			"name": "everyone",
			"language": "en",
			"level": 1,
			"scan_count": 0,
			"has_items": [{"has_item_id": 51, "store_item_id": 110}]}

    def prepare_categories(self, ctgrs, user_level=None):
        item_categories = []
        _ctgrs = copy.deepcopy(ctgrs)
        while len(_ctgrs):
            c = _ctgrs[0]
            group = [c, ]
            # search category group
            if 'group_title' in c:
                group = [x for x in _ctgrs if x.get('group_title') == c.get('group_title')]
            val = {
                'items': []
            }
            for c in group:
                val['title'] = c.get('group_title') if 'group_title' in c else c.get('title')
                if c.get('image_thumbnail_url') is None:
                    # category for basic items
                    itms = [x for x in self.sm._items if x.get('category_id') == c.get('item_category_id')]
                    if user_level:
                        val['level'] = user_level
                    for i in itms:
                        val['items'].append(self.sm.clear_item(i))
                else:
                    val['items'].append(self.sm.clear_category(c))
                _ctgrs.remove(c)
            item_categories.append(val)
        return item_categories

    def item_list_from_categories(self, allow_kanojo, user_level=None):
        ctgrs = self.sm.categories(allow_kanojo, item_class=1)
        # filter categories with items
        ctgrs = [c for c in ctgrs if len([i for i in self.sm._items if c.get('item_category_id', -2)==i.get('category_id', -1)])]
        return self.prepare_categories(ctgrs, user_level=user_level)

    def test_item_list1(self):
        item_list1 = self.sm.goods_list(KANOJO_OWNER, 5)
        item_list2 = self.item_list_from_categories(KANOJO_OWNER, 5)
        self.assertSequenceEqual(item_list1, item_list2)

    def test_item_list2(self):
        item_list1 = self.sm.goods_list(KANOJO_FRIEND, 1)
        item_list2 = self.item_list_from_categories(KANOJO_FRIEND, 1)
        self.assertSequenceEqual(item_list1, item_list2)

    def test_item_list3(self):
        item_list1 = self.sm.goods_list(KANOJO_OTHER, 99)
        item_list2 = self.item_list_from_categories(KANOJO_OTHER, 99)
        self.assertSequenceEqual(item_list1, item_list2)

    def test_item_list_and_categories(self):
        has_items = copy.deepcopy(self.user.get('has_items'))
        item_list = self.sm.goods_list(KANOJO_OWNER, filter_has_items=True, has_items=has_items)
        self.assertGreater(len(item_list), 0)
        self.assertTrue('items' in item_list[0])
        self.assertGreater(len(item_list[0].get('items')), 0)

        item_category = item_list[0].get('items')[0]
        c_items = self.sm.category_goods(item_category.get('item_category_id'), filter_has_items=True, has_items=has_items)
        self.assertGreater(len(item_list), 0)
        self.assertTrue('items' in item_list[0])
        self.assertGreater(len(item_list[0].get('items')), 0)
        for c in c_items:
            self.assertEqual(c.get('flag'), 'user_has')
            for i in c.get('items'):
                self.assertTrue('has_units' in i)

    def test_not_unique_items(self):
        items = copy.deepcopy(self.sm._items)
        items.extend(self.sm._dates)
        ids = [x.get('item_id') for x in items]

        while len(ids):
            item_id = ids.pop(0)
            if item_id != None:
                self.assertFalse(item_id in ids, 'Dublicate item_id: \"%s\"'%item_id)

    def test_not_unique_categories(self):
        categories = copy.deepcopy(self.sm._categories)
        ids = [x.get('item_category_id') for x in categories]
        while len(ids):
            c_id = ids.pop(0)
            if c_id != None:
                self.assertFalse(c_id in ids, 'Dublicate category \"%s\"'%c_id)



if __name__ == '__main__':
    unittest.main()(venv)
