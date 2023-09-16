#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'Andrey Derevyagin'
__copyright__ = 'Copyright © 2015'

import copy
import pymongo.errors
import time

from html import escape

from kanojo import as_product

from constants import *

CLEAR_NONE = 0
CLEAR_SELF = 1

FILL_TYPE_PLAIN = 0
FILL_TYPE_HTML = 1

ALL_ACTIVITIES = (ACTIVITY_SCAN, ACTIVITY_GENERATED, ACTIVITY_ME_ADD_FRIEND, ACTIVITY_APPROACH_KANOJO, ACTIVITY_ME_STOLE_KANOJO, ACTIVITY_MY_KANOJO_STOLEN, ACTIVITY_MY_KANOJO_ADDED_TO_FRIENDS, ACTIVITY_BECOME_NEW_LEVEL, ACTIVITY_MARRIED, ACTIVITY_JOINED, ACTIVITY_BREAKUP)

class ActivityManager(object):
	"""docstring for ActivityManager"""
	def __init__(self, db=None):
		super(ActivityManager, self).__init__()
		self._db = db
		self.last_aid = 1
		if self._db and self._db.seqs.find_one({ 'collection': 'activities' }) is None:
			self._db.seqs.insert({
				'collection': 'activities',
				'id': 0
			})

	def create(self, activity_info):
		'''
				{
					'kanojo': null,
					'product': null,
					'user': null,
					'other_user': null,
					'activity': 'human readeble string',
					'created_timestamp': 0,
					'id': 0,
					'activity_type': 0
				}
		'''
		activity_required_fields = ['activity_type', ]
		for key in activity_required_fields:
			if key not in activity_info:
				print('Error: "%s" key not found in activity'%key)
				return None

		if self._db:
			aid = self._db.seqs.find_and_modify(
				query = {'collection': 'activities'},
				update = {'$inc': {'id': 1}},
				fields = {'id': 1, '_id': 0},
				new = True
			)
			aid = aid.get('id', -1) if aid else -2
			while self._db.activity.find_one({'id': aid}):
				aid += 1
		else:
			aid = self.last_aid
			self.last_aid += 1

		activity = { key: activity_info[key] for key in activity_required_fields }

		activity['id'] = aid
		activity['created_timestamp'] = int(time.time())
		if 'user' in activity_info:
			if isinstance(activity_info.get('user'), dict):
				activity['user'] = activity_info.get('user').get('id')
			else:
				activity['user'] = activity_info.get('user')
		if 'other_user' in activity_info:
			if isinstance(activity_info.get('other_user'), dict):
				activity['other_user'] = activity_info.get('other_user').get('id')
			else:
				activity['other_user'] = activity_info.get('other_user')

		if 'kanojo' in activity_info:
			if isinstance(activity_info.get('kanojo'), dict):
				activity['kanojo'] = activity_info.get('kanojo').get('id')
			else:
				activity['kanojo'] = activity_info.get('kanojo')

		if 'product' in activity_info:
			activity['product'] = activity_info.get('product')

		if 'activity' in activity_info:
			activity['activity'] = activity_info.get('activity')

		if self._db:
			try:
				self._db.activity.insert(activity)
				self.last_aid = aid
			except pymongo.errors.DuplicateKeyError as e:
				return self.create(activity_info)
		return activity

	def clear(self, activity, clear=CLEAR_SELF, user_id=None):
		if activity is None:
			# TODO: maybe should return something else?
			return activity
		if activity == CLEAR_NONE:
			return activity

		allow_keys = ('kanojo', 'product', 'user', 'other_user', 'activity', 'created_timestamp', 'id', 'activity_type', 'activity_type2', )
		rv = { key: activity[key] for key in allow_keys if key in activity }

		if user_id and rv.get('activity_type') == ACTIVITY_ME_STOLE_KANOJO and rv.get('other_user') == user_id:
			rv['activity_type'] = ACTIVITY_MY_KANOJO_STOLEN

		if user_id and rv.get('activity_type') == ACTIVITY_ME_ADD_FRIEND and rv.get('other_user') == user_id:
			rv['activity_type'] = ACTIVITY_MY_KANOJO_ADDED_TO_FRIENDS
			#(rv['user'], rv['other_user']) = (rv.get('other_user'), rv.get('user'))

		# exchange user and other_user
		if rv.get('activity_type') in [ACTIVITY_APPROACH_KANOJO, ACTIVITY_MY_KANOJO_STOLEN, ACTIVITY_MY_KANOJO_ADDED_TO_FRIENDS]:
			(rv['user'], rv['other_user']) = (rv.get('other_user'), rv.get('user'))

		if 'activity' not in rv:
			at = rv.get('activity_type')
			if ACTIVITY_SCAN == at:
				human_time = time.strftime("%d %b %Y %H:%M:%S", time.localtime(rv.get('created_timestamp')))
				rv['activity'] = '{user_name} has scanned on ' + human_time + '.'
			elif ACTIVITY_GENERATED == at:
				rv['activity'] = '{kanojo_name} was generated from {product_name} in {nationality}.'
			elif ACTIVITY_ME_ADD_FRIEND == at:
				rv['activity'] = '{user_name} added {kanojo_name} to friend list.'
			elif ACTIVITY_APPROACH_KANOJO == at:
				rv['activity'] = '{other_user_name} approached {kanojo_name}.'
			elif ACTIVITY_ME_STOLE_KANOJO == at:
				rv['activity'] = '{user_name} stole {kanojo_name} from {other_user_name}.'
			elif ACTIVITY_MY_KANOJO_STOLEN == at:
				rv['activity'] = '{kanojo_name} was stolen by {other_user_name}.'
			elif ACTIVITY_MY_KANOJO_ADDED_TO_FRIENDS == at:
				rv['activity'] = '{other_user_name} added {kanojo_name} to friend list.'
			elif ACTIVITY_BECOME_NEW_LEVEL == at:
				rv['activity'] = '{user_name} became Lev.\"{user_level}\".'
			elif ACTIVITY_MARRIED == at:
				rv['activity'] = '{user_name} get married with {kanojo_name}.'
			elif ACTIVITY_JOINED == at:
				rv['activity'] = '{user_name} has joined.'
			elif ACTIVITY_BREAKUP == at:
				rv['activity'] = '{user_name} break up with {kanojo_name}.'
				rv['activity_type'] = ACTIVITY_ME_ADD_FRIEND
				rv['activity_type2'] = ACTIVITY_BREAKUP
			elif ACTIVITY_ADD_AS_ENEMY == at:
				rv['activity'] = '{user_name} added {other_user_name} as enemy.'
		return rv

	def activities_by_query(self, query, skip=0, limit=6, user_id=None):
		if limit > -1:
			iterator = self._db.activity.find(query).sort([('created_timestamp', -1), ('id', -1), ]).skip(skip).limit(limit)
		else:
			iterator = self._db.activity.find(query).sort([('created_timestamp', -1), ('id', -1), ]).skip(skip)
		rv = []
		for a in iterator:
			rv.append(self.clear(a, clear=CLEAR_SELF, user_id=user_id))
		return rv

	def user_activity(self, user_id, skip=0, limit=6):
		rv = []
		if self._db:
			activity_types = copy.copy(list(ALL_ACTIVITIES))
			activity_types.remove(ACTIVITY_APPROACH_KANOJO)
			activity_types.remove(ACTIVITY_JOINED)
			query = {
				'$or': [
					{
						'user': user_id,
						'activity_type': { '$in': activity_types },
					},
					{
						'other_user': user_id,
						'activity_type': { '$in': [ACTIVITY_APPROACH_KANOJO, ACTIVITY_ME_STOLE_KANOJO, ACTIVITY_ME_ADD_FRIEND] },
					}
				],
			}
			rv = self.activities_by_query(query, skip=skip, limit=limit, user_id=user_id)
		return rv

	def user_activities_4html(self, user_id, skip=0, limit=6):
		rv = []
		if self._db:
			activity_types = copy.copy(list(ALL_ACTIVITIES))
			activity_types.remove(ACTIVITY_APPROACH_KANOJO)
			activity_types.remove(ACTIVITY_JOINED)
			activity_types.append(ACTIVITY_ADD_AS_ENEMY)
			query = {
				'$or': [
					{
						'user': user_id,
						'activity_type': { '$in': activity_types },
					},
					{
						'other_user': user_id,
						'activity_type': { '$in': [ACTIVITY_APPROACH_KANOJO, ACTIVITY_ME_STOLE_KANOJO, ACTIVITY_ME_ADD_FRIEND] },
					}
				],
			}
			rv = self.activities_by_query(query, skip=skip, limit=limit, user_id=user_id)
		return rv

	def kanojo_activities_4html(self, kanojo_id, skip=0, limit=6):
		rv = []
		if self._db:
			activity_types = copy.copy(list(ALL_ACTIVITIES))
			query = {
				'$or': [
					{
						'kanojo': kanojo_id,
						'activity_type': { '$in': activity_types },
					}
				],
			}
			rv = self.activities_by_query(query, skip=skip, limit=limit)
		return rv

	def all_activities(self, skip=0, limit=20, since_id=0):
		rv = []
		if self._db:
			activity_types = copy.copy(list(ALL_ACTIVITIES))
			activity_types.remove(ACTIVITY_APPROACH_KANOJO)
			activity_types.remove(ACTIVITY_SCAN)
			activity_types.append(ACTIVITY_ADD_AS_ENEMY)
			query = {
				'activity_type': { '$in': activity_types },
			}
			if since_id > 0:
				query['id'] = { '$gt': since_id }
			rv = self.activities_by_query(query, skip=skip, limit=limit)
		return rv

	def kanojo_ids(self, activities):
		rv = [el.get('kanojo') for el in [a for a in activities if a.get('kanojo')]]
		return list(set(rv))

	def user_ids(self, activities):
		rv = [el.get('user') for el in [a for a in activities if a.get('user')]]
		rv.extend([el.get('other_user') for el in [a for a in activities if a.get('other_user')]])
		return list(set(rv))

	def fill_format_activities(self, activities, fill_type=FILL_TYPE_PLAIN):
		rv = []
		for a in activities:
			f = {}
			if a.get('kanojo'):
				if FILL_TYPE_PLAIN == fill_type:
					f['kanojo_name'] = a['kanojo'].get('name')
					f['product_name'] = a['kanojo'].get('product_name')
					f['nationality'] = a['kanojo'].get('nationality')
				elif FILL_TYPE_HTML == fill_type:
					a['kanojo_url'] = '/kanojo/%d.html'%a['kanojo'].get('id')
					if a['kanojo'].get('id'):
						f['kanojo_name'] = '<a href="%s">%s</a>'%(a['kanojo_url'], escape(a['kanojo'].get('name')))
					else:
						f['kanojo_name'] = '%s'%escape(a['kanojo'].get('name'))
			if a.get('user'):
				if FILL_TYPE_PLAIN == fill_type:
					f['user_name'] = a['user'].get('name')
				elif FILL_TYPE_HTML == fill_type:
					a['user_url'] = '/user/%d.html'%a['user'].get('id')
					if a['user'].get('id'):
						f['user_name'] =  '<a href="%s">%s</a>'%(a['user_url'], escape(a['user'].get('name')))
					else:
						f['user_name'] =  '%s'%escape(a['user'].get('name'))
				f['user_level'] = a['user'].get('level')
			if a.get('other_user'):
				if FILL_TYPE_PLAIN == fill_type:
					f['other_user_name'] = a['other_user'].get('name')
				elif FILL_TYPE_HTML == fill_type:
					a['other_user_url'] = '/user/%d.html'%a['other_user'].get('id')
					if a['other_user'].get('id'):
						f['other_user_name'] =  '<a href="%s">%s</a>'%(a['other_user_url'], escape(a['other_user'].get('name')))
					else:
						f['other_user_name'] = '%s'%escape(a['other_user'].get('name'))
				f['other_user_level'] = a['other_user'].get('level')
			try:
				a['activity'] = a['activity'].format(**f)
			except KeyError as err:
				print('Error in activity format(KeyError): ', err, a)
				continue
			rv.append(a)
		return rv

	def fill_activities(self, activities, users, kanojos, def_user, def_kanojo, fill_type=FILL_TYPE_PLAIN):
		for a in activities:
			if 'kanojo' in a:
				kanojo = next((k for k in kanojos if k.get('id') == a.get('kanojo')), None)
				a['kanojo'] = kanojo if kanojo else def_kanojo
				a['product'] = as_product(kanojo) if kanojo else as_product(def_kanojo)
			if 'user' in a:
				user = next((u for u in users if u.get('id') == a.get('user')), None)
				a['user'] = user if user else def_user
			if 'other_user' in a:
				other_user = next((u for u in users if u.get('id') == a.get('other_user')), None)
				a['other_user'] = other_user if other_user else def_user
		activities = self.fill_format_activities(activities, fill_type=fill_type)
		return activities

	def time_diff(self, tm):
		'@ x day ago'
		return ''
		return '@ %d seconds ago'%tm

	def create_html_block(self, activities_filled):
		if len(activities_filled) == 0:
			return '<h1 class="msg_small_alert">No activitities.</h1>'

		rv = ''
		tm = int(time.time())
		for a in activities_filled:
			# <div class="activities_box" id="activity70"><div class="l_activities_box"><a href="/user/2.html"><img class="icon" height="50" width="50" src="http://gdrive-cdn.herokuapp.com/5594f233507a7e0009dfdd2b/2.jpg"></a></div><div class="r_activities_box"><a href="/kanojo/1.html"><img class="icon" height="50" width="50" src="http://gdrive-cdn.herokuapp.com/549987b3cd22cc00070385a9/best_girl.png"></a></div><div class="c_activities_box"><span html="true"><a href="/user/2.html">Red Pear</a> added <a href="/kanojo/1.html">ヴェルデ</a> to friend list.</span><br><span id="activity70_time" value="1436440765">@ 1 day ago</span></div></div>
			# LEFT
			if a.get('activity_type') in [ACTIVITY_GENERATED, ACTIVITY_MY_KANOJO_STOLEN, ]:
				(url, img) =  (a.get('kanojo_url'), a.get('kanojo', {}).get('profile_image_url'))
			elif a.get('activity_type') in [ACTIVITY_APPROACH_KANOJO, ACTIVITY_MY_KANOJO_ADDED_TO_FRIENDS, ]:
				(url, img) =  (a.get('other_user_url'), a.get('other_user', {}).get('profile_image_url'))
			else:
				(url, img) =  (a.get('user_url'), ''+a.get('user', {}).get('profile_image_url'))
			tmp = '<div class="l_activities_box"><a href="%s"><img class="icon" height="50" width="50" src="%s"></a></div>'%(url, img)

			# RIGHT
			if a.get('activity_type') in [ACTIVITY_ME_ADD_FRIEND, ACTIVITY_ME_STOLE_KANOJO, ACTIVITY_BREAKUP, ACTIVITY_APPROACH_KANOJO, ACTIVITY_MY_KANOJO_ADDED_TO_FRIENDS, ]:
				(url, img) =  (a.get('kanojo_url'), a.get('kanojo', {}).get('profile_image_url'))
			elif a.get('activity_type') in [ACTIVITY_ADD_AS_ENEMY, ACTIVITY_MY_KANOJO_STOLEN, ]:
				(url, img) =  (a.get('other_user_url'), ''+a.get('other_user', {}).get('profile_image_url'))
			else:
				(url, img) = None, None
			if url:
				tmp += '<div class="r_activities_box"><a href="%s"><img class="icon" height="50" width="50" src="%s"></a></div>'%(url, img)

			# CENTER
			tmp += '<div class="c_activities_box"><span html="true">%s</span><br><span id="activity%d_time" value="%d">%s</span></div>'%(a.get('activity'), a.get('id'), a.get('created_timestamp'), self.time_diff(tm - a.get('created_timestamp')))
			rv += '<div class="activities_box" id="activity%d">%s</div>'%(a.get('id'), tmp)
		return rv


if __name__ == "__main__":

	from pymongo import MongoClient
	import config

	mdb_connection_string = config.MDB_CONNECTION_STRING
	db_name = mdb_connection_string.split('/')[-1]
	db = MongoClient(mdb_connection_string)[db_name]

	a = ActivityManager(db)
	#a = ActivityManager()

	'''
	print a.create({
			'activity_type': ACTIVITY_GENERATED,
			'user': 1,
			'kanojo': 1
		})
	'''
	'''
	print a.create({
			'activity_type': ACTIVITY_APPROACH_MY_KANOJO,
			'user': 2,
			'other_user': 1,
			'kanojo': 1
		})
	'''
	print(a.user_activity(2))
	tmp = a.all_activities()
	print(tmp)
	print(a.user_ids(tmp))