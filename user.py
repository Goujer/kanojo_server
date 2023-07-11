#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'Andrey Derevyagin'
__copyright__ = 'Copyright © 2014-2015'

#Library imports
import copy
import pymongo.errors
import math
import random
import time

from collections import OrderedDict
from functools import cmp_to_key
from pymongo import MongoClient

#Imports from local
import config

from constants import *
from images import save_user_profile_image

CLEAR_NONE = 0
CLEAR_SELF = 1
CLEAR_OTHER = 2

def user_order_dict_cmp(x, y):
	order = ('money', 'sex', 'birth_day', 'enemy_count', 'id', 'relation_status','kanojo_count', 'stamina', 'birth_month', 'email', 'birth_year', 'friend_count', 'stamina_max', 'generate_count', 'profile_image_url', 'password', 'tickets', 'name', 'language', 'level', 'scan_count', )
	x,y = x[0], y[0]
	if x in order and y in order:
		return order.index(x)-order.index(y)
	elif x in order:
		return -1
	elif y in order:
		return 1
	return (x > y) - (x < y)

class UserManager(object):
	"""docstring for UserManager"""
	def __init__(self, db=None, server=None, kanojo_manager=None, store=None, activity_manager=None):
		super(UserManager, self).__init__()
		self.db = db
		self.server = server
		self.kanojo_manager = kanojo_manager
		self.store = store
		self.activity_manager = activity_manager
		self.last_uid = 1
		if self.db and self.db.seqs.find_one({ 'collection': 'users' }) is None:
			self.db.seqs.insert({
					'collection': 'users',
					'id': 0
				})

	def create(self, uuid, name, password, email, birthday, sex, profile_image_data):
		if self.db:
			uid = self.db.seqs.find_and_modify(
					query = {'collection': 'users'},
					update = {'$inc': {'id': 1}},
					fields = {'id': 1, '_id': 0},
					new = True
				)
			uid = uid.get('id', -1) if uid else -2
			while self.db.users.find_one({'id': uid}):
				uid += 1
		else:
			uid = self.last_uid
			self.last_uid += 1
		tm = int(time.time())
		if name == "":
			name = generate_name()
		user = {
				"create_time": tm,
				"last_login": tm,
				"birthday": birthday,
				"id": uid,
				"uuid": uuid,
				"name": name,
				"level": 1,
				"money": 1000,
				"stamina": 100,
				"email": email,
				"profile_image_url": None,
				"tickets": 20,
				"language": "en",
				"scan_count": 0,
				"generate_count": 0,
				"password": password,
				#"stamina_max": 1080,
				#"relation_status": 2,
				#"birth_day": 27,
				#"birth_month": 7,
				#"birth_year": 2014,
				#"friend_count": 11660,
				#"enemy_count": 4839,
				#"kanojo_count": 351,
				"kanojos": [],
				"friends": [],
				"enemies": [],
				"likes": [],
				# ----
				#"stamina_recover_index": (tm % 86400) / 60
			}
		if self.db:
			try:
				self.db.users.insert(user)
				self.last_uid = uid
			except pymongo.errors.DuplicateKeyError:
				return self.create(name, password, email, birthday, sex, profile_image_data)

			if self.activity_manager:
				self.activity_manager.create({
						'activity_type': ACTIVITY_JOINED,
						'user': user,
					})
			if profile_image_data:
				save_user_profile_image(profile_image_data.stream, uid)
		return user

	def save(self, user):
		if user and '_id' in user and self.db:
			return self.db.users.save(user)
		return False

	@property
	def default_user(self):
		return {"generate_count": 0,
				"language": "ja",
				"level": 1,
				"kanojo_count": 0,
				"money": 100,
				"birth_month": 10,
				"stamina_max": 100,
				"profile_image_url": None,
				"stamina": 100,
				"money_max": 100,
				"scan_count": 0,
				"birth_day": 25,
				"enemy_count": 0,
				"wish_count": 0,
				"id": 0,
				"name": 'unknown'}

	def fill_fields(self, usr):
		usr['stamina_max'] = (usr.get('level', 0) + 9) * 10
		dt = time.gmtime(usr.get('birthday', 0))
		usr['birth_day'] = dt.tm_mday
		usr['birth_month'] = dt.tm_mon
		usr['birth_year'] = dt.tm_year
		usr['kanojo_count'] = len(usr.get('kanojos', []))
		usr['friend_count'] = len(usr.get('friends', []))
		usr['enemy_count'] = len(usr.get('enemies', []))
		if not usr.get('profile_image_url'):
			usr['profile_image_url'] = 'http://bk-dump.herokuapp.com/images/common/no_pictire_available.png'
		return usr

	def clear(self, usr, clear, self_uid=None, self_user=None):
		if usr is None:
			# TODO: maybe should return something else?
			return usr
		if clear == CLEAR_NONE:
			tmp_user = copy.copy(usr)
			self.fill_fields(tmp_user)
			return tmp_user
		else:
			tmp_user = copy.copy(usr)
			self.fill_fields(tmp_user)
			allow_keys = ['id', 'name', 'level', 'money', 'sex', 'stamina', 'profile_image_url', 'scan_count', 'stamina_max', 'relation_status', 'kanojo_count', 'friend_count', 'enemy_count', 'generate_count']
			if clear == CLEAR_SELF:
				allow_keys.extend(['tickets', 'language', 'birth_day', 'birth_month', 'birth_year', 'description'])
				if self_uid is None:
					self_uid = tmp_user.get('id')
			rv = { key: tmp_user[key] for key in allow_keys if key in tmp_user }
			if self_uid:
				if self_uid == tmp_user.get('id'):
					rv['relation_status'] = USER_RELATION_SELF
				else:
					self_user = self.user(uid=self_uid, clear=CLEAR_NONE)
			if self_user:
				rv['relation_status'] = USER_RELATION_SELF if self_user.get('id') == tmp_user.get('id') else USER_RELATION_ENEMY if tmp_user.get('id') in self_user.get('enemies') else USER_RELATION_OTHER
			return OrderedDict(sorted(list(rv.items()), key=cmp_to_key(user_order_dict_cmp)))

	def login(self, uuid, email=None, password=None):
		query = {
			"uuid": {
				"$exists": True,
				"$eq": uuid
			}
		}
		user = self.db.users.find_one(query)
		if user:
			# TODO This will need to be removed after enough user migration
			last_login = user.get('last_login', 0)
			if last_login == 0:
				user['last_login'] = int(time.time())
				self.save(user)
			#End of TODO
			if time.time() - user.get('last_login', 0) > 31556952: #Seconds in a year
				return None
			else:
				user['last_login'] = int(time.time())
				self.save(user)
		elif email and password:
			query = {
				"$and": [
					{"email": {
						"$exists": True,
						"$eq": email
					}},
					{"password": {
						"$exists": True,
						"$eq": password.capitalize()
					}}
				]
			}
			user = self.db.users.find_one(query)
			if user:
				user['uuid'] = uuid
				user['last_login'] = time.time()
				self.save(user)
			else:
				return None
		if not user:
			return None
		else:
			return self.clear(user, clear=CLEAR_SELF, self_uid=None, self_user=None)

	def user(self, uuid=None, uid=None, self_uid=None, self_user=None, clear=CLEAR_SELF, email=None, password=None):
		if not self.db:
			return None
		if uid:
			query = { "id": uid }
			user = self.db.users.find_one(query)
		elif uuid:
			query = {
				"uuid": {
					"$exists": True,
					"$eq": uuid
				}
			}
			user = self.db.users.find_one(query)
			if (not user) and email and password:
				query = {
						"$and": [
							{"email": {
								"$exists": True,
								"$eq": email
							}},
							{"password": {
								"$exists": True,
								"$eq": password.capitalize()
							}}
						]
					}
				user = self.db.users.find_one(query)
				if user:
					user['uuid'] = uuid
					self.save(user)
				else:
					return None
		else:
			return None
		return self.clear(user, clear=clear, self_uid=self_uid, self_user=self_user)

	def users(self, ids, self_uid=None, self_user=None):
		tmp_ids = list(ids)
		if self_user is None and self_uid is not None and self_uid not in ids:
			tmp_ids.append(self_uid)
		query = { "id": { '$in': tmp_ids } }
		rv = []
		for u in self.db.users.find(query):
			rv.append(u)
			if self_user is None and self_uid is not None and u.get('id') == self_uid:
				self_user = copy.copy(u)
		rv = [self.clear(u, clear=CLEAR_OTHER, self_user=self_user) for u in rv]
		return rv

	def add_kanojo_as_friend(self, user, kanojo, increment_scan_couner=True, update_db_record=True):
		uid = user.get('id')
		if uid not in kanojo.get('followers'):
			kanojo['followers'].append(uid)
			if increment_scan_couner and self.kanojo_manager:
				self.kanojo_manager.increment_scan_counter(kanojo, update_db_record=update_db_record)
			elif update_db_record:
				self.kanojo_manager.save(kanojo)
		if kanojo.get('id') not in user.get('friends'):
			#user['friends'].append(kanojo['id'])
			user['friends'].insert(0, kanojo.get('id'))
			self.user_change(user, stamina_change=5, money_change=-25, update_db_record=False)
			if increment_scan_couner:
				self.increment_scan_couner(user, update_db_record=False)
			if update_db_record:
				self.save(user)
				self.kanojo_manager.save(kanojo)
			if self.activity_manager:
				self.activity_manager.create({
						'activity_type': ACTIVITY_ME_ADD_FRIEND,
						'user': user,
						'kanojo': kanojo,
						'other_user': kanojo.get('owner_user_id')
					})

	def add_user_as_enemy(self, user, enemy_user_or_id=0, update_db_record=False):
		enemy_uid = enemy_user_or_id
		if isinstance(enemy_uid, dict):
			enemy_uid = enemy_uid.get('id', 0)
		rv = False
		if enemy_uid > 0:
			enemies = user.get('enemies', [])
			if enemy_uid not in enemies:
				enemies.insert(0, enemy_uid)
				user['enemies'] = enemies
				rv = True
				if update_db_record:
					self.save(user)

				if self.activity_manager:
					self.activity_manager.create({
							'activity_type': ACTIVITY_ADD_AS_ENEMY,
							'user': user,
							'other_user': enemy_uid,
						})
		return rv

	def create_kanojo_from_barcode(self, user, barcode_info, params):
		if user.get('stamina') < 20:
			return False
		kanojo = self.kanojo_manager.create(barcode_info, params, user)
		if kanojo:
			try:
				user['generate_count'] = int(user.get('generate_count', 0)) + 1
			except ValueError as e:
				pass
			k = user.get('kanojos', [])
			#k.append(kanojo.get('id'))
			k.insert(0, kanojo.get('id'))
			user['kanojos'] = k
			self.user_change(user, stamina_change=20, money_change=-100, update_db_record=False)
			self.increment_scan_couner(user, update_db_record=True)

			if self.activity_manager:
				self.activity_manager.create({
						'activity_type': ACTIVITY_GENERATED,
						'user': user,
						'kanojo': kanojo,
					})
		return kanojo

	# x = lambda y: int(math.floor((2*math.sqrt(3)*math.sqrt(5*y+3888)-216)/5+1))
	# y = FLOOR(A3*(7.2+A3/12))
	# x - level, y - scan count 
	def increment_scan_couner(self, user, inc_value=1, update_db_record=False):
		user['scan_count'] = user.get('scan_count', 0) + inc_value
		lvl = int(math.floor((2*math.sqrt(3)*math.sqrt(5*user['scan_count']+3888)-216)/5+1))
		if user.get('level') < lvl:
			lvl_diff = lvl - user.get('level', 0)
			user['level'] = lvl
			self.user_change(user, money_change=-lvl_diff*1000, up_stamina=True, update_db_record=False)

			if self.activity_manager:
				self.activity_manager.create({
						'activity_type': ACTIVITY_BECOME_NEW_LEVEL,
						'user': user,
						'activity': '{user_name} became Lev.\"' + str(lvl) + '\".'
					})
		if update_db_record:
			self.save(user)

	def scan_kanojo(self, user, kanojo):
		kid = kanojo.get('id')
		if kid in user.get('kanojos'):
			user['kanojos'].insert(0, user['kanojos'].pop(user['kanojos'].index(kid)))
		if kid in user.get('friends'):
			user['friends'].insert(0, user['friends'].pop(user['friends'].index(kid)))
		self.increment_scan_couner(user, update_db_record=True)
		self.kanojo_manager.increment_scan_counter(kanojo, update_db_record=True)

	def set_like(self, user, kanojo, like_value, update_db_record=False):
		self.kanojo_manager.set_like(kanojo, like_value, user, update_db_record=update_db_record)
		changed = False
		like_kanojos = user.get('likes', [])
		kid = kanojo.get('id')
		if like_value:
			if kid not in like_kanojos:
				like_kanojos.insert(0, kid)
				user['likes'] = like_kanojos
				changed = True
		else:
			if kid in like_kanojos:
				like_kanojos.remove(kid)
				user['likes'] = like_kanojos
				changed = True
		if changed and update_db_record:
			return self.save(user)
		return changed

	def user_items(self, user):
		return user.get('has_items', [])

	def add_store_item(self, user, store_item):
		'''
			only add store item to user dict (tickets not changed)
		'''
		units = store_item.get('buy_units', 1)
		store_item_id = store_item.get('base_store_item_id', store_item.get('item_id'))
		has_items = user.get('has_items', [])
		_itm = [el for el in has_items if el.get('store_item_id')==store_item_id]
		if len(_itm):
			_itm = _itm[0]
			_itm['units'] = _itm.get('units', 1) + units
		else:
			_itm = { 
				'store_item_id': store_item.get('base_store_item_id', store_item.get('item_id'))
			}
			if units != 1:
				_itm['units'] = units
			has_items.append(_itm)
		user['has_items'] = has_items
		self.save(user)
		return _itm

	def give_present(self, user, kanojo, store_item_id):
		has_item = [x for x in user.get('has_items', []) if x.get('store_item_id')==store_item_id]
		if len(has_item) and has_item[0].get('units', 1) >= 1:
			has_item = has_item[0]
			rv = { 'code': 200 }
			store_item = self.store.get_item(store_item_id)

			relation_status = self.kanojo_manager.relation_status(kanojo, user)
			if 'clothes_item_id' in store_item:
				weight_mult = 1 if relation_status==2 else 0.35
				self.kanojo_manager.add_clothes(kanojo, clothes_type=store_item.get('clothes_item_id'), like_weight_mult=weight_mult)

				action_dict = self.kanojo_manager.user_do_gift_calc_kanojo_love_increment(kanojo, user, store_item, is_extended=True)
				self.check_approached_kanojo(user, kanojo, action_dict.get('info', {}))
				rv.update(action_dict)

			if 'action' in store_item:
				if store_item.get('action') == 'dump_kanojo':
					rv.update(self.kanojo_manager.user_breakup_with_kanojo_alert(kanojo))
					self.breakup_with_kanojo(user, kanojo)

					if self.activity_manager:
						self.activity_manager.create({
								'activity_type': ACTIVITY_BREAKUP,
								'user': user,
								'kanojo': kanojo,
								#'activity': '{user_name} break up with '
							})
					kanojo = None


			if not rv.get('info', {}).get('busy'):
				if has_item.get('units', 1)==1:
					user['has_items'].remove(has_item)
				else:
					has_item['units'] -= 1
				self.kanojo_manager.save(kanojo)
				self.save(user)
		else:
			rv = {
				"code": 404,
				"alerts": [ { "body": "The Requested Item was not found.", "title": "" } ]
			}
		return rv

	def do_date(self, user, kanojo, store_item_id):
		has_item = [x for x in user.get('has_items', []) if x.get('store_item_id')==store_item_id]
		if len(has_item) and has_item[0].get('units', 1) >= 1:
			has_item = has_item[0]
			rv = { 'code': 200 }
			store_item = self.store.get_date(store_item_id)

			action_dict = self.kanojo_manager.user_do_date_calc_kanojo_love_increment(kanojo, user, store_item, is_extended=True)
			self.kanojo_manager.apply_date(kanojo, store_item)

			self.check_approached_kanojo(user, kanojo, action_dict.get('info', {}))

			rv.update(action_dict)

			if not rv.get('info', {}).get('busy'):
				if has_item.get('units', 1)==1:
					user['has_items'].remove(has_item)
				else:
					has_item['units'] -= 1
				self.kanojo_manager.save(kanojo)
				self.save(user)
		else:
			rv = {
				"code": 404,
				"alerts": [ { "body": "The Requested Item was not found.", "title": "" } ]
			}
		return rv

	def user_change(self, user, stamina_change=0, money_change=0, tickets_change=0, up_stamina=False, update_db_record=True):
		'''
			change user stamina/money/tickets
		'''
		if stamina_change:
			if user.get('stamina', 0) < stamina_change:
				return False
			user['stamina'] = user.get('stamina', 0) - stamina_change
		if money_change:
			if user.get('money', 0) < money_change:
				return False
			user['money'] = user.get('money', 0) - money_change
		if tickets_change:
			if user.get('tickets', 0) < tickets_change:
				return False
			user['tickets'] = user.get('tickets', 0) - tickets_change
		if up_stamina:
			stamina_max = (user.get('level', 0) + 9) * 10
			if user.get('stamina', 0) >= stamina_max:
				return False
			else:
				user['stamina'] += 1
		if update_db_record:
			self.save(user)
		return user

	def check_approached_kanojo(self, user, kanojo, kanojo_love_increment_info, current_owner=None):
		if kanojo is None:
			return None
		# if action at not my kanojo
		if user.get('id') != kanojo.get('owner_user_id'):
			#print user, kanojo, kanojo_love_increment_info
			if not kanojo_love_increment_info.get('busy') and self.activity_manager:

				self.add_user_as_enemy(user, kanojo.get('owner_user_id'))

				self.activity_manager.create({
						'activity_type': ACTIVITY_APPROACH_KANOJO,
						'user': user,
						'kanojo': kanojo,
						'other_user': kanojo.get('owner_user_id')
					})
		if kanojo_love_increment_info.get('change_owner'):
			if not current_owner:
				owner_id = kanojo.get('owner_user_id')
				if owner_id > 0:
					current_owner = self.user(uid=owner_id, clear=CLEAR_NONE)
			if current_owner:
				try:
					current_owner['kanojos'].remove(kanojo.get('id'))
					kanojo['followers'].remove(current_owner.get('id'))
				except ValueError as e:
					pass
				self.save(current_owner)
			try:
				user['friends'].remove(kanojo.get('id'))
			except Exception as e:
				pass
			kanojo['owner_user_id'] = user.get('id')
			user['kanojos'].insert(0, kanojo.get('id'))

			if self.activity_manager:
				self.activity_manager.create({
						'activity_type': ACTIVITY_ME_STOLE_KANOJO,
						'user': user,
						'kanojo': kanojo,
						'other_user': current_owner
					})
		return kanojo_love_increment_info.get('change_owner')

	def user_action(self, user, kanojo, action_string=None, do_gift=None, do_date=None, is_extended_action=False, current_owner=None):
		'''
			is_extended_action - for extended gifts and dates
		'''
		if not self.kanojo_manager:
			return { "code": 500, "love_increment": { "alertShow": 1 }, "alerts": [ { "body": "Server error.", "title": "" } ] }

		# check if user can use this action
		store_item = None
		if action_string:
			price = self.kanojo_manager.user_action_price(action_string)
			#if not price:
			#    return False
		elif do_gift:
			store_item = self.store.get_item(do_gift)
			price = store_item
		elif do_date:
			store_item = self.store.get_date(do_date)
			price = store_item
		else:
			return { "code": 500, "love_increment": { "alertShow": 1 }, "alerts": [ { "body": "Server error.", "title": "" } ] }

		#Have the stats to preform action?
		if user.get('stamina') < price.get('price_s', 0):
			return { "code": 403, "love_increment": { "alertShow": 1 }, "alerts": [ { "body": "You don't have enough stamina.", "title": "" } ] }
		if user.get('money') < price.get('price_b', 0):
			return { "code": 403, "love_increment": { "alertShow": 1 }, "alerts": [ { "body": "You don't have enough money.", "title": "" } ] }
		if user.get('tickets') < price.get('price_t', 0):
			return { "code": 403, "love_increment": { "alertShow": 1 }, "alerts": [ { "body": "You don't have enough tickets.", "title": "" } ] }
		if user.get('level') < price.get('level', 0):
			return { "code": 403, "love_increment": { "alertShow": 1 }, "alerts": [ { "body": "You level to low.", "title": "" } ] }

		# do action
		rv = { 'code': 200 }
		if action_string:
			action_dict = self.kanojo_manager.user_action(kanojo, user, action_string)
			rv.update(action_dict)
		elif do_gift:
			if is_extended_action:
				action_dict = self.add_store_item(user, store_item)
				if action_dict:
					if store_item.get('buy_units', 1) == 1:
						body_str = "%s was added to your item list."%store_item.get('title')
					else:
						body_str = "%s (x%d) was added to your item list."%(store_item.get('title'), store_item.get('buy_units'))
					action_dict = {
						"data": True,
						"alerts": [
							{
								"body": body_str,
								"title": ""
							}
						]
					}
				else:
					action_dict = { 'data': False, 'code': 404 }
				rv.update(action_dict)
			else:
				action_dict = self.kanojo_manager.user_do_gift_calc_kanojo_love_increment(kanojo, user, store_item, is_extended=is_extended_action)
				rv.update(action_dict)
		elif do_date:
			if is_extended_action:
				action_dict = self.add_store_item(user, store_item)
				if action_dict:
					if store_item.get('buy_units', 1) == 1:
						body_str = "%s was added to your item list."%store_item.get('title')
					else:
						body_str = "%s (x%d) was added to your item list."%(store_item.get('title'), store_item.get('buy_units'))
					action_dict = {
						"data": True,
						"alerts": [
							{
								"body": body_str,
								"title": ""
							}
						]
					}
				else:
					action_dict = { 'data': False, 'code': 404 }
				rv.update(action_dict)
			else:
				action_dict = self.kanojo_manager.user_do_date_calc_kanojo_love_increment(kanojo, user, store_item, is_extended=is_extended_action)
				rv.update(action_dict)

		self.check_approached_kanojo(user, kanojo, rv.get('info', {}), current_owner=current_owner)

		self.kanojo_manager.save(kanojo)
		if not rv.get('info', {}).get('busy'):
			self.user_change(user, stamina_change=price.get('price_s', 0), money_change=price.get('price_b', 0), tickets_change=price.get('price_t', 0), update_db_record=True)
		return rv

	def breakup_with_kanojo(self, user, kanojo, update_db_record=True):
		kid = kanojo.get('id')
		uid = user.get('id')
		if kid in user.get('kanojos', []):
			user['kanojos'].remove(kid)
		if kid in user.get('friends', []):
			user['friends'].remove(kid)
		if uid in kanojo.get('followers', []):
			kanojo['followers'].remove(uid)
			if kanojo.get('owner_user_id') == uid:
				kanojo['owner_user_id'] = 0
		if update_db_record:
			if len(kanojo.get('followers')):
				self.kanojo_manager.save(kanojo)
			else:

				self.kanojo_manager.save(kanojo)
				#self.kanojo_manager.delete(kanojo)
			self.save(user)

	def delete_user(self, uid):
		user = self.user(uid=uid, clear=CLEAR_NONE)
		if user:
			#Clear Likes
			for kid in user.get('likes', []):
				kanojo = self.kanojo_manager.kanojo(kid, '', clear=CLEAR_NONE)
				if uid in kanojo.get('likes', []):
					kanojo['likes'].remove(uid)
					self.kanojo_manager.save(kanojo)
			#Clear Kanojos
			for kid in user.get('kanojos', []):
				kanojo = self.kanojo_manager.kanojo(kid, '', clear=CLEAR_NONE)
				self.breakup_with_kanojo(user, kanojo)
			#Remove enemies
			for other_user in self.db.users.find():
				if uid in other_user.get('enemies', []):
					other_user['enemies'].remove(uid)
					self.save(other_user)
			result = self.db.users.delete_one({"id": uid})
			if result.acknowledged and result.deleted_count > 0:
				return self.clear(user, clear=CLEAR_SELF)
		return False

