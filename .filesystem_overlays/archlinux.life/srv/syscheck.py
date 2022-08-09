import json
import select
import uuid
import re
import ipaddress
import datetime
import smtplib
import systemd.journal
import time
import os
import ssl
import subprocess
import sys
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen
from dataclasses import dataclass
from typing import Dict, Any, Tuple, List, Optional

BASE_URL_PKG_SEARCH = 'https://archlinux.org/packages/search/json/'

class JSON_Typer(json.JSONEncoder):
	def _encode(self, obj):
		## Workaround to handle keys in the dictionary being bytes() objects etc.
		## Also handles recursive JSON encoding. In case sub-keys are bytes/date etc.
		##
		## README: If you're wondering why we're doing loads(dumps(x)) instad of just dumps(x)
		##         that's because it would become a escaped string unless we loads() it back as
		##         a regular object - before getting passed to the super(JSONEncoder) which will
		##         do the actual JSON encoding as it's last step. All this shananigans are just
		##         to recursively handle different data types within a nested dict/list/X struct.
		if isinstance(obj, dict):
			## We'll need to iterate not just the value that default() usually gets passed
			## But also iterate manually over each key: value pair in order to trap the keys.
			
			for key, val in list(obj.items()):
				if isinstance(val, dict):
					val = json.loads(json.dumps(val, cls=JSON_Typer)) # This, is a EXTREMELY ugly hack..
															# But it's the only quick way I can think of to 
															# trigger a encoding of sub-dictionaries. (I'm also very tired, yolo!)
				else:
					val = self._encode(val)
				del(obj[key])
				obj[self._encode(key)] = val
			return obj
		elif isinstance(obj, ipaddress.IPv4Address):
			return str(obj)
		elif isinstance(obj, ipaddress.IPv4Network):
			return str(obj)
		elif isinstance(obj, uuid.UUID):
			return str(obj)
		elif getattr(obj, "__dump__", None): #hasattr(obj, '__dump__'):
			return obj.__dump__()
		elif isinstance(obj, datetime.timedelta):
			return (datetime.datetime.today() + obj).isoformat()
		elif isinstance(obj, (datetime.datetime, datetime.date)):
			return obj.isoformat()
		elif isinstance(obj, (list, set, tuple)):
			r = []
			for item in obj:
				r.append(json.loads(json.dumps(item, cls=JSON_Typer)))
			return r
		else:
			return obj

	def encode(self, obj):
		return super(JSON_Typer, self).encode(self._encode(obj))

@dataclass
class PackageSearchResult:
	pkgname: str
	pkgbase: str
	repo: str
	arch: str
	pkgver: str
	pkgrel: str
	epoch: int
	pkgdesc: str
	url: str
	filename: str
	compressed_size: int
	installed_size: int
	build_date: str
	last_update: str
	flag_date: Optional[str]
	maintainers: List[str]
	packager: str
	groups: List[str]
	licenses: List[str]
	conflicts: List[str]
	provides: List[str]
	replaces: List[str]
	depends: List[str]
	optdepends: List[str]
	makedepends: List[str]
	checkdepends: List[str]

	@property
	def pkg_version(self) -> str:
		return self.pkgver

	def __eq__(self, other :'VersionDef') -> bool:
		return self.pkg_version == other.pkg_version

	def __lt__(self, other :'VersionDef') -> bool:
		return self.pkg_version < other.pkg_version

@dataclass
class PackageSearch:
	version: int
	limit: int
	valid: bool
	num_pages: int
	page: int
	results: List[PackageSearchResult]

	def __post_init__(self):
		self.results = [PackageSearchResult(**x) for x in self.results]

def contains(string, patterns):
	# print('--- Parsing string:', string)
	for pattern in patterns:
		if re.findall(pattern, string):
	# 		print('Match on pattern:', pattern)
			return True

	return False

def _make_request(url: str, params: Dict) -> Any:
	ssl_context = ssl.create_default_context()
	ssl_context.check_hostname = False
	ssl_context.verify_mode = ssl.CERT_NONE

	encoded = urlencode(params)
	full_url = f'{url}?{encoded}'

	return urlopen(full_url, context=ssl_context)

def package_search(package :str) -> PackageSearch:
	"""
	Finds a specific package via the package database.
	It makes a simple web-request, which might be a bit slow.
	"""
	# TODO UPSTREAM: Implement bulk search, either support name=X&name=Y or split on space (%20 or ' ')
	# TODO: utilize pacman cache first, upstream second.
	response = _make_request(BASE_URL_PKG_SEARCH, {'name': package})

	if response.code != 200:
		raise PackageError(f"Could not locate package: [{response.code}] {response}")

	data = response.read().decode('UTF-8')

	return PackageSearch(**json.loads(data))

