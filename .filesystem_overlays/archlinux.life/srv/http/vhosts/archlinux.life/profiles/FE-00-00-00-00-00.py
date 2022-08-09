import archinstall

os_drive = archinstall.harddrive(size=10)
mirror_drive = archinstall.harddrive(size=20)

with archinstall.Filesystem(os_drive, archinstall.GPT) as fs:
	fs.use_entire_disk('ext4')
	os_drive.partition[0].format('fat32')
	os_drive.partition[1].format('ext4')
	#os_drive.partition[1].format('btrfs')

	with archinstall.Filesystem(mirror_drive, archinstall.GPT) as fs_mirror:
		fs_mirror.add_partition('primary', start='1MiB', end='100%', format='ext4')
		mirror_drive.partition[0].format('ext4')

	with archinstall.Installer(os_drive.partition[1], boot_partition=os_drive.partition[0], hostname='testmachine') as installation:
		installation.mount(mirror_drive.partition[0], '/srv/http')

		if installation.minimal_installation():
			installation.add_bootloader()
			installation.user_create('anton', 'test', sudo=True)

			interface = archinstall.get_interface_from_mac('08-00-27-07-8C-94')

			archinstall.storage['slimhttp-interface'] = interface
			archinstall.storage['archmirror-packages'] = 'base base-devel linux linux-firmware efibootmgr nano btrfs btrfs-progs'
			installation.install_profile('archmirror')

			installation.configure_nic(nic=interface) # DHCP by default, otherwise: {'nic': nic, 'dhcp': False, 'ip': ip, 'gateway' : gateway, 'dns' : dns}
			installation.enable_service('systemd-networkd')

archinstall.reboot()