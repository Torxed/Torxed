import slimHTTP

import discord # https://realpython.com/how-to-make-a-discord-bot-python/
import aiohttp, asyncio, time, jwt, json, os
import urllib.parse
import urllib.request
import shutil
import glob
from gidgethub.apps import get_installation_access_token # https://github.com/Mariatta/gh_app_demo/blob/master/__main__.py
from gidgethub.aiohttp import GitHubAPI # https://gidgethub.readthedocs.io/en/latest/abc.html?highlight=GitHubAPI#gidgethub.abc.GitHubAPI
from hashlib import sha512
from os import urandom
from discord.utils import get
from discord.abc import Messageable
from threading import Thread, enumerate as tenumerate

GITHUB_KEY = './slimhttp-discord.2020-06-22.private-key.pem' # AT THE BOTTOM: https://github.com/settings/apps/slimhttp-discord
DISCORD_TOKEN = '<token>' # https://discord.com/developers/applications/724626224051126383/bot
GITHUB_APP_ID = 69801 # https://github.com/settings/apps/slimhttp-discord
GITHUB_CLIENT_ID = "<client id>"
GITHUB_APP_SECRET = "<app seecret>" # https://github.com/settings/applications/1321280
GITHUB_WEBHOOK_SECRET = '<webhook secret>'
MAXMIND_API_KEY = '<maxmind api key>'

cache_info = {
	'server_name' : 'slimHTTP',
	'contributors' : {},
	'subscribers' : {},
	'discord_uid_to_github' : {},

	'_guild' : None,
	'_members' : {},
	'_roles' : {},
	'_challenges' : {},
	'_contributor_role' : None,
	'_party_animal_role' : None,
	'_announcement_channel' : None
}

if os.path.isfile('discord_cache.json'):
	with open('discord_cache.json', 'r') as fh:
		cache_info = {**cache_info, **json.load(fh)}

with open(GITHUB_KEY, 'r') as key_fh:
	private_key = key_fh.read()

async def get_installation(gh, jwt_token, username):
	async for installation in gh.getiter(
		"/app/installations",
		jwt=jwt_token,
		accept="application/vnd.github.machine-man-preview+json",
	):
		if installation["account"]["login"] == username:
			return installation

	raise ValueError(f"Can't find installation by that user: {username}")

def get_jwt(app_id):
	# TODO: read is as an environment variable
	payload = {
		"iat": int(time.time()),
		"exp": int(time.time()) + (10 * 60),
		"iss": app_id,
	}
	encoded = jwt.encode(payload, private_key, algorithm="RS256")
	bearer_token = encoded.decode("utf-8")

	return bearer_token

async def refresh_contributors():
	async with aiohttp.ClientSession() as session:
		gh = GitHubAPI(session, "Torxed")

		jwt_token = get_jwt(GITHUB_APP_ID)
		installation = await get_installation(gh, jwt_token, "Torxed")

		access_token = await get_installation_access_token(
			gh, app_id=GITHUB_APP_ID, private_key=private_key, installation_id=installation["id"]
		)

		gh_app = GitHubAPI(session, "Torxed", oauth_token=access_token["token"])
		contributors_response = gh_app.getiter(
			"/repos/Torxed/slimHTTP/contributors"
		)

		async for user in contributors_response:
			cache_info['contributors'][user['login']] = user
		else:
			save_cache(cache_info)

def save_cache(d):
	tmp = d.copy()
	for item in list(tmp.keys()):
		if item[0] == '_':
			del(tmp[item])
	if os.path.isfile('discord_cache.json'):
		shutil.move("discord_cache.json", "discord_cache.json.bkp")
	with open('discord_cache.json', 'w') as fh:
		json.dump(tmp, fh)
	return True

def gen_uid():
	return sha512(urandom(256)).hexdigest()

def get_github_status(nickname :str):
	pass

