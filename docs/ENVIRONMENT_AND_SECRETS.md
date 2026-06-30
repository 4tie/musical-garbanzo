# Environment and Secrets Management

This document explains how to manage environment variables and secrets in HER securely.

## Overview

HER uses environment variables for configuration and secrets management. All sensitive data is stored in environment variables and never committed to Git.

## Environment Variables

### Location

Environment variables are stored in:
- `.env` - Local development (NOT committed to Git)
- `.env.example` - Template with all variables (committed to Git)

### Creating .env File

1. Copy the template:
```bash
cp .env.example .env
```

2. Edit `.env` with your actual values:
```bash
nano .env
# or your preferred editor
```

3. Never commit `.env` to Git (it's in `.gitignore`)

## Environment Variables Reference

### Application Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `APP_NAME` | No | HER | Application name |
| `APP_ENV` | No | local | Environment (local/production) |
| `APP_HOST` | No | 127.0.0.1 | Backend host |
| `BACKEND_PORT` | No | 8000 | Backend port |
| `FRONTEND_PORT` | No | 3000 | Frontend port |

### Database

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | No | sqlite:///./data/her.db | Database connection string |

### Freqtrade Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FREQTRADE_PATH` | No | (empty) | Path to Freqtrade executable |
| `FREQTRADE_USER_DATA_DIR` | No | ./freqtrade_workspace/user_data | Freqtrade user data directory |
| `FREQTRADE_CONFIG_DIR` | No | ./freqtrade_workspace/config | Freqtrade config directory |
| `FREQTRADE_DEFAULT_CONFIG` | No | ./freqtrade_workspace/config/config.generated.json | Default config file |

### Ollama Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OLLAMA_BASE_URL` | No | http://localhost:11434 | Ollama API URL |
| `OLLAMA_MODEL` | No | (empty) | Ollama model to use |

### Discord Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DISCORD_NOTIFICATIONS_ENABLED` | No | false | Enable Discord notifications |
| `DISCORD_BOT_TOKEN` | No | (empty) | Discord bot token (SECRET) |
| `DISCORD_CHANNEL_ID` | No | (empty) | Discord channel ID for notifications |

### Security

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `APP_SECRET_KEY` | No | change-me | Application secret key (SECRET) |

## Secrets Management

### What Are Secrets?

Secrets are sensitive information that should never be exposed:
- API keys
- Bot tokens
- Database passwords
- Encryption keys
- Private certificates

### How HER Protects Secrets

1. **Pydantic SecretStr**
   - Backend uses Pydantic's `SecretStr` type for sensitive values
   - Secrets are never logged or printed in debug output
   - API responses exclude secret fields

2. **Git Protection**
   - `.env` is in `.gitignore`
   - `.env.example` contains only placeholder values
   - Runtime data directories are ignored

3. **API Safety**
   - Public settings endpoint excludes all secrets
   - System status endpoint never includes tokens or keys
   - Logs never contain secret values

### Checking Environment Status

Use the provided script to check your environment configuration:
```bash
source .venv/bin/activate
python scripts/print-env-status.py
```

This script:
- Shows which variables are configured
- Never prints actual secret values
- Uses safe placeholders like `***CONFIGURED***` or `NOT SET`

## Security Best Practices

### For Development

1. **Never commit .env**
   - Always keep `.env` in `.gitignore`
   - Use `.env.example` as template
   - Review `.gitignore` before committing

2. **Use strong secrets**
   - Generate random strings for tokens and keys
   - Use different secrets for different environments
   - Rotate secrets periodically

3. **Limit access**
   - Only share `.env` with trusted team members
   - Use secure channels for sharing secrets
   - Never paste secrets in chat or email

### For Production

1. **Use environment-specific .env**
   - Create separate `.env.production` file
   - Never use development secrets in production
   - Use proper secret management services if available

2. **Secure the secret key**
   - Generate a strong random `APP_SECRET_KEY`
   - Store it securely (environment variable or secret manager)
   - Never use the default "change-me" value

3. **Monitor for leaks**
   - Regularly audit Git history for accidental commits
   - Rotate secrets if exposure is suspected
   - Use tools like git-secrets or pre-commit hooks

## Discord Bot Setup

### Creating a Discord Bot

1. Go to https://discord.com/developers/applications
2. Create a new application
3. Go to the "Bot" section and create a bot
4. Copy the bot token
5. Enable required intents (Message Content, Server Members)
6. Invite bot to your server with required permissions

### Configuring in HER

1. Set in `.env`:
```bash
DISCORD_NOTIFICATIONS_ENABLED=true
DISCORD_BOT_TOKEN=your_bot_token_here
DISCORD_CHANNEL_ID=your_channel_id_here
```

2. Test configuration:
```bash
python scripts/test-discord-env.py
python scripts/test-discord-env.py --send-test
```

### Getting Channel ID

1. Enable Developer Mode in Discord (Settings > Advanced)
2. Right-click the channel
3. Select "Copy ID"

## Freqtrade Setup

### Installing Freqtrade

```bash
pip install freqtrade
```

### Configuring in HER

1. Set in `.env`:
```bash
FREQTRADE_PATH=/usr/local/bin/freqtrade
# or just "freqtrade" if in PATH
```

2. Test configuration:
```bash
python scripts/test-freqtrade.py
```

## Ollama Setup

### Installing Ollama

Visit https://ollama.ai and follow installation instructions for your OS.

### Pulling a Model

```bash
ollama pull llama3
# or any other model
```

### Configuring in HER

1. Set in `.env`:
```bash
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3
```

2. Start Ollama:
```bash
ollama serve
```

3. Test configuration:
```bash
python scripts/test-ollama.py
```

## Troubleshooting

### .env File Not Loading

1. Verify `.env` exists in project root
2. Check file permissions
3. Ensure no syntax errors (no quotes around values)
4. Restart backend after changes

### Secrets Appearing in Logs

1. Check that Pydantic SecretStr is used for sensitive fields
2. Review logging configuration
3. Ensure no explicit logging of secret values

### Git Trying to Commit .env

1. Verify `.gitignore` contains `.env`
2. Run `git rm --cached .env` if accidentally staged
3. Run `git status` to verify it's no longer tracked

## Integration Check Scripts

HER provides safe scripts to verify integrations without exposing secrets:

- `scripts/test-freqtrade.py` - Check Freqtrade configuration
- `scripts/test-ollama.py` - Check Ollama service
- `scripts/test-discord-env.py` - Check Discord configuration
- `scripts/print-env-status.py` - Display environment status safely

All scripts:
- Never print actual secret values
- Use safe placeholders
- Perform read-only checks only
- Don't send messages unless explicitly requested

## Additional Resources

- [Pydantic SecretStr Documentation](https://docs.pydantic.dev/latest/concepts/pydantic_settings/#secret-types)
- [Python-dotenv Documentation](https://saurabh-kumar.com/python-dotenv/)
- [Discord Developer Portal](https://discord.com/developers/applications)
- [Freqtrade Documentation](https://www.freqtrade.io/)
- [Ollama Documentation](https://ollama.ai/)
