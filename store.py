#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'Andrey Derevyagin, Goujer'
__copyright__ = 'Copyright © 2014-2015, 2020-2022'

import codecs
import copy
import json

from constants import *

ITEM_DESRIPTION_DICT = {
	# TODO make behaviour match this description better
	'attention': '\n*Attention\nThis is consumable item.\nThis item is for the user who is at level 1 or higher.\nWhen she wears clothes, love level is cut down less likely. Effectiveness is depending upon clothes she wears.\nWhen you give her more than 1clothes at the same time, KANOJO by herself selects which clothes she wears daily. Outfits can be given by her [friends], but she often seems to put on clothes given from her [owner].\nDressing time is depending on her area(where she was born).',
	'date1': ' Enemies won\'t be able to approach your KANOJO for 1day when using this item.\nCaution: You can use this item only for your KANOJO.',
	'date7': ' Enemies won\'t be able to approach your KANOJO for 7days when using this item.\nCaution: You can use this item only for your KANOJO.',
	'date12h': ' Enemies won\'t be able to approach your KANOJO for 12hours when using this item.\nCaution: You can use this item only for your KANOJO.',
}
DESCRIPTION_FORMAT = "Dressing time: {dressing_time}\nIt throbs very much somehow when she puts this on..."

# TODO Set 'flag' on item_categories to "true" if it is owned items
# Currency Exchange 115Yen = $1 = 1 Ticket = ? B-coin

