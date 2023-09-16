#!/usr/bin/env python
# -*- coding: utf-8 -*-

__version__ = '0.1'
__author__ = 'Andrey Derevyagin'
__copyright__ = 'Copyright © 2015'

import unittest
from activity import ActivityManager, FILL_TYPE_HTML, FILL_TYPE_PLAIN


class ActivityTest(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(ActivityTest, self).__init__(*args, **kwargs)
        self.a = ActivityManager()
        self.activities = [
            {
                "_id": {  "$oid": "558fda9245b41c0bebb59e91" },
                "kanojo": 1,
                "user": 1,
                "created_timestamp": 1435490962,
                "id": 1,
                "activity_type": 2
            },
            {
                "_id": { "$oid": "558ff93b45b41c0c89485ebc" },
                "kanojo": 1,
                "user": 2,
                "other_user": 1,
                "created_timestamp": 1435498811,
                "id": 2,
                "activity_type": 7
            },
            {
                "_id": {  "$oid": "55967c00333b97000afc2ab7" },
                "user": 1,
                "activity_type": 7,
                "other_user": 2,
                "created_timestamp": 1435925504,
                "id": 42,
                "kanojo": 855
            },
            {
                "_id": {  "$oid": "5598fdde219c5f0009c92e2e" },
                "kanojo": 870,
                "id": 57,
                "user": 1,
                "other_user": 0,
                "activity_type": 8,
                "created_timestamp": 1436089822
            }
        ]

    def test_kanojo_and_user_lists(self):
        kanojo_ids = self.a.kanojo_ids(self.activities)
        user_ids = self.a.user_ids(self.activities)
        kanojo_ids_set = set()
        user_ids_set = set()
        for a in self.activities:
            if a.get('kanojo'):
                kanojo_ids_set.add(a['kanojo'])
            if a.get('user'):
                user_ids_set.add(a['user'])
            if a.get('other_user'):
                user_ids_set.add(a['other_user'])
        self.assertSequenceEqual(set(kanojo_ids), kanojo_ids_set)
        self.assertSequenceEqual(set(user_ids), user_ids_set)

    def test_fill_activities(self):
        users = [
            {
                'id': 1,
                'name': 'everyone',
            },
            {
                'id': 2,
                'name': 'second',
            },
        ]
        kanojos = [
            {
                'id': 1,
                'name': 'first kanojo',
            },
            {
                'id': 855,
                'name': '855 kanojo',
            },
            {
                'id': 870,
                'name': '870 kanojo',
            },
        ]
        tmp_a = []
        for a in self.activities:
            tmp_a.append(self.a.clear(a))
        a1 = self.a.fill_activities(tmp_a, users, kanojos, {'id': 0, 'name': 'default user'}, {'id': 0, 'name': 'default kanojo'}, fill_type=FILL_TYPE_HTML)
        #print a1
        self.assertEqual(len(a1), len(tmp_a))

if __name__ == '__main__':
    unittest.main()(venv)
