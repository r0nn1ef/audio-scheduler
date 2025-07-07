import time
import schedule
import pygame
from datetime import datetime, time as dt_time
import pytz
import logging
import yaml
import argparse
import os
import json

LOG_FILE = '/var/log/audio_player.log'
logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

YAML_FILE = 'schedule.yml'
TIMEZONE = pytz.timezone('America/Chicago')
STATE_FILE = 'play_state.json'

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
                if state.get('date') != datetime.now(TIMEZONE).strftime('%Y-%m-%d'):
                    return {"date": datetime.now(TIMEZONE).strftime('%Y-%m-%d'), "played_calls": []}
                return state
        except json.JSONDecodeError:
            logging.warning(f"Error decoding {STATE_FILE}, starting with empty state.")
    return {"date": datetime.now(TIMEZONE).strftime('%Y-%m-%d'), "played_calls": []}

def save_state(state):
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f)
    except IOError as e:
        logging.error(f"Could not save state to {STATE_FILE}: {e}")

pygame.mixer.init()

def play_audio(filepath, call_name, volume=1.0):
    logging.info(f"Attempting to play {call_name} at {datetime.now(TIMEZONE).strftime('%Y-%m-%d %H:%M:%S %Z%z')} with volume {volume}")
    state = load_state()
    current_date = datetime.now(TIMEZONE).strftime('%Y-%m-%d')

    if state.get('date') != current_date:
        state = {"date": current_date, "played_calls": []}

    if call_name in state.get('played_calls', []):
        logging.info(f"'{call_name}' already played today. Skipping.")
        return

    try:
        pygame.mixer.music.load(filepath)
        pygame.mixer.music.set_volume(volume)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
        logging.info(f"Successfully played {call_name}")
        state['played_calls'].append(call_name)
        save_state(state)
    except pygame.error as e:
        logging.error(f"Error playing {call_name}: {e}")
        if call_name in state['played_calls']:
            state['played_calls'].remove(call_name)
            save_state(state)

def load_schedule():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    yaml_path = os.path.join(script_dir, YAML_FILE)
    try:
        with open(yaml_path, 'r') as f:
            schedule_data = yaml.safe_load(f)
            return schedule_data.get('weekdays', {}), schedule_data.get('weekends', {})
    except FileNotFoundError:
        logging.error(f"YAML configuration file '{yaml_path}' not found.")
        return {}, {}
    except yaml.YAMLError as e:
        logging.error(f"Error parsing YAML file '{yaml_path}': {e}")
        return {}, {}

def schedule_audio_jobs(initial_startup=False):
    weekday_schedule, weekend_schedule = load_schedule()
    now = datetime.now(TIMEZONE)
    day_of_week = now.weekday()
    current_time_obj = now.time()

    schedule.clear()

    selected_schedule = weekday_schedule if day_of_week <= 4 else weekend_schedule
    logging.info("Determined today is a weekday." if day_of_week <= 4 else "Determined today is a weekend day.")

    state = load_state()

    for call, details in selected_schedule.items():
        play_time_str = details.get('time')
        audio_file = details.get('audio_file')

        if not play_time_str or not audio_file:
            logging.warning(f"Skipping '{call}': missing 'time' or 'audio_file'.")
            continue

        try:
            scheduled_time_obj = dt_time.fromisoformat(play_time_str)
        except ValueError:
            logging.warning(f"Invalid time format for '{call}': {play_time_str}. Skipping.")
            continue

        if initial_startup and current_time_obj > scheduled_time_obj:
            logging.info(f"Skipping scheduling '{call}' today ({play_time_str}) as its time already passed on initial startup.")
            continue

        schedule.every().day.at(play_time_str).do(play_audio, audio_file, call)
        logging.info(f"Scheduled '{call}' to play at {play_time_str} from '{audio_file}'")

def main():
    parser = argparse.ArgumentParser(description='Play bugle calls. Can be used to play a specific call or schedule calls.')
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    play_parser = subparsers.add_parser('play', help='Play a specific MP3 file.')
    play_parser.add_argument('filepath', help='Path to the MP3 file to play.')
    play_parser.add_argument('--volume', type=float, default=1.0, help='Playback volume (0.0 to 1.0). Default is 1.0.')

    subparsers.add_parser('schedule', help='Schedule bugle calls based on YAML.')

    args = parser.parse_args()

    is_initial_startup = False
    uptime_seconds = -1
    try:
        with open('/proc/uptime', 'r') as f:
            uptime_seconds = float(f.readline().split()[0])
    except FileNotFoundError:
        logging.warning("Could not read /proc/uptime to determine system uptime.")

    if uptime_seconds != -1 and uptime_seconds < 300:
        is_initial_startup = True
        logging.info(f"Detected initial system startup (uptime: {uptime_seconds:.2f}s). Adjusting scheduling behavior.")
    elif uptime_seconds == -1:
        logging.warning("Uptime check failed. Assuming not initial startup unless proven otherwise.")

    if args.command == 'play':
        play_audio(args.filepath, 'Manual Playback', args.volume)
    elif args.command == 'schedule':
        schedule_audio_jobs(initial_startup=is_initial_startup)
        while True:
            schedule.run_pending()
            time.sleep(1)
    else:
        logging.error("No command specified. Use 'play <file>' or 'schedule'.")
        parser.print_help()

if __name__ == '__main__':
    main()