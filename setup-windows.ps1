# PowerShell setup script for Windows
# Assumes Python is installed and available in PATH
python -m pip install --upgrade pip
pip install -r requirements.txt
Write-Host "Run the script with:"
Write-Host "set TG_API_ID=YOUR_ID"
Write-Host "set TG_API_HASH=YOUR_HASH"
Write-Host "set TG_CHANNEL=telegram"
Write-Host "python telegram_osint_example.py"
