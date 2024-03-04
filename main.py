from flask import Flask, request, jsonify, make_response
import json
from flask_cors import CORS
from pymongo import MongoClient
from pymongo import ReturnDocument
from bson import ObjectId
import base64
from deepface import DeepFace
import random
import os
from rq import Queue
from rq.job import Job
from worker import conn
import time
from flask_bcrypt import Bcrypt
from PIL import Image
import io
import redis
import os
from multiprocessing import shared_memory
import pickle
import psutil
from io import BytesIO

app = Flask(__name__)
app.config['SECRET_KEY'] = 'my-secret-key-for-authentication'
CORS(app)

q = Queue(connection=conn)


bcrypt = Bcrypt(app)

client = MongoClient('mongodb+srv://hamouaitabderrahim:HMvqsDkH1VI14yPC@cluster0.a9flbes.mongodb.net/data-collection?retryWrites=true&w=majority')

db = client["data-collection"]

shared_sessions = None

sessions = conn.get('sessions')
if sessions is None:
	conn.set('sessions', json.dumps({}))
	sessions = conn.get('sessions')
else:
	sessions = json.loads(sessions)

parent = shared_memory.ShareableList([json.dumps({})])

users = db["users"]
emotion_recordings = db["emotion_recordings"]

@app.route('/')
def index():
	return 'Hello, Hamou. You`re the best, believe me wellah!'

# Authentication Routes
@app.route('/api/auth/signin', methods=['POST'])
def signin():
	username = request.json['username']
	password = request.json['password']
	user = users.find_one({"username": username})
	if user is not None:
		print(user)
		user['_id'] = str(user['_id'])
		password_is_valid = bcrypt.check_password_hash(user['password'], password)
		if password_is_valid:
			return jsonify({'message': 'Document created successfully', 'user': user }), 200
		else:
			return jsonify({ 'message': 'Wrong password' })
	else:
		return jsonify({'error': 'No user matches the provided data'}), 400

@app.route('/api/auth/signup', methods=['POST'])
def signup():
	user = users.find_one({ "username": request.json['username'] })
	if user is None:
		user = users.insert_one({
			"fullName": request.json['fullName'],
			"username": request.json['username'],
			"password": bcrypt.generate_password_hash(request.json['password']).decode('utf-8'),
			"image": ''
			})
		user = users.find_one({ "_id": user.inserted_id })
		user['_id'] = str(user['_id'])
		return jsonify({ 'message': 'User signed up successfully', 'user': user })
	else:
		return jsonify({'error': 'Username already exists'}), 400

@app.route('/api/update-user/<string:id>', methods=['PUT'])
def update_user(id):
	try:
		user_id = ObjectId(id)
		update_data = {
			"$set": {
				"fullName": request.json.get('fullname'),
				"image": request.json.get('image')
				}
        	}
		user = users.find_one_and_update(
			{"_id": user_id},
			update_data,
			return_document=True
		)
		user['_id'] = str(user['_id'])
		return jsonify({"user": user}), 200
	except Exception as error:
		return jsonify({"error": dir(error)}), 400

@app.route('/api/delete-user/<string:id>', methods=['DELETE'])
def delete_user(id):
	user_id = ObjectId(id)
	result = users.delete_one({'_id': user_id})
	if result.deleted_count == 1:
		return jsonify({ 'message': 'User deleted successfully' })
	return jsonify({ 'error': 'User not deleted' })

def get_python_process_port():
	for proc in psutil.process_iter(['pid', 'name', 'connections']):
		if proc.info['name'] == 'python':
			for conn in proc.info['connections']:
				if conn.status == psutil.CONN_LISTEN:
					return conn.laddr.port
	return None

