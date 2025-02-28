#!/usr/bin/env python
# -*- coding: utf-8 -*-

__version__ = '0.1'
__author__ = 'Andrey Derevyagin'
__copyright__ = 'Copyright © 2014'

import copy
import random
import string
import unittest

from kanojo import KanojoManager

class KanojoTest(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(KanojoTest, self).__init__(*args, **kwargs)
        self.km = KanojoManager(generate_secret='1qa2')
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
            #"wardrobe": [24, 48, 58, 60, 63, 75],
            "wardrobe": [
                {
                    "id": 24,
                    "like_weight_mult": 1
                },
                {
                    "id": 48,
                    "like_weight_mult": 1
                },
                {
                    "id": 58,
                    "like_weight_mult": 1.5
                },
                {
                    "id": 60,
                    "like_weight_mult": 1
                },
                {
                    "id": 63,
                    "like_weight_mult": 0.75
                },
                {
                    "id": 75,
                    "like_weight_mult": 2
                }
            ],
            "nationality": "Japan",
            "advertising_product_url": None,
            "profile_image_full_url": "http://gdrive-cdn.herokuapp.com/get/0B-nxIpt4DE2TWE1hM0g2bF9LNkU/637179.png",
            "love_gauge": 50,
            "mouth_position": 0.1,
            "name": "\u3042\u304a\u3075\u3043\u308b",
            "fringe_type": 10,
            "nose_type": 1,
            "birthday": 1415271083
        }

    def test_select_clothes_interval(self):
        kanojo = copy.deepcopy(self.kanojo)
        clothes = []
        for i in range(1417822084, 1417822084+60*60*24*15, 60*60):
            #tm = datetime.fromtimestamp(i, pytz.timezone('Europe/Kiev'))
            (clothes_type, changed) = self.km.select_clothes(kanojo, test_time=i)
            if changed and clothes_type not in clothes:
                clothes.append(clothes_type)
        self.assertLessEqual(len(clothes), len(kanojo.get('wardrobe', [])))

    def test_select_clothes_compare(self):
        #from datetime import datetime
        #import pytz

        kanojo = copy.deepcopy(self.kanojo)
        clothes = []
        dt = []
        for i in range(1417822084, 1417822084+60*60*24*5, 60*60):
            #tm = datetime.fromtimestamp(i, pytz.timezone('Europe/Kiev'))
            (clothes_type, changed) = self.km.select_clothes(kanojo, test_time=i)
            dt.append({
                    "time": i,
                    "clothes_type": clothes_type,
                    "changed": changed
                })
            if changed and clothes_type not in clothes:
                clothes.append(clothes_type)
            #print '%02d %d %d'%(tm.hour, clothes_type, changed)
        #import json
        #print json.dumps(dt)

        old = [{"clothes_type": 60, "changed": True, "time": 1417822084}, {"clothes_type": 60, "changed": False, "time": 1417825684}, {"clothes_type": 60, "changed": False, "time": 1417829284}, {"clothes_type": 60, "changed": False, "time": 1417832884}, {"clothes_type": 60, "changed": False, "time": 1417836484}, {"clothes_type": 60, "changed": False, "time": 1417840084}, {"clothes_type": 60, "changed": False, "time": 1417843684}, {"clothes_type": 60, "changed": False, "time": 1417847284}, {"clothes_type": 58, "changed": True, "time": 1417850884}, {"clothes_type": 58, "changed": False, "time": 1417854484}, {"clothes_type": 58, "changed": False, "time": 1417858084}, {"clothes_type": 58, "changed": False, "time": 1417861684}, {"clothes_type": 58, "changed": False, "time": 1417865284}, {"clothes_type": 58, "changed": False, "time": 1417868884}, {"clothes_type": 58, "changed": False, "time": 1417872484}, {"clothes_type": 58, "changed": False, "time": 1417876084}, {"clothes_type": 58, "changed": False, "time": 1417879684}, {"clothes_type": 75, "changed": True, "time": 1417883284}, {"clothes_type": 75, "changed": False, "time": 1417886884}, {"clothes_type": 5, "changed": False, "time": 1417890484}, {"clothes_type": 24, "changed": True, "time": 1417894084}, {"clothes_type": 24, "changed": False, "time": 1417897684}, {"clothes_type": 24, "changed": False, "time": 1417901284}, {"clothes_type": 24, "changed": False, "time": 1417904884}, {"clothes_type": 24, "changed": False, "time": 1417908484}, {"clothes_type": 60, "changed": True, "time": 1417912084}, {"clothes_type": 60, "changed": False, "time": 1417915684}, {"clothes_type": 60, "changed": False, "time": 1417919284}, {"clothes_type": 60, "changed": False, "time": 1417922884}, {"clothes_type": 60, "changed": False, "time": 1417926484}, {"clothes_type": 60, "changed": False, "time": 1417930084}, {"clothes_type": 60, "changed": False, "time": 1417933684}, {"clothes_type": 58, "changed": True, "time": 1417937284}, {"clothes_type": 58, "changed": False, "time": 1417940884}, {"clothes_type": 58, "changed": False, "time": 1417944484}, {"clothes_type": 58, "changed": False, "time": 1417948084}, {"clothes_type": 58, "changed": False, "time": 1417951684}, {"clothes_type": 58, "changed": False, "time": 1417955284}, {"clothes_type": 58, "changed": False, "time": 1417958884}, {"clothes_type": 58, "changed": False, "time": 1417962484}, {"clothes_type": 58, "changed": False, "time": 1417966084}, {"clothes_type": 75, "changed": True, "time": 1417969684}, {"clothes_type": 75, "changed": False, "time": 1417973284}, {"clothes_type": 5, "changed": False, "time": 1417976884}, {"clothes_type": 24, "changed": True, "time": 1417980484}, {"clothes_type": 24, "changed": False, "time": 1417984084}, {"clothes_type": 24, "changed": False, "time": 1417987684}, {"clothes_type": 24, "changed": False, "time": 1417991284}, {"clothes_type": 24, "changed": False, "time": 1417994884}, {"clothes_type": 60, "changed": True, "time": 1417998484}, {"clothes_type": 60, "changed": False, "time": 1418002084}, {"clothes_type": 60, "changed": False, "time": 1418005684}, {"clothes_type": 60, "changed": False, "time": 1418009284}, {"clothes_type": 60, "changed": False, "time": 1418012884}, {"clothes_type": 60, "changed": False, "time": 1418016484}, {"clothes_type": 60, "changed": False, "time": 1418020084}, {"clothes_type": 58, "changed": True, "time": 1418023684}, {"clothes_type": 58, "changed": False, "time": 1418027284}, {"clothes_type": 58, "changed": False, "time": 1418030884}, {"clothes_type": 58, "changed": False, "time": 1418034484}, {"clothes_type": 58, "changed": False, "time": 1418038084}, {"clothes_type": 58, "changed": False, "time": 1418041684}, {"clothes_type": 58, "changed": False, "time": 1418045284}, {"clothes_type": 58, "changed": False, "time": 1418048884}, {"clothes_type": 58, "changed": False, "time": 1418052484}, {"clothes_type": 75, "changed": True, "time": 1418056084}, {"clothes_type": 75, "changed": False, "time": 1418059684}, {"clothes_type": 5, "changed": False, "time": 1418063284}, {"clothes_type": 24, "changed": True, "time": 1418066884}, {"clothes_type": 24, "changed": False, "time": 1418070484}, {"clothes_type": 24, "changed": False, "time": 1418074084}, {"clothes_type": 24, "changed": False, "time": 1418077684}, {"clothes_type": 24, "changed": False, "time": 1418081284}, {"clothes_type": 60, "changed": True, "time": 1418084884}, {"clothes_type": 60, "changed": False, "time": 1418088484}, {"clothes_type": 60, "changed": False, "time": 1418092084}, {"clothes_type": 60, "changed": False, "time": 1418095684}, {"clothes_type": 60, "changed": False, "time": 1418099284}, {"clothes_type": 60, "changed": False, "time": 1418102884}, {"clothes_type": 60, "changed": False, "time": 1418106484}, {"clothes_type": 58, "changed": True, "time": 1418110084}, {"clothes_type": 58, "changed": False, "time": 1418113684}, {"clothes_type": 58, "changed": False, "time": 1418117284}, {"clothes_type": 58, "changed": False, "time": 1418120884}, {"clothes_type": 58, "changed": False, "time": 1418124484}, {"clothes_type": 58, "changed": False, "time": 1418128084}, {"clothes_type": 58, "changed": False, "time": 1418131684}, {"clothes_type": 58, "changed": False, "time": 1418135284}, {"clothes_type": 58, "changed": False, "time": 1418138884}, {"clothes_type": 75, "changed": True, "time": 1418142484}, {"clothes_type": 75, "changed": False, "time": 1418146084}, {"clothes_type": 5, "changed": False, "time": 1418149684}, {"clothes_type": 24, "changed": True, "time": 1418153284}, {"clothes_type": 24, "changed": False, "time": 1418156884}, {"clothes_type": 24, "changed": False, "time": 1418160484}, {"clothes_type": 24, "changed": False, "time": 1418164084}, {"clothes_type": 24, "changed": False, "time": 1418167684}, {"clothes_type": 60, "changed": True, "time": 1418171284}, {"clothes_type": 60, "changed": False, "time": 1418174884}, {"clothes_type": 60, "changed": False, "time": 1418178484}, {"clothes_type": 60, "changed": False, "time": 1418182084}, {"clothes_type": 60, "changed": False, "time": 1418185684}, {"clothes_type": 60, "changed": False, "time": 1418189284}, {"clothes_type": 60, "changed": False, "time": 1418192884}, {"clothes_type": 58, "changed": True, "time": 1418196484}, {"clothes_type": 58, "changed": False, "time": 1418200084}, {"clothes_type": 58, "changed": False, "time": 1418203684}, {"clothes_type": 58, "changed": False, "time": 1418207284}, {"clothes_type": 58, "changed": False, "time": 1418210884}, {"clothes_type": 58, "changed": False, "time": 1418214484}, {"clothes_type": 58, "changed": False, "time": 1418218084}, {"clothes_type": 58, "changed": False, "time": 1418221684}, {"clothes_type": 58, "changed": False, "time": 1418225284}, {"clothes_type": 75, "changed": True, "time": 1418228884}, {"clothes_type": 75, "changed": False, "time": 1418232484}, {"clothes_type": 5, "changed": False, "time": 1418236084}, {"clothes_type": 24, "changed": True, "time": 1418239684}, {"clothes_type": 24, "changed": False, "time": 1418243284}, {"clothes_type": 24, "changed": False, "time": 1418246884}, {"clothes_type": 24, "changed": False, "time": 1418250484}]
        self.assertSequenceEqual(old, dt)

    def test_add_clothes(self):
        kanojo = copy.deepcopy(self.kanojo)
        self.km.add_clothes(kanojo, 24, like_weight_mult=1.5)
        self.assertNotEqual(self.kanojo, kanojo)

        wardrobe1 = filter(lambda el: el.get('id')==24, self.kanojo.get('wardrobe'))
        wardrobe2 = filter(lambda el: el.get('id')==24, kanojo.get('wardrobe'))
        self.assertEqual(next(wardrobe2).get('like_weight_mult')-1.5, next(wardrobe1).get('like_weight_mult'))

        self.km.add_clothes(kanojo, 51)
        self.assertEqual(len(self.kanojo.get('wardrobe'))+1, len(kanojo.get('wardrobe')))

    def test_user_action_price(self):
        kanojo = copy.deepcopy(self.kanojo)

        price = self.km.user_action_price('10|12|21|21|20|12|12|20')
        self.assertEqual(price.get('price_s'), 10)

        price = self.km.user_action_price('10|11')
        self.assertEqual(len(price), 0)

        self.assertSequenceEqual(kanojo, self.kanojo)

    def test_action_string_to_freq(self):
        dt = action_string_to_freq('10|12|21|11|21|11|12|21')
        self.assertSequenceEqual(dt, { 10: 1, 11: 2, 12: 2, 21: 3 })

    def test_bits2int(self):
        data = bytearray((123,169,85,108,13,191,22,67,55,62,29,157,92,1,5,95))
        for i in range(len(data)-1):
            self.assertEqual(self.km.bits2int(data, 0+i*8, 8+i*8), data[i])
            self.assertEqual(self.km.bits2int(data, 1+i*8, 9+i*8), (data[i] & 0x7f) << 1 | (data[i+1] & 0xe0) >> 7)
            self.assertEqual(self.km.bits2int(data, 2+i*8, 10+i*8), (data[i] & 0x3f) << 2 | (data[i+1] & 0xc0) >> 6)
            self.assertEqual(self.km.bits2int(data, 3+i*8, 11+i*8), (data[i] & 0x1f) << 3 | (data[i+1] & 0xf8) >> 5)
            self.assertEqual(self.km.bits2int(data, 4+i*8, 12+i*8), (data[i] & 0x0f) << 4 | (data[i+1] & 0xf0) >> 4)
        self.assertEqual(self.km.bits2int(data, 4, 22), (data[0] & 0x0f) << 14 | data[1] << 6 | (data[2] & 0xfc) >> 2)
        self.assertEqual(self.km.bits2int(data, 0, 24), data[0] << 16 | data[1] << 8 | data[2])

    def test_kanojo_generate(self):
        #bc1 = ''.join(random.choice(string.printable) for _ in range(13))
        bc1 = ''.join(random.choice(string.digits) for _ in range(13))
        bc2 = ''.join(random.choice(string.printable) for _ in range(13))
        barcode_info1 = self.km.generate(bc1)
        barcode_info2 = self.km.generate(bc2)
        barcode_info3 = self.km.generate(bc1)

        self.assertIsNotNone(barcode_info1)
        self.assertIsNotNone(barcode_info2)
        self.assertEqual(len(barcode_info1.keys()), len(barcode_info2.keys()))
        self.assertSequenceEqual(barcode_info1, barcode_info3)



if __name__ == '__main__':
    unittest.main()(venv)
