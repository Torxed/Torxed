import slimHTTP
import slimDNS
import json
import tarfile
import os
import git
import shutil
import glob
import time
import urllib.request
from subprocess import Popen, PIPE, STDOUT

security_keys = {
	'<pre shared key>' : 'daylight'
}

def on_request(request):
	if len(request.payload):
		try:
			request_data = json.loads(request.payload.decode('UTF-8'))
		except:
			return None

		if 'pre_shared_key' not in request_data:
			return None

		if request_data['pre_shared_key'] not in security_keys:
			return None

		if 'request' in request_data:
			if request_data['request'] == 'get-domains':
				domains = json.dumps(
					{
						"domains" : [
										filter_domain for filter_domain in {
											'.'.join(domain.split('.')[-2:]) for domain in slimDNS.storage['instances'][":53-UDP"].database.keys()
										} if filter_domain != 'in-addr.arpa'
									]
					}
				)
				return slimHTTP.HTTP_RESPONSE(headers={'Access-Control-Allow-Origin' : 'https://api.archlinux.life', 'Content-Type' : 'application/json'},
												payload=bytes(domains, 'UTF-8'))
			
			elif request_data['request'] == 'get-records':
				return slimHTTP.HTTP_RESPONSE(headers={'Access-Control-Allow-Origin' : 'https://api.archlinux.life', 'Content-Type' : 'application/json'},
												payload=bytes(json.dumps({"domains" : slimDNS.storage['instances'][":53-UDP"].database}), 'UTF-8'))

			elif request_data['request'] == 'update-record':
				domain = request_data['domain']
				record_type = request_data['type']

				for instances in slimDNS.storage['instances']:
					if not slimDNS.storage['instances'][instances].update(domain, record_type, target=request_data['target'], ttl=60):
						if not slimDNS.storage['instances'][instances].add(domain, record_type, target=request_data['target'], ttl=60):
							print(f' ! Failed to add new record in {instances}')
						else:
							print(f' [x] Added new record in {instances}')
					else:
						print(f" - Updated existing record in {instances}: {domain} -> {request_data['target']}")

				return slimHTTP.HTTP_RESPONSE(headers={'Access-Control-Allow-Origin' : 'https://api.archlinux.life', 'Content-Type' : 'application/json'},
												payload=bytes(json.dumps({"status" : "ok"}), 'UTF-8'))