def is_package_updated(pkgname, repo):
	linux_version = subprocess.check_output(['pacman', '-Q', pkgname]).strip().decode()
	if patch_version := linux_version[linux_version.rfind('-'):]:
		if patch_version[0] == '-' and patch_version[1:].isalnum():
			linux_version = linux_version[:linux_version.rfind('-')].split(' ')[1]
	if weird_version_notation := ':' in linux_version:
		linux_version = linux_version[linux_version.find(':')+1:]

	upstream_linux_version = 0
	for result in package_search(pkgname).results:
		if result.pkgname == pkgname and result.repo == repo:
			upstream_linux_version = result.pkgver

	if linux_version == upstream_linux_version:
		return True

	return False

ssh_sender = 'ssh'
disk_sender = 'disk'
package_sender = 'package'
domain = 'archlinux.life'
reciever = 'anton'
smtp_u = sys.argv[0]
smtp_p = sys.argv[1]

journal = systemd.journal.Reader()
journal.log_level(systemd.journal.LOG_INFO)

# journal.add_match(_SYSTEMD_UNIT="systemd-udevd.service")
journal.seek_tail()
journal.get_previous()
# journal.get_next() # it seems this is not necessary.

p = select.poll()
p.register(journal, journal.get_events())
failed_ssh_patterns = [r'pam_faillock\(sshd:auth\): User unknown', r'pam_unix\(sshd:auth\): check pass; user unknown', r'pam_faillock\(sshd:auth\): User unknown', r'Invalid user.*?from', r'Connection closed by.*?port.*', 'error: kex_exchange_identification', 'no matching key exchange method found', '.*?authentication failure.*?', r'Disconnected from.*?\[preauth\]', r'Received disconnect from.*?\[preauth\]', 'Timeout before authentication', 'Failed password for']

last_disk_mail = time.time() - 86400
last_linux_update_check = time.time() - 86400

packages = {
	'linux' : {'repo' : 'core', 'up-to-date' : True},
	'postgresql' : {'repo' : 'core', 'up-to-date' : True},
	'postfix' : {'repo' : 'extra', 'up-to-date' : True},
	'dovecot' : {'repo' : 'community', 'up-to-date' : True},
	'nginx' : {'repo' : 'core', 'up-to-date' : True},
	'openssl' : {'repo' : 'core', 'up-to-date' : True},
	'iptables' : {'repo' : 'core', 'up-to-date' : True},
	'python' : {'repo' : 'core', 'up-to-date' : True},
	'powerdns'  : {'repo' : 'core', 'up-to-date' : True}
}

while p.poll():
	if journal.process() != systemd.journal.APPEND:
		continue

	# Funnel off the journal for related messages
	for entry in journal:
		#print(entry.get('MESSAGE'))
		if entry.get('_SYSTEMD_UNIT', 'unknown') == 'sshd.service' and entry.get('MESSAGE') and contains(entry['MESSAGE'], failed_ssh_patterns) is False:
			if 'sshd:' in entry.get('_CMDLINE', ''):
				user = entry['_CMDLINE'].split(' ', 2)[1]
			else:
				user = 'unknown'

			server = smtplib.SMTP('localhost')
			server.set_debuglevel(0)
			server.login(smtp_u, smtp_p)
			server.sendmail(f"{ssh_sender}@{domain}", f"{reciever}@{domain}", f"User {user} has logged in via SSH.\n\nDebug information: {json.dumps(entry, cls=JSON_Typer, indent=4)}")
			server.quit()

	# Check the disk space left
	statvfs = os.statvfs('/')
	if (disk_size_left := (int(statvfs.f_frsize * statvfs.f_bfree / 1024 / 1024 / 1024 * 100) / 100)) < 5:
		if time.time() - last_disk_mail > 86400: # 24h
			server = smtplib.SMTP('localhost')
			server.set_debuglevel(0)
			server.login(smtp_u, smtp_p)
			server.sendmail(f"{disk_sender}@{domain}", f"{reciever}@{domain}", f"Server have {disk_size_left}G left on /")
			server.quit()

			last_disk_mail = time.time()

	# Check if packages are up to date
	if time.time() - last_linux_update_check > 86400: #24h
		found_one_out_of_date = False
		for package in packages:
			packages[package]['up-to-date'] = is_package_updated(package, packages[package]['repo'])
			if packages[package]['up-to-date'] is False:
				found_one_out_of_date = True

		if found_one_out_of_date:
			server = smtplib.SMTP('localhost')
			server.set_debuglevel(0)
			server.login(smtp_u, smtp_p)
			server.sendmail(f"{package_sender}@{domain}", f"{reciever}@{domain}", f"Found one or more packages that were out of date:\n{json.dumps(packages, indent=4)}")
			server.quit()

		# Reset in turn for next run
		for package in packages:
			packages[package]['up-to-date'] = True

		last_linux_update_check = time.time()
