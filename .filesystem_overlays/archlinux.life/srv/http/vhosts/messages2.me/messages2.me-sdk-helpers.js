export async function HTTPSendJSON(url = '', data = {}, method='POST') {
	// Default options are marked with *
	try {
		const response = await fetch(url, {
			method: method, // *GET, POST, PUT, DELETE, etc.
			mode: 'cors', // no-cors, *cors, same-origin
			cache: 'no-cache', // *default, no-cache, reload, force-cache, only-if-cached
			credentials: 'same-origin', // include, *same-origin, omit
			headers: {
				'Content-Type': 'application/json'
				// 'Content-Type': 'application/x-www-form-urlencoded',
			},
			redirect: 'follow', // manual, *follow, error
			referrerPolicy: 'no-referrer', // no-referrer, *no-referrer-when-downgrade, origin, origin-when-cross-origin, same-origin, strict-origin, strict-origin-when-cross-origin, unsafe-url
			body: JSON.stringify(data) // body data type must match "Content-Type" header
		});
		return response.json()
	} catch(e) {
		console.warn("Connection issues!")
	}
}

// https://bradyjoslin.com/blog/encryption-webcrypto/
async function getPasswordKey(password) {
	let enc = new TextEncoder(); // always utf-8

	return await window.crypto.subtle.importKey(
		"raw",
		enc.encode(password),
		"PBKDF2",
		false,
		["deriveKey"]
	);
}

async function deriveKey(passwordKey, salt, keyUsage) {
	return window.crypto.subtle.deriveKey(
		{
			name: "PBKDF2",
			salt: salt,
			iterations: 250000,
			hash: "SHA-256",
		},
		passwordKey,
		{ name: "AES-GCM", length: 256 },
		false,
		keyUsage
	);
}

async function encryptData(password, salt, iv) {
	let enc = new TextEncoder(); // always utf-8

	try {
		//const salt = window.crypto.getRandomValues(new Uint8Array(16));
		const passwordKey = await getPasswordKey(password);
		const aesKey = await deriveKey(passwordKey, enc.encode(salt), ["encrypt"]);
		const encryptedContent = await window.crypto.subtle.encrypt({
			name: "AES-GCM",
			iv: enc.encode(iv),
		}, aesKey, new TextEncoder().encode(password));

		const encryptedContentArr = new Uint8Array(encryptedContent);

		return encryptedContentArr;
	} catch(e) {
		console.log('Error:', e);
	}
}

export function login(username, password, callback) {
	console.info("Getting a salt and iv for the login session.")
	HTTPSendJSON('https://api.messages2.me/authenticate', {
			"user" : username
		}).then(data => {
			if(!data || typeof data === 'undefined')
				return;

			console.info("Encrypting password using salt and iv");

			encryptData(password, data['salt'], data['iv']).then((data) => {
				let pwhash = btoa(String.fromCharCode.apply(null, data));
				console.log("Logging in using password hash:", pwhash);
				
				HTTPSendJSON('https://api.messages2.me/authenticate', {
						"user" : username,
						"password" : pwhash
					}).then(data => {
						if(typeof data['status'] !== 'undefined' && data['status'] == 'success')
							console.info("Login complete:", data);
						else
							console.error("Login failed:", data);
						callback(data);
					}
				);
			});
		}
	);
}