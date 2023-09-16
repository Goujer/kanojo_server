#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'Andrey Derevyagin'
__copyright__ = 'Copyright © 2015'

import json
import unittest

from reactionword import ReactionwordManager

class ReactionwordTest(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(ReactionwordTest, self).__init__(*args, **kwargs)
        self.rw = ReactionwordManager()

    def test_out(self):
        #for a in [1,2,3,4, 10,11,12,20,21]:
        for a in [1,2,3, 10,11,12,20,21]:
            for pod in range(4):
                reactionword = json.loads(self.rw.reactionword_json(a, pod))
                self.assertGreater(len(reactionword), 1)

if __name__ == '__main__':
	unittest.main()(venv)