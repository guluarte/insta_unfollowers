# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "click",
#     "instaloader",
# ]
# ///

import sys
from pathlib import Path
from typing import Optional

import click
import instaloader


def get_session_path(username: str) -> Path:
    """Get path to session file for the given username"""
    return Path(f"./sessions/session-{username}")


def login(username: str) -> instaloader.Instaloader:
    """Log in to Instagram account with session persistence"""
    L = instaloader.Instaloader(max_connection_attempts=1)
    session_path = get_session_path(username)

    # Try to load a saved session
    if session_path.exists():
        try:
            L.load_session_from_file(username, str(session_path))
            click.echo(f"✅ Session loaded for @{username}")
            return L
        except Exception as e:
            click.echo(
                f"⚠️ Session load failed: {e}. A new login is required.", err=True
            )
            session_path.unlink()  # Delete corrupted session file

    # Manual login to handle 2FA
    password = click.prompt(f"🔑 Enter password for @{username}", hide_input=True)
    try:
        L.login(username, password)
    except instaloader.exceptions.TwoFactorAuthRequiredException:
        click.echo("📱 2FA required. Enter code from your authenticator app.")
        two_factor_code = click.prompt("Enter 2FA code")
        try:
            L.two_factor_login(two_factor_code)
        except instaloader.exceptions.BadCredentialsException:
            click.echo("❌ Invalid 2FA code.", err=True)
            sys.exit(1)
        except Exception as e:
            click.echo(f"❌ 2FA login failed: {e}", err=True)
            sys.exit(1)
    except instaloader.exceptions.BadCredentialsException:
        click.echo("❌ Incorrect password.", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Login failed: {e}", err=True)
        sys.exit(1)

    # Save session for future use
    try:
        L.save_session_to_file(str(session_path))
        click.echo(f"🔑 Session saved to {session_path}")
    except Exception as e:
        click.echo(f"⚠️  Could not save session: {e}", err=True)

    return L


@click.command()
@click.argument("username", required=False)
def main(username: Optional[str] = None):
    """
    Find accounts that don't follow you back on Instagram

    USERNAME: Your Instagram username (optional if saved session exists)
    """
    if not username:
        username = click.prompt("📝 Enter your Instagram username")
    # Ensure username is non-empty
    while not username or username.strip() == "":
        click.echo("❌ Username cannot be empty")
        username = click.prompt("📝 Enter your Instagram username")

    # Add type assertion for Pyright
    assert isinstance(username, str) and username != ""

    try:
        # Initialize and login
        loader = login(username)

        # Get profile data
        profile = instaloader.Profile.from_username(loader.context, username)

        click.echo("⏳ Loading followers...")
        followers = {f.username for f in profile.get_followers()}

        click.echo("⏳ Loading following...")
        following = {f.username for f in profile.get_followees()}

        # Calculate non-followers
        non_followers = following - followers

        # Display results
        click.echo(f"\n🔍 Results for @{username}:")
        click.echo(f"• Followers: {len(followers)}")
        click.echo(f"• Following: {len(following)}")
        click.echo(f"• Not following back: {len(non_followers)}\n")

        if non_followers:
            click.echo("🚫 Accounts not following you back:")
            for i, account in enumerate(sorted(non_followers), 1):
                click.echo(f"{i}. {account}")
        else:
            click.echo("🎉 Everyone you follow follows you back!")

    except instaloader.exceptions.ProfileNotExistsException:
        click.echo(f"❌ Error: Profile '@{username}' doesn't exist", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
