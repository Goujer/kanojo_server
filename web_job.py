#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'Andrey Derevyagin,  Goujer'
__copyright__ = 'Copyright © 2014-2015, 2020-2022'

import atexit
import os.path
import re
import ssl
import urllib.parse
from hashlib import sha224
from html import escape

import pymongo.errors
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, Response, abort, json, jsonify, redirect, render_template, request, send_file, \
	send_from_directory, session
from flask_api.decorators import set_parsers

from activity import ActivityManager
from bkmultipartparser import BKMultipartParser
from constants import *
from geo_ip import GEOIP_WEB_SERVICE, GeoIP
from images import save_kanojo_profile_image, save_product_image, save_resized_image
from kanojo import *
from reactionword import ReactionwordManager
from store import StoreManager
from thread_post import Post
from user import *

if config.USE_HTTPS:
	context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
	context.load_cert_chain(config.SSL_CERTIFICATE_FILE, keyfile=config.SSL_PRIVATEKEY_FILE)

app = Flask(__name__)
app.debug = config.DEBUG
app.secret_key = config.SESSION_SECRET_KEY
#app.config['SESSION_COOKIE_DOMAIN'] = '192.168.1.19'
#session.permanent = True
#app.permanent_session_lifetime = datetime.timedelta(minutes=5)
#app.config['DEFAULT_PARSERS'] = []

#Set Up Debug From WSGI
from werkzeug.debug import DebuggedApplication
application = DebuggedApplication(app, config.DEBUG)

mdb_connection_string = config.MDB_CONNECTION_STRING_REAL
db_name = mdb_connection_string.split('/')[-1]
db2 = MongoClient(mdb_connection_string)[db_name]

mdb_connection_string = config.MDB_CONNECTION_STRING
db_name = mdb_connection_string.split('/')[-1]
db = MongoClient(mdb_connection_string)[db_name]

kanojo_manager = KanojoManager(db,
					clothes_magic=config.CLOTHES_MAGIC,
					generate_secret=config.KANOJO_SECRET
				)
store = StoreManager()
activity_manager = ActivityManager(db=db)
user_manager = UserManager(db, kanojo_manager=kanojo_manager, store=store, activity_manager=activity_manager)
geoIP = GeoIP(db, secret1=config.GEOIP_SECRET1, secret2=config.GEOIP_SECRET2, secret3=config.GEOIP_SECRET3)
reactionword = ReactionwordManager()

@app.template_filter('date_format')
def timectime(s):
	dt = time.gmtime(s)
	return '%d-%02d-%02d'%(dt.tm_year, dt.tm_mon, dt.tm_mday)

def order_dict_cmp(x, y):
	order = ('code', )
	x,y = x[0], y[0]
	if x in order and y in order:
		return order.index(x)-order.index(y)
	elif x in order:
		return -1
	elif y in order:
		return 1
	return (x > y) - (x < y)

def json_response(data):
	if isinstance(data, dict):
		data = OrderedDict(sorted(list(data.items()), key=cmp_to_key(order_dict_cmp)))
	rtext = json.dumps(data)
	if request.method == 'POST':
		if request.form.get('callback', False):
			rtext = '%s(%s);'%(request.form.get('callback', ''), rtext)
	else:
		if request.args.get('callback', False):
			rtext = '%s(%s);'%(request.args.get('callback', ''), rtext)
	return Response(rtext, status=200, mimetype='application/json')

def server_url():
	if config.USE_HTTPS:
		return request.url_root.replace('http:/', 'https:/')
	return request.url_root

def get_remote_ip():
	if not request.headers.getlist("X-Forwarded-For"):
		remote_ip = request.remote_addr
	else:
		remote_ip = request.headers.getlist("X-Forwarded-For")[0]
	return remote_ip

@app.route('/')
def index():
	remote_ip = get_remote_ip()
	tz_string = geoIP.ip2timezone(remote_ip, service_type=GEOIP_WEB_SERVICE)
	#print remote_ip, tz_string
	val = {}
	posts = []
	#for p in db.posts_rejected.find().sort('time', 1):
	for p in db.posts.find().sort('time', 1):
		posts.append(Post(post=p, timezone_string=tz_string))
	val['posts'] = posts
	return render_template('thread.html', **val)

@app.route('/robots.txt')
@app.route('/favicon.ico')
def robots_txt():
	return send_from_directory(app.static_folder, request.path[1:])

def check_post_request(post_request):
	ban_rules = (
		#{
		#    'ip': '127.0.0.1'
		#},
		{
			'ip': '46.161.41.34',
			#'User-Agent': 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1)'
		},
		#{
		#    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/40.0.2214.115 YaBrowser/15.2.2214.3643 Safari/537.36'
		#},
	)
	tmp = db.settings.find_one({ 'ban_rules': { '$exists': True } })
	if tmp:
		ban_rules = tmp.get('ban_rules', list())
	reject_rule = None
	remote_ip = get_remote_ip()
	for rule in ban_rules:
		if 'ip' in rule and remote_ip != rule.get('ip'):
			continue
		flag = True
		for k in [el for el in list(rule.keys()) if el!='ip']:
			if post_request.headers.get(k) != rule.get(k):
				flag = False
				break
		if flag:
			#if rule.has_key('ip') and post_request.remote_addr != rule.get('ip'):
			#    continue
			reject_rule = rule
		if reject_rule is not None:
			print('Rejected by rule:', rule)
			break
	if reject_rule is None:
		print(post_request.headers)
	return reject_rule

@app.route('/post', methods=['POST'])
def post():
	reject_rule = check_post_request(request)
	#if not check_post_request(request):
	#    return 'You are banned for this thread.'
	prms = request.form

	name = 'Сырно' if len(prms.get('nya1').strip()) == 0 else prms.get('nya1').strip()
	msg = escape(prms.get('nya2').strip())
	pwd = prms.get('password', '').strip()
	if len(msg):
		msg = message_marking(msg)
		msg = clickableURLs(msg)
		msg = checkRefLinks(msg, 1)
		msg = checkQuotes(msg)
		if reject_rule is None:
			seqs_collection = 'posts'
		else:
			seqs_collection = 'posts_rejected'
		pid = db.seqs.find_and_modify(
				query = {'collection': seqs_collection},
				update = {'$inc': {'id': 1}},
				fields = {'id': 1, '_id': 0},
				new = True
			)
		while db.posts.find_one({'id': pid if pid else 1}):
			pid += 1
		if pid is None:
			pid = {
					'collection': seqs_collection,
					'id': 1
				}
			try:
				db.seqs.insert_one(pid)
			except pymongo.errors.DuplicateKeyError as e:
				abort(500)
		post = {
			'pid': pid.get('id'),
			'post': msg.replace("\n", '<br>'),
			'poster': name,
			'time': int(time.time())
		}
		if pwd:
			post['password'] = sha224(pwd).hexdigest()
		if reject_rule is None:
			db.posts.insert_one(post)
		else:
			post['reject_rule'] = reject_rule
			db.posts_rejected.insert_one(post)
			return 'You are banned for this thread.'

	return redirect("/", code=302)

marking_rules = (
  (re.compile('\*\*(?P<bold>.*?)\*\*', re.VERBOSE), r'<b>\g<bold></b>'),
  (re.compile('__(?P<underline>.*?)__', re.VERBOSE), r'<span class="underline">\g<underline></span>'),
  (re.compile('--(?P<strike>.*?)--', re.VERBOSE), r'<strike>\g<strike></strike>'),
  (re.compile('%%(?P<spoiler>.*?)%%', re.VERBOSE), r'<span class="spoiler">\g<spoiler></span>'),
  (re.compile('\*(?P<italic>.*?)\*', re.VERBOSE), r'<i>\g<italic></i>'),
  (re.compile('_(?P<italic>.*?)_', re.VERBOSE), r'<i>\g<italic></i>'),
  (re.compile('`(?P<code>.*?)`', re.VERBOSE), r'<code>\g<code></code>'),
)

def message_marking(message):
	l = []
	for line in message.split('\n'):
		line = line.strip()
		for (p, mark_sub) in marking_rules:
			line = p.sub(mark_sub, line)
		l.append(line)
	return '\n'.join(l)

def refLinksReplace(match):
	match = match.group()
	postid = match[len('&gt;&gt;'):]
	parentid = 1
	if parentid != 0:
		if postid == parentid:
			return r'<a href="/.html" onclick="javascript:highlight(' + '\'' + postid + '\'' + r', true);">&gt;&gt;' + postid + '</a>'
		else:
			return '<a href="#' + postid + r'" onclick="javascript:highlight(' + '\'' + postid + '\'' + r', true);">&gt;&gt;' + postid + '</a>'
	return match

def checkQuotes(message):
	message = re.compile(r'^&gt;(.*)$', re.MULTILINE).sub(r'<span class="unkfunc">&gt;\1</span>', message)
	return message

def checkRefLinks(message, parentid):
	message = re.compile(r'&gt;&gt;([0-9]+)').sub(refLinksReplace, message)
	return message

def clickableURLs(message):
	translate_prog = prog = re.compile(r'\b(http|ftp|https)://\S+(\b|/)|\b[-.\w]+@[-.\w]+')
	i = 0
	list = []
	while 1:
		m = prog.search(message, i)
		if not m:
			break
		j = m.start()
		list.append(message[i:j])
		i = j
		url = m.group(0)
		while url[-1] in '();:,.?\'"<>':
			url = url[:-1]
		i = i + len(url)
		url = url
		if ':' in url:
			repl = '<a href="%s">%s</a>' % (url, url)
		else:
			repl = '<a href="mailto:%s">&lt;%s&gt;</a>' % (url, url)
		list.append(repl)
	j = len(message)
	list.append(message[i:j])
	return ''.join(list)

@app.route('/last_kanojos.html')
def last_kanojos_html():
	val = {}
	return render_template('last_kanojos.html', **val)

