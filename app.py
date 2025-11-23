# server/app.py
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json
import os
from datetime import datetime
from threading import Lock

app = Flask(__name__, static_folder='../client', static_url_path='/static')
CORS(app)  # allow cross-origin requests (adjust origins in production)

DATA_FILE = 'messages.json'
lock = Lock()

def ensure_datafile():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f)

def load_messages():
    ensure_datafile()
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_messages(msgs):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(msgs, f, ensure_ascii=False, indent=2)

@app.route('/')
def root():
    # serve the client index.html for convenience
    return send_from_directory('../client', 'index.html')

@app.route('/send', methods=['POST'])
def send():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'invalid json'}), 400

    username = data.get('username', 'Anon')
    text = data.get('text', '').strip()
    if not text:
        return jsonify({'error': 'empty message'}), 400

    message = {
        'id': int(datetime.utcnow().timestamp() * 1000),
        'username': username,
        'text': text,
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }

    with lock:
        msgs = load_messages()
        msgs.append(message)
        # optional: keep only last N messages
        if len(msgs) > 1000:
            msgs = msgs[-1000:]
        save_messages(msgs)

    return jsonify({'status': 'ok', 'message': message}), 201

@app.route('/messages', methods=['GET'])
def messages():
    # Optional query param since=<timestamp> to get new messages only
    since = request.args.get('since')  # ISO timestamp or ms id
    msgs = load_messages()
    if since:
        try:
            # if numeric id
            since_id = int(since)
            msgs = [m for m in msgs if m['id'] > since_id]
        except:
            msgs = [m for m in msgs if m['timestamp'] > since]
    return jsonify({'messages': msgs})

if __name__ == '__main__':
    ensure_datafile()
    app.run(host='0.0.0.0', port=5000, debug=True)
