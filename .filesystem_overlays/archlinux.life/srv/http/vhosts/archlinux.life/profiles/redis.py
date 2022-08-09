import archinstall

installation.add_additional_packages(['redis'])
installation.enable_service(f"redis.service")

def search_and_replace_line(look_for, replace_with, obj):
	if type(obj) == str:
		obj = obj.split('\n')
	else:
		obj = obj.readlines()

	for line in obj:
		if look_for.lower() in line.lower():
			return '\n'.join(obj).replace(line, replace_with)

	return False

with open(f"{installation.mountpoint}/etc/redis.conf", "r") as redis_fh:
	redis = search_and_replace_line('port 6379', 'port 0', redis_fh.read())
	redis = search_and_replace_line('unixsocketperm', 'unixsocketperm 770', redis)
