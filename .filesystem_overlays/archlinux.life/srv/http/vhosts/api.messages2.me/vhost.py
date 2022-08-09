import base64
import os
import time
import json
import psycopg2
import psycopg2.extras
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

import slimHTTP

http = slimHTTP.instances[':443']

database_settings = {
	'hostname' : '10.0.2.2',
	'database' : 'messages2me',
	'username' : 'messages2me',
	'password' : '<db password>'
}

DEBUG = True

class DBWorker:
	def __init__(self, hostname, database, username, password):
		self.con = psycopg2.connect(f"host={hostname} dbname={database} user={username} password={password}")
		self.con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
		self.debug = DEBUG

	def on_enter(self):
		pass

	def on_exit(self):
		pass

	def __enter__(self):
		self.cur = self.con.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

		self.on_enter()

		return self.cur

	def __exit__(self, *args, **kwargs):
		self.on_exit()
		self.cur.close()

	def close(self):
		self.con.close()

class AttendanceWorker(DBWorker):
	def __init__(self, *args, **kwargs):
		DBWorker.__init__(self, *args, **kwargs)

	def on_enter(self):
		if self.debug:
			self.cur.execute("DROP TABLE IF EXISTS attendances;")

		self.cur.execute("CREATE TABLE IF NOT EXISTS attendances (id SERIAL, identity INT NOT NULL, room INT NOT NULL, active BOOLEAN DEFAULT FALSE, joined TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(identity, room), UNIQUE(identity, active), PRIMARY KEY(identity, room));")

		if self.debug:
			self.cur.execute("INSERT INTO attendances (identity, room, active) VALUES (1, 1, TRUE);")
			self.cur.execute("INSERT INTO attendances (identity, room, active) VALUES (2, 1, TRUE);")

		self.debug = False

class RoomWorker(DBWorker):
	def __init__(self, *args, **kwargs):
		DBWorker.__init__(self, *args, **kwargs)

	def on_enter(self):

		if self.debug:
			self.cur.execute("DROP TABLE IF EXISTS rooms;")

			self.cur.execute("CREATE TABLE IF NOT EXISTS rooms (id SERIAL PRIMARY KEY, identity VARCHAR(133) NOT NULL, homeserver INT NOT NULL, database_handle VARCHAR NOT NULL, UNIQUE(identity, homeserver));")
			self.cur.execute("INSERT INTO rooms (identity, homeserver, database_handle) VALUES ('room_ac38b550266f6268ed35fb5e71ada7f8950feb08f26477d1c7a1274fcd5746f2da59b9ccca1a9fdd746ebfb6706bfa4eb75d11930a6185c6b86122d6ab4c1ed0', 1, '10.0.2.2');")
	
		self.debug = False