@app.route('/last_kanojos.json')
def last_kanojos():
	data = {
		'code': 200,
		'kanojos': []
	}
	for i in db.info.find().sort('timestamp', -1).limit(100):
		i.pop('_id', None)
		i.pop('timestamp', None)
		kid = i.get('kid')
		if kid is None:
			kid = i.get('img_url', '').split('/')[-1].split('.')[0]
			if kid.isdigit():
				kid = int(kid)
		if isinstance(kid, int):
			i['url'] = f'http://www.barcodekanojo.com/kanojo/{kid}/{i.get("name", "_")}'
		data['kanojos'].append(i)
	return json_response(data)

@app.route('/add_job', methods=['POST'])
def add_job():
	data = request.form.get('nya')
	#data = 'https://www.barcodekanojo.com/user/407529/Everyone http://www.barcodekanojo.com/kanojo/2606490/아...바타  fsdf'
	re_u = re.compile('^https?://www\.barcodekanojo\.com/user/(\d+)/.+$')
	re_k = re.compile('^https?://www\.barcodekanojo\.com/kanojo/(\d+)/.+$')
	users = []
	kanojos = []
	errors = []
	for line in data.split():
		s = re_u.search(line.strip())
		if s:
			users.append(int(s.groups()[0]))
		else:
			k = re_k.search(line.strip())
			if k:
				kanojos.append(int(k.groups()[0]))
			else:
				errors.append(line.strip())
	val = {
		'users': users,
		'kanojos': kanojos,
		'errors': errors,
	}
	if len(users) or len(kanojos):
		dt = {}
		if len(users):
			dt['users'] = users
		if len(kanojos):
			dt['kanojos'] = kanojos
		db2.save_jobs.insert_one(dt)
	return render_template('add_job.html', **val)

'''
@app.route('/images/<fn>', methods=['GET'])
def images_root(fn):
	return send_from_directory('%s/images'%app.static_folder, fn)

@app.route('/images/api/item/basic/<fn>')
@app.route('/images/store/<fn>')
def images_store(fn):
	return send_from_directory('%s/images/store'%app.static_folder, fn)

@app.route('/images/profile_bkgr/<fn>')
def images_profile_bkgr(fn):
	return send_from_directory('%s/images/profile_bkgr'%app.static_folder, fn)
'''

@app.route('/images/<path:path>', methods=['GET'])
def images_dir(path):
	filename = f'{app.static_folder}/images/{path.lower()}'
	if os.path.isfile(filename):
		return send_file(filename)
	abort(404)

### --------------- storage.barcodekanojo.com ---------------

@app.route('/avatar/<path:path>')
def avatar(path):
	#if request.headers['Host'] == 'storage.barcodekanojo.com':
	filename = '%s/avatar_data/%s'%(app.static_folder, path.lower())
	if os.path.isfile(filename):
		return send_file(filename)
	abort(404)

### --------------- DRESS UP ---------------

@app.route('/dress_up')
def dress_up():
	return redirect('/dress_up/index.html', code=302)

@app.route('/dress_up/<fn>')
def dress_up_file(fn):
	filename = '%s/dress_up/%s'%(app.static_folder, fn)
	if os.path.isfile(filename):
		return send_file(filename)
	abort(404)

def dresup_json_to_barcode(dressup_json):
	keys = ["c_skin", "c_hair", "c_eye", "c_clothes", "body", "hair", "face", "fringe", "mouth", "eye", "nose", "brow", "ear", "spot", "glasses", "accessory", "clothes"]
	r_keys = list(dressup_json.keys())
	for k in keys:
		if k not in r_keys:
			rv = {'code': 400}
			return json_response(rv)
	bc = {
		'skin_color': dressup_json.get('c_skin'),
		'hair_color': dressup_json.get('c_hair'),
		'eye_color': dressup_json.get('c_eye'),
		'clothes_color': dressup_json.get('c_clothes'),
		'body_type': dressup_json.get('body'),
		'hair_type': dressup_json.get('hair'),
		'face_type': dressup_json.get('face'),
		'fringe_type': dressup_json.get('fringe'),
		'mouth_type': dressup_json.get('mouth'),
		'eye_type': dressup_json.get('eye'),
		'nose_type': dressup_json.get('nose'),
		'brow_type': dressup_json.get('brow'),
		'ear_type': dressup_json.get('ear'),
		'spot_type': dressup_json.get('spot'),
		'glasses_type': dressup_json.get('glasses'),
		'accessory_type': dressup_json.get('accessory'),
		'clothes_type': dressup_json.get('clothes')
	}
	return bc

@app.route('/search_barcode.json', methods=['POST'])
def search_barcode():
	data = request.get_json()
	query = {
		'$or': [
			{ 'owner_user_id': { '$exists': False } },
			{ 'owner_user_id': 0 }
		]
	}
	query.update(dresup_json_to_barcode(data))
	query.pop('clothes_color', None)
	kanojo = db2.kanojo.find_one(query)
	if kanojo:
		rv = { 'code': 200 }
		rv['barcode'] = kanojo.get('barcode')
	else:
		rv = { 'code': 404 }
	return json_response(rv)

def _genarete_barcode(bid):
	#55.{10}[1]
	n = bid * config.BARCODE_SECRET % 9999999999
	str12 = '55' + str(n).zfill(10)
	sum1 = 0
	sum2 = 0
	i = 1
	for digit in str12:
		if i%2:
			sum1 += int(digit)
		else:
			sum2 += int(digit)
		i = i+1
	rv = (10 - (sum2*3 + sum1) % 10) % 10
	return f'{str12}{rv:d}'

@app.route('/generate_barcode.json', methods=['POST'])
def generate_barcode():
	data = request.get_json()
	barcode = dresup_json_to_barcode(data)
	barcode['race_type'] = 10
	barcode['eye_position'] = 0
	barcode['brow_position'] = 0
	barcode['mouth_position'] = 0

	barcode['sexual'] = randint(0, 99)
	barcode['recognition'] = randint(0, 99)
	barcode['consumption'] = randint(0, 99)
	barcode['possession'] = randint(0, 99)
	barcode['flirtable'] = randint(0, 99)

	bc = None
	while True:
		bid = db.seqs.find_and_modify(
					query = {'collection': 'barcode_counter'},
					update = {'$inc': {'id': 1}},
					fields = {'id': 1, '_id': 0},
					new = True
				)
		while db.barcode_tmp.find_one({'id': bid if bid else 1}):
			bid += 1
		if not bid:
			bid = {
					'collection': 'barcode_counter',
					'id': 1
				}
			try:
				db.seqs.insert_one(bid)
			except pymongo.errors.DuplicateKeyError as e:
				return jsonify({ 'code': 500 })
		bid = bid.get('id')
		if bid > 9999999999:
			return jsonify({ 'code': 500 })
		bc = _genarete_barcode(bid)
		q = { 'barcode': bc }
		if db.kanojos.find_one(q) or db.barcode_tmp.find_one(q):
			continue
		break
	barcode['barcode'] = bc
	barcode['timestamp'] = int(time.time())
	if db.barcode_tmp.find_one({ 'barcode': bc }):
		db.barcode_tmp.update_one(barcode)
	else:
		db.barcode_tmp.insert_one(barcode)

	rv = { 'code': 200 }
	rv['barcode'] = bc
	return json_response(rv)


### --------------- BARCODE STATISTIC ---------------

@app.route('/barcode_stat')
def barcode_stat():
	return redirect('/barcode_stat/index.html', code=302)

@app.route('/barcode_stat/<fn>')
def barcode_stat_file(fn):
	filename = '%s/barcode_stat/%s'%(app.static_folder, fn)
	if os.path.isfile(filename):
		return send_file(filename)
	abort(404)


### --------------- LAST ACTIVITY ---------------

@app.route('/last_activity.json')
def last_activity():
	prms = request.args
	try:
		since_id = int(prms.get('since_id', 0))
	except ValueError as e:
		return json_response({ "code": 400 })
	activities = activity_manager.all_activities(since_id=since_id)
	uids = activity_manager.user_ids(activities)
	kids = activity_manager.kanojo_ids(activities)

	users = user_manager.users(uids)
	kanojos = kanojo_manager.kanojos(kids)

	activities = activity_manager.fill_activities(activities, users, kanojos, user_manager.default_user, kanojo_manager.default_kanojo, fill_type=1)

	rspns = { "code": 200 }
	rspns['last_id'] = activities[0].get('id') if len(activities) else since_id
	rspns['activities'] = activities
	return json_response(rspns)

@app.route('/user/<uid>.html')
def user_html(uid):
	try:
		uid = int(uid)
	except ValueError as e:
		return abort(400)
	user = user_manager.user(uid=uid, clear=CLEAR_NONE)
	if not user:
		abort(404)
	user = user_manager.fill_fields(user)
	user.pop('_id', None)

	kids = copy.copy(user.get('kanojos'))
	if len(kids) > 18:
		kids = kids[:18]

	uids = copy.copy(user.get('enemies'))
	if len(uids) > 18:
		uids = uids[:18]

	activities = activity_manager.user_activities_4html(uid, limit=10)
	uids.extend(activity_manager.user_ids(activities))
	kids.extend(activity_manager.kanojo_ids(activities))
	uids = list(set(uids))
	kids = list(set(kids))
	kanojos = kanojo_manager.kanojos(kids)
	users = user_manager.users(uids)

	for i in range(min(18, len(user.get('kanojos')))):
		user['kanojos'][i] = next((k for k in kanojos if k.get('id') == user['kanojos'][i]), kanojo_manager.default_kanojo)

	for i in range(min(18, len(user.get('enemies')))):
		user['enemies'][i] = next((u for u in users if u.get('id') == user['enemies'][i]), user_manager.default_user)

	activities = activity_manager.fill_activities(activities, users, kanojos, user_manager.default_user, kanojo_manager.default_kanojo, fill_type=1)

	val = {
		'stamina_percentage': user.get('stamina') * 10 / (user.get('level') + 9),
		'is_dict': lambda x: isinstance(x, dict),
		'len_zero': lambda x: len(x)==0,
		'activities_html': activity_manager.create_html_block(activities),
	}
	val.update(user)
	return render_template('user.html', **val)

