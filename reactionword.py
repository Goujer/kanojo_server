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

	def reactionword_json(self, a, pod):
		itms = [x for x in self._items if a in x.get('a') and ('pod' not in x or pod in x.get('pod'))]
		if len(itms):
			itm = random.choice(itms)
			return itm.get('data')
		else:
			return json.dumps(["…",])