class Room1Worker(DBWorker):
	def __init__(self, *args, **kwargs):
		DBWorker.__init__(self, *args, **kwargs)
		temp_cursor = self.con.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
		temp_cursor.execute(f"SELECT 'CREATE DATABASE room_ac38b550266f6268ed35fb5e71ada7f8950feb08f26477d1c7a1274fcd5746f2da59b9ccca1a9fdd746ebfb6706bfa4eb75d11930a6185c6b86122d6ab4c1ed0 OWNER {kwargs['username']}' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'room_ac38b550266f6268ed35fb5e71ada7f8950feb08f26477d1c7a1274fcd5746f2da59b9ccca1a9fdd746ebfb6706bfa4eb75d11930a6185c6b86122d6ab4c1ed0')")

	def on_enter(self):

		if self.debug:
			self.cur.execute("DROP TABLE IF EXISTS messages;")
			self.cur.execute("DROP TABLE IF EXISTS members;")
			self.cur.execute("DROP TABLE IF EXISTS room_meta;")

			self.cur.execute("CREATE TABLE IF NOT EXISTS members (id SERIAL PRIMARY KEY, identity INT, role VARCHAR(25), UNIQUE(identity, role));")
			self.cur.execute("CREATE TABLE IF NOT EXISTS messages (id SERIAL PRIMARY KEY, message_id VARCHAR(128) NOT NULL, sender INT, reciever INT, data VARCHAR, delivered TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(message_id));")

			self.cur.execute("INSERT INTO members (identity, role) VALUES (1, 'creator');")
			self.cur.execute("INSERT INTO members (identity, role) VALUES (2, 'member');")
			self.cur.execute("INSERT INTO members (identity, role) VALUES (3, 'member');")

			self.cur.execute("INSERT INTO messages (message_id, sender, reciever, data) VALUES ('1', 2, 1, '{\"message\":\"this is a message\"}');")
			self.cur.execute("INSERT INTO messages (message_id, sender, reciever, data) VALUES ('2', 2, 2, '{\"message\":\"this is a message\"}');")
			self.cur.execute("INSERT INTO messages (message_id, sender, reciever, data) VALUES ('3', 2, 1, '{\"message\":\"this is a second message\"}');")
			self.cur.execute("INSERT INTO messages (message_id, sender, reciever, data) VALUES ('4', 2, 2, '{\"message\":\"this is a second message\"}');")

		self.cur.execute("CREATE TABLE IF NOT EXISTS room_meta (id SERIAL PRIMARY KEY, identity VARCHAR(128) NOT NULL, created TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(identity));")
	
		if self.debug:
			self.cur.execute("INSERT INTO room_meta (identity) VALUES ('The Saloon');")
	
		self.debug = False

class Identities(DBWorker):
	def __init__(self, *args, **kwargs):
		DBWorker.__init__(self, *args, **kwargs)

	def on_enter(self):
		if self.debug:
			self.cur.execute("DROP TABLE IF EXISTS identities;")
			self.cur.execute("DROP TABLE IF EXISTS client_sessions;")
			self.cur.execute("DROP TABLE IF EXISTS credentials;")
			self.cur.execute("DROP TABLE IF EXISTS homeservers;")
		
		self.cur.execute("CREATE TABLE IF NOT EXISTS homeservers (id SERIAL, identity VARCHAR NOT NULL UNIQUE, address VARCHAR NOT NULL, updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (id, identity));")
		self.cur.execute("CREATE TABLE IF NOT EXISTS client_sessions (id SERIAL, ip INET NOT NULL, token VARCHAR(254) NOT NULL, identity INT NOT NULL, created TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(ip, token), PRIMARY KEY (id, ip, token, identity));")
		self.cur.execute("CREATE TABLE IF NOT EXISTS identities (id SERIAL, verified BOOLEAN DEFAULT FALSE, identity VARCHAR NOT NULL, homeserver INT, displayname VARCHAR(250), contact_info VARCHAR(250) NOT NULL, verified_on_ip INET, created TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(identity, homeserver), PRIMARY KEY (id, identity, homeserver));")
		self.cur.execute("CREATE TABLE IF NOT EXISTS credentials (id SERIAL, identity INT NOT NULL UNIQUE, salt VARCHAR(20) NOT NULL, iv VARCHAR(20) NOT NULL, pw_hash VARCHAR NOT NULL, updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (id, identity));")

		if self.debug:
			self.cur.execute("INSERT INTO homeservers (identity, address) VALUES ('messages2.me', '10.0.2.2');")
			self.cur.execute("INSERT INTO homeservers (identity, address) VALUES ('riot.hvornum.se', 'hvornum.se');")

			self.cur.execute("INSERT INTO identities (identity, displayname, contact_info, homeserver) VALUES ('anton', 'Anton', 'anton@messages2.me', 1);")
			self.cur.execute("INSERT INTO credentials (identity, salt, iv, pw_hash) VALUES (1, '80a84204c5a8a7686e56', '86e569f789977ab0d0ba', 'kZYaHEx5Giji0btKWrfGrFraeVc=');")

			self.cur.execute("INSERT INTO identities (identity, displayname, contact_info, homeserver) VALUES ('wifu', 'Wifu', 'wifu@messages2.me', 1);")
			self.cur.execute("INSERT INTO credentials (identity, salt, iv, pw_hash) VALUES (2, '80a84204c5a8a7686e56', '86e569f789977ab0d0ba', 'kZYaHEx5Giji0btKWrfGrFraeVc=');")

			self.cur.execute("INSERT INTO identities (identity, displayname, contact_info, homeserver) VALUES ('botalainen', 'Bot Botalainen', 'bot@messages2.me', 2);")
			self.cur.execute("INSERT INTO credentials (identity, salt, iv, pw_hash) VALUES (3, '80a84204c5a8a7686e56', '86e569f789977ab0d0ba', 'kZYaHEx5Giji0btKWrfGrFraeVc=');")
		
		self.debug = False