@app.route('/kanojo/<kid>.html')
def kanojo_html(kid):
	try:
		kid = int(kid)
	except ValueError as e:
		return abort(400)
	kanojo = kanojo_manager.kanojo(kid, clear=CLEAR_NONE)
	if kanojo is None:
		abort(404)
	kanojo = kanojo_manager.fill_fields(kanojo)
	kanojo.pop('_id', None)

	uids = copy.copy(kanojo.get('followers'))
	if len(uids) > 18:
		uids = uids[:18]
	if kanojo.get('owner_user_id') and kanojo.get('owner_user_id') not in uids:
		uids.append(kanojo.get('owner_user_id'))

	activities = activity_manager.kanojo_activities_4html(kanojo.get('id'), limit=10)
	uids.extend(activity_manager.user_ids(activities))
	#kids.extend(activity_manager.kanojo_ids(activities))

	users = user_manager.users(uids)
	kanojo['owner_user'] = next((u for u in users if u.get('id') == kanojo.get('owner_user_id')), user_manager.default_user)
	for i in range(min(18, len(kanojo.get('followers')))):
		kanojo['followers'][i] = next((u for u in users if u.get('id') == kanojo['followers'][i]), user_manager.default_user)

	activities = activity_manager.fill_activities(activities, users, [kanojo, ], user_manager.default_user, kanojo_manager.default_kanojo, fill_type=1)

	val = {
		'red_level': lambda x: x < 30,
		'len_zero': lambda x: len(x)==0,
		'is_dict': lambda x: isinstance(x, dict),
		'like_rate0': 5-kanojo.get('like_rate', 0),
		'activities_html': activity_manager.create_html_block(activities),
	}
	val.update(kanojo)
	#print json.dumps(kanojo)
	return render_template('kanojo.html', **val)

### --------------- KANOJO SERVER ---------------

@app.route('/api/account/verify.json', methods=['GET', 'POST'])
def acc_verify():
	prms = request.form if request.method == 'POST' else request.args
	uuid = prms.get('uuid')
	email = prms.get('email')
	password = prms.get('password')
	api = prms.get('api')
	language = prms.get('language')
	ip_hash = hashlib.md5(get_remote_ip(), usedforsecurity=False).hexdigest()
	if api and language:
		client_data = db.analytics.find_one({'client': ip_hash})
		if client_data:
			client_data['api'] = int(api)
			client_data['language']=language
			db.analytics.update_one(client_data)
		else:
			client_data = {'client': ip_hash,
							'api': int(api),
							'language': language}
			db['analytics'].insert_one('client_data')
	if uuid:
		user = user_manager.login(uuid=uuid, email=email, password=password)
		if not user:
			return jsonify({ "code": 404, "alerts": [{"body": "User not found", "title": "Warning"}]})
		session['id'] = user.get('id')
		return jsonify({ "code": 200, "user": user })
	else:
		return jsonify({ "code": 400 })

@app.route('/api/account/signup.json', methods=['POST'])
def acc_signup():
	prms = request.form
	uuid = prms.get('uuid')
	name = prms.get('name', generate_name())
	password = prms.get('password')
	email = prms.get('email').lower()
	birthday = int(time.mktime(time.strptime('%s-%s-%s 12:00:00' % (prms.get('birth_year', 1990), prms.get('birth_month', 1), prms.get('birth_day', 1)), '%Y-%m-%d %H:%M:%S'))) - time.timezone
	sex = prms.get('sex', 'Not Sure')
	profile_image_data = prms.get('profile_image_data')
	if uuid and email and password:
		query = {
			"email": {
				"$exists": True,
				"$eq": email
			}
		}
		existing_user = db.users.find_one(query)
		if existing_user:
			return jsonify({"code": 400, "alerts": [{"body": "Email already in use.", "title": ""}]})
		else:
			user = user_manager.create(uuid, name, password, email, birthday, sex, profile_image_data)
			if not user:
				return jsonify({"code": 507})
			else:
				session['id'] = user.get('id')
				return jsonify({"code": 200, "user": user_manager.clear(user, clear=CLEAR_SELF)})
	else:
		return jsonify({"code": 400})

@app.route('/api/account/delete.json', methods=['POST'])
def acc_delete():
	if 'id' not in session:
		return jsonify({ "code": 401 })
	else:
		user_id = int(request.form.get('user_id'))
		if user_id == session['id']:
			user = user_manager.delete_user(uid=user_id)
			if user:
				return jsonify({"code": 200, "user": user, 'alerts': [{'body': f'User has been deleted', 'title': 'Info'}]})
			else:
				return jsonify({"code": 500})
		else:
			return jsonify({"code": 400})

@app.route('/api/account/show.json', methods=['GET'])
def account_show():
	if 'id' not in session:
		return json_response({ "code": 401 })

	user = user_manager.user(uid=session['id'], clear=CLEAR_SELF)
	if user:
		return jsonify({ "code": 200, "user": user })
	else:
		return jsonify({ "code": 404 })


#TODO Fix Search
@app.route('/user/current_kanojos.json', methods=['GET','POST'])
def user_currentkanojos():
	#kanojo_manager.server = request.url_root[:-1]
	kanojo_manager.server = server_url()[:-1]

	if 'id' not in session:
		return jsonify({ "code": 401 })

	prms = request.form if request.method == 'POST' else request.args
	if prms.get('user_id') is None or prms.get('index') is None or prms.get('limit') is None:
		return json_response({ "code": 400 })
	user_id = int(prms.get('user_id'))
	index = int(prms.get('index'))
	limit = int(prms.get('limit'))
	search = prms.get('search')
	user = user_manager.user(uid=user_id, clear=CLEAR_NONE)
	if user is None:
		return jsonify({ "code": 200, "user": user })

	rspns = {"code":200}

	kanojos_ids = user.get('kanojos')
	current_kanojos = []

	if search is not None:
		self_user = user_manager.user(uid=session['id'], clear=CLEAR_NONE)
		current_kanojos = kanojo_manager.kanojos(kanojo_ids=kanojos_ids, search=search, self_user=self_user, clear=CLEAR_NONE)
		if index < len(current_kanojos):
			current_kanojos = []
		else:
			if (index + limit) > len(current_kanojos):
				current_kanojos = current_kanojos[index:]
			else:
				current_kanojos = current_kanojos[index:index + limit]
			current_kanojos = kanojo_manager.fill_owners_info(current_kanojos, owner_users=(self_user, user), self_user=self_user)
		rspns['search_result'] = {'hit_count': len(current_kanojos)}
	elif index < len(kanojos_ids):
		if (index+limit) > len(kanojos_ids):
			kanojos_ids = kanojos_ids[index:]
		else:
			kanojos_ids = kanojos_ids[index:index+limit]
		self_user = user_manager.user(uid=session['id'], clear=CLEAR_NONE)
		current_kanojos = kanojo_manager.kanojos(kanojo_ids=kanojos_ids, search=search, self_user=self_user, clear=CLEAR_NONE)
		current_kanojos = kanojo_manager.fill_owners_info(current_kanojos, owner_users=(self_user, user), self_user=self_user)
	rspns['current_kanojos'] = current_kanojos
	rspns['user'] = user_manager.clear(user, CLEAR_OTHER, self_uid=session['id'])
	return json_response(rspns)

@app.route('/api/user/friend_kanojos.json', methods=['GET','POST'])
def user_friendkanojos():
	if 'id' not in session:
		return json_response({ "code": 401 })
	prms = request.form if request.method == 'POST' else request.args
	if prms.get('user_id') is None or prms.get('index') is None or prms.get('limit') is None:
		return json_response({ "code": 400 })
	user_id = int(prms.get('user_id'))
	index = int(prms.get('index'))
	limit = int(prms.get('limit'))
	search = prms.get('search')
	user = user_manager.user(uid=user_id, clear=CLEAR_NONE)
	if user is None:
		return json_response({ "code": 200, "user": None })
	rspns = { "code": 200 }

	kanojos_ids = user.get('friends')
	friend_kanojos = []
	if search is not None:
		self_user = user_manager.user(uid=session['id'], clear=CLEAR_NONE)
		friend_kanojos = kanojo_manager.kanojos(kanojo_ids=kanojos_ids, search=search, self_user=self_user, clear=CLEAR_NONE)
		if index < len(friend_kanojos):
			friend_kanojos = []
		else:
			if (index + limit) > len(friend_kanojos):
				friend_kanojos = friend_kanojos[index:]
			else:
				friend_kanojos = friend_kanojos[index:index + limit]
			user_ids = kanojo_manager.kanojos_owner_users(friend_kanojos)
			users = user_manager.users(user_ids, self_user=self_user)
			friend_kanojos = kanojo_manager.fill_owners_info(friend_kanojos, owner_users=users, self_user=self_user)
		rspns['search_result'] = {'hit_count':len(friend_kanojos)}
	elif index < len(kanojos_ids):
		if (index+limit) > len(kanojos_ids):
			kanojos_ids = kanojos_ids[index:]
		else:
			kanojos_ids = kanojos_ids[index:index+limit]
		self_user = user_manager.user(uid=session['id'], clear=CLEAR_NONE)
		friend_kanojos = kanojo_manager.kanojos(kanojo_ids=kanojos_ids, self_user=self_user, clear=CLEAR_NONE)

		user_ids = kanojo_manager.kanojos_owner_users(friend_kanojos)
		users = user_manager.users(user_ids, self_user=self_user)
		friend_kanojos = kanojo_manager.fill_owners_info(friend_kanojos, owner_users=users, self_user=self_user)
	rspns['friend_kanojos'] = friend_kanojos
	rspns['user'] = user_manager.clear(user, CLEAR_OTHER, self_uid=session['id'])
	return json_response(rspns)

