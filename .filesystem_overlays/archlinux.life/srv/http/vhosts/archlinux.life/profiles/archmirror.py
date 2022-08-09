import os
import shutil
import archinstall

installation.install_profile('slimhttp')

if 'archmirror-packages' not in archinstall.storage:
	archinstall.storage['archmirror-packages'] = 'base base-devel linux linux-firmware efibootmgr nano btrfs btrfs-progs'

if not os.path.isdir(f"{installation.mountpoint}/srv/http/vhosts/mirror"):
	os.makedirs(f"{installation.mountpoint}/srv/http/vhosts/mirror")

installation.log(f"Syncing down {archinstall.storage['archmirror-packages'].count(' ')+1} packages to mirror location: {installation.mountpoint}/srv/http/vhosts/mirror", level=archinstall.LOG_LEVELS.Info)
installation.arch_chroot(f"sh -c \"mkdir /tmp/pacmandb; pacman --noconfirm -Suyw --cachedir /srv/http/vhosts/mirror --dbpath /tmp/pacmandb {archinstall.storage['archmirror-packages']}\"")
installation.log(f'Updating package database: {installation.mountpoint}/srv/http/vhosts/mirror/archmirror.db.tar.gz', level=archinstall.LOG_LEVELS.Info)
installation.arch_chroot(f"sh -c 'repo-add /srv/http/vhosts/mirror/archmirror.db.tar.gz /srv/http/vhosts/mirror/{{*.pkg.tar.xz,*.pkg.tar.zst}}'")

if os.path.isfile(f"{installation.mountpoint}/srv/http/mirror.py"):
	shutil.copy2(f"{installation.mountpoint}/srv/http/mirror.py", f"{installation.mountpoint}/srv/http/mirror.py.bkp")

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
			'archmirror.local' : {
				'web_root' : './vhosts/mirror',
				'index' : 'index.html'
			}
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

with open(f"{installation.mountpoint}/srv/http/mirror.py", 'w') as server:
	server.write(server_template)