def get_homeserver(reciever):
	with IW as session:
		session.execute("SELECT homeservers.identity, homeservers.address FROM homeservers, identities WHERE identities.homeserver=homeservers.id AND identities.id=%s", (reciever,))
		for row in session:
			return row

def get_room_homeserver(room_id):
	with RW as session:
		session.execute("SELECT rooms.identity, homeservers.address, rooms.database_handle FROM rooms, homeservers WHERE rooms.homeserver=homeservers.id AND rooms.identity=%s", (room_id,))
		for row in session:
			return row


room_workers = {
}
AW = AttendanceWorker(**database_settings)
IW = Identities(**database_settings)
RW = RoomWorker(**database_settings)

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
		response += b'Access-Control-Allow-Origin: https://messages2.me\r\n'
		response += b'Access-Control-Allow-Headers: Content-Type, Accept\r\n'
		response += b'\r\n'
		return response

def random_base64(length=20):
	return base64.b64encode(bytes(str(time.time()), 'UTF-8')+os.urandom(length)).decode('UTF-8')

def token_to_identity(token):
	if token:
		with IW as session:
			session.execute("SELECT identity FROM client_sessions WHERE token=%s;", (token,))
			if session.rowcount:
				return session.fetchone()['identity']

@http.route('/authenticate', vhost='api.messages2.me')
def authenticate(request):
	if pre_flight := pre_flight_check(request):
		return pre_flight

	if _method(request) == b'POST':
		if (user := request.data.get('user', None)):
			with IW as session:
				session.execute("SELECT identities.identity, identities.displayname, credentials.salt, credentials.iv, credentials.pw_hash FROM identities, credentials WHERE credentials.identity=identities.id AND identities.identity=%s;", (user,))
				if session.rowcount:
					user_info = session.fetchone()
					if not (password := request.data.get('password', None)):
						return request.build_headers({'Access-Control-Allow-Origin' : 'https://messages2.me', 'Content-Typet' : 'application/json'}) + bytes(json.dumps({
							'status' : 'ready',
							'salt' : user_info['salt'],
							'iv' : user_info['iv']
						}), 'UTF-8')
					elif password == user_info['pw_hash']:
						token = random_base64()
						session.execute("INSERT INTO client_sessions (ip, token, identity) VALUES (%s, %s, (SELECT id FROM identities WHERE identity=%s));", (str(request.CLIENT_IDENTITY.address), token, user))
						return request.build_headers({'Access-Control-Allow-Origin' : 'https://messages2.me', 'Content-Typet' : 'application/json'}) + bytes(json.dumps({'status' : 'success', 'token' : token}), 'UTF-8')

				print(f"Incorrect username or password from database records ({session.rowcount}): {username} & {password}")

	return request.build_headers({'Access-Control-Allow-Origin' : 'https://messages2.me', 'Content-Typet' : 'application/json'}) + bytes(json.dumps({'status' : 'failed', 'details' : "Unable to authenticate."}), 'UTF-8')