@app.route('/api/kanojo/like_rankings.json', methods=['GET','POST'])
def kanojo_likerankings():
	if 'id' not in session:
		return json_response({ "code": 401 })
	prms = request.form if request.method == 'POST' else request.args
	if prms.get('index') is None or prms.get('limit') is None:
		return json_response({ "code": 400 })
	index = int(prms.get('index'))
	limit = int(prms.get('limit'))
	query = {}
	order = [
		('like_rate', -1),
		('id', -1),
	]
	kanojos = db.kanojos.find(query).sort(order).skip(index).limit(limit)
	self_user = user_manager.user(uid=session['id'], clear=CLEAR_NONE)
	rspns = { "code": 200 }
	like_ranking_kanojos = []
	for k in kanojos:
		like_ranking_kanojos.append(k)

	user_ids = kanojo_manager.kanojos_owner_users(like_ranking_kanojos)
	users = user_manager.users(user_ids, self_user=self_user)
	like_ranking_kanojos = kanojo_manager.fill_owners_info(like_ranking_kanojos, owner_users=users, self_user=self_user)

	rspns['like_ranking_kanojos'] = like_ranking_kanojos
	return jsonify(rspns)

@app.route('/api/kanojo/show.json', methods=['GET','POST'])
def kanojo_show():
	if 'id' not in session:
		return json_response({ "code": 401 })
	prms = request.form if request.method == 'POST' else request.args
	if prms.get('kanojo_id') is None or prms.get('screen') is None:
		return json_response({ "code": 400 })
	kanojo_id = int(prms.get('kanojo_id'))
	rspns = { "code": 200 }
	rspns['messages'] = {"notify_amendment_information": "This information is already used by other users.\nIf your amendment would be incorrect, you will be restricted user."}
	self_user = user_manager.user(uid=session['id'], clear=CLEAR_NONE)
	kanojo = kanojo_manager.kanojo(kanojo_id, self_user=self_user, clear=CLEAR_NONE)
	if kanojo:
		owner_user = user_manager.user(uid=kanojo.get('owner_user_id'), clear=CLEAR_NONE)
		rspns['kanojo'] = kanojo_manager.clear(kanojo, self_user, owner_user=owner_user, clear=CLEAR_OTHER, check_clothes=True)
		rspns['owner_user'] = user_manager.clear(owner_user, CLEAR_OTHER, self_user=self_user)

		rspns['product'] = as_product(kanojo)

		kanojo_date_alert = kanojo_manager.kanojo_date_alert(kanojo)
		if kanojo_date_alert:
			rspns['alerts'] = [ kanojo_date_alert, ]
	else:
		rspns = { "code": 404 }
		rspns['alerts'] = [{"body": "The Requested KANOJO was not found.", "title": ""}]
	return json_response(rspns)

@app.route('/user/enemy_users.json', methods=['GET','POST'])
def user_enemy_users():
	if 'id' not in session:
		return json_response({ "code": 401 })
	prms = request.form if request.method == 'POST' else request.args
	if prms.get('user_id') is None or prms.get('index') is None or prms.get('limit') is None:
		return json_response({ "code": 400 })
	user_id = int(prms.get('user_id'))
	index = int(prms.get('index'))
	limit = int(prms.get('limit'))
	user = user_manager.user(uid=user_id, clear=CLEAR_NONE)
	rspns = { "code": 200 }
	rspns['user'] = user_manager.clear(user, CLEAR_OTHER, self_uid=session['id'])
	enemy_users = []
	# TODO: get enemy users
	rspns['enemy_users'] = enemy_users
	return json_response(rspns)

@app.route('/api/communication/play_on_live2d.json', methods=['GET', 'POST'])
def communication_play_on_live2d():
	'''
		actions codes (reverse direction):
			10 - swipe
			11 - shake
			12 - touch head
			20 - kiss
			21 - touch breasts
	'''
	if 'id' not in session:
		return json_response({ "code": 401 })
	prms = request.form if request.method == 'POST' else request.args
	if prms.get('kanojo_id') is None or prms.get('actions') is None:
		return json_response({ "code": 400 })
	try:
		kanojo_id = int(prms.get('kanojo_id'))
	except ValueError:
		return json_response({ "code": 400 })
	actions = prms.get('actions')

	rspns = { "code": 200 }
	self_user = user_manager.user(uid=session['id'], clear=CLEAR_NONE)
	kanojo = kanojo_manager.kanojo(kanojo_id, self_user=self_user, clear=CLEAR_NONE)

	if kanojo:
		owner_user = user_manager.user(uid=kanojo.get('owner_user_id'), clear=CLEAR_NONE)
		rspns['owner_user'] = user_manager.clear(owner_user, CLEAR_OTHER, self_user=self_user)
		#url = request.url_root+'apibanner/kanojoroom/reactionword.html'
		url = server_url() + 'web/reactionword.html'

		if actions and len(actions):
			dt = user_manager.user_action(self_user, kanojo, action_string=actions, current_owner=owner_user)

			if 'love_increment' in dt and 'info' in dt:
				tmp = dt.get('info', {})
				prms = { key: tmp[key] for key in ['pod', 'a'] if key in tmp }
				dt['love_increment']['reaction_word'] = f'{url}?{urllib.parse.urlencode(prms)}'
				#print dt['love_increment']['reaction_word']
				dt.pop('info', None)

			rspns.update(dt)
		rspns['self_user'] = user_manager.clear(self_user, CLEAR_SELF, self_user=self_user)
		rspns['kanojo'] = kanojo_manager.clear(kanojo, self_user, clear=CLEAR_OTHER)
	else:
		rspns = { "code": 404 }
		rspns['alerts'] = [{"body": "The Requested KANOJO was not found.", "title": ""}]
	return json_response(rspns)

# this url builds in 'communication_play_on_live2d'
@app.route('/apibanner/kanojoroom/reactionword.html')
@app.route('/web/reactionword.html')
def apibanner_kanojoroom_reactionword():
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
	# TODO: add more text strings
	prms = request.args
	if prms.get('a') is None or prms.get('pod') is None:
		return json_response({ "code": 400 })
	try:
		a = int(prms.get('a'))
		pod = int(prms.get('pod'))
	except ValueError:
		return json_response({ "code": 400 })
	val = {
		'text': reactionword.reactionword_json(a, pod)
	}
	return render_template('apibanner_kanojoroom_reactionword.html', **val)

@app.route('/api/kanojo/vote_like.json', methods=['GET', 'POST'])
def kanojo_vote_like():
	if 'id' not in session:
		return json_response({ "code": 401 })
	prms = request.form if request.method == 'POST' else request.args
	if prms.get('kanojo_id') is None or prms.get('like') is None:
		return json_response({ "code": 400 })
	try:
		kanojo_id = int(prms.get('kanojo_id'))
		like = prms.get('like').lower() == 'true'
	except ValueError:
		return json_response({ "code": 400 })
	rspns = { "code": 200 }
	self_user = user_manager.user(uid=session['id'], clear=CLEAR_NONE)
	kanojo = kanojo_manager.kanojo(kanojo_id, self_user=self_user, clear=CLEAR_NONE)

	if not user_manager.set_like(self_user, kanojo, like, update_db_record=True):
		return json_response({"code": 500})

	rspns['kanojo'] = kanojo_manager.clear(kanojo, self_user, clear=CLEAR_OTHER)
	return json_response(rspns)

@app.route('/api/resource/product_category_list.json', methods=['GET','POST'])
def resource_product_category_list():
	if 'id' not in session:
		return jsonify({"code": 401})

	rspns = {"code": 200}
	with open('product_category_list.json') as json_file:
		rspns.update(json.load(json_file))
	#rspns['categories'] = [{"id": "1", "name": "Drink"}, {"id": "2", "name": "Food"}, {"id": "3", "name": "Snack"}, {"id": "4", "name": "Alcohol"}, {"id": "5", "name": "Beer"}, {"id": "6", "name": "Tabacco"}, {"id": "7", "name": "Magazines"}, {"id": "8", "name": "Stationary"}, {"id": "9", "name": "Industrial tool"}, {"id": "10", "name": "Electronics"}, {"id": "11", "name": "Kitchenware"}, {"id": "12", "name": "Clothes"}, {"id": "13", "name": "Accessory"}, {"id": "14", "name": "Music"}, {"id": "15", "name": "DVD"}, {"id": "16", "name": "TVgame"}, {"id": "17", "name": "Sports gear"}, {"id": "18", "name": "Health & beauty"}, {"id": "19", "name": "Medicine"}, {"id": "20", "name": "Medical supplies"}, {"id": "22", "name": "Book"}, {"id": "21", "name": "others"}]
	return jsonify(rspns)

