import time
import schedule
import pygame
from datetime import datetime, time as dt_time # Import time specifically
import pytz
import logging
import yaml
import argparse
import os
import json # For persistent state

# --- Logging Configuration ---
LOG_FILE = '/var/log/audio_player.log'
logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuration ---
YAML_FILE = 'schedule.yml'
TIMEZONE = pytz.timezone('America/Chicago') # Or your actual timezone

# --- State Management ---
STATE_FILE = 'play_state.json' # File to store played calls today

def load_state():
    """Loads the state (e.g., calls played today) from a JSON file."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
                # Ensure the 'date' matches today, clear if not
                if state.get('date') != datetime.now(TIMEZONE).strftime('%Y-%m-%d'):
                    return {"date": datetime.now(TIMEZONE).strftime('%Y-%m-%d'), "played_calls": []}
                return state
        except json.JSONDecodeError:
            logging.warning(f"Error decoding {STATE_FILE}, starting with empty state.")
            pass # Fall through to create new state
    return {"date": datetime.now(TIMEZONE).strftime('%Y-%m-%d'), "played_calls": []}

def save_state(state):
    """Saves the current state to a JSON file."""
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f)
    except IOError as e:
        logging.error(f"Could not save state to {STATE_FILE}: {e}")

# --- Initialize Pygame Mixer ---
pygame.mixer.init()

# --- Function to Play Audio ---
def play_audio(filepath, call_name, volume=1.0):
    log_message = f"Attempting to play {call_name} at {datetime.now(TIMEZONE).strftime('%Y-%m-%d %H:%M:%S %Z%z')} with volume {volume}"
    logging.info(log_message)

    state = load_state()
    current_date = datetime.now(TIMEZONE).strftime('%Y-%m-%d')

    if state.get('date') != current_date:
        # Reset state if day has changed (should be handled by load_state, but double check)
        state = {"date": current_date, "played_calls": []}

    # Check if this call has already been played today
    if call_name in state.get('played_calls', []):
        logging.info(f"'{call_name}' already played today. Skipping.")
        return # Do not play again

    try:
        pygame.mixer.music.load(filepath)
        pygame.mixer.music.set_volume(volume)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
        logging.info(f"Successfully played {call_name}")

        # Mark as played for today
        state['played_calls'].append(call_name)
        save_state(state)

    except pygame.error as e:
        logging.error(f"Error playing {call_name}: {e}")
        # Optionally, remove from 'played_calls' if it failed to play
        if call_name in state['played_calls']:
            state['played_calls'].remove(call_name)
            save_state(state)

# --- Load Schedule from YAML ---
def load_schedule():
    # Use os.path.join for robust path handling
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

# --- Schedule Jobs Based on Day of the Week ---
def schedule_audio_jobs(initial_startup=False): # Added initial_startup flag
    weekday_schedule, weekend_schedule = load_schedule()
    now = datetime.now(TIMEZONE)
    day_of_week = now.weekday()  # Monday is 0, Sunday is 6
    current_time_obj = now.time() # Just the time part

    schedule.clear()  # Clear any existing schedules

    selected_schedule = {}
    if 0 <= day_of_week <= 4:  # Monday to Friday
        logging.info("Determined today is a weekday.")
        selected_schedule = weekday_schedule
    elif 5 <= day_of_week <= 6:  # Saturday or Sunday
        logging.info("Determined today is a weekend day.")
        selected_schedule = weekend_schedule

    state = load_state() # Load state to know what's already played today

    for call, details in selected_schedule.items():
        play_time_str = details.get('time')
        audio_file = details.get('audio_file')

        if play_time_str and audio_file:
            # Parse the scheduled time
            try:
                scheduled_time_obj = dt_time.fromisoformat(play_time_str)
            except ValueError:
                logging.warning(f"Invalid time format for '{call}': {play_time_str}. Skipping.")
                continue

            # Check if this is an initial startup and the time has already passed today
            # AND if it hasn't been played already (from state)
            if initial_startup and current_time_obj > scheduled_time_obj and \
               call not in state.get('played_calls', []):
                logging.info(f"Skipping past scheduled '{call}' ({play_time_str}) on initial startup.")
                continue # DO NOT schedule if it's past and it's boot time

            # Schedule the job for future days
            schedule.every().day.at(play_time_str).do(play_audio, audio_file, call)
            logging.info(f"Scheduled '{call}' to play at {play_time_str} from '{audio_file}'")
        else:
            logging.warning(f"Skipping '{call}': missing 'time' or 'audio_file'.")

def main():
    parser = argparse.ArgumentParser(description='Play bugle calls. Can be used to play a specific call or schedule calls.')
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Subparser for playing a specific file
    play_parser = subparsers.add_parser('play', help='Play a specific MP3 file.')
    play_parser.add_argument('filepath', help='Path to the MP3 file to play.')
    play_parser.add_argument('--volume', type=float, default=1.0, help='Playback volume (0.0 to 1.0). Default is 1.0.')

    # Subparser for scheduling calls
    schedule_parser = subparsers.add_parser('schedule', help='Schedule bugle calls based on YAML.')

    args = parser.parse_args()

    # --- Initial Startup Logic ---
    # This determines if the script is starting for the first time after a system boot.
    # We use os.path.getmtime for a rough estimate of script modification/creation time,
    # or more robustly, check system uptime.
    # For now, let's just assume if it's running via 'schedule' command, it's potentially
    # a new boot scenario where we need to be careful.

    is_initial_startup = False
    # A simple check: if the log file size is very small, it might be a fresh run or first run of the day
    # Or, more robustly, check system uptime:
    uptime_seconds = -1
    try:
        with open('/proc/uptime', 'r') as f:
            uptime_seconds = float(f.readline().split()[0])
    except FileNotFoundError:
        logging.warning("Could not read /proc/uptime to determine system uptime.")

    # Consider it an initial startup if uptime is less than a certain threshold (e.g., 5 minutes = 300 seconds)
    if uptime_seconds != -1 and uptime_seconds < 300: # 5 minutes
        is_initial_startup = True
        logging.info(f"Detected initial system startup (uptime: {uptime_seconds:.2f}s). Adjusting scheduling behavior.")
    elif uptime_seconds == -1: # If uptime check failed, be cautious
         logging.warning("Uptime check failed. Assuming not initial startup unless proven otherwise.")

    # --- Command Handling ---
    if args.command == 'play':
        play_audio(args.filepath, 'Manual Playback', args.volume)
    elif args.command == 'schedule':
        # Pass the initial_startup flag to the scheduling function
        schedule_audio_jobs(initial_startup=is_initial_startup)
        while True:
            schedule.run_pending()
            time.sleep(1)
    else:
        # If no command is given (e.g., when run directly by systemd without 'schedule' argument)
        # This block will likely be hit if your ExecStart is just 'python3 your_script.py'
        logging.error("No command specified. Use 'play <file>' or 'schedule'.")
        parser.print_help()

if __name__ == '__main__':
    main()