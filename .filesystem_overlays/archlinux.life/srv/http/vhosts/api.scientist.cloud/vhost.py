import slimHTTP
import BankID
import time
import json
import psycopg2
import psycopg2.extras
import traceback
import ipaddress
import base64
import os
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

http = slimHTTP.instances[':443']

db_host = '10.0.2.2'
db_user = 'scientist'
db_name = 'scientist'
db_password = '<db password>'

build_times = {
	'custom' : 5,
	'vbike' : 3
}

DEBUG=False

class DBWorker:
	def __init__(self):
		self.con = psycopg2.connect(f"host={db_host} dbname={db_name} user={db_user} password={db_password}")
		self.con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

	def __enter__(self):
		self.cur = self.con.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

		global DEBUG
		if DEBUG:
			self.cur.execute("DROP TABLE products;")
			self.cur.execute("DROP TABLE payment_statuses;")
			self.cur.execute("DROP TABLE orders;")
			self.cur.execute("DROP TABLE identities;")
			self.cur.execute("DROP TABLE client_sessions;")

		self.cur.execute("CREATE TABLE IF NOT EXISTS client_sessions (id SERIAL PRIMARY KEY, ip INET NOT NULL, personalNumber VARCHAR(13) NOT NULL, occured TIMESTAMP DEFAULT CURRENT_TIMESTAMP);")
		self.cur.execute("CREATE TABLE IF NOT EXISTS products (id SERIAL PRIMARY KEY, product_name VARCHAR(50) NOT NULL, price REAL NOT NULL, UNIQUE(product_name));")
		self.cur.execute("CREATE TABLE IF NOT EXISTS payment_statuses (id SERIAL, description VARCHAR(20) NOT NULL, UNIQUE(description));")
		self.cur.execute("CREATE TABLE IF NOT EXISTS payments (id SERIAL, ammount REAL NOT NULL, order_number INT NOT NULL, occured TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(ammount, order_number, occured));")
		self.cur.execute("CREATE TABLE IF NOT EXISTS status_changes (id SERIAL, order_number INT NOT NULL, previous VARCHAR(20), new VARCHAR(20) NOT NULL, comment VARCHAR(500), occured TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(order_number, new, occured));")
		self.cur.execute("CREATE TABLE IF NOT EXISTS identities (id SERIAL, verified BOOLEAN DEFAULT FALSE, personalNumber VARCHAR(13) NOT NULL UNIQUE, givenName VARCHAR(250), surName VARCHAR(250), phoneNumber VARCHAR(10) NOT NULL, email VARCHAR(250) NOT NULL, identified_on_ip INET, PRIMARY KEY (id, personalNumber));")
		self.cur.execute("CREATE TABLE IF NOT EXISTS orders (id SERIAL, product_id INT NOT NULL, status INT, owner INT NOT NULL, payment_status INT NOT NULL, orderSpecs JSONB NOT NULL, PRIMARY KEY (id, product_id));")
		
		if DEBUG:
			self.cur.execute("INSERT INTO payment_statuses (description) VALUES('unpaid');")
			self.cur.execute("INSERT INTO products (product_name, price) VALUES('custom', 50000);")
			self.cur.execute("INSERT INTO products (product_name, price) VALUES('vbike', 80000);")

		DEBUG = False

		return self.cur

	def __exit__(self, *args, **kwargs):
		self.cur.close()
		self.con.close()

def get_lead_time(model='custom'):
	with DBWorker() as cur:
		cur.execute(f"SELECT count(id) FROM orders WHERE status != (SELECT id FROM status_changes WHERE new='waiting' LIMIT 1);")
		for row in cur:
			return f"{max(row['count'], 1)*build_times.get(model.lower(), 4)} weeks"

def _method(request):
	return request.headers[b'METHOD']

def pre_flight_check(request):
	method = _method(request)
	if method == b'OPTIONS':
		## https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS
		response = b''
		response += b'HTTP/1.1 204 No Content\r\n'
		response += b'Allow: POST, GET\r\n'
		response += b'Cache-Control: max-age=604800\r\n'
		response += b'Access-Control-Allow-Origin: https://scientist.cloud\r\n'
		response += b'Access-Control-Allow-Headers: Content-Type, Accept\r\n'
		response += b'\r\n'
		return response

