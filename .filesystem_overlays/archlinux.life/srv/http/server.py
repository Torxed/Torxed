import os

import slimHTTP
import slimDNS
import slimWS

import logging
import sys

root = logging.getLogger()
root.setLevel(logging.DEBUG)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
root.addHandler(handler)

http = slimHTTP.server(slimHTTP.HTTP)
https = slimHTTP.server(slimHTTP.HTTPS)
dns = slimDNS.server(slimDNS.UDP)
dns_tcp = slimDNS.server(slimDNS.TCP)
websocket = slimWS.WebSocket()

def config(instance):
	return {
		'web_root' : './vhosts/default',
		'index' : 'index.html',
		'ssl' : {
			'cert' : '/etc/certificates/fullchain.pem',
			'key' : '/etc/certificates/privkey.pem',
		},
		'vhosts' : {
			# Hvornum .se
			'hvornum.se' : {
				'web_root' : './vhosts/hvornum.se',
				'index' : 'index.html'
			},

			# ArchLinux .life
			'archlinux.life' : {
				'web_root' : './vhosts/archlinux.life',
				'index' : 'index.html'
			},
			'api.archlinux.life' : {
				'module' : './vhosts/api.archlinux.life/vhost.py'
			},

			# Scientist .cloud
			'scientist.cloud' : {
				'web_root' : './vhosts/scientist.cloud',
				'index' : 'index.html'
			},
			'api.scientist.cloud' : {
				'module' : './vhosts/scientist.cloud/vhost.py'
			},

			# python.rip
			'python.rip' : {
				'web_root' : './vhosts/python.rip',
				'index' : 'index.html'
			},

			# messages2.me
			'messages2.me' : {
				'web_root' : './vhosts/messages2.me',
				'index' : 'index.html'
			},
			'api.messages2.me' : {
				'module' : './vhosts/messages2.me/vhost.py'
			}
		}
	}

@websocket.frame
def on_ws_frame(frame):
	virtual_host = frame.CLIENT_IDENTITY.virtual_host

	if virtual_host in (vhost_configs := config(None)['vhosts']) \
	  and 'websocket' in vhost_configs[virtual_host] \
	  and os.path.isfile(vhost_configs[virtual_host]['websocket']):

		loaded_module = slimHTTP.Imported(vhost_configs[virtual_host]['websocket'])
		with loaded_module as module:
			if hasattr(module, 'on_request'):
				yield module.on_request(frame)
	else:
		yield {
			'status' : 'connected'
		}


@https.configuration
def config_route(instance):
	return config(instance)

@http.configuration
def config_route(instance):
	return config(instance)

@http.on_upgrade
def upgrade(request):
	new_identity = websocket.WS_CLIENT_IDENTITY(request)
	new_identity.upgrade(request) # Sends Upgrade request to client
	return new_identity

@https.on_upgrade
def upgrade(request):
	new_identity = websocket.WS_CLIENT_IDENTITY(request)
	new_identity.upgrade(request) # Sends Upgrade request to client
	return new_identity

# http://www.webdnstools.com/dnstools/check-domain-results?domain=scientist.cloud&nameserver=ns1.scientist.cloud
# https://zonemaster.iis.se/?resultid=c69620fb2318685d
def records(server):
	return {
		"hvornum.se" : {
			"A" : {"target" : "109.74.10.228", "ttl" : 60},
			"SOA" : {"target" : "hvornum.se", "ttl" : 60},
			"NS" : {"target" : "hvornum.se", "ttl" : 60}
		},
		"storage.hvornum.se" : {
			"A" : {"target" : "109.74.10.228", "type" : "A", "ttl" : 60}
		},
		"archlinux.life" : {
			"A" : {"target" : "109.74.10.228", "ttl" : 60},
			"SOA" : {"target" : "archlinux.life", "ttl" : 60},
			"NS" : {"target" : "archlinux.life", "ttl" : 60},
			"MX" : [{"target" : "archlinux.life", "ttl" : 60, "priority" : 5}]
		},
		"api.archlinux.life" : {
			"A" : {"target" : "109.74.10.228", "ttl" : 60}
		},
		"_matrix._tcp.riot.hvornum.se" : {
			"SRV" : {"ttl" : 60, "priority" : 10, "port" : 8448, "target" : "storage.hvornum.se"}
		},
		"scientist.cloud" : {
			"A" : {"target" : "109.74.10.228", "ttl" : 60},
			"SOA" : {"target" : "ns1.scientist.cloud", "ttl" : 60},
			"MX" : [{"target" : "mx01.glesys.se", "ttl" : 60, "priority" : 5}, {"target" : "mx02.glesys.se", "ttl" : 60, "priority" : 5}],
			"NS" : [{"target" : "ns1.scientist.cloud", "ttl" : 60}, {"target" : "ns2.scientist.cloud", "ttl" : 60}],
			"TXT" : {"target" : 'v=spf1 mx ip4:46.21.102.81 ip4:109.74.10.228 -all"', "ttl" : 60},
			"SPF" : {"target" : "ns1.scientist.cloud", "ttl" : 60},
			"CAA" : {"target" : "ns1.scientist.cloud", "ttl" : 60}
		},
		"ns1.scientist.cloud" : {
			"A" : {"target" : "109.74.10.228", "ttl" : 60},
		},
		"ns2.scientist.cloud" : {
			"A" : {"target" : "109.74.10.228", "ttl" : 60},
		},
		"www.scientist.cloud" : {
			"A" : {"target" : "109.74.10.228", "ttl" : 60},
		},
		"api.scientist.cloud" : {
			"A" : {"target" : "109.74.10.228", "ttl" : 60},
		},
		"mail.scientist.cloud" : {
			"MX" : [{"target" : "mx01.glesys.se", "ttl" : 60, "priority" : 5}, {"target" : "mx02.glesys.se", "ttl" : 60, "priority" : 5}],
			"TXT" : {"target" : '"v=spf1 mx ip4:46.21.102.81 ip4:109.74.10.228 -all"', "ttl" : 60},
			"SPF" : {"target" : "ns1.scientist.cloud", "ttl" : 60}
		},
		"messages2.me" : {
			"A" : {"target" : "109.74.10.228", "ttl" : 60},
			"SOA" : {"target" : "ns1.messages2.me", "ttl" : 60},
			"NS" : [{"target" : "ns1.messages2.me", "ttl" : 60}, {"target" : "ns2.messages2.me", "ttl" : 60}],
		},
		"ns1.messages2.me" : {
			"A" : {"target" : "109.74.10.228", "ttl" : 60},
		},
		"ns2.messages2.me" : {
			"A" : {"target" : "109.74.10.228", "ttl" : 60},
		},
		"api.messages2.me" : {
			"A" : {"target" : "109.74.10.228", "ttl" : 60},
		},

		"228.10.74.109.in-addr.arpa" : {
			"PTR" : False # We don't allow PTR lookups on this IP.
		}
	}

@dns.records
def config_route(instance):
	return records(instance)
@dns_tcp.records
def config_route(instance):
	return records(instance)

while 1:
	for event, event_data in dns.poll():
		pass
	for event, event_data in dns_tcp.poll():
		pass
	for event, event_data in https.poll():
		pass
	for event, event_data in http.poll():
		pass
