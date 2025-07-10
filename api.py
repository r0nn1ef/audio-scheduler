from flask import Flask, request, jsonify, abort, send_from_directory
from functools import wraps
from datetime import datetime
import yaml
import os
import json
import logging

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, 'config.yml')
REQUEST_FILE = os.path.join(BASE_DIR, 'play_request.json')

# Load config
def load_config():
    with open(CONFIG_PATH, 'r') as f:
        return yaml.safe_load(f)

config = load_config()
logging.basicConfig(level=logging.INFO)

# Token-based auth
def require_token(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("X-API-Token")
        if not token or token != config.get("api_token"):
            abort(401)
        return f(*args, **kwargs)
    return decorated

# Get today’s schedule
def get_todays_schedule():
    now = datetime.now()
    weekday = now.weekday()
    return config['weekdays'] if weekday < 5 else config['weekends']

@app.route('/status')
@require_token
def status():
    state_file = os.path.join(BASE_DIR, 'play_state.json')
    try:
        with open(state_file, 'r') as f:
            state = json.load(f)
        return jsonify(state)
    except Exception:
        return jsonify({"error": "Unable to read state"}), 500

@app.route('/play', methods=['POST'])
@require_token
def play():
    data = request.get_json()
    call = data.get('call')
    schedule = get_todays_schedule()

    if call not in schedule:
        return jsonify({"error": f"'{call}' is not in today's schedule"}), 404

    audio_file = schedule[call]['audio_file']
    full_path = os.path.join(BASE_DIR, audio_file)

    if not os.path.exists(full_path):
        return jsonify({"error": f"File not found: {audio_file}"}), 404

    payload = {
        "timestamp": datetime.now().isoformat(),
        "call": call,
        "filepath": full_path
    }

    try:
        with open(REQUEST_FILE, 'w') as f:
            json.dump(payload, f)
        return jsonify({"status": "queued", "call": call})
    except Exception as e:
        logging.error(f"Failed to write request: {e}")
        return jsonify({"error": "Internal error"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)