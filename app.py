# server/app.py
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json
import os
from datetime import datetime
from threading import Lock
import shutil

# Initialize Flask app
app = Flask(__name__, static_folder='../client', static_url_path='/static')
CORS(app)  # allow cross-origin requests

# Path to store messages.json inside server folder
DATA_FILE = os.path.join(os.path.dirname(__file__), 'messages.json')
BACKUP_FOLDER = os.path.join(os.path.dirname(__file__), 'backup_messages')

lock = Lock()

# --- Ensure backup folder exists ---
if not os.path.exists(BACKUP_FOLDER):
    os.makedirs(BACKUP_FOLDER)

# --- Create backup on server start ---
if os.path.exists(DATA_FILE):
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(BACKUP_FOLDER, f"messages_{timestamp}.json")
    shutil.copy2(DATA_FILE, backup_file)
    print(f"[INFO] messages.json backed up to {backup_file}")

# --- Ensure messages.json exists ---
def ensure_datafile():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=2)

# --- Load messages from JSON ---
def load_messages():
    ensure_datafile()
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

# --- Save messages to JSON ---
def save_messages(msgs):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(msgs, f, ensure_ascii=False, indent=2)

# --- Serve client page ---
@app.route('/')
def root():
    return send_from_directory('../client', 'index.html')

# --- Send message endpoint ---
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
        msgs.append(message)  # append all messages; no limit
        save_messages(msgs)

    return jsonify({'status': 'ok', 'message': message}), 201

# --- Get messages endpoint ---
@app.route('/messages', methods=['GET'])
def messages():
    since = request.args.get('since')  # optional
    msgs = load_messages()
    if since:
        try:
            since_id = int(since)
            msgs = [m for m in msgs if m['id'] > since_id]
        except:
            msgs = [m for m in msgs if m['timestamp'] > since]
    return jsonify({'messages': msgs})

# --- Main ---
if __name__ == '__main__':
    ensure_datafile()
    print("[INFO] Starting Flask server on 0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
