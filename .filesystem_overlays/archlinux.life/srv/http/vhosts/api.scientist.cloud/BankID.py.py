import json
import hashlib
import hmac
import time
import qrcode
import socket
import glob
import urllib.parse
from PIL import Image
from base64 import b64encode

from OpenSSL import SSL
from OpenSSL.crypto import load_certificate, load_privatekey, PKey, FILETYPE_PEM, TYPE_RSA, X509, X509Req, dump_certificate, dump_privatekey
from OpenSSL._util import ffi as _ffi, lib as _lib

class HTTP_REQUEST():
	def __init__(self, host, url, payload={}, headers={}, client_certificate=None, client_private_key=None):
		self.host = host
		self.url = url
		self.payload = payload
		self.headers = headers
		self.client_certificate = client_certificate
		self.client_private_key = client_private_key

		if self.client_certificate is None or self.client_private_key is None:
			raise ValueError("HTTP_REQUEST for BankID requires a client certificate & key for identification.")

		self.endpoint = None

	def certificate_verification(self, conn, cert, errnum, depth, ret_code):
		cert_hash = cert.get_subject().hash()
		cert_info = dict(cert.get_subject().get_components())
		cert_serial = cert.get_serial_number()

		if cert_info[b'CN'] == bytes(self.host, 'UTF-8'):
			return True
			
		return False

	def _print_info(self, *args, **kwargs):
		pass#print(args, kwargs)

	def _init_connection(self):
		context = SSL.Context(SSL.TLSv1_2_METHOD)
		context.set_verify(SSL.VERIFY_PEER | SSL.VERIFY_FAIL_IF_NO_PEER_CERT, self.certificate_verification)
		context.set_verify_depth(9)
		context.set_info_callback(self._print_info)

		context.use_privatekey_file(self.client_private_key)
		context.use_certificate_file(self.client_certificate)

		context.set_default_verify_paths()
		context.set_mode(SSL.MODE_RELEASE_BUFFERS)

		endpoint = socket.socket()
		endpoint.connect((self.host, 443))
		self.endpoint = SSL.Connection(context, endpoint)
		self.endpoint.set_connect_state()

	def get_response(self):
		if not self.endpoint:
			self._init_connection()

		if self.payload:
			web_request = f'POST {self.url} HTTP/1.1\r\n'
			if not self.headers.get('Content-Length'):
				self.headers['Content-Length'] = len(self.payload)
		else:
			web_request = f'GET {self.url} HTTP/1.1\r\n'

		if not self.headers.get('Host'):
			self.headers['Host'] = self.host

		for key, val in self.headers.items():
			web_request += f'{key}: {val}\r\n'

		web_request += f'\r\n'
		web_request += self.payload

		self.endpoint.send(bytes(web_request, 'UTF-8'))

		## Recieve the response:
		response = self.endpoint.recv(8192)
		headers_raw, payload_raw = response.split(b'\r\n\r\n',1)
		headers = {}
		for row in headers_raw.split(b'\r\n'):
			if b':' in row:
				key, value = row.split(b':', 1)
				headers[key.strip().decode('UTF-8')] = value.strip().decode('UTF-8')

		payload = b''
		while True:
			payload_length, payload_raw = payload_raw.split(b'\r\n', 1)
			payload_length = int(payload_length, 16)

			while len(payload_raw) < payload_length:
				payload_raw += self.endpoint.recv(8192)

			payload_buffert = payload_raw[payload_length+2:]

			if payload_length == 0:
				break

			payload += payload_raw
			payload_raw = payload_buffert + self.endpoint.recv(8192)

		self.endpoint.close()
		return headers, payload.decode('UTF-8')

class BankID():
	def __init__(self, host='appapi2.test.bankid.com', client_certificate='bankid_certificate.pem', client_private_key='bankid_key.pem'):
		self.host = host
		self.client_certificate = client_certificate
		self.client_private_key = client_private_key
		# Cert & Key - Extracted from FPTestcert3_20200618.p12 (https://www.bankid.com/utvecklare/test) using:
		#  openssl pkcs12 -in FPTestcert3_20200618.p12 -out testkey.pem -nocerts -nodes
		#  openssl pkcs12 -in FPTestcert3_20200618.p12 -out testcert.pem -clcerts -nokeys

	def sign(self, personal_number, message='Ond Vetenskapsman', host='127.0.0.1'):
		request_body = {
			"personalNumber": personal_number,
			"endUserIp": host,
			"userVisibleData": b64encode(bytes(message, 'UTF-8')).decode('UTF-8')
		}
		request_data = json.dumps(request_body)
		headers = {
			'Content-Type': 'application/json',
			'Host': self.host,
			'Content-Length': len(request_data)
		}

		self.connection = HTTP_REQUEST(self.host, url='/rp/v5.1/sign', payload=request_data, headers=headers, client_certificate=self.client_certificate, client_private_key=self.client_private_key)
		headers, response = self.connection.get_response()
		return json.loads(response)

	def collect(self, orderReference):
		request_data = json.dumps({"orderRef": orderReference})
		headers = {
			'Content-Type': 'application/json',
			'Host': self.host,
			'Content-Length': len(request_data)
		}

		self.connection = HTTP_REQUEST(self.host, url='/rp/v5.1/collect', payload=request_data, headers=headers, client_certificate=self.client_certificate, client_private_key=self.client_private_key)
		headers, response = self.connection.get_response()

		json_payload = json.loads(response)

		return json_payload