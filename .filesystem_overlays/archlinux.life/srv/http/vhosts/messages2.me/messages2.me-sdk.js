import {HTTPSendJSON, login} from './messages2.me-sdk-helpers.js';

window.login = login;
window.HTTPSendJSON = HTTPSendJSON;
window.rooms = {}
window.access_token = null;
window.active_room = null;

window.get_rooms = (callback) => {
	HTTPSendJSON('https://api.messages2.me/getRooms', {
			"token" : access_token
		}).then(data => {
			rooms = data['rooms'];

			callback()
		}
	);
}

window.send_message = (message) => {
	Object.keys(rooms[active_room]["members"]).forEach((member_id) => {
		//if(member['identity'] == 1)
		//	return;

		HTTPSendJSON('https://api.messages2.me/sendMessage', {
				"token" : access_token,
				"room_id" : active_room,
				"reciever" : member_id,
				"data" : {
					"message" : message
				}
			}).then(data => {
				if(data?.['status'] != 'success') {
					console.error(data);
				}
			}
		);
	})
}

window.get_messages = (room_id, latest_id=null, callback) => {
	callback(room_id);

	let payload_data = {
		"token" : access_token,
		"room_id" : room_id
	}
	if (latest_id)
		payload_data['from_id'] = latest_id;

	HTTPSendJSON('https://api.messages2.me/getMessages', payload_data).then(data => {
		if (!data || typeof data === 'undefined')
			return;

		rooms[room_id]['messages'] = rooms[room_id]['messages'].concat(data['messages'])
		callback(room_id);

		if(message_retriever && data['messages'].length) {
			clearInterval(message_retriever);

			message_retriever = setInterval(() => {
				get_messages(room_id, rooms[room_id]['messages'].slice(-1)[0]['id'], callback)
			}, 1000)
		}
	});

	if(!message_retriever) {
		message_retriever = setInterval(() => {
			get_messages(room_id, rooms[room_id]['messages'].slice(-1)[0]['id'], callback)
		}, 1000)
	}
}

window.get_members = (room_id, callback) => {
	if (Object.keys(rooms[room_id]['members']).length <= 0) {
		HTTPSendJSON('https://api.messages2.me/getMembers', {
				"token" : access_token,
				"room_id" : room_id
			}).then(data => {
				rooms[room_id]['members'] = data['members']
				callback(room_id);
			}
		);
	} else {
		callback(room_id);
	}
}