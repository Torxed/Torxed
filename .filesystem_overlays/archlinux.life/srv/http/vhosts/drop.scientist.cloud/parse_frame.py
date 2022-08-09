import os
import random
import time
import hashlib
import slimWS

if not 'drop.scientist.cloud' in slimWS.storage:
	slimWS.storage['drop.scientist.cloud'] = {
		'sessions' : {}
	}

def drop_old_session(requested_id):
	if not requested_id in slimWS.storage['drop.scientist.cloud']['sessions']:
		return True
	else:
		for connected_to in slimWS.storage['drop.scientist.cloud']['sessions'][requested_id]['connected_to']:
			if connected_to in slimWS.storage['drop.scientist.cloud']['sessions']:
				slimWS.storage['drop.scientist.cloud']['sessions'][connected_to]['identity'].send({
					'disconnect' : requested_id
				})

def on_request(frame):
	if 'action' in frame.data and frame.data['action'] == 'register':
		attempts = 0
		session_id = None
		while session_id is None and attempts < 9999:
			potential_id = random.randint(1000, 9999)
			if potential_id not in slimWS.storage['drop.scientist.cloud']['sessions']:
				session_id = potential_id
				break
			elif time.time() - slimWS.storage['drop.scientist.cloud']['sessions'][potential_id]['last_seen'] > 60:
				if drop_old_session(potential_id):
					session_id = potential_id
					break

			attempts += 1

		if session_id:
			slimWS.storage['drop.scientist.cloud']['sessions'][session_id] = {'identity' : frame.CLIENT_IDENTITY, 'session_token' : hashlib.sha512(os.urandom(24)).hexdigest(), 'last_seen' : time.time(), 'connected_to' : []}

			return {
				'action' : 'registered',
				'session_id' : session_id
			}
	elif 'session_id' in frame.data and 'from_session' in frame.data:
		if frame.data['from_session'] in slimWS.storage['drop.scientist.cloud']['sessions']:
			from_session = frame.data['from_session']
			session_id = frame.data['session_id']

			sender_session = slimWS.storage['drop.scientist.cloud']['sessions'][from_session]
			
			if sender_session['identity'].fileno == frame.CLIENT_IDENTITY.fileno or sender_session['identity'].address == frame.CLIENT_IDENTITY.address:
				if type(session_id) is int and session_id in slimWS.storage['drop.scientist.cloud']['sessions']:
					if slimWS.storage['drop.scientist.cloud']['sessions'][session_id]['identity'].send({**frame.data, 'session_token' : slimWS.storage['drop.scientist.cloud']['sessions'][session_id]['session_token']}) == 0:
						print(f'Error sending data from {from_session} to session {session_id}. Shutting session down!')
						slimWS.storage['drop.scientist.cloud']['sessions'][session_id]['identity'].close()
						del(slimWS.storage['drop.scientist.cloud']['sessions'][session_id])