@app.route('/activity/user_timeline.json', methods=['GET','POST'])
def activity_usertimeline():
	'''
		activity_type
			01 - ("Nightmare has scanned on 2014/10/04 05:31:50.\n")
			02 - ("Violet was generated from 星光産業 .")
			05 - Me add new friend ("Filter added 葵 to friend list.")
			07 - approached my kanojo  ("KH approached めりい.")
			08 - me stole kanojo ("Devourer stole うる from Nobody.")
			09 - my kanojo was stollen ("ふみえ was stolen by Nobody.")
			10 - other user added my kanojo ("呪いのBlu-ray added ぽいと to friend list.")
			11 - ("Everyone became Lev.\"99\".")
			15 - me married ("Devourer get married with うる.")
	'''
	'''
		rv = {
			'activities': [
				{
					'kanojo': null,
					'product': null,
					'user': null,
					'other_user': null,
					'activity': 'human readable string',
					'created_timestamp': 0,
					'id': 0,
					'activity_type': 0
				}
			]
		}
	'''
	if 'id' not in session:
		return json_response({ "code": 401 })
	prms = request.form if request.method == 'POST' else request.args
	if prms.get('index') is None or prms.get('limit') is None:
		return json_response({ "code": 400 })
	index = int(prms.get('index'))
	limit = int(prms.get('limit'))
	self_uid = session['id']
	try:
		user_id = int(prms.get('user_id', self_uid))
	except Exception as e:
		return json_response({ "code": 400 })

	activities = activity_manager.user_activity(user_id=user_id, skip=index, limit=limit)
	uids = activity_manager.user_ids(activities)
	kids = activity_manager.kanojo_ids(activities)

	self_user = user_manager.user(uid=self_uid, clear=CLEAR_NONE)
	kanojos = kanojo_manager.kanojos(kids, self_user, clear=CLEAR_NONE)

	user_ids = kanojo_manager.kanojos_owner_users(kanojos)
	if user_ids:
		uids.extend(user_ids)
		uids = list(set(uids))
	users = user_manager.users(uids, self_user=self_user)
	kanojos = kanojo_manager.fill_owners_info(kanojos, owner_users=users, self_user=self_user)

	activities = activity_manager.fill_activities(activities, users, kanojos, user_manager.default_user, kanojo_manager.default_kanojo)

	rspns = { "code": 200 }
	rspns['activities'] = activities
	#print json.dumps(rspns)
	return jsonify(rspns)


	#return json_response({"code": 200, "activities": []})
	data = {"activities": [{"kanojo": {"mascot_enabled": "0", "avatar_background_image_url": None, "in_room": True, "mouth_type": 1, "skin_color": 2, "body_type": 1, "race_type": 10, "spot_type": 1, "birth_day": 12, "sexual": 61, "id": 1, "relation_status": 2, "on_advertising": None, "clothes_type": 3, "brow_type": 10, "consumption": 17, "like_rate": 0, "eye_position": 0, "source": "", "location": "Somewhere", "birth_month": 10, "follower_count": 1, "goods_button_visible": True, "accessory_type": 1, "birth_year": 2014, "status": "Born in  12 Oct 2014 @ Somewhere. Area: Italy. 1 users are following.\nShe has relationship with id:1", "hair_type": 3, "clothes_color": 3, "ear_type": 1, "brow_position": 0, "barcode": "8028670007619", "love_gauge": 50, "profile_image_url": "https://192.168.1.19/profile_images/kanojo/1.png?w=88&h=88&face=true", "possession": 11, "eye_color": 5, "glasses_type": 1, "hair_color": 23, "face_type": 3, "nationality": "Italy", "advertising_product_url": None, "geo": "0.0000,0.0000", "emotion_status": 50, "voted_like": False, "eye_type": 101, "mouth_position": 0, "name": "\\u30f4\\u30a7\\u30eb\\u30c7", "fringe_type": 22, "nose_type": 1, "advertising_banner_url": None, "advertising_product_title": None, "recognition": 11}, "product": None, "user": {"friend_count": 0, "tickets": 20, "name": "everyone", "language": "en", "level": 1, "kanojo_count": 1, "money": 0, "stamina_max": 100, "facebook_connect": False, "profile_image_url": None, "sex": "not sure", "stamina": 100, "twitter_connect": False, "birth_month": 10, "id": 1, "birth_day": 11, "enemy_count": 0, "scan_count": 0, "email": None, "relation_status": 2, "birth_year": 2014, 'description': '', 'generate_count': 0, 'password': ''}, "other_user": {"friend_count": 0, "tickets": 20, "name": "id:1", "language": "en", "level": 1, "kanojo_count": 1, "money": 0, "stamina_max": 100, "facebook_connect": False, "profile_image_url": None, "sex": "not sure", "stamina": 100, "twitter_connect": False, "birth_month": 10, "id": 2, "birth_day": 11, "enemy_count": 0, "scan_count": 0, "email": None, "relation_status": 2, "birth_year": 2014, 'description': '', 'generate_count': 0, 'password': ''}, "activity": "AKI approached dsad.", "created_timestamp": 1413382843, "id": 16786677, "activity_type": 7}], "code": 200}
	return json_response(data)
	data = json.dumps(data)
	data = '''{"activities": [{"kanojo": {"mascot_enabled": "0", "avatar_background_image_url": null, "in_room": true, "mouth_type": 1, "skin_color": 2, "body_type": 1, "race_type": 10, "spot_type": 1, "birth_day": 12, "sexual": 61, "id": 1, "relation_status": 2, "on_advertising": null, "clothes_type": 3, "brow_type": 10, "consumption": 17, "like_rate": 0, "eye_position": 0, "source": "", "location": "Somewhere", "birth_month": 10, "follower_count": 1, "goods_button_visible": true, "accessory_type": 1, "birth_year": 2014, "status": "Born in  12 Oct 2014 @ Somewhere. Area: Italy. 1 users are following.\nShe has relationship with id:1", "hair_type": 3, "clothes_color": 3, "ear_type": 1, "brow_position": 0, "barcode": "8028670007619", "love_gauge": 50, "profile_image_url": "https://192.168.1.19/profile_images/kanojo/1.png?w=88&h=88&face=true", "possession": 11, "eye_color": 5, "glasses_type": 1, "hair_color": 23, "face_type": 3, "nationality": "Italy", "advertising_product_url": null, "geo": "0.0000,0.0000", "emotion_status": 50, "voted_like": false, "eye_type": 101, "mouth_position": 0, "name": "\\u30f4\\u30a7\\u30eb\\u30c7", "fringe_type": 22, "nose_type": 1, "advertising_banner_url": null, "advertising_product_title": null, "recognition": 11}, "product": null, "user": {"friend_count": 0, "tickets": 5, "name": "id:1", "language": "en", "level": 1, "kanojo_count": 1, "money": 0, "stamina_max": 100, "facebook_connect": false, "profile_image_url": null, "sex": "not sure", "stamina": 100, "twitter_connect": false, "birth_month": 10, "id": 1, "birth_day": 11, "enemy_count": 0, "scan_count": 0, "email": null, "relation_status": 2, "birth_year": 2014, 'description': '', 'generate_count': 0, 'password': ''}, "other_user": {"friend_count": 0, "tickets": 20, "name": "id:1", "language": "en", "level": 1, "kanojo_count": 1, "money": 0, "stamina_max": 100, "facebook_connect": false, "profile_image_url": null, "sex": "not sure", "stamina": 100, "twitter_connect": false, "birth_month": 10, "id": 1, "birth_day": 11, "enemy_count": 0, "scan_count": 0, "email": null, "relation_status": 2, "birth_year": 2014, 'description': '', 'generate_count': 0, 'password': ''}, "activity": "AKI approached dsad.", "created_timestamp": 1413382843, "id": 16786677, "activity_type": 7}], "code": 200}'''
	from gzip import GzipFile
	from io import BytesIO
	gzip_buffer = BytesIO()
	with GzipFile(mode='wb',
					compresslevel=6,
					fileobj=gzip_buffer) as gzip_file:
		gzip_file.write(data)
	response = Response()
	response.data = gzip_buffer.getvalue()
	response.headers['Content-Encoding'] = 'gzip'
	response.headers['Content-Length'] = response.content_length
	response.headers['Vary'] = 'Accept-Encoding'
	response.headers['Server'] = 'Apache'
	response.headers['Cache-Control'] = 'max-age=0, no-cache'
	response.headers['Keep-Alive'] = 'timeout=2, max=100'
	response.headers['X-Mod-Pagespeed'] = '1.6.29.7-3566'
	response.headers['Connection'] = 'Keep-Alive'
	return response

#http://www.barcodekanojo.com/profile_images/kanojo/625028/1289899377/non.png?w=50&h=50&face=true
@app.route('/profile_images/kanojo/<kid>/<crop>.png', methods=['GET'])
def profile_images_kanojo(kid, crop):
	# TODO: web
	prms = request.args
	size = prms.get('size', False)
	filename = f'profile_images/kanojo/{kid}/{crop}'
	if not os.path.isfile(filename+'.png'):
		print("Image not found at: ", filename)
		abort(404)
	else:
		if size:
			size = int(size)
			if not os.path.isfile(f'{filename}_{size}.png'):
				save_resized_image(filename, size)
			filename += f'_{size}'
		filename += '.png'
		if os.path.isfile(filename):
			return send_file(filename, mimetype='image/png')
		abort(500)

@app.route('/profile_images/user/<uid>.jpg', methods=['GET'])
def profile_images_user(uid):
	# TODO: web
	filename = f'profile_images/user/{uid}.jpg'
	if os.path.isfile(filename):
		return send_file(filename, mimetype='image/jpeg')
	abort(404)

#TODO Find way to moderate user submitted images
@app.route('/product_images/barcode/<barcode>.jpg', methods=['GET'])
def product_images_barcode(barcode):
	filename = f'product_images/barcode/{barcode}.jpg'
	if os.path.isfile(filename):
		return send_file(filename, mimetype='image/jpeg')
	abort(404)

@app.route('/api/notification/register_token.json', methods=['POST'])
def notification_register_token():
	if 'id' not in session:
		return json_response({ "code": 401 })
	time.sleep(1)
	return json_response({ "code": 200 })

@app.route('/api/message/dialog.json', methods=['GET'])
def api_message_dialog():
	if 'id' not in session:
		return jsonify({ "code": 401 })
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
	# TODO: add more text strings
	prms = request.args
	if prms.get('a') is None or prms.get('pod') is None:
		return jsonify({ "code": 400 })
	try:
		a = int(prms.get('a'))
		pod = int(prms.get('pod'))
	except ValueError:
		return jsonify({ "code": 400 })
	val = reactionword.reactionword_json(a, pod)
	returning = jsonify({ "code": 200,
						"kanojo_message": {
							"text": val,
							"btn_text": "Test"}})
	return returning

@app.route('/api/webview/chart.json', methods=['GET'])
def api_webview_chart():
	prms = request.args
	if prms.get('kanojo_id') is None:
		return json_response({ "code": 400 })
	kanojo_id = int(prms.get('kanojo_id'))
	rspns = { 'code': 200 }
	kanojo = kanojo_manager.kanojo(kanojo_id, None, clear=CLEAR_NONE)
	if kanojo:
		rspns['url'] = server_url()+ 'web/wv_chart.html?c=%d&j=%d&d=%d&s=%d&f=%d'%(kanojo.get('consumption')+100, kanojo.get('possession')+100, kanojo.get('recognition')+100, kanojo.get('sexual')+100, kanojo.get('flirtable',50)+100)
	else:
		rspns = { 'code': 404 }
	return json_response(rspns)

