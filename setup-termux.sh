#!/data/data/com.termux/files/usr/bin/bash
# Setup script for Termux
pkg update -y && pkg install -y python git
python -m pip install --upgrade pip
pip install -r requirements.txt
printf '\nRun the script with:\n'
printf 'TG_API_ID=YOUR_ID TG_API_HASH=YOUR_HASH TG_CHANNEL=telegram \n'
printf 'python telegram_osint_example.py\n'
