import archinstall

try:
	archinstall.sys_command('umount -R /mnt')
except:
	pass

db_password = 'SomethingLongHereYolo:D'

os_drive = archinstall.harddrive(size=8)
database_drive = archinstall.harddrive(size=20)

with archinstall.Filesystem(os_drive, archinstall.GPT) as fs:
	fs.use_entire_disk('ext4')
	os_drive.partition[0].format('fat32')
	os_drive.partition[1].format('ext4')

	with archinstall.Filesystem(database_drive, archinstall.GPT) as fs_mirror:
		fs_mirror.add_partition('primary', start='1MiB', end='100%', format='ext4')
		database_drive.partition[0].format('ext4')

	with archinstall.Installer(os_drive.partition[1], boot_partition=os_drive.partition[0], hostname='archpostgres') as installation:

		if installation.minimal_installation():
			installation.add_bootloader()
			installation.set_locale('en_US', encoding='UTF-8')
			installation.user_create('anton', 'test', sudo=True)

			interface = archinstall.get_interface_from_mac('08-00-27-31-72-95')

			installation.mount(database_drive.partition[0], '/var/lib/postgres')
			installation.install_profile('postgresql')

			with archinstall.temporary_boot(installation) as os:
				os.sys_command(f"psql -d template1 CREATE USER gitlab WITH PASSWORD '{db_password}';")
				os.sys_command(f"psql -d template1 ALTER USER gitlab SUPERUSER;")
				os.sys_command(f"psql -d template1 CREATE DATABASE gitlabhq_production OWNER gitlab;")

			with open(f"{installation.mountpoint}/var/lib/postgres/data/postgresql.conf") as postgresql:
				postgresql.write("listen_addresses = '*'\n")# localhost,my_local_ip_address

			with open(f"{installation.mountpoint}/var/lib/postgres/data/pg_hba.conf") as postgresql:
				postgresql.write("host    all             all             172.16.13.0/24   md5\n")

			installation.configure_nic(nic=interface)
			installation.enable_service('systemd-networkd')

#archinstall.reboot()