@http.route('/getRooms', vhost='api.messages2.me')
def getRooms(request):
	if pre_flight := pre_flight_check(request):
		return pre_flight

	if _method(request) == b'POST':
		if not (user_id := token_to_identity(request.data.get('token', None))):
			return request.build_headers({'Access-Control-Allow-Origin' : 'https://messages2.me', 'Content-Typet' : 'application/json'}) + bytes(json.dumps({'status' : 'failed', 'details' : "Unable to get rooms."}), 'UTF-8')

		rooms = {}
		if (homeserver := get_homeserver(user_id))['address'] == '10.0.2.2':
			with AW as attendance_session:
				attendance_session.execute("SELECT rooms.identity, attendances.active FROM rooms, attendances WHERE attendances.room=rooms.id AND attendances.identity=%s;", (user_id,))
				for room in attendance_session:
					room_id = room['identity']
					
					rooms[room_id] = {
						'members' : {},
						'messages' : [],
						'meta' : {
							'active' : room['active']
						}
					}

					if (homeserver := get_room_homeserver(room_id))['address'] == '10.0.2.2':
						if not room_id in room_workers:
							room_workers[room_id] = Room1Worker(**{**database_settings, 'hostname' : homeserver['database_handle']})

						with room_workers[room_id] as room_worker:
							room_worker.execute("SELECT identity, role FROM members;")
							members = {}
							for member in room_worker.fetchall():
								with IW as identity:
									print(member)
									
									identity.execute("SELECT identities.displayname FROM identities, credentials WHERE credentials.identity=%s AND credentials.identity=identities.id", (member['identity'],))
									members[member['identity']] = {
										'identity' : member['identity'],
										'displayname' : identity.fetchone()['displayname'],
										'role' : member['role']
									}

							room_worker.execute("SELECT id, message_id, sender, data FROM messages WHERE reciever=%s ORDER BY delivered ASC LIMIT 100;", (user_id,))
							messages = room_worker.fetchall()

							room_worker.execute("SELECT identity FROM room_meta;")
							room_meta = room_worker.fetchone()

							rooms[room_id]['meta'] |= room_meta
							rooms[room_id]['members'] = members
							rooms[room_id]['messages'] = messages
					else:
						print(f"Getting room information from external homeserver: {homeserver}")
		else:
			print(f"Getting rooms for external users {user_id} via homeserver: {homeserver}")

		return request.build_headers({'Access-Control-Allow-Origin' : 'https://messages2.me', 'Content-Typet' : 'application/json'}) + bytes(json.dumps({
			'status' : 'success',
			'rooms' : rooms
		}), 'UTF-8')

	return request.build_headers({'Access-Control-Allow-Origin' : 'https://messages2.me', 'Content-Typet' : 'application/json'}) + bytes(json.dumps({'status' : 'failed', 'details' : "Unable to get rooms."}), 'UTF-8')

@http.route('/getMembers', vhost='api.messages2.me')
def getMembers(request):
	if pre_flight := pre_flight_check(request):
		return pre_flight

	if _method(request) == b'POST':
		if not (user_id := token_to_identity(request.data.get('token', None))) or (room_id := request.data.get('room_id', None)) is None:
			return request.build_headers({'Access-Control-Allow-Origin' : 'https://messages2.me', 'Content-Typet' : 'application/json'}) + bytes(json.dumps({'status' : 'failed', 'details' : "Unable to get room members."}), 'UTF-8')

		if (homeserver := get_room_homeserver(room_id))['address'] == '10.0.2.2':
			if not room_id in room_workers:
				room_workers[room_id] = Room1Worker(**{**database_settings, 'hostname' : homeserver['database_handle']})

			with room_workers[room_id] as room_worker:
				room_worker.execute("SELECT identity, role FROM members;")
				members = room_worker.fetchall()
				rooms[room_id]['members'] = members
		else:
			print(f"Getting rooms for external room {room_id} via homeserver: {homeserver}")

		return request.build_headers({'Access-Control-Allow-Origin' : 'https://messages2.me', 'Content-Typet' : 'application/json'}) + bytes(json.dumps({
			'status' : 'success',
			'room_id' : room_id,
			'members' : members
		}), 'UTF-8')

	return request.build_headers({'Access-Control-Allow-Origin' : 'https://messages2.me', 'Content-Typet' : 'application/json'}) + bytes(json.dumps({'status' : 'failed', 'details' : "Unable to get room members."}), 'UTF-8')