def ip_is_spamming(ip, socialSecurity, insert_on_check=True):
	with DBWorker() as cur:
		print("Checking if someone's started BankID within 1 min with this IP:", ip)
		cur.execute(f"SELECT count(id) FROM client_sessions WHERE ip=%s AND now() - INTERVAL '1 minute' < occured LIMIT 1;", (str(ip),))
		for row in cur:
			if row['count']:
				return True

		if insert_on_check:
			cur.execute(f"INSERT INTO client_sessions (ip, personalNumber) VALUES (%s, %s);", (str(ip), socialSecurity))

	return False

@http.route('/reserve', vhost='api.scientist.cloud')
def reserve(request):
	if pre_flight := pre_flight_check(request):
		return pre_flight

	if _method(request) == b'POST':
		session = BankID.BankID()
		socialSecurity = request.data['personalNumber']

		print(request)
		"""
		{
		    "personalNumber": "0011223344",
		    "phoneNumber": "0700000000",
		    "email": "anton@domain.lan",
		    "orderDetails": {
		        "longRange": true,
		        "motorUpgrade": false,
		        "quickChargers": true,
		        "existingChassi": false
		    },
		    "endUserIp": "127.0.0.1",
		    "userVisibleData": "RXZpbCBTY2llbnRpc3QgLSBNb3RvcmN5Y2xlIFJlc2VydmF0aW9uIDE="
		}
		"""

		if ip_is_spamming(ipaddress.ip_address(request.CLIENT_IDENTITY.address), socialSecurity):
			return request.build_headers({'Access-Control-Allow-Origin' : 'https://scientist.cloud', 'Content-Typet' : 'application/json'}) + bytes(json.dumps({'status' : 'internally-aborted', 'hintCode' : 'Too many BankID attempts!'}), 'UTF-8')

		print(f"Placing an order for: {request.data}")
		#traceback.print_stack()

		with DBWorker() as cur:
			cur.execute(f"SELECT id FROM identities WHERE personalNumber=%s", (socialSecurity,))
			if not cur.rowcount:
				cur.execute(f"INSERT INTO identities (personalNumber, phoneNumber, email) VALUES (%s, %s, %s)", (socialSecurity, request.data['phoneNumber'], request.data['email']))
				
			cur.execute(f"INSERT INTO orders (product_id, owner, payment_status, orderSpecs) VALUES ((SELECT id FROM products WHERE product_name=%s), (SELECT id FROM identities WHERE personalNumber=%s), (SELECT id FROM payment_statuses WHERE description='unpaid'), %s)", (
				request.data['orderDetails']['option'].lower(),
				socialSecurity,
				json.dumps(request.data['orderDetails'])
			))

			cur.execute(f"INSERT INTO status_changes (order_number, new) VALUES (%s, %s)", (1, "pending-signature"))

		information = session.sign(socialSecurity, host=request.data['endUserIp'])
		print('Order is placed:', information)
		return request.build_headers({'Access-Control-Allow-Origin' : 'https://scientist.cloud', 'Content-Typet' : 'application/json'}) + bytes(json.dumps({'status' : 'pending', 'orderRef' : information.get('orderRef')}), 'UTF-8')

