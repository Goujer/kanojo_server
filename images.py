#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'Goujer'
__copyright__ = 'Copyright © 2022'

import io
import os
import os.path
import shutil

from PIL import Image

user_image_size = 200
product_image_size = 400

user_path = './profile_images/user/'
kanojo_path = './profile_images/kanojo/'
product_path = './product_images/barcode/'

def save_image(content, filename='image.png'):
	with open(filename, 'bw') as f:
		f.write(content)
	return filename

#For User
def save_user_profile_image(img_data, uid):
	# Setup paths
	if not os.path.isdir(user_path):
		os.makedirs(user_path)
	filename = os.path.join(user_path, str(uid))

	# Open Image Data
	image = Image.open(img_data)

	# Resize if needed
	(width, height) = image.size
	if width > user_image_size or height > user_image_size:
		image = image.resize((user_image_size, user_image_size), resample=Image.LANCZOS)

	# Save file
	dt = io.BytesIO()
	image.save(dt, format="JPEG", quality=100)
	save_image(dt.getvalue(), filename=f'{filename}.jpg')
	dt.close()

# For Product
def save_product_image(img_data, barcode):
	if not os.path.isdir(product_path):
		os.makedirs(product_path)
	filename = os.path.join(product_path, barcode)

	# Open Image Data
	image = Image.open(img_data)

	# Resize if needed
	(width, height) = image.size
	if width > user_image_size or height > user_image_size:
		image = image.resize((user_image_size, user_image_size), resample=Image.LANCZOS)

	# Save file
	dt = io.BytesIO()
	image.save(dt, format="JPEG", quality=100)
	save_image(dt.getvalue(), filename=f'{filename}.jpg')
	dt.close()

#For Kanojo
def save_kanojo_profile_image(img_data, kid):
	destination = os.path.join(kanojo_path, str(kid), "")
	if os.path.isdir(destination):
		shutil.rmtree(destination, ignore_errors=True)
	os.makedirs(destination)

	im = Image.open(img_data)

	#cr = im.crop((104, 40, 170 + 94, 170 + 40))	#Original face from 368 (fixed to be centered)
	cr = im.crop((im.width * 0.269, im.width * 0.108, im.width * 0.731, im.width * 0.570))
	dt = io.BytesIO()
	cr.save(dt, format="png")
	save_image(dt.getvalue(), filename=os.path.join(destination, 'icon.png'))
	dt.close()

	cr = im.crop((im.width*0.1875, 0.00, im.width*0.8125, im.width*0.625))	#Good for bust image (v1 style icon). This has been verified by Kanojo Wars site.
	dt = io.BytesIO()
	cr.save(dt, format="png")
	save_image(dt.getvalue(), filename=os.path.join(destination, 'bust.png'))
	dt.close()

	dt = io.BytesIO()
	im.save(dt, format="png")
	save_image(dt.getvalue(), filename=os.path.join(destination, 'full.png'))
	dt.close()

def save_resized_image(filename, size):
	im = Image.open(filename+'.png')
	rs = im.resize((size, size), resample=Image.LANCZOS)
	dt = io.BytesIO()
	rs.save(dt, format="png")
	save_image(dt.getvalue(), filename=f'{filename}_{size}.png')
	dt.close()

if __name__=='__main__':
	im = Image.open('1.png')
	#im = Image.open(StringIO.StringIO(buffer))
	cr = im.crop((94, 40, 170+94, 170+40))
	cr.thumbnail((88, 88), Image.ANTIALIAS)
	dt = io.StringIO()
	cr.save(dt, format="png")
	save_image(dt.getvalue(), filename='best_girl.png')
	dt.close()

	dt = io.StringIO()
	im.save(dt, format="png")
	save_image(dt.getvalue(), filename='fk.png')
	dt.close()