class discordHost(discord.Client):
	async def on_ready(self):
		print(f'{DiscordThread.discord_client.user} has connected.')
		for guild in DiscordThread.discord_client.guilds:
			if guild.name == cache_info['server_name']:
				cache_info['_guild'] = guild

				for member in guild.members:
					cache_info['_members'][member.id] = member

				for role in cache_info['_guild'].roles:
					cache_info['_roles'][role.id] = role
					if role.name == 'Contributors':
						print('Found: [Role] Contributors')
						cache_info['_contributor_role'] = role
					elif role.name == 'Party Animal':
						print('Found: [Role] Party Animal')
						cache_info['_party_animal_role'] = role

				for channel in guild.channels:
					if channel.name == 'release_party':
						cache_info['_announcement_channel'] = channel

		await refresh_contributors()

	async def on_member_join(self, member):
		cache_info['_members'][member.id] = member

	async def on_message(self, message):
		if message.guild:# and message.channel.name == 'howto':
			if message.content == '!verify' and cache_info['_contributor_role']:
				if message.author.id not in cache_info['discord_uid_to_github']:
					print(f'Sending GitHub verification link to: {message.author.name}')
					uid = gen_uid()
					cache_info['_challenges'][uid] = message.author
					verify_link = f"https://github.com/login/oauth/authorize?client_id={GITHUB_CLIENT_ID}&redirect_uri=https%3A%2F%2Fverifiy.hvornum.se%2Fverify%2Findex.html&scope=read:user&allow_signup=false&state={uid}"

					verify_message = discord.Embed(title="Verify your GitHub account!",
													type="rich",
													description="Verify your account by authorizing the slimHTTP oAuth app on GitHub.", url=verify_link)
					await message.delete()
					await message.author.send(embed=verify_message)

					save_cache(cache_info)
				else:
					print(f'GitHub account already verified for: {message.author.name}')
			elif message.content[:4] == '!sub' and cache_info['_party_animal_role']:
				cache_info['subscribers'][message.author.id] = True
				await promote_user(message.author, cache_info['_party_animal_role'])
				await message.delete()

				save_cache(cache_info)

			elif message.content == '!test':
				await send_message(cache_info['_announcement_channel'], f"{cache_info['_party_animal_role'].mention}, New test message.")


def github_convert_code_to_token(code):
	headers = {'User-Agent': 'slimHTTP-discord', 'Accept' : 'application/json'}#, 'Content-Type' : 'application/x-www-form-urlencoded'}

	req = urllib.request.Request(f"https://github.com/login/oauth/access_token/?client_id={GITHUB_CLIENT_ID}&client_secret={GITHUB_APP_SECRET}&code={code}", None, headers)
	with urllib.request.urlopen(req) as response:
		return json.loads(response.read().decode('UTF-8'))

def github_get_user_info(access_token):
	headers = {'User-Agent': 'slimHTTP-discord',
				'Accept' : 'application/json',
				'Authorization' : f'token {access_token}'}#, 'Content-Type' : 'application/x-www-form-urlencoded'}

	req = urllib.request.Request(f"https://api.github.com/user", None, headers)
	with urllib.request.urlopen(req) as response:
		return json.loads(response.read().decode('UTF-8'))

async def promote_user(user, role):
	DiscordThread.discord_client.wait_until_ready()
	print('Promoting....')
	print(user)
	print(role)
	await user.add_roles(role)

https = slimHTTP.instances[':443']

def on_request(request):
	if not 'ssh_uids' in slimHTTP.internal.storage:
		slimHTTP.internal.storage['ssh_uids'] = {}

	if b'uid' in request.headers[b'URI_QUERY']:
		uid = request.headers[b'URI_QUERY'][b'uid']
		print('UID:', uid)

		if request.headers[b'METHOD'] == b'PUT':
			if request.headers[b'URL'] == '/ssh-reg/':
				slimHTTP.internal.storage['ssh_uids'][uid] = time.time()
				print(f'Registered temporary session for {uid}')
				return slimHTTP.HTTP_RESPONSE(ret_code=204)

		elif request.headers[b'METHOD'] == b'GET':
			if request.headers[b'URL'] == '/ssh-check/':
				print(f'Returning status for {uid}')
				response = {'status' : slimHTTP.internal.storage['ssh_uids'][uid] is True}
				return slimHTTP.HTTP_RESPONSE(ret_code=200, headers={'Content-Type' : 'application/json'}, payload=bytes(json.dumps(response), 'UTF-8'))

			elif request.headers[b'URL'] == '/ssh-verify/':
				print(f'Session for {uid} is now verified.')
				slimHTTP.internal.storage['ssh_uids'][uid] = True
				return slimHTTP.HTTP_RESPONSE(ret_code=204)

	return None

