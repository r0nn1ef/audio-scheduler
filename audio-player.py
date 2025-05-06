import time
import schedule
import pygame
from datetime import datetime
import pytz
import logging
import yaml
import argparse

# --- Logging Configuration ---
LOG_FILE = '/var/log/audio_player.log'
logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuration ---
YAML_FILE = 'schedule.yaml'
TIMEZONE = pytz.timezone('America/Chicago')

# --- Initialize Pygame Mixer ---
pygame.mixer.init()

# --- Function to Play Audio ---
def play_audio(filepath, call_name, volume=1.0):
    log_message = f"Playing {call_name} at {datetime.now(TIMEZONE).strftime('%Y-%m-%d %H:%M:%S %Z%z')} with volume {volume}"
    logging.info(log_message)
    try:
        pygame.mixer.music.load(filepath)
        pygame.mixer.music.set_volume(volume)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
    except pygame.error as e:
        logging.error(f"Error playing {call_name}: {e}")

# --- Load Schedule from YAML ---
def load_schedule():
    try:
        with open(YAML_FILE, 'r') as f:
            schedule_data = yaml.safe_load(f)
            return schedule_data.get('weekdays', {}), schedule_data.get('weekends', {})
    except FileNotFoundError:
        logging.error(f"YAML configuration file '{YAML_FILE}' not found.")
        return {}, {}
    except yaml.YAMLError as e:
        logging.error(f"Error parsing YAML file '{YAML_FILE}': {e}")
        return {}, {}

# --- Schedule Jobs Based on Day of the Week ---
def schedule_bugle_calls():
    weekday_schedule, weekend_schedule = load_schedule()
    now = datetime.now(TIMEZONE)
    day_of_week = now.weekday()  # Monday is 0, Sunday is 6

    schedule.clear()  # Clear any existing schedules

    if 0 <= day_of_week <= 4:  # Monday to Friday
        logging.info("Scheduling weekday bugle calls.")
        for call, details in weekday_schedule.items():
            play_time = details.get('time')
            audio_file = details.get('audio_file')
            if play_time and audio_file:
                schedule.every().day.at(play_time).do(play_audio, audio_file, call)
                logging.info(f"Scheduled weekday '{call}' to play at {play_time} from '{audio_file}'")
            else:
                logging.warning(f"Skipping weekday '{call}': missing 'time' or 'audio_file'.")
    elif 5 <= day_of_week <= 6:  # Saturday or Sunday
        logging.info("Scheduling weekend bugle calls.")
        for call, details in weekend_schedule.items():
            play_time = details.get('time')
            audio_file = details.get('audio_file')
            if play_time and audio_file:
                schedule.every().day.at(play_time).do(play_audio, audio_file, call)
                logging.info(f"Scheduled weekend '{call}' to play at {play_time} from '{audio_file}'")
            else:
                logging.warning(f"Skipping weekend '{call}': missing 'time' or 'audio_file'.")

def main():
    parser = argparse.ArgumentParser(description='Play bugle calls.  Can be used to play a specific call or schedule calls.')
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Subparser for playing a specific file
    play_parser = subparsers.add_parser('play', help='Play a specific MP3 file.')
    play_parser.add_argument('filepath', help='Path to the MP3 file to play.')
    play_parser.add_argument('--volume', type=float, default=1.0, help='Playback volume (0.0 to 1.0). Default is 1.0.')

    # Subparser for scheduling calls
    schedule_parser = subparsers.add_parser('schedule', help='Schedule bugle calls based on YAML.')

    args = parser.parse_args()

    if args.command == 'play':
        play_audio(args.filepath, 'Manual Playback', args.volume)
    elif args.command == 'schedule':
        schedule_bugle_calls()
        while True:
            schedule.run_pending()
            time.sleep(1)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()