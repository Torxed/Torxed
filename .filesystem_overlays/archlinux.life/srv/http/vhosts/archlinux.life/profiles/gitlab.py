import os
import hashlib
import archinstall

installation.add_additional_packages(['gitlab'])
installation.install_profile('redis')

gitlab_secret = hashlib.sha512(os.urandom(512)).hexdigest()
gitlab_password = 'SomethingLongHereYolo:D'
gitlab_db = 'gitlabdb.local'

installation.enable_service(f"gitlab-gitaly.service")

def search_and_replace_line(look_for, replace_with, obj):
	if type(obj) == str:
		obj = obj.split('\n')
	else:
		obj = obj.readlines()

	for line in obj:
		if look_for.lower() in line.lower():
			return '\n'.join(obj).replace(line, replace_with)

	return False


## Update gneral gitlab YAML configuration.

with open(f"{installation.mountpoint}/etc/webapps/gitlab/gitlab.yml", "r") as config_fh:
	gitlab = config_fh.read()

if 'gitlab-hostname' in archinstall.storage:
	gitlab = search_and_replace_line('host: localhost', f"    host: {archinstall.storage['gitlab-hostname']}")
if 'gitlab-timezone' in archinstall.storage:
	gitlab = search_and_replace_line('time_zone:', f"    time_zone: {archinstall.storage['gitlab-timezone']}")

with open(f"{installation.mountpoint}/etc/webapps/gitlab/gitlab.yml", "w") as config_fh:
	config_fh.write(gitlab)


## Update gitaly configration

with open(f"{installation.mountpoint}/etc/webapps/gitlab/gitlab.yml", "r") as gitaly_fh:
	gitaly = gitaly_fh.read()


## Update Puma configuration

with open(f"{installation.mountpoint}/etc/webapps/gitlab/puma.rb", "r") as puma:
	if (new_config := search_and_replace_line('unix://', "bind 'tcp://127.0.0.1:8080'", puma)) is False:
		raise KeyError("Could not identify unix:// socket in GitLab puma config.")

with open(f"{installation.mountpoint}/etc/webapps/gitlab/puma.rb", "w") as puma:
	puma.write(new_config)


## Update secrets

with open(f"{installation.mountpoint}/etc/webapps/gitlab/secret", "w") as gitlab_fh:
	gitlab_fh.write(gitlab_secret)

with open(f"{installation.mountpoint}/etc/webapps/gitlab/secrets.yml", "w") as gitlab_fh:
	gitlab_fh.write(f'production:')
	gitlab_fh.write(f'  secret_key_base: {gitlab_secret}')
	gitlab_fh.write(f'  db_key_base: {gitlab_secret}')


# Replace resque with the TCP connection:

with open(f"{installation.mountpoint}/etc/webapps/gitlab/resque.yml", "w") as resque:
	resque.write("development:\n")
	resque.write("  url: unix:/run/redis/redis.sock\n")
	resque.write("test:\n")
	resque.write("  url: unix:/run/redis/redis.sock\n")
	resque.write("production:\n")
	resque.write("  url: unix:/run/redis/redis.sock\n")


# Configure database pointer

with open(f"{installation.mountpoint}/etc/webapps/gitlab/database.yaml", "w") as database:
	database_config = search_and_replace_line(f'password:', f'  password: {gitlab_password}', database.read())
	database_config = search_and_replace_line(f'host: localhost:', f'  host: {gitlab_db}', database_config)


# Initialize the webapp

archinstall.sys_command('gpasswd -a redis gitlab')

with archinstall.temporary_boot(installation) as os:
	os.sys_command(f"sh -c 'cd /usr/share/webapps/gitlab && sudo -u gitlab $(cat environment | xargs) bundle exec rake gitlab:setup")

archinstall.sys_command(f"sh -c 'chmod -R ug+rwX,o-rwx {installation.mountpoint}/var/lib/gitlab/repositories/'")
archinstall.sys_command(f"sh -c 'chmod -R ug-s {installation.mountpoint}/var/lib/gitlab/repositories'")
archinstall.sys_command(f"sh -c 'find {installation.mountpoint}/var/lib/gitlab/repositories/ -type d -print0 | xargs -0 chmod g+s'")


# And finally, enable the gitlab target.

installation.enable_service('gitlab.target')