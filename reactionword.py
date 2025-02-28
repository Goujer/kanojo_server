#!/usr/bin/env python
# -*- coding: utf-8 -*-

__version__ = '0.1'
__author__ = 'Andrey Derevyagin'
__copyright__ = 'Copyright © 2015'

import json
import random

class ReactionwordManager(object):
	"""docstring for ReactionwordManager"""
	def __init__(self, reactionword_file='reactionword.json'):
		tmp = json.load(open(reactionword_file, encoding='utf-8'))
		self._items = tmp.get('reactionword')

	#TODO Add Reaction Words from recovered media

	'''
		a - action param
			1 - gift to kanojo
			2 - extended gift
			3 - date
			4 - extended date (not use)
			10,11,12 - main touch action
			20,21 - main touch by stamina action 
		pod - part of day param
			0 - night
			1 - morning
			2 - day
			3 - evening
	'''
	def reactionword_json(self, actions: list[int], pod: int):
		itms = [x for x in self._items for a in actions if a in x.get('a') and ('pod' not in x or pod in x.get('pod'))]
		if len(itms):
			itm = random.choice(itms)
			val = itm.get('data')
		else:
			val = ["Umm, the server messed up", "I don't know what to say, sorry", "Ask Goujer for help please."]

		return {"text": val,
				"btn_text": "Next"}
