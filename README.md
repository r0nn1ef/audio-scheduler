# Solar-Powered Audio Player System

## Project Overview

This project is designed to create a solar-powered, automated bugle call system using a Raspberry Pi Zero. It plays 
various US Army bugle calls (like Reveille, Retreat, Tattoo, and Taps) at scheduled times based on the day of the week 
(weekdays and weekends). The schedule and audio file paths are configured using a YAML file, making it easy to customize 
without modifying the Python code. The system is intended to run headless and be powered by a small solar power setup, 
making it ideal for outdoor use.

## Features

* **Scheduled Playback:** Plays bugle call MP3 files at times defined in a YAML configuration file.
* **Weekday/Weekend Schedules:** Supports different schedules for weekdays (Monday-Friday) and weekends (Saturday-Sunday).
* **Command-Line Testing:** Includes an option to play specific MP3 files directly from the command line for testing purposes.
* **Headless Operation:** Designed to run on a Raspberry Pi Zero without a monitor.
* **Solar Power Ready:** Intended to be powered by a small solar power system (components not included in this software setup).
* **Configurable via YAML:** Schedule times and audio file paths are easily managed in a separate `schedule.yaml` file.

## Prerequisites

* **Raspberry Pi Zero 2 W:** The central processing unit for the system.
* **Raspberry Pi OS Lite:** A lightweight operating system for the Raspberry Pi (recommended for headless operation).
* **Audio Output:** A way for the Raspberry Pi to play audio (e.g., a HAT with speakers or connection to external speakers).
* **MP3 Audio Files:** You will need MP3 files for the bugle calls you want to schedule.
* **Solar Power Components (Optional):** Solar panel, charge controller, and battery for автономное operation.
* **Python 3:** Must be installed on the Raspberry Pi.
* **Required Python Packages:**
    * `pygame`
    * `schedule`
    * `pytz`
    * `PyYAML`

## Installation

1.  **Install Raspberry Pi OS Lite:** Flash Raspberry Pi OS Lite onto your microSD card and configure it for headless 
    operation (enable SSH, configure Wi-Fi if needed).
2.  **Boot the Raspberry Pi:** Insert the microSD card into your Raspberry Pi Zero and power it on.
3.  **Connect via SSH:** Connect to your Raspberry Pi Zero via SSH from your computer.
4.  **Install Required Python Packages:** Run the following command in the terminal:
    ```bash
    sudo apt update
    sudo apt install python3-pip
    pip3 install pygame schedule pytz pyyaml
    ```
5.  **Clone the Repository:**:
    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```
    Alternatively, users can manually copy the Python script (`bugle-call.py`) and the `schedule.yaml` file to a directory on the Raspberry Pi.
6.  **Create `schedule.yaml`:** Create a file named `schedule.yaml` in the same directory as your Python script with the 
      following structure (adjust paths and times as needed):
    ```yaml
    weekdays:
      reveille:
        time: "06:00"
        audio_file: "/path/to/your/file/reveille.mp3"
      retreat:
        time: "18:00"
        audio_file: "/path/to/your/file/retreat.mp3"
      tattoo:
        time: "22:00"
        audio_file: "/path/to/your/file/tattoo.mp3"
      taps:
        time: "23:00"
        audio_file: "/path/to/your/file/taps.mp3"

    weekends:
      reveille:
        time: "07:00"
        audio_file: "/path/to/your/file/reveille.mp3"
      retreat:
        time: "19:00"
        audio_file: "/path/to/your/file/retreat.mp3"
      taps:
        time: "23:30"
        audio_file: "/path/to/your/file/taps.mp3"
    ```
    **Note:** Replace `/path/to/your/file/audio.mp3` with the actual paths to your bugle call MP3 files. You may need to 
    create separate directories (e.g., `weekdays`, `weekends`) to organize your audio files.

## Usage

### Running the Scheduler

To start the bugle call scheduler, navigate to the directory containing the Python script and run:

```bash
python3 bugle-call.py schedule