class StoreManager(object):
	"""docstring for StoreManager"""
	def __init__(self, store_file='store_items.json'):
		super(StoreManager, self).__init__()
		gift_info = json.load(open('gift_items.json', encoding='utf-8'))

		#store_info = json.load(open(store_file, encoding='utf-8'))
		#self._items = store_info.get('items')
		#self._dates = store_info.get('dates')
		#self._categories = store_info.get('categories')
		#store_dates = json.load(open(dates_file))
		#self._dates_categories = store_dates.get('categories')

	def items(self, kanojo_relation, item_class):
		_items = self._items if item_class == 1 else self._dates
		ctgrs = self.categories(kanojo_relation, item_class)
		ctgrs = [x.get('item_category_id') for x in ctgrs]
		itms = [x for x in _items if x.get('relation_level', 0xFF) & kanojo_relation and x.get('category_id', 0) in ctgrs]
		#itms = filter(lambda x: x.get('allow_kanojo', 0) & kanojo_relation, _items)
		return itms

	def categories(self, kanojo_relation, item_class):
		#_categories = self._items_categories if item_class==1 else self._dates_categories
		ctgrs = [x for x in self._categories if x.get('kanojo_relation', 0) & kanojo_relation]
		return ctgrs

	def clear_category(self, ctgr):
		allow_keys = ['item_category_id', 'image_thumbnail_url', 'description', 'expand_flag', 'title']
		rv = {}
		for k in list(ctgr.keys()):
			if k in allow_keys:
				rv[k] = ctgr[k]
		if 'image_thumbnail_url' not in ctgr:
			rv.pop('item_category_id', None)
		return rv

	def clear_item(self, itm):
		allow_keys = ['description', 'title', 'item_id', 'image_url', 'image_thumbnail_url', 'price', 'has_units', 'purchasable_level']
		rv = {}
		for k in list(itm.keys()):
			if k in allow_keys:
				rv[k] = itm[k]
		if 'description' in rv:
			rv['description'] = rv['description'].format(**ITEM_DESRIPTION_DICT)
		if 'price' not in rv and 'has_units' not in rv:
			price = None
			if 'price_t' in itm:
				price = 'Ticket: {price_t}'.format(**itm)
			if 'price_b' in itm:
				price = 'Price: {price_b}B Coins'.format(**itm) if price is None else price + ', {price_b}B Coins'.format(**itm)
			if 'price_s' in itm:
				price = 'Price: {price_s} stamina'.format(**itm) if price is None else price + ', {price_s} stamina'.format(**itm)
			if price:
				rv['price'] = price
		return rv

	def category_by_id(self, item_category_id, item_class):
		#_categories = self._items_categories if item_class==ITEM_CLASS_GOODS else self._dates_categories
		_ctgrs = [c for c in self._categories if c.get('item_category_id') == item_category_id]
		if len(_ctgrs):
			return _ctgrs[0]
		return None

	def _items2categories(self, itms, item_class, user_level=None, has_items=None, set_user_has_flag=False):
		#_categories = self._items_categories if item_class == ITEM_CLASS_GOODS else self._dates_categories
		item_categories = []
		_itms = copy.deepcopy(itms)
		while len(_itms):
			i = _itms[0]
			c = self.category_by_id(i.get('category_id'), item_class=item_class)
			if c:
				_ctgrs = [el for el in self._categories if el.get('group_title', -1) == c.get('group_title', -2) or el.get('item_category_id') == c.get('item_category_id')]
				val = {
					'items': []
				}
				if set_user_has_flag:
					val['flag'] = 'user_has'
				for c in _ctgrs:
					val['title'] = c.get('group_title') if 'group_title' in c else c.get('title')
					# category for basic items
					_c_items = [x for x in _itms if x.get('category_id') == c.get('item_category_id')]
					if len(_c_items):
						if c.get('image_thumbnail_url') is None:
							if user_level:
								val['level'] = user_level
							for i in _c_items:
								val['items'].append(self.clear_item(i))
						else:
							tmp_category = self.clear_category(c)

							# add has items counter to title
							if set_user_has_flag:
								has_units_counter = 0
								for i in _c_items:
									tmp = [x for x in has_items if x.get('store_item_id')==i.get('item_id')]
									if len(tmp):
										has_units_counter += tmp[0].get('units', 1)
								if has_units_counter:
									tmp_category['title'] += ' (%d)'%has_units_counter

							val['items'].append(tmp_category)
						for i in _c_items:
							_itms.remove(i)
				item_categories.append(val)
			else:
				_itms.remove(i)
		return item_categories

	def _item_list(self, kanojo_relation, item_class, user_level=None, filter_has_items=False, has_items=None):
		items = self.items(kanojo_relation, item_class=item_class)
		if filter_has_items:
			store_item_ids = [x.get('store_item_id') for x in has_items]
			items = [x for x in items if x.get('item_id') in store_item_ids]
		return self._items2categories(items, item_class=item_class, user_level=user_level, has_items=has_items, set_user_has_flag=filter_has_items)

	def goods_list(self, kanojo_relation, user_level=None, filter_has_items=False, has_items=None):
		return self._item_list(kanojo_relation=kanojo_relation, item_class=GIFT_ITEM_CLASS, user_level=user_level, filter_has_items=filter_has_items, has_items=has_items)

	def dates_list(self, kanojo_relation, user_level=None, filter_has_items=False, has_items=None):
		return self._item_list(kanojo_relation=kanojo_relation, item_class=DATE_ITEM_CLASS, user_level=user_level, filter_has_items=filter_has_items, has_items=has_items)

	def _category_items2categories(self, itms, set_user_has_flag=False, has_items=None):
		item_categories = []
		_itms = copy.deepcopy(itms)
		while len(_itms):
			i = _itms[0]
			if 'group' in i:
				val = {
					'items': [],
					'title': i.get('group')
				}
				if set_user_has_flag:
					val['flag'] = 'user_has'
				_c_items = [x for x in _itms if x.get('group')==i.get('group')]
				for i in _c_items:
					if has_items:
						tmp_arr = [x for x in has_items if x.get('store_item_id')==i.get('item_id')]
						if tmp_arr:
							units = tmp_arr[0].get('units', 1)
							i['has_units'] = '1 unit' if units==1 else '%d units'%units
							# item_id for has_items equal has_item_id and "do_extend_gift" in params get has_item_id
							# but how about "x10" store items?
							# Maybe this bad idea?
							# Update: item_id universal id (use for show and buy items on store and give has item as present to kanojo)
							# commented!
							#i['item_id'] = i.get('has_item_id')
					val['items'].append(self.clear_item(i))
					_itms.remove(i)
				item_categories.append(val)
			else:
				_itms.remove(i)
		return item_categories

	def _category_items(self, item_category_id, item_class, filter_has_items=False, has_items=None):
		_items = self._items if item_class==1 else self._dates
		itms = [x for x in _items if x.get('category_id') == item_category_id]
		store_item_ids = [x.get('store_item_id') for x in has_items]
		if filter_has_items:
			itms = [x for x in itms if x.get('item_id') in store_item_ids]
		else:
			itms = [x for x in itms if not x.get('hidden_in_store') or x.get('item_id') in store_item_ids]
		return self._category_items2categories(itms, set_user_has_flag=filter_has_items, has_items=has_items)

	def category_goods(self, item_category_id, filter_has_items=False, has_items=None):
		return self._category_items(item_category_id=item_category_id, item_class=GIFT_ITEM_CLASS, filter_has_items=filter_has_items, has_items=has_items)

	def category_dates(self, item_category_id, filter_has_items=False, has_items=None):
		return self._category_items(item_category_id=item_category_id, item_class=DATE_ITEM_CLASS, filter_has_items=filter_has_items, has_items=has_items)

	def get_item(self, item_id):
		'''
			get item from GOODS!!!
		'''
		itm = [x for x in self._items if x.get('item_id') == item_id]
		if len(itm):
			return itm[0]
		return None

	def get_date(self, item_id=None):
		itm = [x for x in self._dates if x.get('item_id') == item_id]
		if len(itm):
			return itm[0]
		return None

	def item_type(self, item_id):
		'''
			for extended items only
			return 1 - if item_id is item(goods)
			       2 - if item_id is date
		'''
		item_ids = [el.get('item_id') for el in self._items]
		date_ids = [el.get('item_id') for el in self._dates]
		if item_id in item_ids and item_id not in date_ids:
			return GIFT_ITEM_CLASS
		elif item_id in date_ids and item_id not in item_ids:
			return DATE_ITEM_CLASS
		else:
			return 0