# this url build in 'api_webview_chart'
@app.route('/web/wv_chart.html', methods=['GET'])
def wv_chart():
	prms = request.args
	if prms.get('c') is None or prms.get('j') is None and prms.get('d') is None or prms.get('s') is None and prms.get('f') is None:
		return abort(400)
	val = {
		'celebrity': prms.get('c'),
		'jealousy': prms.get('j'),
		'dedication': prms.get('d'),
		'sexual': prms.get('s'),
		'flirtable': prms.get('f'),
	}
	return render_template('wv_chart.html', **val)

@app.route('/api/webview/show.json', methods=['GET'])
def api_webview_show():
	#print request.cookies
	if 'id' not in session:
		return json_response({ "code": 401 })
	prms = request.args
	if prms.get('uuid') is None:
		return json_response({ "code": 400 })
	rspns = { 'code': 200 }
	#rspns['url'] = request.url_root[7:] + 'web/i.html?user_id=%d'%session['id']
	rspns['url'] = server_url()[8:] + 'web/i.html?user_id=%d'%session['id']
	#rspns['url'] = 'www.ya.ru'
	#rspns = {"url": "www.barcodekanojo.com/wv_main?language=en&user_id=407529&uuid=UFMjIlUgVSdMUSBYWUxVVFUjTCNZIFZMJVYnVFdVJFEnIFQkAkI", "code": 200}
	response = json_response(rspns)
	#for key in request.cookies.keys():
	#    if key[:3] == '044':
	#        response.set_cookie(key, request.cookies.get(key))
	#response.mimetype = 'text/html'
	return response

# this url build in 'api_webview_show'
@app.route('/web/i.html', methods=['GET'])
def web_i():
	val = {}
	return render_template('index_m.html', **val)

@app.route('/api/barcode/query.json', methods=['GET', 'POST'])
def barcode_query():
	if 'id' not in session:
		return json_response({ "code": 401 })
	prms = request.form if request.method == 'POST' else request.args
	if prms.get('barcode') is None:
		return json_response({ "code": 400 })
	barcode = prms.get('barcode')
	session['barcode'] = barcode
	kanojo = kanojo_manager.kanojo_by_barcode(barcode)

	if kanojo is None or len(kanojo) == 0:
		# not found in db, search in barcode_tmp database
		bc = db.barcode_tmp.find_one( { 'barcode': barcode } )
		rspns = {
			"code": 200,
			"product": None,
			"scan_history": {"kanojo_count": 0, "friend_count": 0, "barcode": barcode, "total_count": 0},
			"messages": {
				"notify_amendment_information": "This information is already used by other users.\nIf your amendment would be incorrect, you will be restricted user.",
				"inform_girlfriend": "She is your KANOJO, and you have scanned this barcode 0times.",
				"inform_friend": "She belongs to , and you have scanned this barcode 0times.",
				"do_generate_kanojo": "Would you like to generate this KANOJO?\nIt requires 20 stamina.",
				"do_add_friend": "She belongs to no one.\nDo you want to add her on your friend list ? It requires 5 stamina."
			},
		}
		if bc:
			bc.pop('_id', None)
			rspns["barcode"] = bc
		else:
			bc_info = kanojo_manager.generate(barcode)
			if bc_info:
				rspns["barcode"] = bc_info
				bc = copy.deepcopy(bc_info)
				bc['timestamp'] = int(time.time())
				db.barcode_tmp.insert_one(bc)
			else:
				rspns = {
					"code": 400,
					"exception": "",
					"alerts": [
						{"body": "Barcode error", "title": ""}
					]
				}
	else:
		kanojo = kanojo[0]
		owner_user = user_manager.user(uid=kanojo.get('owner_user_id'), clear=CLEAR_NONE)
		if owner_user is None:
			owner_user = user_manager.default_user
		self_user = user_manager.user(uid=session['id'], clear=CLEAR_NONE)

		kid = kanojo.get('id')
		if kid in self_user.get('kanojos') or kid in self_user.get('friends'):
			user_manager.scan_kanojo(self_user, kanojo)

		rspns = { 'code': 200 }
		#barcode = '************'
		rspns['product'] = as_product(kanojo)
		rspns['scan_history'] = {"kanojo_count": 0, "friend_count": 0, "barcode": barcode, "total_count": 0}
		rspns['messages'] = {
			"notify_amendment_information": "This information is already used by other users.\nIf your amendment would be incorrect, you will be restricted user.",
			"inform_girlfriend": "She is your KANOJO.",
			"inform_friend": f"She belongs to {owner_user.get('name')}, and your friend.",
			"do_generate_kanojo": "Would you like to generate this KANOJO?\nIt requires 20 stamina.",
			"do_add_friend": f"She belongs to {owner_user.get('name')}.\nDo you want to add her on your friend list? It requires 0 stamina."
		}
		rspns['barcode'] = as_barcode(kanojo)
		rspns['kanojo'] = kanojo_manager.clear(kanojo, self_user, clear=CLEAR_SELF)
		rspns['owner_user'] = user_manager.clear(owner_user, CLEAR_OTHER, self_user=self_user)
	return json_response(rspns)

# curl -v -k --trace-ascii curl.trace -x http://192.168.1.41:8888 -include --form barcode=8028670007619 --form asd=zxc http://192.168.1.19:5000/2/barcode/scan.json
@app.route('/api/barcode/scan.json', methods=['POST'])
@set_parsers(BKMultipartParser)
def barcode_scan():
	if 'id' not in session:
		return json_response({ "code": 401 })
	parser = BKMultipartParser()
	options = {
		'content_length': request.headers.get('content_length')
	}
	(prms, files) = parser.parse(request.stream.read(), request.headers.get('Content-Type'), **options)
	if prms.get('barcode') is None or prms.get('barcode') != session.get('barcode'):
		return json_response({ "code": 400 })
	session.pop('barcode', None)
	barcode = prms.get('barcode')
	kanojos = kanojo_manager.kanojo_by_barcode(barcode)
	if kanojos is None or len(kanojos) == 0:
		rspns = {
			"code": 404,
			"exception": "",
			"alerts": [
				{"body": "Kanojo don't found.", "title": ""}
			]
		}
	else:
		uid = session['id']
		if 'product_image_data' in files:
			f = files['product_image_data']
			save_product_image(f.stream, barcode)

		self_user = user_manager.user(uid=uid, clear=CLEAR_NONE)
		for k in kanojos:
			user_manager.add_kanojo_as_friend(self_user, k)
			user_manager.scan_kanojo(self_user, k)
		rspns = { 'code': 200 }
		rspns['user'] = user_manager.clear(self_user, CLEAR_SELF, self_user=self_user)
	return json_response(rspns)

@app.route('/api/barcode/decrease_generating.json', methods=['GET'])
def barcode_decrease_generating():
	if 'id' not in session:
		return json_response({ "code": 401 })
	prms = request.args
	barcode = prms.get('barcode')
	uid = session['id']
	self_user = user_manager.user(uid=uid, clear=CLEAR_NONE)
	rspns = { 'code': 200 }
	rspns['user'] = user_manager.clear(self_user, CLEAR_SELF, self_user=self_user)
	#rspns['product'] = { 'category': 'Industrial tool', 'company_name': 'wakaba', 'name': 'test', 'price': '$9.95', 'product': 'iichan', 'product_image_url': 'http://www.deviantsart.com/g3629d.png' }
	rspns['product'] = { 'category': 'Industrial tool', 'company_name': 'wakaba', 'name': None, 'price': '$9.95', 'product': 'iichan', 'product_image_url': None }
	return json_response(rspns)

@app.route('/api/barcode/scan_and_generate.json', methods=['POST'])
@set_parsers(BKMultipartParser)
def barcode_scan_and_generate():
	if 'id' not in session:
		return json_response({ "code": 401 })
	parser = BKMultipartParser()
	options = {
		'content_length': request.headers.get('content_length')
	}
	(prms, files) = parser.parse(request.stream.read(), request.headers.get('Content-Type'), **options)
	if 'barcode' not in prms or 'kanojo_name' not in prms or 'kanojo_profile_image_data' not in files:
		return json_response({ "code": 400 })

	rspns = { 'code': 200 }
	barcode = prms.get('barcode')
	uid = session['id']

	kanojo = kanojo_manager.kanojo_by_barcode(barcode)
	if kanojo:
		rspns = { "code": 409, "love_increment": { "alertShow": 1 }, "alerts": [ { "body": "Kanojo with this barcode already exists.", "title": "" } ] }
		return json_response(rspns)

	self_user = user_manager.user(uid=uid, clear=CLEAR_NONE)
	bc_info = db.barcode_tmp.find_one({ 'barcode': barcode })

	if bc_info:

		kanojo = user_manager.create_kanojo_from_barcode(self_user, bc_info, prms)
		if kanojo:
			f = files['kanojo_profile_image_data']
			save_kanojo_profile_image(f.stream, kanojo['id'])

			if 'product_image_data' in files:
				f = files['product_image_data']
				save_product_image(f.stream, barcode)

			rspns['kanojo'] = kanojo_manager.clear(kanojo, self_user, clear=CLEAR_OTHER, check_clothes=True)
			rspns['user'] = user_manager.clear(self_user, CLEAR_SELF, self_user=self_user)
			db.barcode_tmp.delete_one(bc_info)
		else:
			rspns = { "code": 403, "love_increment": { "alertShow": 1 }, "alerts": [ { "body": "You don't have enough stamina.", "title": "" } ] }
	else:
		rspns = { 'code': 404 }

	return jsonify(rspns)

