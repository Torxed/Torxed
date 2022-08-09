import archinstall

try:
	archinstall.sys_command('umount -R /mnt')
except:
	pass

os_drive = archinstall.harddrive(size=8)
gitlab_drive = archinstall.harddrive(size=20)

with archinstall.Filesystem(os_drive, archinstall.GPT) as fs:
	fs.use_entire_disk('ext4')
	os_drive.partition[0].format('fat32')
	os_drive.partition[1].format('ext4')

	with archinstall.Filesystem(gitlab_drive, archinstall.GPT) as fs_mirror:
		fs_mirror.add_partition('primary', start='1MiB', end='100%', format='ext4')
		gitlab_drive.partition[0].format('ext4')

	with archinstall.Installer(os_drive.partition[1], boot_partition=os_drive.partition[0], hostname='archpostgres') as installation:

		if installation.minimal_installation():
			installation.add_bootloader()
			installation.set_locale('en_US', encoding='UTF-8')
			installation.user_create('anton', 'test', sudo=True)

			# installation.install_profile('SElinux')

			interface = archinstall.get_interface_from_mac('08-00-27-4B-02-F8')

			installation.mount(gitlab_drive.partition[0], '/var/lib/gitlab')

			archinstall.storage['gitlab-hostname'] = 'gitlab.local'
			archinstall.storage['gitlab-timezone'] = 'Europe/Stockholm'
			archinstall.storage['slimhttp-interface'] = interface

			installation.install_profile('gitlab')
			installation.install_profile('slimhttp')

			installation.configure_nic(nic=interface)
			installation.enable_service('systemd-networkd')

#archinstall.reboot()