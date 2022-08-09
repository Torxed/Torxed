# slimCrypt
Javascript wrapper for [window.crypto.subtle.encrypt()](https://developer.mozilla.org/en-US/docs/Web/API/SubtleCrypto/encrypt) using one-time-key's transmitted via private/public keypairs.

# Installation

```html
<script type="text/javascript">
	// Loading JavaScript from a cross-site resource is blocked.
	// But there's nothing stopping us from downloading the script
	// as a text-blob and placing it within the <script> </ script> tags,
	// which causes the browser to parse it, but not as a forrain object.
	//
	// #LoadingScriptsFromGithub
	var script = document.createElement('script');
	script.type = 'text/javascript';

	let xhr = new XMLHttpRequest();
	xhr.open("GET", 'https://raw.githubusercontent.com/Torxed/slimCrypt/master/slimCrypt.js', true);
	xhr.onreadystatechange = function() {
		if (this.readyState === XMLHttpRequest.DONE && this.status === 200) {
			script.innerHTML = this.responseText;
			document.head.appendChild(script);
		}
	}
	xhr.send();
</script>
```

# Usage

### Encrypting a string

```javascript
let string_to_be_encrypted = "A message or something";
generate_one_time_key((one_time_key) => {
    encrypt_with_key(string_to_be_encrypted, one_time_key, (encrypt_struct) => {
        wrap_key_in_pubkey(encrypt_struct, one_time_key, connected_to['publicKey'], (wrapped_key) => {
            let struct = {
                'payload': encrypt_struct['b64_encrypted_payload'],
                'key' : wrapped_key,
                'iv' : btoa(encrypt_struct['iv']),
                'key_format' : encrypt_struct['key_format'],
                "access_token": access_token
            }
            socket.send(struct);
        });
    });
})
```

### Decrypting a string

```javascript
let struct = {
    'payload': encrypt_struct['b64_encrypted_payload'],
    'key' : wrapped_key,
    'iv' : btoa(encrypt_struct['iv']),
    'key_format' : encrypt_struct['key_format'],
    "access_token": access_token
}

let array = JSON.parse("["+atob(struct['payload'])+"]");
let encrypted_message = new Uint8Array(array);
let one_time_key_wrapped = new Uint8Array(JSON.parse("["+atob(struct['key'])+"]"));

load_private_key(keys['privateKey'], (privateKey) => {
    extract_one_time_key(one_time_key_wrapped, privateKey, (one_time_key) => {
        let options = {
            name: struct['key_format'],
            iv: new Uint8Array(JSON.parse("["+atob(struct['iv'])+"]"))
        };
        decrypt_with_key(options, one_time_key, encrypted_message, (decrypted_message) => {
            console.log(decrypted_message)
        });
    });
});
```
