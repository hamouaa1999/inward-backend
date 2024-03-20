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
from workers.worker import conn
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
import random
from images import happy, sad, surprise, angry, fear, disgusted

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
	return 'Hello, Hamou. You`re the best, believe me!'

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
		return jsonify({ 'message': 'User deleted successfully...' })
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
	emotions = ["happy", "sad", "angry", "disgust", "surprise", "fear"]
	bytes_arrays_string = images.split("|")
	for byte_array_str in bytes_arrays_string:
		try:
			
			images = [happy, sad, surprise, angry, fear, disgusted]
			image = random.choice(images)
			print('index', images.index(image))
			with open("image.png", "wb") as fh:
				fh.write(base64.b64decode(image))
		except Exception as e:
			print("Error:", e)
		emotions_probabilities = DeepFace.analyze(img_path = "image.png",
			actions = ['emotion']
		)
		if user_id not in sessions:
			print("New one")
			sessions[user_id] = {"happy": 0, "sad": 0, "disgust": 0, "angry": 0, "surprise": 0, "fear": 0, "start_time": str(hour) + ":" + str(minute)}
			emotion = emotions_probabilities[0]['dominant_emotion']
			sessions[user_id][emotion] = 1
		else:
			print("Old one")
			emotion = emotions_probabilities[0]['dominant_emotion']
			sessions[user_id][emotion] = sessions[user_id][emotion] + 1
	if len(bytes_arrays_string) < 32:
		emotions_recording = emotion_recordings.find_one({ "id_user": user_id, "date": str(day) + '-' + str(month) + '-' + str(year) })
		if emotions_recording is not None:
			total = sessions[user_id]["happy"] + sessions[user_id]["sad"] + sessions[user_id]["disgust"] + sessions[user_id]["fear"] + sessions[user_id]["surprise"] + sessions[user_id]["angry"]
			emotions_recording["recordings"].append({
					"period_start": sessions[user_id]["start_time"],
					"period_end": str(hour) + ":" + str(minute),
					"happy": str((sessions[user_id]["happy"] / total) * 100) + "%",
					"anger": str((sessions[user_id]["angry"] / total) * 100) + "%",
					"sad": str((sessions[user_id]["sad"] / total) * 100) + "%",
					"surprise": str((sessions[user_id]["surprise"] / total) * 100) + "%",
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
			total = sessions[user_id]["happy"] + sessions[user_id]["sad"] + sessions[user_id]["disgust"] + sessions[user_id]["fear"] + sessions[user_id]["surprise"] + sessions[user_id]["angry"]
			emotion_recordings.insert_one({
				"id_user": user_id,
				"date": str(day) + '-' + str(month) + '-' + str(year),
				"happy": str((sessions[user_id]["happy"] / total) * 100) + "%",
				"anger": str((sessions[user_id]["angry"] / total) * 100) + "%",
				"sad": str((sessions[user_id]["sad"] / total) * 100) + "%",
				"surprise": str((sessions[user_id]["surprise"] / total) * 100) + "%",
				"disgust": str((sessions[user_id]["disgust"] / total) * 100) + "%",
				"fear": str((sessions[user_id]["fear"] / total) * 100) + "%",
				"recordings": [{
					"period_start": sessions[user_id]["start_time"],
					"period_end": str(hour) + ":" + str(minute),
					"happy": str((sessions[user_id]["happy"] / total) * 100) + "%",
					"anger": str((sessions[user_id]["angry"] / total) * 100) + "%",
					"sad": str((sessions[user_id]["sad"] / total) * 100) + "%",
					"surprise": str((sessions[user_id]["surprise"] / total) * 100) + "%",
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
	app.run(debug=True, host="0.0.0.0", port=5000)