# Local Integration Checks for HER

This document describes how to verify that Freqtrade, Ollama, and Discord are properly configured for HER without performing trading actions, downloading data, or exposing secrets.

## Overview

HER provides safe integration check scripts that verify external service configuration without:
- Running real trading
- Running backtests
- Downloading market data
- Generating trading strategies
- Sending Discord messages (unless explicitly requested)
- Exposing secrets in output

## Freqtrade Integration Check

### Script
`scripts/test-freqtrade.py`

### What It Does
- Loads `.env` and reads Freqtrade configuration:
  - `FREQTRADE_PATH`
  - `FREQTRADE_USER_DATA_DIR`
  - `FREQTRADE_CONFIG_DIR`
- Checks if Freqtrade executable is configured
- Runs `freqtrade --version` to verify the executable works
- Confirms `freqtrade_workspace/user_data` exists
- Verifies required subdirectories exist:
  - `strategies`
  - `data`
  - `backtest_results`
  - `hyperopt_results`
  - `hyperopts`
  - `plot`
  - `logs`

### What It Does NOT Do
- Does NOT run backtests
- Does NOT download market data
- Does NOT run trading
- Does NOT modify any configurations

### Running the Check
```bash
source .venv/bin/activate
python scripts/test-freqtrade.py
```

### Output
The script prints:
- Configuration status (configured/not configured)
- Executable found status
- User data directory existence
- Version information (if available)
- Missing subdirectories (if any)

### Common Failure Reasons
1. **Freqtrade not installed**: Freqtrade executable not found in PATH or configured path
2. **Path not configured**: `FREQTRADE_PATH` not set in `.env`
3. **User data directory missing**: `freqtrade_workspace/user_data` does not exist
4. **Subdirectories missing**: Required folders not created in user_data

## Ollama Integration Check

### Script
`scripts/test-ollama.py`

### What It Does
- Loads `.env` and reads Ollama configuration:
  - `OLLAMA_BASE_URL`
  - `OLLAMA_MODEL`
- Calls Ollama API to check if service is reachable
- Lists available models (safe read-only operation)
- Checks if configured model is available

### What It Does NOT Do
- Does NOT send any trading prompts
- Does NOT generate trading strategies
- Does NOT perform any inference

### Running the Check
```bash
source .venv/bin/activate
python scripts/test-ollama.py
```

### Output
The script prints:
- Ollama URL
- Service reachability (yes/no)
- Model configuration status (yes/no)
- Configured model availability (yes/no)
- List of installed model names (if safe)

### Common Failure Reasons
1. **Ollama not running**: Service not started with `ollama serve`
2. **Wrong URL**: `OLLAMA_BASE_URL` points to wrong endpoint
3. **Model not installed**: Configured model not pulled with `ollama pull`
4. **Network issues**: Cannot connect to Ollama service

## Discord Integration Check

### Script
`scripts/test-discord-env.py`

### What It Does
- Loads `.env` and reads Discord configuration:
  - `DISCORD_NOTIFICATIONS_ENABLED`
  - `DISCORD_BOT_TOKEN`
  - `DISCORD_CHANNEL_ID`
- Never prints the actual token value
- Prints configured/missing booleans
- If notifications are enabled and credentials exist, verifies bot token with a safe API call
- Only sends a test message if called with `--send-test` flag

### What It Does NOT Do
- Does NOT send messages by default
- Does NOT print secrets
- Does NOT call Discord API if notifications are disabled

### Running the Check
```bash
# Check configuration only (no message sent)
source .venv/bin/activate
python scripts/test-discord-env.py

# Check configuration and send test message
source .venv/bin/activate
python scripts/test-discord-env.py --send-test
```

### Test Message Content
When `--send-test` is used, the message sent is:
```
HER setup test: Discord integration is configured.
```

### Output
The script prints:
- Notifications enabled status
- Token configured status (never the actual token)
- Channel ID configured status
- Token validity (if verified)
- Test message sent status (if `--send-test` used)

### Common Failure Reasons
1. **Notifications disabled**: `DISCORD_NOTIFICATIONS_ENABLED=false` or not set
2. **Token missing**: `DISCORD_BOT_TOKEN` not configured
3. **Channel ID missing**: `DISCORD_CHANNEL_ID` not configured
4. **Invalid token**: Bot token is incorrect or expired
5. **No permissions**: Bot lacks permission to send messages to the channel
6. **Channel not found**: Channel ID is incorrect or bot not in channel

## Development Script

### Script
`scripts/dev.sh`

### What It Does
- Prints HER local development instructions
- Shows how to start backend and frontend
- Lists integration check commands
- Displays relevant URLs

### Running the Script
```bash
./scripts/dev.sh
```

### Starting Services

#### Backend Only
```bash
source .venv/bin/activate
export PYTHONPATH=/home/mohs/Desktop/her/backend
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

Or use the convenience script:
```bash
./scripts/dev-backend.sh
```

#### Frontend Only
```bash
cd frontend
npm run dev
```

Or use the convenience script:
```bash
./scripts/dev-frontend.sh
```

#### Both (Separate Terminals)
Terminal 1 (Backend):
```bash
source .venv/bin/activate
export PYTHONPATH=/home/mohs/Desktop/her/backend
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

Terminal 2 (Frontend):
```bash
cd frontend
npm run dev
```

## System Check

### Script
`scripts/check-system.py`

### What It Does
- Checks Python version
- Checks virtual environment
- Checks required Python packages
- Verifies project structure

### Running the Check
```bash
source .venv/bin/activate
python scripts/check-system.py
```

## Running All Checks

To verify all integrations at once:
```bash
source .venv/bin/activate
python scripts/test-freqtrade.py
python scripts/test-ollama.py
python scripts/test-discord-env.py
python scripts/check-system.py
```

## Security Notes

- **Secrets Protection**: All scripts are designed to never print sensitive information like API keys, tokens, or passwords
- **Read-Only Operations**: Integration checks use safe, read-only API calls
- **No Trading Actions**: No script performs trading, backtesting, or data downloads
- **Opt-in Testing**: Discord test message requires explicit `--send-test` flag

## Troubleshooting

### Freqtrade Issues
- Ensure Freqtrade is installed: `pip install freqtrade`
- Set `FREQTRADE_PATH` in `.env` if not in system PATH
- Create user_data directory structure if missing

### Ollama Issues
- Start Ollama: `ollama serve`
- Pull required model: `ollama pull <model_name>`
- Check `OLLAMA_BASE_URL` in `.env` (default: `http://localhost:11434`)

### Discord Issues
- Enable notifications: `DISCORD_NOTIFICATIONS_ENABLED=true`
- Create bot at https://discord.com/developers/applications
- Get bot token from Discord Developer Portal
- Add bot to your server with message permissions
- Get channel ID from Discord (enable Developer Mode)
- Set `DISCORD_BOT_TOKEN` and `DISCORD_CHANNEL_ID` in `.env`
