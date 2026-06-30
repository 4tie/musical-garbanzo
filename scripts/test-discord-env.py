#!/usr/bin/env python3
"""
Test Discord integration for HER.
Checks Discord configuration and optionally sends a test message.
Does NOT send messages by default.
"""
import sys
from pathlib import Path

try:
    import httpx
except ImportError:
    print("Error: httpx is required. Install with: pip install httpx")
    sys.exit(1)

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.config import settings


def check_discord_config():
    """Check Discord configuration."""
    print(f"DISCORD_NOTIFICATIONS_ENABLED: {settings.DISCORD_NOTIFICATIONS_ENABLED}")
    print(f"DISCORD_CHANNEL_ID: {'***CONFIGURED***' if settings.DISCORD_CHANNEL_ID else 'NOT SET'}")
    print(f"DISCORD_BOT_TOKEN: {'***CONFIGURED***' if settings.DISCORD_BOT_TOKEN else 'NOT SET'}")
    
    has_token = bool(settings.DISCORD_BOT_TOKEN)
    has_channel = bool(settings.DISCORD_CHANNEL_ID)
    
    if not settings.DISCORD_NOTIFICATIONS_ENABLED:
        print("  ℹ Discord notifications are disabled")
        return False, has_token, has_channel
    
    print("  ✓ Discord notifications are enabled")
    
    if not has_token:
        print("  ✗ Discord bot token not configured")
    else:
        print("  ✓ Discord bot token configured")
    
    if not has_channel:
        print("  ✗ Discord channel ID not configured")
    else:
        print("  ✓ Discord channel ID configured")
    
    return settings.DISCORD_NOTIFICATIONS_ENABLED, has_token, has_channel


def verify_discord_token():
    """Verify Discord bot token with a safe API call."""
    try:
        token = settings.DISCORD_BOT_TOKEN.get_secret_value() if settings.DISCORD_BOT_TOKEN else None
        
        if not token:
            print("  ✗ No token to verify")
            return False
        
        # Use Discord API to get current bot user (safe read-only operation)
        response = httpx.get(
            "https://discord.com/api/v10/users/@me",
            headers={"Authorization": f"Bot {token}"},
            timeout=5.0
        )
        
        if response.status_code == 200:
            bot_info = response.json()
            bot_name = bot_info.get("username", "unknown")
            print(f"  ✓ Bot token is valid (bot: {bot_name})")
            return True
        elif response.status_code == 401:
            print("  ✗ Bot token is invalid (401 Unauthorized)")
            return False
        elif response.status_code == 429:
            print("  ⚠ Rate limited by Discord API")
            return None
        else:
            print(f"  ✗ Token verification failed (status {response.status_code})")
            return False
    except httpx.ConnectError:
        print("  ✗ Cannot connect to Discord API")
        return False
    except httpx.TimeoutException:
        print("  ✗ Connection to Discord API timed out")
        return False
    except Exception as e:
        print(f"  ✗ Error verifying token: {e}")
        return False


def send_test_message():
    """Send a test message to Discord."""
    try:
        token = settings.DISCORD_BOT_TOKEN.get_secret_value() if settings.DISCORD_BOT_TOKEN else None
        channel_id = settings.DISCORD_CHANNEL_ID
        
        if not token or not channel_id:
            print("  ✗ Cannot send test message: token or channel ID missing")
            return False
        
        # Send a simple test message
        message_content = "HER setup test: Discord integration is configured."
        
        response = httpx.post(
            f"https://discord.com/api/v10/channels/{channel_id}/messages",
            headers={"Authorization": f"Bot {token}"},
            json={"content": message_content},
            timeout=5.0
        )
        
        if response.status_code == 200:
            print("  ✓ Test message sent successfully")
            return True
        elif response.status_code == 403:
            print("  ✗ Bot does not have permission to send messages to this channel")
            return False
        elif response.status_code == 404:
            print("  ✗ Channel not found or bot not in channel")
            return False
        else:
            print(f"  ✗ Failed to send message (status {response.status_code})")
            return False
    except Exception as e:
        print(f"  ✗ Error sending test message: {e}")
        return False


def main():
    """Run all Discord checks."""
    print("=" * 60)
    print("HER Discord Integration Check")
    print("=" * 60)
    
    # Check for --send-test flag
    send_test = "--send-test" in sys.argv
    
    print("\n[Discord Configuration]")
    enabled, has_token, has_channel = check_discord_config()
    
    print("\n[Token Verification]")
    token_valid = None
    if enabled and has_token:
        token_valid = verify_discord_token()
    else:
        print("  ⚠ Skipping token verification (not enabled or no token)")
    
    print("\n[Test Message]")
    if send_test:
        if enabled and has_token and has_channel:
            message_sent = send_test_message()
        else:
            print("  ⚠ Cannot send test message (not configured)")
            message_sent = False
    else:
        print("  ℹ Test message not sent (use --send-test to send)")
        message_sent = None
    
    print("\n" + "=" * 60)
    print("Summary:")
    print(f"  Notifications Enabled: {enabled}")
    print(f"  Token Configured: {has_token}")
    print(f"  Channel Configured: {has_channel}")
    print(f"  Token Valid: {token_valid}")
    print(f"  Test Message Sent: {message_sent}")
    print("=" * 60)
    
    if not enabled:
        print("\nℹ Discord notifications are disabled")
        print("   Set DISCORD_NOTIFICATIONS_ENABLED=true in .env to enable")
        sys.exit(0)
    elif not has_token or not has_channel:
        print("\n⚠ Discord is enabled but not fully configured")
        print("   Set DISCORD_BOT_TOKEN and DISCORD_CHANNEL_ID in .env")
        sys.exit(1)
    elif token_valid is False:
        print("\n⚠ Discord bot token is invalid")
        sys.exit(1)
    else:
        print("\n✓ Discord integration looks good")
        if send_test and message_sent:
            print("  Test message sent successfully")
        sys.exit(0)


if __name__ == "__main__":
    main()