@https.route('/geoip', vhost='verify.hvornum.se')
def docs_handler(request):
	if not os.path.isfile('geolite.db'):
		import tarfile
		response = urllib.request.urlopen(f"https://download.maxmind.com/app/geoip_download?edition_id=GeoLite2-Country&license_key={MAXMIND_API_KEY}&suffix=tar.gz")
		with open('geolite.db.tar.gz', 'wb') as db:
			db.write(response.read())

		tf = tarfile.open('geolite.db.tar.gz')
		tf.extractall()

	import geoip2.database
	with geoip2.database.Reader(f"./{glob.glob('GeoLite2-*')[0]}/GeoLite2-Country.mmdb") as reader:
		match = reader.country(request.CLIENT_IDENTITY.address)

		return slimHTTP.HTTP_RESPONSE(ret_code=200, headers={'Content-Type' : 'application/json'}, payload=bytes(json.dumps({'ip' : request.CLIENT_IDENTITY.address, 'country' : match.country.iso_code}), 'UTF-8'))

@https.route('/docs', vhost='verify.hvornum.se')
def docs_handler(request):
	print(request.headers)
	print(request.payload)

@https.route('/verify', vhost='verify.hvornum.se')
def auth_handler(request):
	#print('Auth:', request.headers)
	if b'code' in request.headers[b'URI_QUERY'] and b'state' in request.headers[b'URI_QUERY']:
		code = request.headers[b'URI_QUERY'][b'code'].decode('UTF-8')

		challenge_callback = github_convert_code_to_token(code)
		uid = request.headers[b'URI_QUERY'][b'state'].decode('UTF-8')
		if uid in cache_info['_challenges']:
			github_user_info = github_get_user_info(access_token=challenge_callback['access_token']) # {"login":"Torxed","id":861439,"node_id":"MDQ6VXNlcjg2MTQzOQ==","avatar_url":"https://avatars3.githubusercontent.com/u/861439?v=4","gravatar_id":"","url":"https://api.github.com/users/Torxed","html_url":"https://github.com/Torxed","followers_url":"https://api.github.com/users/Torxed/followers","following_url":"https://api.github.com/users/Torxed/following{/other_user}","gists_url":"https://api.github.com/users/Torxed/gists{/gist_id}","starred_url":"https://api.github.com/users/Torxed/starred{/owner}{/repo}","subscriptions_url":"https://api.github.com/users/Torxed/subscriptions","organizations_url":"https://api.github.com/users/Torxed/orgs","repos_url":"https://api.github.com/users/Torxed/repos","events_url":"https://api.github.com/users/Torxed/events{/privacy}","received_events_url":"https://api.github.com/users/Torxed/received_events","type":"User","site_admin":false,"name":"Anton Hvornum","company":null,"blog":"http://hvornum.se/","location":"Sweden","email":"anton.feeds+github@gmail.com","hireable":null,"bio":"Thread lightly, Ye who enter here.. Here be dragons","twitter_username":null,"public_repos":84,"public_gists":28,"followers":17,"following":6,"created_at":"2011-06-20T10:39:53Z","updated_at":"2020-06-23T12:21:44Z","private_gists":59,"total_private_repos":28,"owned_private_repos":28,"disk_usage":105282,"collaborators":9,"two_factor_authentication":false,"plan":{"name":"pro","space":976562499,"collaborators":0,"private_repos":9999}}
			discord_user = cache_info['_challenges'][uid]
			cache_info['discord_uid_to_github'][discord_user.id] = github_user_info

			save_cache(cache_info)

			if github_user_info["login"] in contributors:
				print(f'Promoting {discord_user}[{github_user_info["login"]}] to contributor')
				DiscordThread.discord_client.loop.create_task(promote_user(discord_user, cache_info['_contributor_role']))
				return slimHTTP.HTTP_RESPONSE(ret_code=307, headers={'Location' : '/verification_ok.html?gnick=Torxed'}, payload=b'')

			return slimHTTP.HTTP_RESPONSE(ret_code=307, headers={'Location' : '/verification_ok_notyet.html?gnick=Torxed'}, payload=b'')
	return slimHTTP.HTTP_RESPONSE(ret_code=307, headers={'Location' : '/verification_failed.html'}, payload=b'')