@http.route('/getMessages', vhost='api.messages2.me')
def getMessages(request):
	if pre_flight := pre_flight_check(request):
		return pre_flight

	if _method(request) == b'POST':
		if not (user_id := token_to_identity(request.data.get('token', None))) or (room_id := request.data.get('room_id', None)) is None:
			return request.build_headers({'Access-Control-Allow-Origin' : 'https://messages2.me', 'Content-Typet' : 'application/json'}) + bytes(json.dumps({'status' : 'failed', 'details' : "Unable to get room messages."}), 'UTF-8')

		if (homeserver := get_room_homeserver(room_id))['address'] == '10.0.2.2':
			if not room_id in room_workers:
				room_workers[room_id] = Room1Worker(**{**database_settings, 'hostname' : homeserver['database_handle']})

			if request.data.get('from_id', None):
				sql_string = "SELECT id, message_id, sender, data FROM messages WHERE reciever=%s AND id > %s ORDER BY delivered ASC LIMIT 100;"
				sql_arguments = (user_id, request.data['from_id'])
			else:
				sql_string = "SELECT id, message_id, sender, data FROM messages WHERE reciever=%s ORDER BY delivered ASC LIMIT 100;"
				sql_arguments = (user_id,)

			messages = []
			with room_workers[room_id] as room_worker:
				room_worker.execute(sql_string, sql_arguments)
				messages = room_worker.fetchall()
		else:
			print(f"Requesting messages from external homeserver {homeserver}")

		return request.build_headers({'Access-Control-Allow-Origin' : 'https://messages2.me', 'Content-Typet' : 'application/json'}) + bytes(json.dumps({
			'status' : 'success',
			'room_id' : room_id,
			'messages' : messages
		}), 'UTF-8')

	return request.build_headers({'Access-Control-Allow-Origin' : 'https://messages2.me', 'Content-Typet' : 'application/json'}) + bytes(json.dumps({'status' : 'failed', 'details' : "Unable to get room messages."}), 'UTF-8')


@http.route('/sendMessage', vhost='api.messages2.me')
def sendMessage(request):
	if pre_flight := pre_flight_check(request):
		return pre_flight

	if _method(request) == b'POST':
		if not (user_id := token_to_identity(request.data.get('token', None))) or (room_id := request.data.get('room_id', None)) is None:
			return request.build_headers({'Access-Control-Allow-Origin' : 'https://messages2.me', 'Content-Typet' : 'application/json'}) + bytes(json.dumps({'status' : 'failed', 'details' : "Unable to deliver messages."}), 'UTF-8')

		if (homeserver := get_room_homeserver(room_id))['address'] == '10.0.2.2':
			if not room_id in room_workers:
				room_workers[room_id] = Room1Worker(**{**database_settings, 'hostname' : homeserver['database_handle']})

			with room_workers[request.data['room_id']] as room_worker:
				message_id = random_base64()
				room_worker.execute("INSERT INTO messages (message_id, sender, reciever, data) VALUES (%s, %s, %s, %s);", (
					message_id,
					token_to_identity(request.data['token']),
					request.data['reciever'],
					json.dumps(request.data['data'])
				))

			if room_worker.rowcount:
				return request.build_headers({'Access-Control-Allow-Origin' : 'https://messages2.me', 'Content-Typet' : 'application/json'}) + bytes(json.dumps({
					'status' : 'success',
					'message_id' : message_id,
					'details' : "message has been delivered"
				}), 'UTF-8')
		else:
			print(f"Relaying message to external homeserver: {homeserver}")

	return request.build_headers({'Access-Control-Allow-Origin' : 'https://messages2.me', 'Content-Typet' : 'application/json'}) + bytes(json.dumps({'status' : 'failed', 'details' : "Unable to deliver messages."}), 'UTF-8')