@http.route('/getReservationStatus', vhost='api.scientist.cloud')
def getReservationStatus(request):
	if pre_flight := pre_flight_check(request):
		return pre_flight

	# if ip_is_spamming(ipaddress.ip_address(request.CLIENT_IDENTITY.address), None, insert_on_check=False):
	# 	return request.build_headers({'Access-Control-Allow-Origin' : 'https://scientist.cloud', 'Content-Typet' : 'application/json'}) + bytes(json.dumps({'status' : 'internally-aborted', 'hintCode' : 'Too many BankID attempts!'}), 'UTF-8')

	if _method(request) == b'POST':
		session = BankID.BankID()

		print("Checking status on order:", request.data)
		order_status = session.collect(request.data['orderRef'])
		"""
		{
		    "orderRef": "XXXXXXXX-YYYY-ZZZZ-ÅÅÅÅ-ÄÄÄÄÄÄÄÄÄÄÄÄ",
		    "status": "complete",
		    "completionData": {
		        "user": {
		            "personalNumber": "000011223344",
		            "name": "Full Name",
		            "givenName": "Full Given Name",
		            "surname": "Surname"
		        },
		        "device": {
		            "ipAddress": "Ip Of Signer"
		        },
		        "cert": {
		            "notBefore": "1626732000000",
		            "notAfter": "1658354399000"
		        },
		        "signature": "..."
		    }
		}
		"""
		if 'completionData' in order_status:
			with DBWorker() as cur:
				cur.execute(f"UPDATE identities SET verified=TRUE, givenName=%s, surName=%s, identified_on_ip=%s WHERE personalNumber=%s", (
					order_status['completionData']['user']['givenName'],
					order_status['completionData']['user']['surname'],
					str(ipaddress.ip_address(order_status['completionData']['device']['ipAddress'])),
					order_status['completionData']['user']['personalNumber']
				))

		return request.build_headers({'Access-Control-Allow-Origin' : 'https://scientist.cloud', 'Content-Typet' : 'application/json'}) + bytes(json.dumps(order_status), 'UTF-8')

@http.route('/leadTime', vhost='api.scientist.cloud')
def leadTime(request):
	if pre_flight := pre_flight_check(request):
		return pre_flight

	if _method(request) == b'POST':
		return request.build_headers({'Access-Control-Allow-Origin' : 'https://scientist.cloud', 'Content-Typet' : 'application/json'}) + bytes(json.dumps({'status' : 'ok', 'wait_time' : get_lead_time(request.data.get('model'))}), 'UTF-8')
	else:
		print('Unknown method:', _method(request))

	return request.build_headers()

accounts = {
	'anton' : {
		'pwdata' : {
			'salt' : 'somesalt',
			'iv' : 'salted',
			'pw' : 'hashed pw'
		},
		'access_tokens' : {

		}
	}
}
tokens = {
	
}

def random_base64(length=20):
	return base64.b64encode(bytes(str(time.time()), 'UTF-8')+os.urandom(length)).decode('UTF-8')

@http.route('/authenticate', vhost='api.scientist.cloud')
def leadTime(request):
	if pre_flight := pre_flight_check(request):
		return pre_flight

	if _method(request) == b'POST':
		if (user := request.data.get('user', None)) in accounts and (password := request.data.get('password', None)):
			if accounts[user]['pwdata']['pw'] == password:
				token = random_base64()
				tokens[token] = user
				accounts[user]['access_tokens'][token] = {}
				return request.build_headers({'Access-Control-Allow-Origin' : 'https://scientist.cloud', 'Content-Typet' : 'application/json'}) + bytes(json.dumps({'status' : 'ready', 'token' : token}), 'UTF-8')
		elif (user := request.data.get('user', None)) in accounts:
			return request.build_headers({'Access-Control-Allow-Origin' : 'https://scientist.cloud', 'Content-Typet' : 'application/json'}) + bytes(json.dumps({'status' : 'ready', 'salt' : accounts[user]['pwdata']['salt'], 'iv' : accounts[user]['pwdata']['iv']}), 'UTF-8')

@http.route('/orderHistory', vhost='api.scientist.cloud')
def leadTime(request):
	if pre_flight := pre_flight_check(request):
		return pre_flight

	if _method(request) == b'POST':
		if (token := request.data.get('token', None)) in tokens:
			user = tokens[request.data['token']]

			with DBWorker() as cur:
				cur.execute(f"SELECT identities.email, products.product_name, orders.orderspecs FROM products, orders, identities WHERE orders.product_id=products.id AND orders.owner=identities.id AND identities.verified=TRUE;")
				if cur.rowcount:
					return request.build_headers({'Access-Control-Allow-Origin' : 'https://scientist.cloud', 'Content-Typet' : 'application/json'}) + bytes(json.dumps({
						'status' : 'ready',
						'orders' : cur.fetchall()
					}), 'UTF-8')

			return request.build_headers({'Access-Control-Allow-Origin' : 'https://scientist.cloud', 'Content-Typet' : 'application/json'}) + bytes(json.dumps({'status' : 'ready', 'orders' : []}), 'UTF-8')
		else:
			return request.build_headers()