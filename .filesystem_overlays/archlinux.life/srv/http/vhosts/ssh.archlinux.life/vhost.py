import slimHTTP

def on_request(request):
	if not 'ssh_uids' in slimHTTP.internal.storage:
		slimHTTP.internal.storage['ssh_uids'] = {}

	if b'uid' in request.headers[b'URI_QUERY']:
		uid = request.headers[b'URI_QUERY'][b'uid']

		if request.headers[b'METHOD'] == b'PUT':
			if request.headers[b'URL'] == '/ssh-reg/':
				slimHTTP.internal.storage['ssh_uids'][uid] = time.time()
				print(f'[ssh.hvornum.se] Registered temporary session for {uid}')
				return slimHTTP.HTTP_RESPONSE(ret_code=204)

		elif request.headers[b'METHOD'] == b'GET':
			if request.headers[b'URL'] == '/ssh-check/':
				print(f'[ssh.hvornum.se] Returning status for {uid}')
				response = {'status' : slimHTTP.internal.storage['ssh_uids'][uid] is True}
				return slimHTTP.HTTP_RESPONSE(ret_code=200, headers={'Content-Type' : 'application/json'}, payload=bytes(json.dumps(response), 'UTF-8'))

			elif request.headers[b'URL'] == '/ssh-verify/':
				print(f'[ssh.hvornum.se] Session for {uid} is now verified.')
				slimHTTP.internal.storage['ssh_uids'][uid] = True
				return slimHTTP.HTTP_RESPONSE(ret_code=204)

	return None