import os
import archinstall

installation.add_additional_packages(['git', 'screen', 'python'])
installation.arch_chroot('git clone https://github.com/Torxed/slimHTTP.git /srv/http/slimHTTP')

service_template = """
[Unit]
Description=HTTP service on %I.
Wants=network.target
Before=network.target

[Service]
Type=simple
WorkingDirectory=/srv/http
ExecStart=/usr/bin/screen -S "slim" -D -m python3 /srv/http/server.py --interface=%I
ExecStop=/usr/bin/screen -X -S "slim" quit

[Install]
WantedBy=multi-user.target
"""

server_template = """
import sys
import slimHTTP

args = {}
positionals = []
for arg in sys.argv[1:]:
	if '--' == arg[:2]:
		if '=' in arg:
			key, val = [x.strip() for x in arg[2:].split('=')]
		else:
			key, val = arg[2:], True
		args[key] = val
	else:
		positionals.append(arg)

http = slimHTTP.server(slimHTTP.HTTP, interface=args['interface'])
#https = slimHTTP.server(slimHTTP.HTTPS, interface=args['interface'])

def config(instance):
	return {
		'web_root' : './vhosts/default',
		'index' : 'index.html',
		'ssl' : {
			'cert' : '/home/anton/fullchain.pem',
			'key' : '/home/anton/privkey.pem',
		},
		'vhosts' : {
		}
	}

# @https.configuration
# def config_route(instance):
# 	return config(instance)

@http.configuration
def config_route(instance):
	return config(instance)

while 1:
#	for event, event_data in https.poll():
#		pass
	for event, event_data in http.poll():
		pass
"""

if not os.path.isdir(f"{installation.mountpoint}/etc/systemd/system"):
	os.makedirs(f"{installation.mountpoint}/etc/systemd/system")
if not os.path.isdir(f"{installation.mountpoint}/srv/http/vhosts/default"):
	os.makedirs(f"{installation.mountpoint}/srv/http/vhosts/default")


with open(f"{installation.mountpoint}/etc/systemd/system/slimHTTP@.service", 'w') as service:
	service.write(service_template)

with open(f"{installation.mountpoint}/srv/http/server.py", 'w') as server:
	server.write(server_template)

installation.enable_service(f"slimHTTP@{archinstall.storage['slimhttp-interface']}.service")

