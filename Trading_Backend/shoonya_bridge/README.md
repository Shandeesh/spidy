# Shoonya Cloud Bridge - Deployment Pack

This folder contains the standalone "Shoonya Floor" backend for Spidy AI. 
It is designed to run on a Cloud VPS (AWS/DigitalOcean/PythonAnywhere) to ensure 24/7 uptime for your trading bot.

## Prerequisites
- Python 3.9+
- Pip

## Installation (Cloud / Local)

1. **Copy Files**: Move this entire `shoonya_bridge` folder to your server.
2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Install Shoonya API**:
   The official library is required.
   ```bash
   pip install NorenRestApiPy --upgrade
   # OR if pip install fails (sometimes it does for specific versions), clone it:
   # git clone https://github.com/Shoonya-Dev/NorenRestApiPy.git
   ```

## Configuration
Edit `shoonya_server.py` or set Environment Variables for security:
- `SHOONYA_USER`: Your User ID
- `SHOONYA_PWD`: Your Password
- `SHOONYA_FACTOR2`: Your PAN or DOB
- `SHOONYA_API_KEY`: Your App Key

## Running the Bot
```bash
# Run with Auto-Restart (Production)
./run_cloud.sh

# OR Manual Run
python shoonya_server.py
```

## API Endpoints
- Pulse: `GET /status`
- Control: `POST /cloud/control` (Action: STOP/START)