async def send_message(target, message, content=None):
	if type(message) == str:
		await target.send(content=message)
	else:
		await target.send(content=content, embed=message)

@https.route('/repo', vhost='verify.hvornum.se')
def repo_change(request):
	try:
		repo_info = json.loads(request.payload.decode('UTF-8'))
	except:
		print('Error parsing JSON:', request.payload)
		return None
		
	print(json.dumps(repo_info, indent=4))
	if 'ref' in repo_info and 'before' in repo_info:

		branch = os.path.basename(repo_info['ref'])
		prev_commit_id = repo_info['before']
		new_commit_id = repo_info['after']

		sender = repo_info['sender']['login']
		avatar = repo_info['sender']['avatar_url'] # or 'gravatar_id'

		if cache_info['_announcement_channel']:
			head_commit_url = repo_info['head_commit']['url']
			commit_message = repo_info['head_commit']['message']

			markers = {commit_message.find(marker): marker for marker in {'.', ':', '!', ','}} # Find the first occurance of these markers commonly used in commit messages.
			discord_message = discord.Embed(title=commit_message.split(markers[min(markers)], 1)[0],
											type="rich",
											description=commit_message, url=head_commit_url)
			discord_message.set_image(url='https://hvornum.se/git_commit.png')

			discord_message_content = f"A new commit in [{branch}] is out with the following messages:"
			if 'commits' in repo_info:
				discord_message_content += '\n'
				for commit in repo_info['commits']:
					discord_message_content += commit['message'] +'\n'

			DiscordThread.discord_client.loop.create_task(send_message(cache_info['_announcement_channel'], discord_message, content=discord_message_content))
			
	if 'release' in repo_info:
		rel_type = 'New release'
		if repo_info['action'] == 'prereleased':
			rel_type = 'Pre-release'

		release_name = repo_info['release']['name']
		release_url = repo_info['release']['html_url']
		
		sender = repo_info['release']['author']['login']
		avatar = repo_info['release']['author']['avatar_url'] # or 'gravatar_id'
		release_icon = 'https://hvornum.se/release.png'

		if cache_info['_announcement_channel']:
			release_message = repo_info['release']['body']

			markers = {release_message.find(marker): marker for marker in {'.', ':', '!', ','}} # Find the first occurance of these markers commonly used in commit messages.
			discord_message = discord.Embed(title=f"[{release_name}] {release_message.split(markers[min(markers)], 1)[0]}",
											description=release_message,
											url=release_url)
			discord_message.set_image(url=release_icon)
			DiscordThread.discord_client.loop.create_task(send_message(cache_info['_announcement_channel'], discord_message, content=f"Hey {cache_info['_party_animal_role'].mention}! A new release [{release_name}] is out:"))

	if 'issue' in repo_info:
		if 'pull_request' in repo_info['issue']:
			pull_url = repo_info['issue']['pull_request']['html_url']
			pull_nr = repo_info['issue']['number']
			if 'comment' in repo_info:
				comment_owner = repo_info['comment']['user']['login']
				comment_avatar = repo_info['comment']['user']['avatar_url']
				comment_message = repo_info['comment']['body']

				if cache_info['_announcement_channel']:
					markers = {comment_message.find(marker): marker for marker in {'.', ':', '!', ','}} # Find the first occurance of these markers commonly used in commit messages.
					discord_message = discord.Embed(title=f"{comment_message.split(markers[min(markers)], 1)[0]}",
													type="rich",
													description=comment_message, url=pull_url)
					discord_message.set_image(url=comment_avatar)
					DiscordThread.discord_client.loop.create_task(send_message(cache_info['_announcement_channel'], discord_message, content=f"[PR #{pull_nr}] New comment:"))

@https.route('/docs', vhost='verify.hvornum.se')
def docs_handler(request):
	print(request.headers)
	print(request.payload)

class Threader(Thread):
	def __init__(self):
		Thread.__init__(self)
		self.loop = asyncio.get_event_loop()
		self.start()

	async def starter(self):
		self.discord_client = discordHost()
		await self.discord_client.start(DISCORD_TOKEN)

	def run(self):
		self.name = 'Discord.py'

		self.loop.create_task(self.starter())
		self.loop.run_forever()

if not 'DiscordThread' in __builtins__:
	__builtins__['DiscordThread'] = Threader()