def generate_name():
	colors = ('Aqua', 'Aquamarine', 'Azure', 'Beige', 'Bisque', 'Black', 'Blue', 'Brown', 'Burlywood', 'Chartreuse',
			  'Chocolate', 'Coral', 'Cornflower', 'Cornsilk', 'Crimson', 'Cyan', 'Firebrick', 'Fuchsia', 'Gainsboro',
			  'Gold', 'Goldenrod', 'Gray', 'Green', 'Honeydew', 'Indigo', 'Ivory', 'Khaki', 'Lavender', 'Lime', 'Linen',
			  'Magenta', 'Maroon', 'Moccasin', 'Olive', 'Orange', 'Orchid', 'Peru', 'Pink', 'Plum', 'Purple', 'Red',
			  'Salmon', 'Seashell', 'Sienna', 'Silver', 'Snow', 'Tan', 'Teal', 'Thistle', 'Tomato', 'Turquoise',
			  'Violet', 'Wheat', 'White', 'Yellow')
	fruits = ('Apple', 'Apricot', 'Avocado', 'Banana', 'Bilberry', 'Blackberry', 'Blackcurrant', 'Blueberry',
			  'Boysenberry', 'Cantaloupe', 'Currant', 'Cherry', 'Cherimoya', 'Cloudberry', 'Coconut', 'Cranberry',
			  'Damson', 'Date', 'Dragonfruit', 'Durian', 'Elderberry', 'Feijoa', 'Fig', 'Goji berry', 'Gooseberry',
			  'Grape', 'Grapefruit', 'Guava', 'Huckleberry', 'Jabouticaba', 'Jackfruit', 'Jambul', 'Jujube', 'Kiwi',
			  'Kumquat', 'Lemon', 'Lime', 'Loquat', 'Lychee', 'Mango', 'Melon', 'Miracle fruit', 'Mulberry',
			  'Nectarine', 'Olive', 'Papaya', 'Passionfruit', 'Peach', 'Pear', 'Persimmon', 'Physalis', 'Plum',
			  'Pineapple', 'Pomegranate', 'Pomelo', 'Quince', 'Raspberry', 'Rambutan', 'Redcurrant', 'Satsuma',
			  'Strawberry')
	return f'{random.choice(colors)} {random.choice(fruits)}'

if __name__ == "__main__":
	mdb_connection_string = config.MDB_CONNECTION_STRING
	db_name = mdb_connection_string.split('/')[-1]
	db = MongoClient(mdb_connection_string)[db_name]

	u = UserManager(db)
	print(generate_name())
	#u.create('~')

	import json
	'''
	user = u.user(uid=1, clear=CLEAR_NONE)
	user.pop('_id', None)
	print json.dumps(user)
	'''
	print(json.dumps(u.users([1,2], self_uid=1)))