#TODO Need password verification in here
@app.route('/api/account/update.json', methods=['POST'])
@set_parsers(BKMultipartParser)
def account_update():
	if 'id' not in session:
		return json_response({ "code": 401 })
	parser = BKMultipartParser()
	options = {
		'content_length': request.headers.get('content_length')
	}
	(prms, files) = parser.parse(request.stream.read(), request.headers.get('Content-Type'), **options)

	uid = session['id']
	self_user = user_manager.user(uid=uid, clear=CLEAR_NONE)

	updated = False
	if 'name' in prms:
		self_user['name'] = prms['name']
		updated = True
	if 'new_password' in prms and (('current_password' in prms and self_user['password'] == prms['current_password']) or self_user['password'] == ''):
		self_user['password'] = prms['new_password']
		updated = True
	if 'email' in prms:
		newEmail = prms['email'].lower()
		if newEmail != self_user['email']:
			query = {
				"email": {
					"$exists": True,
					"$eq": newEmail
				}
			}
			existing_user = db.users.find_one(query)
			if existing_user:
				return jsonify({"code": 400, "alerts": [{"body": "Email already in use.", "title": ""}]})
			else:
				self_user['email'] = prms['email']
				updated = True
	if 'birth_year' in prms and 'birth_month' in prms and 'birth_day' in prms:
		self_user['birthday'] = int(time.mktime(time.strptime('%s-%s-%s 12:00:00'%(prms['birth_year'], prms['birth_month'], prms['birth_day'] ), '%Y-%m-%d %H:%M:%S'))) - time.timezone
		updated = True
	if 'sex' in prms:
		self_user['sex'] = prms['sex']
		updated = True
	if 'profile_image_data' in files:
		f = files['profile_image_data']
		save_user_profile_image(f.stream, uid)
		updated = True

	if updated:
		user_manager.save(self_user)

	rspns = {'code': 200,
				"alerts": [{"body": "Your account have been saved.", "title": ""}],
				'user': user_manager.clear(self_user, CLEAR_SELF, self_user=self_user)}
	return jsonify(rspns)

@app.route('/api/activity/scanned_timeline.json', methods=['GET'])
def activity_scanned_timeline():
	'''
	'''
	if 'id' not in session:
		return json_response({ "code": 401 })
	prms = request.args
	if 'barcode' not in prms or 'index' not in prms and 'limit' not in prms:# or not prms.has_key('since_id'):
		return json_response({ "code": 400 })
	barcode = prms.get('barcode')
	try:
		index = int(prms.get('index'))
		limit = int(prms.get('limit'))
	except ValueError as e:
		return json_response({ "code": 400 })
	# TODO: logic
	rspns = { 'code': 200 }
	rspns['activities'] = []
	return json_response(rspns)

@app.route('/api/barcode/update.json', methods=['POST'])
@set_parsers(BKMultipartParser)
#TODO: Update Kanojo image here?
def barcode_update():
	'''
		update product info
	'''
	if 'id' not in session:
		return json_response({ "code": 401 })
	parser = BKMultipartParser()
	options = {
		'content_length': request.headers.get('content_length')
	}
	(prms, files) = parser.parse(request.stream.read(), request.headers.get('Content-Type'), **options)
	if prms.get('barcode') is None:
		return json_response({"code": 400})
	barcode = prms.get('barcode')
	kanojo = kanojo_manager.kanojo_by_barcode(barcode)

	if kanojo is None or len(kanojo) == 0:
		rspns = {"code": 404}
		rspns['alerts'] = [{"body": "The Requested KANOJO was not found.", "title": ""}]
	else:
		if 'product_image_data' in files:
			f = files['product_image_data']
			save_product_image(f.stream, barcode)

		kanojo = kanojo[0]
		kanojo['company_name'] = prms.get('company_name')
		kanojo['product_name'] = prms.get('product_name')
		kanojo['product_category_id'] = prms.get('product_category_id')
		kanojo['product_comment'] = prms.get('product_comment')
		#TODO: Deal with geo
		if kanojo_manager.save(kanojo):
			rspns = {'code': 200}
		else:
			rspns = {"code": 500}
			rspns['alerts'] = [{"body": "KANOJO data could not be saved.", "title": "Internal Server Error"}]

	return json_response(rspns)


@app.route('/api/communication/store_items.json', methods=['GET'])
def communication_store_items():
	'''
		item_class: 1 - items, 2 - date, 3 - tickets
	'''
	if 'id' not in session:
		return json_response({ "code": 401 })
	prms = request.args
	if 'item_class' not in prms or 'item_category_id' not in prms:
		return json_response({ "code": 400 })
	try:
		item_class = int(prms.get('item_class'))
		item_category_id = int(prms.get('item_category_id'))
	except ValueError:
		return json_response({ "code": 400 })
	rspns = { 'code': 200 }

	# TODO: show ticket items
	self_user = user_manager.user(uid=session['id'], clear=CLEAR_NONE)
	if item_class == 3:
		rspns['item_categories'] = []
	elif item_class==1:
		rspns['item_categories'] = store.category_goods(item_category_id, has_items=user_manager.user_items(self_user))
	elif item_class==2:
		rspns['item_categories'] = store.category_dates(item_category_id, has_items=user_manager.user_items(self_user))
	return json_response(rspns)

@app.route('/api/communication/date_list.json', methods=['GET'])
def communication_date_list():
	'''
		type_id - 1 (store, can buy this items), 2 - belongings list
		kanojo_id - kanojo_id
	'''
	if 'id' not in session:
		return json_response({ "code": 401 })
	prms = request.args
	if 'type_id' not in prms or 'kanojo_id' not in prms:
		return json_response({ "code": 400 })
	try:
		type_id = int(prms.get('type_id'))
		kanojo_id = int(prms.get('kanojo_id'))
	except ValueError as e:
		return json_response({ "code": 400 })

	rspns = { 'code': 200 }

	kanojo = kanojo_manager.kanojo(kanojo_id, None, clear=CLEAR_NONE)
	self_user = user_manager.user(uid=session['id'], clear=CLEAR_NONE)
	# Find Relationship level
	kanojo_relation = RELATION_OTHER
	if session['id'] == kanojo.get('owner_user_id'):
		kanojo_relation = RELATION_KANOJO
	elif session['id'] in kanojo.get('followers', []):
		kanojo_relation = RELATION_FRIEND

	if type_id == TYPE_STORE:
		rspns['item_categories'] = store.dates_list(kanojo_relation, user_level=self_user.get('level'))
	elif type_id == TYPE_ITEM_LIST:
		has_items = user_manager.user_items(self_user)
		if has_items:
			rspns['item_categories'] = store.dates_list(kanojo_relation, user_level=self_user.get('level'), filter_has_items=True, has_items=has_items)
		else:
			rspns['item_categories'] = []

	return json_response(rspns)

@app.route('/shopping/compare_price.json', methods=['GET', 'POST'])
def shopping_compare_price():
	if 'id' not in session:
		return json_response({ "code": 401 })
	prms = request.form if request.method == 'POST' else request.args
	if 'store_item_id' not in prms or 'price' not in prms:
		return json_response({ "code": 400 })
	try:
		store_item_id = int(prms.get('store_item_id'))
		price = int(prms.get('price'))
	except ValueError as e:
		return json_response({ "code": 400 })

	self_user = user_manager.user(uid=session['id'], clear=CLEAR_NONE)
	rspns = { 'code': 200 }
	#  Client work with commented lines
	#rspns['store_item_id'] = store_item_id
	#rspns['use_ticket'] = price
	#rspns['numbers_ticket'] = self_user.get('tickets', 0)
	return json_response(rspns)

@app.route('/api/communication/item_list.json', methods=['GET'])
def communication_item_list():
	'''
		type_id - 1 (can buy), 2 - belongings list
		kanojo_id - kanojo_id
	'''
	if 'id' not in session:
		return json_response({ "code": 401 })
	prms = request.args
	if 'type_id' not in prms or 'kanojo_id' not in prms:
		return json_response({ "code": 400 })
	try:
		type_id = int(prms.get('type_id'))
		kanojo_id = int(prms.get('kanojo_id'))
	except ValueError:
		return json_response({ "code": 400 })
	rspns = { 'code': 200 }

	kanojo = kanojo_manager.kanojo(kanojo_id, None, clear=CLEAR_NONE)
	self_user = user_manager.user(uid=session['id'], clear=CLEAR_NONE)
	kanojo_relation = RELATION_OTHER
	if kanojo.get('owner_user_id') == session['id']:
		kanojo_relation = RELATION_KANOJO
	elif session['id'] in kanojo.get('followers', []):
		kanojo_relation = RELATION_FRIEND
	if type_id == GIFT_ITEM_CLASS:
		rspns['item_categories'] = store.goods_list(kanojo_relation, user_level=self_user.get('level'))
	elif type_id == DATE_ITEM_CLASS:
		has_items = user_manager.user_items(self_user)
		if has_items:
			rspns['item_categories'] = store.goods_list(kanojo_relation, user_level=self_user.get('level'), filter_has_items=True, has_items=has_items)
		else:
			rspns['item_categories'] = []
	return json_response(rspns)

@app.route('/communication/has_items.json', methods=['GET'])
def communication_has_items():
	'''
		item_class: 1 - items, 2 - date
	'''
	if 'id' not in session:
		return json_response({ "code": 401 })
	prms = request.args
	if 'item_class' not in prms or 'item_category_id' not in prms:
		return json_response({ "code": 400 })
	try:
		item_class = int(prms.get('item_class'))
		item_category_id = int(prms.get('item_category_id'))
	except ValueError as e:
		return json_response({ "code": 400 })
	rspns = { 'code': 200 }

	self_user = user_manager.user(uid=session['id'], clear=CLEAR_NONE)
	has_items = user_manager.user_items(self_user)
	if item_class == 3:
		rspns['item_categories'] = []
	elif item_class==1:
		if has_items:
			rspns['item_categories'] = store.category_goods(item_category_id, filter_has_items=True, has_items=has_items)
		else:
			rspns['item_categories'] = []
	elif item_class==2:
		if has_items:
			rspns['item_categories'] = store.category_dates(item_category_id, filter_has_items=True, has_items=has_items)
		else:
			rspns['item_categories'] = []
	return json_response(rspns)

