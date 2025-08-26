#!/usr/bin/env bash
# Setup script for Ubuntu (including Ubuntu Userland)
sudo apt update
sudo apt install -y python3 python3-pip git
pip3 install -r requirements.txt
printf '\nRun the script with:\n'
printf 'TG_API_ID=YOUR_ID TG_API_HASH=YOUR_HASH TG_CHANNEL=telegram \\\n'
printf 'python3 telegram_osint_example.py\n'