def post_images_task(user_id, images, minute, hour, day, month, year):
	print('size', len(sessions))
	emotions = ["happy", "sad", "angry", "disgust", "surprised", "fear"]
	bytes_arrays_string = images.split("|")
	for byte_array_str in bytes_arrays_string:
		try:
			print(byte_array_str)
			img = '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'
			with open("image.png", "wb") as fh:
				fh.write(base64.b64decode(img))
		except Exception as e:
			print("Error:", e)
		emotions_probabilities = DeepFace.analyze(img_path = "image.png",
			actions = ['emotion']
		)
		if user_id not in sessions:
			print("New one")
			sessions[user_id] = {"happy": 0, "sad": 0, "disgust": 0, "angry": 0, "surprised": 0, "fear": 0, "start_time": str(hour) + ":" + str(minute)}
			emotion = emotions_probabilities[0]['dominant_emotion']
			sessions[user_id][emotion] = 1
		else:
			print("Old one")
			emotion = emotions_probabilities[0]['dominant_emotion']
			sessions[user_id][emotion] = sessions[user_id][emotion] + 1
	if len(bytes_arrays_string) < 32:
		emotions_recording = emotion_recordings.find_one({ "id_user": user_id, "date": str(day) + '-' + str(month) + '-' + str(year) })
		if emotions_recording is not None:
			total = sessions[user_id]["happy"] + sessions[user_id]["sad"] + sessions[user_id]["disgust"] + sessions[user_id]["fear"] + sessions[user_id]["surprised"] + sessions[user_id]["angry"]
			emotions_recording["recordings"].append({
					"period_start": sessions[user_id]["start_time"],
					"period_end": str(hour) + ":" + str(minute),
					"happy": str((sessions[user_id]["happy"] / total) * 100) + "%",
					"anger": str((sessions[user_id]["angry"] / total) * 100) + "%",
					"sad": str((sessions[user_id]["sad"] / total) * 100) + "%",
					"surprise": str((sessions[user_id]["surprised"] / total) * 100) + "%",
					"disgust": str((sessions[user_id]["disgust"] / total) * 100) + "%",
					"fear": str((sessions[user_id]["fear"] / total) * 100) + "%"
				})
			update_data = {
			"$set": {
				"happy": get_general_emotion(emotions_recording["recordings"], "happy"),
				"sad": get_general_emotion(emotions_recording["recordings"], "sad"),
				"disgust": get_general_emotion(emotions_recording["recordings"], "disgust"),
				"fear": get_general_emotion(emotions_recording["recordings"], "fear"),
				"anger": get_general_emotion(emotions_recording["recordings"], "anger"),
				"surprise": get_general_emotion(emotions_recording["recordings"], "surprise"),
				"recordings": emotions_recording["recordings"]
				}
        	}
			emotion_recordings.find_one_and_update(
				{"_id": emotions_recording["_id"]},
				update_data,
				return_document=True
			)
		else:
			total = sessions[user_id]["happy"] + sessions[user_id]["sad"] + sessions[user_id]["disgust"] + sessions[user_id]["fear"] + sessions[user_id]["surprised"] + sessions[user_id]["angry"]
			emotion_recordings.insert_one({
				"id_user": user_id,
				"date": str(day) + '-' + str(month) + '-' + str(year),
				"happy": str((sessions[user_id]["happy"] / total) * 100) + "%",
				"anger": str((sessions[user_id]["angry"] / total) * 100) + "%",
				"sad": str((sessions[user_id]["sad"] / total) * 100) + "%",
				"surprise": str((sessions[user_id]["surprised"] / total) * 100) + "%",
				"disgust": str((sessions[user_id]["disgust"] / total) * 100) + "%",
				"fear": str((sessions[user_id]["fear"] / total) * 100) + "%",
				"recordings": [{
					"period_start": sessions[user_id]["start_time"],
					"period_end": str(hour) + ":" + str(minute),
					"happy": str((sessions[user_id]["happy"] / total) * 100) + "%",
					"anger": str((sessions[user_id]["angry"] / total) * 100) + "%",
					"sad": str((sessions[user_id]["sad"] / total) * 100) + "%",
					"surprise": str((sessions[user_id]["surprised"] / total) * 100) + "%",
					"disgust": str((sessions[user_id]["disgust"] / total) * 100) + "%",
					"fear": str((sessions[user_id]["fear"] / total) * 100) + "%"
				}]
			})
		del sessions[user_id]
	conn.set('sessions', json.dumps(sessions))

@app.route('/api/post-images', methods=['POST'])
def post_images():
	#global shared_sessions
	from main import post_images_task
	job = q.enqueue_call(
        func=post_images_task, args=(request.json.get('userId'), request.json.get('images'), request.json.get('minute'), request.json.get('hour'), request.json.get('day'), request.json.get('month'), request.json.get('year')), result_ttl=0
    )
	print(job.get_id())
	return jsonify({ 'message': 'It works correctly' })

@app.route('/users/<string:value>/emotion-recordings', methods=['GET'])
def get_emotion_recordings(value):
	documents = emotion_recordings.find({"id_user": value})
	documents_list = []
	for doc in documents:
		doc['_id'] = str(doc['_id'])  # Convert ObjectId to string
		documents_list.append(doc)
	if documents_list:
		return jsonify({ "records": documents_list }), 200
	else:
		return jsonify({'message': 'No documents found with the specified attribute and value'}), 404



@app.route('/create', methods=['POST'])
def create():
    data = request.json
    if data:
        print(data)
        return jsonify({'message': 'Document created successfully', 'id': 'str(result.inserted_id)'}), 200
    else:
        return jsonify({'error': 'No data provided'}), 400

def get_general_emotion(recordings, emotion):
	emotion_frequency = 0
	for recording in recordings:
		emotion_frequency = emotion_frequency + float(recording[emotion][:-1])
	return str(emotion_frequency / len(recordings)) + "%"


if __name__ == '__main__':
	app.run(debug=True)