@app.route('/communication/do_gift.json', methods=['GET', 'POST'])
def communication_do_gift():
	if 'id' not in session:
		return json_response({ "code": 401 })
	prms = request.form if request.method == 'POST' else request.args
	if 'basic_item_id' not in prms or 'kanojo_id' not in prms:
		return json_response({ "code": 400 })
	try:
		basic_item_id = int(prms.get('basic_item_id'))
		kanojo_id = int(prms.get('kanojo_id'))
	except ValueError as e:
		return json_response({ "code": 400 })

	kanojo = kanojo_manager.kanojo(kanojo_id, None, clear=CLEAR_NONE)
	self_user = user_manager.user(uid=session['id'], clear=CLEAR_NONE)
	owner_user = user_manager.user(uid=kanojo.get('owner_user_id'), clear=CLEAR_NONE)

	rspns = { 'code': 200 }
	rspns['owner_user'] = user_manager.clear(owner_user, CLEAR_OTHER, self_user=self_user)
	url = server_url() + 'web/reactionword.html'
	do_gift = user_manager.user_action(user=self_user, kanojo=kanojo, do_gift=basic_item_id, is_extended_action=False)
	if 'love_increment' in do_gift and 'info' in do_gift:
		tmp = do_gift.get('info', {})
		prms = { key: tmp[key] for key in ['pod', 'a'] if key in tmp }
		do_gift['love_increment']['reaction_word'] = f'{url}?{urllib.parse.urlencode(prms)}'
		do_gift.pop('info', None)
	rspns.update(do_gift)
	rspns['self_user'] = user_manager.clear(self_user, CLEAR_SELF, self_user=self_user)
	if kanojo.get('owner_user_id') != session['id']:
		rspns['owner_user'] = user_manager.user(uid=kanojo.get('owner_user_id'), clear=CLEAR_OTHER)
	else:
		rspns['owner_user'] = user_manager.clear(self_user, CLEAR_OTHER, self_user=self_user)
	return json_response(rspns)

@app.route('/shopping/verify_tickets.json', methods=['GET', 'POST'])
def shopping_verify_tickets():
	"""
		buy extend gift/date
	"""
	if 'id' not in session:
		return json_response({ "code": 401 })
	prms = request.form if request.method == 'POST' else request.args
	if 'store_item_id' not in prms or 'use_tickets' not in prms:
		return json_response({ "code": 400 })
	try:
		store_item_id = int(prms.get('store_item_id'))
		use_tickets = int(prms.get('use_tickets'))
	except ValueError as e:
		return json_response({ "code": 400 })

	rspns = { 'code': 200 }
	self_user = user_manager.user(uid=session['id'], clear=CLEAR_NONE)
	item_type = store.item_type(store_item_id)

	buy_present = None
	if item_type==GIFT_ITEM_CLASS:
		buy_present = user_manager.user_action(self_user, None, do_gift=store_item_id, is_extended_action=True)
	elif item_type==DATE_ITEM_CLASS:
		buy_present = user_manager.user_action(self_user, None, do_date=store_item_id, is_extended_action=True)
	else:
		rspns = { 'code': 400 }
	rspns.update(buy_present)
	return json_response(rspns)

@app.route('/communication/do_extend_gift.json', methods=['GET', 'POST'])
def communication_do_extend_gift():
	if 'id' not in session:
		return json_response({ "code": 401 })
	prms = request.form if request.method == 'POST' else request.args
	if 'extend_item_id' not in prms or 'kanojo_id' not in prms:
		return json_response({ "code": 400 })
	try:
		extend_item_id = int(prms.get('extend_item_id'))
		kanojo_id = int(prms.get('kanojo_id'))
	except ValueError as e:
		return json_response({ "code": 400 })

	kanojo = kanojo_manager.kanojo(kanojo_id, None, clear=CLEAR_NONE)
	self_user = user_manager.user(uid=session['id'], clear=CLEAR_NONE)
	owner_user = user_manager.user(uid=kanojo.get('owner_user_id'), clear=CLEAR_NONE)

	rspns = { 'code': 200 }
	rspns['owner_user'] = user_manager.clear(owner_user, CLEAR_OTHER, self_user=self_user)
	url = server_url() + 'web/reactionword.html'
	give_present = user_manager.give_present(self_user, kanojo, extend_item_id)
	if 'love_increment' in give_present and 'info' in give_present:
		tmp = give_present.get('info', {})
		prms = { key: tmp[key] for key in ['pod', 'a'] if key in tmp }
		give_present['love_increment']['reaction_word'] = '%s?%s'%(url, urllib.parse.urlencode(prms))
		give_present.pop('info', None)
	rspns.update(give_present)
	rspns['kanojo'] = kanojo_manager.clear(kanojo, self_user, clear=CLEAR_OTHER, check_clothes=True)
	rspns['self_user'] = user_manager.clear(self_user, CLEAR_SELF, self_user=self_user)
	if kanojo.get('owner_user_id') != session['id']:
		rspns['owner_user'] = user_manager.user(uid=kanojo.get('owner_user_id'), clear=CLEAR_OTHER)
	else:
		rspns['owner_user'] = user_manager.clear(self_user, CLEAR_OTHER, self_user=self_user)
	return json_response(rspns)

@app.route('/communication/do_date.json', methods=['GET', 'POST'])
def communication_do_date():
	if 'id' not in session:
		return json_response({ "code": 401 })
	prms = request.form if request.method == 'POST' else request.args
	if 'basic_item_id' not in prms or 'kanojo_id' not in prms:
		return json_response({ "code": 400 })
	try:
		basic_item_id = int(prms.get('basic_item_id'))
		kanojo_id = int(prms.get('kanojo_id'))
	except ValueError as e:
		return json_response({ "code": 400 })

	kanojo = kanojo_manager.kanojo(kanojo_id, None, clear=CLEAR_NONE)
	self_user = user_manager.user(uid=session['id'], clear=CLEAR_NONE)
	owner_user = user_manager.user(uid=kanojo.get('owner_user_id'), clear=CLEAR_NONE)

	rspns = {'code':200,
			'owner_user':user_manager.clear(owner_user, CLEAR_OTHER, self_user=self_user)}
	url = server_url() + 'web/reactionword.html'
	do_date = user_manager.user_action(user=self_user, kanojo=kanojo, do_date=basic_item_id, is_extended_action=False)
	if 'love_increment' in do_date and 'info' in do_date:
		tmp = do_date.get('info', {})
		prms = { key: tmp[key] for key in ['pod', 'a'] if key in tmp }
		do_date['love_increment']['reaction_word'] = '%s?%s'%(url, urllib.parse.urlencode(prms))
		do_date.pop('info', None)
	rspns.update(do_date)
	rspns['self_user'] = user_manager.clear(self_user, CLEAR_SELF, self_user=self_user)
	if kanojo.get('owner_user_id') != session['id']:
		rspns['owner_user'] = user_manager.user(uid=kanojo.get('owner_user_id'), clear=CLEAR_OTHER)
	else:
		rspns['owner_user'] = user_manager.clear(self_user, CLEAR_OTHER, self_user=self_user)
	return json_response(rspns)

@app.route('/communication/do_extend_date.json', methods=['GET', 'POST'])
def communication_do_extend_date():
	if 'id' not in session:
		return json_response({ "code": 401 })
	prms = request.form if request.method == 'POST' else request.args
	if 'extend_item_id' not in prms or 'kanojo_id' not in prms:
		return json_response({ "code": 400 })
	try:
		extend_item_id = int(prms.get('extend_item_id'))
		kanojo_id = int(prms.get('kanojo_id'))
	except ValueError as e:
		return json_response({ "code": 400 })

	kanojo = kanojo_manager.kanojo(kanojo_id, None, clear=CLEAR_NONE)
	self_user = user_manager.user(uid=session['id'], clear=CLEAR_NONE)
	owner_user = user_manager.user(uid=kanojo.get('owner_user_id'), clear=CLEAR_NONE)

	rspns = { 'code': 200 }
	rspns['owner_user'] = user_manager.clear(owner_user, CLEAR_OTHER, self_user=self_user)
	url = server_url() + 'web/reactionword.html'
	do_date = user_manager.do_date(self_user, kanojo, extend_item_id)
	if 'love_increment' in do_date and 'info' in do_date:
		tmp = do_date.get('info', {})
		prms = { key: tmp[key] for key in ['pod', 'a'] if key in tmp }
		do_date['love_increment']['reaction_word'] = '%s?%s'%(url, urllib.parse.urlencode(prms))
		do_date.pop('info', None)
	rspns.update(do_date)
	rspns['kanojo'] = kanojo_manager.clear(kanojo, self_user, clear=CLEAR_OTHER, check_clothes=True)
	rspns['self_user'] = user_manager.clear(self_user, CLEAR_SELF, self_user=self_user)
	if kanojo.get('owner_user_id') != session['id']:
		rspns['owner_user'] = user_manager.user(uid=kanojo.get('owner_user_id'), clear=CLEAR_OTHER)
	else:
		rspns['owner_user'] = user_manager.clear(self_user, CLEAR_OTHER, self_user=self_user)
	return json_response(rspns)

# --------  CRON  --------

#@sched.scheduled_job('interval', minutes=10)
def update_stamina_job():
	for user in db.users.find():
		if (user_manager.user_change(user, up_stamina=True, update_db_record=True)):
			print('Recover stamina \"%s\"(id:%d) Stamina:%d'%(user.get('name'), user.get('id'), user.get('stamina')))

def test_job():
	print(int(time.time()))

# Update Stamina ever 2 minutes
sched = BackgroundScheduler()
sched.add_job(update_stamina_job, 'interval', minutes=2, id='update_stamina_job', replace_existing=True)
#sched.add_job(test_job, 'interval', seconds=30)
sched.start()
atexit.register(lambda: sched.shutdown())

if __name__ == "__main__":
	#app.run(host='0.0.0.0', port=443, ssl_context=context)
	if config.USE_HTTPS:
		app.run(host=config.HOST, port=config.PORT, ssl_context=context)
	else:
		app.run(host=config.HOST, port=config.PORT)
	#app.run(host='localhost')