if __name__ == "__main__":
	import pprint
	KANOJO_OWNER = 1
	k_type = KANOJO_OWNER
	u_level = 1
	sm = StoreManager()
	#dt = sm.category_goods(6)
	#pprint.pprint(dt)
	#print json.dumps(dt)

	user = {"facebook_connect": False, "money": 0, "sex": "male", "create_time": 1413019326, "likes": [], "id": 1, "description": None, "uuid": ["test_uuid"], "stamina": 100, "kanojos": [1, 368], "email": None, "twitter_connect": False, "generate_count": 0, "profile_image_url": "http://www.deviantsart.com/2oo69ib.jpg", "birthday": 1413025200, "enemies": [], "password": None, "friends": [231, 31, 149, 333, 335, 336, 337, 339, 30, 220, 361], "tickets": 20, "name": "everyone", "language": "en", "level": 1, "scan_count": 0, "has_items": [{"store_item_id": 153}, {"store_item_id": 102, "units": 2}]}
	#print json.dumps(sm.goods_list(KANOJO_OWNER, filter_has_items=True, has_items=user.get('has_items')))
	#print json.dumps(user)

	#print json.dumps(sm.dates_list(KANOJO_OWNER))
	print(json.dumps(sm.category_dates(8, has_items=[])))

	exit()

	def ordered(obj):
		if isinstance(obj, dict):
			return {k: ordered(v) for k, v in list(obj.items())}
		if isinstance(obj, list):
			return sorted(ordered(x) for x in obj)
		else:
			return obj
	dt_old = sm.item_list_from_categories(k_type, user_level=u_level)
	dt = {
		"code": 200,
		"item_categories": [
			{
				"items": [
					{
						"description": "Any KANOJOs love flowers. This item may increase KANOJO's love level.",
						"title": "A bunch of flowers",
						"price": "Price: 25B Coins",
						"image_url": "http://www.barcodekanojo.com/images/api/item/basic/gift_flower.png",
						"item_id": 1,
						"image_thumbnail_url": "http://www.barcodekanojo.com/images/api/item/basic/gift_flower_thm.png"},
					{
						"description": "A bit fancy gift. This item may increase KANOJO's love level.",
						"title": "Perfume",
						"price": "Price: 40B Coins",
						"image_url": "http://www.barcodekanojo.com/images/api/item/basic/gift_perfume.png",
						"item_id": 2,
						"image_thumbnail_url": "http://www.barcodekanojo.com/images/api/item/basic/gift_perfume_thm.png"}],
				"level": 1,
				"title": "B coin"},
			{
				"items": [
					{
						"category_id": 6,
						"image_thumbnail_url": "http://www.barcodekanojo.com/images/api/item/category/thm/wardrobe_thm.png",
						"description": "Buy clothes to your Kanojo or friends for present!",
						"expand_flag": 0,
						"title": "Clothes"},
					{
						"category_id": 24,
						"image_thumbnail_url": "http://www.barcodekanojo.com/images/api/item/category/thm/category_glasses.png",
						"description": "Be more fashionable with glasses! Give it to her now!",
						"expand_flag": 0,
						"title": "EyeWear"},
					{
						"category_id": 46,
						"image_thumbnail_url": "http://www.barcodekanojo.com/images/api/item/consumption/thm/item_bcoin_thm.png",
						"description": "B coin",
						"expand_flag": 0,
						"title": "B COIN"},
					{
						"category_id": 44,
						"image_thumbnail_url": "http://www.barcodekanojo.com/images/api/item/consumption/thm/item_permanant_kanojo_thm.png",
						"description": "Wedding Ware For Permanent Kanojo",
						"expand_flag": 1,
						"title": "Wedding Ware"}],
				"title": "Wardrobe"},
			{
				"items": [
					{
						"category_id": 7,
						"image_thumbnail_url": "http://www.barcodekanojo.com/images/api/item/category/thm/drink_energy_thm.png",
						"description": "Gain your Stamina.",
						"expand_flag": 0,
						"title": "Energy Drinks"
					}
				],
				"title": "Portion"
			},
			{
				"items": [
					{
						"category_id": 8,
						"image_thumbnail_url": "http://www.barcodekanojo.com/images/api/item/category/thm/letter_goodbye_thm.png",
						"description": "To dump your Kanojo...",
						"expand_flag": 0,
						"title": "Goodbye Letter"
					}
				],
				"title": "Other"}]}
	print('Сomparison:', ordered(dt) == ordered(dt_old))
	#print json.dumps(dt_old)

