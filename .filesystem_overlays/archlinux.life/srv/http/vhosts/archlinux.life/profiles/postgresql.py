import os
import archinstall

installation.add_additional_packages(['postgresql'])
installation.arch_chroot("sh -c 'sudo -iu postgres initdb -D /var/lib/postgres/data'")

#with archinstall.temporary_boot(installation) as os:
#	os.sys_command("createuser --interactive")

installation.enable_service(f"postgresql.service")

