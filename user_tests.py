#!/usr/bin/env python
# -*- coding: utf-8 -*-

__version__ = '0.1'
__author__ = 'Andrey Derevyagin'
__copyright__ = 'Copyright © 2014'

import copy
import unittest

from kanojo import KanojoManager
from store import StoreManager
from user import UserManager

class UserTest(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(UserTest, self).__init__(*args, **kwargs)
        self.store = StoreManager()
        self.um = UserManager(kanojo_manager=KanojoManager(), store=self.store)
        self.user = {
            "facebook_connect": False,
            "money": 0,
            "sex": "male",
            "create_time": 1413019326,
            "likes": [],
            "id": 1,
            "description": None,
            "uuid": ["test_uuid1", "test_uuid1"],
            "stamina": 100,
            "kanojos": [1, 368],
            "email": "everyone@barcodekanojo.com",
            "twitter_connect": False,
            "generate_count": 0,
            "profile_image_url": "http://www.deviantsart.com/2oo69ib.jpg",
            "birthday": 1413025200,
            "enemies": [],
            "password": None,
            "friends": [231, 31, 149, 333, 335, 336, 337, 339, 30, 220, 361],
            "tickets": 20,
            "name": "everyone",
            "language": "en",
            "level": 1, 
            "scan_count": 0
        }
        self.kanojo = {
            "mascot_enabled": "0",
            "avatar_background_image_url": None,
            "mouth_type": 4,
            "skin_color": 1,
            "body_type": 1,
            "race_type": 10,
            "spot_type": 1,
            "sexual": 16,
            "id": 368,
            "recognition": 42,
            "clothes_type": 5,
            "brow_type": 4,
            "consumption": 14,
            "like_rate": 0,
            "eye_position": 0.8,
            "followers": [1],
            "location": "Somewhere",
            "accessory_type": 6,
            "possession": 28,
            "hair_type": 19,
            "clothes_color": 4,
            "ear_type": 2,
            "brow_position": -0.9,
            "barcode": "4011708223260",
            "eye_type": 101,
            "profile_image_url": "http://www.deviantsart.com/3m68o83.png",
            "eye_color": 3,
            "glasses_type": 1,
            "hair_color": 14,
            "owner_user_id": 1,
            "face_type": 4,
            "nationality": "Japan",
            "advertising_product_url": None,
            "profile_image_full_url": "http://gdrive-cdn.herokuapp.com/get/0B-nxIpt4DE2TWE1hM0g2bF9LNkU/637179.png",
            "love_gauge": 50,
            "mouth_position": 0.1,
            "name": "\\u3042\\u304a\\u3075\\u3043\\u308b",
            "fringe_type": 10,
            "nose_type": 1,
            "birthday": 1415271083
        }
        self.kanojo_friend = {"mascot_enabled": "0", "avatar_background_image_url": None, "mouth_type": 10, "nose_type": 3, "body_type": 1, "race_type": 10, "spot_type": 1, "sexual": 19, "id": 31, "recognition": 36, "clothes_type": 4, "brow_type": 2, "consumption": 18, "like_rate": 0, "eye_position": 0, "followers": [1], "location": "Somewhere", "accessory_type": 1, "possession": 27, "hair_type": 15, "clothes_color": 3, "ear_type": 1, "brow_position": 0, "barcode": "hidden", "love_gauge": 50, "profile_image_url": "http://www.deviantsart.com/u7ij6n.png", "eye_color": 6, "glasses_type": 1, "hair_color": 16, "owner_user_id": 0, "face_type": 4, "nationality": "Japan", "advertising_product_url": None, "profile_image_full_url": "http://gdrive-cdn.herokuapp.com/get/0B-nxIpt4DE2TbnZtVVB1T1RYX00/1277508.png", "eye_type": 112, "mouth_position": 0, "name": "\\u30b0\\u30e9\\u30cb\\u30fc\\u30cb", "fringe_type": 3, "skin_color": 10, "birthday": 1413571308}

    def test_user_action_approche(self):
        user = copy.deepcopy(self.user)
        kanojo = copy.deepcopy(self.kanojo)
        kanojo2 = copy.deepcopy(self.kanojo_friend)

        km = self.um.kanojo_manager
        self.um.kanojo_manager = None
        dt = self.um.user_action(user, kanojo)
        self.assertEqual(dt.get('code'), 500)

        self.um.kanojo_manager = km
        dt = self.um.user_action(user, kanojo)
        self.assertEqual(dt.get('code'), 500)

        dt = self.um.user_action(user, kanojo, action_string="10|12|21")
        self.assertEqual(dt.get('code'), 200)
        self.assertTrue('love_increment' in dt)
        self.assertTrue('increase_love' in dt.get('love_increment'))
        self.assertGreater(dt.get('love_increment').get('increase_love'), 0)
        self.assertEqual(dt.get('love_increment').get('decrement_love'), 0)
        self.assertEqual(self.user.get('stamina')-10, user.get('stamina'))
        #print dt

        dt = self.um.user_action(user, kanojo2, action_string="10|12|21|21|20|12|12|20")
        self.assertEqual(dt.get('code'), 200)
        self.assertTrue('love_increment' in dt)
        self.assertTrue('decrement_love' in dt.get('love_increment'))
        self.assertGreater(dt.get('love_increment').get('decrement_love'), 0)
        self.assertEqual(dt.get('love_increment').get('increase_love'), 0)
        self.assertEqual(self.user.get('stamina')-20, user.get('stamina'))

        kanojo2 = copy.deepcopy(self.kanojo_friend)
        kanojo2['love_gauge'] = 1
        dt = self.um.user_action(user, kanojo2, action_string="10|12|21|21|20|12|12|20")
        self.assertEqual(dt.get('code'), 200)
        self.assertTrue('love_increment' in dt)
        self.assertEqual(self.user.get('stamina')-30, user.get('stamina'))
        self.assertTrue(dt.get('info').get('change_owner'))

        user['stamina'] = 5
        dt = self.um.user_action(user, kanojo, action_string="10|12|21")
        self.assertEqual(dt.get('code'), 403)

    def test_user_action_item(self):
        user = copy.deepcopy(self.user)
        kanojo = copy.deepcopy(self.kanojo)
        kanojo2 = copy.deepcopy(self.kanojo_friend)

        dt = self.um.user_action(user, kanojo, do_gift=110, is_extended_action=True)
        self.assertEqual(dt.get('code'), 200)
        self.assertTrue(dt.get('data'))
        self.assertFalse(self.um.user_items(self.user))
        self.assertTrue(self.um.user_items(user))
        self.assertEqual(len(self.um.user_items(user)), 1)

        # not extended gift
        dt = self.um.user_action(user, kanojo, do_gift=1, is_extended_action=False)
        self.assertEqual(dt.get('code'), 403)
        self.assertTrue('love_increment' in dt)
        self.assertEqual(dt.get('love_increment').get('alertShow'), 1)
        self.assertTrue('alerts' in dt)

        user['money'] = 100
        dt = self.um.user_action(user, kanojo, do_gift=1, is_extended_action=False)
        self.assertEqual(dt.get('code'), 200)
        self.assertTrue('love_increment' in dt)
        self.assertGreater(dt.get('love_increment').get('increase_love'), 0)
        self.assertNotEqual(kanojo.get('love_gauge'), self.kanojo.get('love_gauge'))

    def test_add_store_item(self):
        user = copy.deepcopy(self.user)

        store_item = self.store.get_item(110)
        self.assertIsNotNone(store_item)

        dt = self.um.add_store_item(user, store_item)
        self.assertIsNotNone(dt)
        #self.assertEqual(dt.get('has_item_id'), store_item.get('has_item_id'))
        self.um.add_store_item(user, store_item)
        dt = self.um.add_store_item(user, store_item)
        self.assertEqual(dt.get('units'), 3)

    def test_give_present(self):
        user = copy.deepcopy(self.user)
        kanojo = copy.deepcopy(self.kanojo)
        kanojo2 = copy.deepcopy(self.kanojo_friend)

        store_item = self.store.get_item(110)
        self.assertIsNotNone(store_item)
        self.um.add_store_item(user, store_item)

        has_items = self.um.user_items(user)
        self.assertIsNotNone(has_items)
        self.assertGreater(len(has_items), 0)

        item = has_items[0]
        dt = self.um.give_present(user, kanojo, item.get('store_item_id'))
        #print dt




if __name__ == '__main__':
    unittest.main()(venv)
