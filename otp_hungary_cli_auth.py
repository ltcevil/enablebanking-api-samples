#!/usr/bin/env python3
"""
Interactive CLI script for authenticating with OTP Bank Hungary using Enable Banking API.

This script guides you through the authentication process with interactive prompts
and detailed instructions on how to obtain the required credentials.
"""

import json
import os
import sys
import uuid
from datetime import datetime, timezone, timedelta
from pprint import pprint
from urllib.parse import urlparse, parse_qs

import requests
import jwt as pyjwt


API_ORIGIN = "https://api.enablebanking.com"
ASPSP_NAME = "OTP Bank"
ASPSP_COUNTRY = "HU"


def print_banner():
    """Print a welcome banner."""
    print("\n" + "=" * 70)
    print(" OTP Bank Hungary - Enable Banking Authentication CLI")
    print("=" * 70 + "\n")


def print_section(title):
    """Print a section header."""
    print(f"\n{'─' * 70}")
    print(f"  {title}")
    print(f"{'─' * 70}\n")


def get_config():
    """
    Get configuration from user input or config file.

    Returns:
        dict: Configuration containing keyPath, applicationId, and redirectUrl
    """
    print_section("Step 1: Configuration Setup")

    print("Do you have a config.json file already set up? (y/n)")
    print("If you're unsure, type 'n' for guided setup.\n")

    has_config = input("Your choice: ").strip().lower()

    if has_config == 'y':
        try:
            config_path = input("\nEnter path to config.json (or press Enter for '../config.json'): ").strip()
            if not config_path:
                config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

            with open(config_path, "r") as f:
                config = json.load(f)

            print("\n✓ Configuration loaded successfully!")
            print(f"  Application ID: {config.get('applicationId', 'N/A')}")
            print(f"  Key Path: {config.get('keyPath', 'N/A')}")
            print(f"  Redirect URL: {config.get('redirectUrl', 'N/A')}")

            return config
        except FileNotFoundError:
            print("\n✗ Config file not found. Starting guided setup...")
        except json.JSONDecodeError:
            print("\n✗ Invalid JSON in config file. Starting guided setup...")

    print("\n" + "=" * 70)
    print("GUIDED SETUP - How to get your Enable Banking credentials")
    print("=" * 70)

    print("\n1. CREATE DEVELOPER ACCOUNT:")
    print("   → Visit: https://enablebanking.com/")
    print("   → Click 'Get started' to create a developer account")
    print("   → Complete the registration process\n")

    print("2. REGISTER YOUR APPLICATION:")
    print("   → Visit: https://enablebanking.com/cp/applications")
    print("   → Click 'New Application' or similar button")
    print("   → Fill in application details:")
    print("     • Name: Choose any name (e.g., 'OTP Hungary CLI')")
    print("     • Redirect URL: http://localhost:8080/auth_redirect")
    print("   → Generate a private key (choose browser generation)")
    print("   → Download the .pem file (it will be named with your app ID)")
    print("     Example: aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee.pem\n")

    print("3. SAVE THE CREDENTIALS:")
    print("   → Place the .pem file in the same directory as this script")
    print("   → Note down your Application ID (the UUID from the filename)\n")

    input("Press Enter once you have completed these steps...")

    print("\n" + "-" * 70)

    # Get application ID
    print("\nEnter your Application ID:")
    print("(This is the UUID from your .pem filename)")
    print("Example: 0377783c-3414-4bb1-a7d4-0c3eb54cd4b0")
    application_id = input("\nApplication ID: ").strip()

    # Get key path
    print("\nEnter the path to your .pem private key file:")
    print("(You can use relative path like './your-app-id.pem')")
    default_key_path = f"{application_id}.pem"
    print(f"Press Enter to use: {default_key_path}")
    key_path = input("\nKey path: ").strip()
    if not key_path:
        key_path = default_key_path

    # Get redirect URL
    print("\nEnter your redirect URL:")
    print("(This should match what you configured in the Enable Banking portal)")
    print("Press Enter to use: http://localhost:8080/auth_redirect")
    redirect_url = input("\nRedirect URL: ").strip()
    if not redirect_url:
        redirect_url = "http://localhost:8080/auth_redirect"

    config = {
        "applicationId": application_id,
        "keyPath": key_path,
        "redirectUrl": redirect_url
    }

    # Ask if they want to save
    print("\nDo you want to save this configuration to config.json? (y/n)")
    save_config = input("Your choice: ").strip().lower()

    if save_config == 'y':
        config_path = input("\nEnter path to save config.json (or press Enter for './config.json'): ").strip()
        if not config_path:
            config_path = "config.json"

        with open(config_path, "w") as f:
            json.dump(config, f, indent=4)
        print(f"\n✓ Configuration saved to {config_path}")

    return config


def create_jwt(config):
    """
    Create a JWT token for API authentication.

    Args:
        config (dict): Configuration containing keyPath and applicationId

    Returns:
        str: JWT token
    """
    print_section("Step 2: Creating Authentication Token")

    key_path = config["keyPath"]

    # Try to read the private key
    try:
        if not os.path.isabs(key_path):
            # Try relative to script directory
            key_path_abs = os.path.join(os.path.dirname(os.path.abspath(__file__)), key_path)
            if not os.path.exists(key_path_abs):
                # Try relative to current directory
                key_path_abs = os.path.abspath(key_path)
        else:
            key_path_abs = key_path

        with open(key_path_abs, "rb") as f:
            private_key = f.read()

        print(f"✓ Private key loaded from: {key_path_abs}")
    except FileNotFoundError:
        print(f"\n✗ ERROR: Private key file not found at: {key_path}")
        print("\nPlease ensure:")
        print("  1. You have downloaded the .pem file from Enable Banking portal")
        print("  2. The file is in the correct location")
        print("  3. The path in your config is correct")
        sys.exit(1)

    iat = int(datetime.now().timestamp())
    jwt_body = {
        "iss": "enablebanking.com",
        "aud": "api.enablebanking.com",
        "iat": iat,
        "exp": iat + 3600,
    }

    jwt_token = pyjwt.encode(
        jwt_body,
        private_key,
        algorithm="RS256",
        headers={"kid": config["applicationId"]},
    )

    print("✓ JWT token created successfully")

    return jwt_token


def verify_application(jwt_token):
    """
    Verify the application credentials by fetching application details.

    Args:
        jwt_token (str): JWT authentication token

    Returns:
        dict: Application details or None if failed
    """
    print_section("Step 3: Verifying Application Credentials")

    headers = {"Authorization": f"Bearer {jwt_token}"}

    try:
        r = requests.get(f"{API_ORIGIN}/application", headers=headers)

        if r.status_code == 200:
            app = r.json()
            print("✓ Application verified successfully!")
            print(f"\n  Application Name: {app.get('name', 'N/A')}")
            print(f"  Application ID: {app.get('application_id', 'N/A')}")
            print(f"  Redirect URLs: {', '.join(app.get('redirect_urls', []))}")
            return app
        else:
            print(f"\n✗ ERROR: Failed to verify application (HTTP {r.status_code})")
            print(f"Response: {r.text}")
            print("\nPlease check:")
            print("  1. Your Application ID is correct")
            print("  2. Your private key matches the application")
            print("  3. Your application is active in the Enable Banking portal")
            return None
    except requests.RequestException as e:
        print(f"\n✗ ERROR: Network error occurred: {e}")
        return None


def start_authorization(jwt_token, app, config):
    """
    Start the authorization flow with OTP Bank Hungary.

    Args:
        jwt_token (str): JWT authentication token
        app (dict): Application details
        config (dict): Configuration

    Returns:
        str: Authorization URL or None if failed
    """
    print_section("Step 4: Starting Authorization with OTP Bank Hungary")

    headers = {"Authorization": f"Bearer {jwt_token}"}

    # Use redirect URL from config or fall back to app's first redirect URL
    redirect_url = config.get("redirectUrl", app["redirect_urls"][0])

    body = {
        "access": {
            "valid_until": (datetime.now(timezone.utc) + timedelta(days=90)).isoformat()
        },
        "aspsp": {"name": ASPSP_NAME, "country": ASPSP_COUNTRY},
        "state": str(uuid.uuid4()),
        "redirect_url": redirect_url,
        "psu_type": "personal",
    }

    print(f"Requesting authorization for:")
    print(f"  Bank: {ASPSP_NAME}")
    print(f"  Country: {ASPSP_COUNTRY}")
    print(f"  Account Type: Personal")
    print(f"  Access Valid Until: {body['access']['valid_until']}")

    try:
        r = requests.post(f"{API_ORIGIN}/auth", json=body, headers=headers)

        if r.status_code == 200:
            auth_url = r.json()["url"]
            print("\n✓ Authorization request created successfully!")
            return auth_url
        else:
            print(f"\n✗ ERROR: Failed to create authorization (HTTP {r.status_code})")
            print(f"Response: {r.text}")
            return None
    except requests.RequestException as e:
        print(f"\n✗ ERROR: Network error occurred: {e}")
        return None


def complete_authentication(auth_url, jwt_token):
    """
    Complete the authentication by handling the redirect and creating a session.

    Args:
        auth_url (str): Authorization URL for the user to visit
        jwt_token (str): JWT authentication token

    Returns:
        dict: Session details or None if failed
    """
    print_section("Step 5: Complete Authentication")

    print("\n" + "=" * 70)
    print("IMPORTANT: Follow these steps to authenticate")
    print("=" * 70)

    print("\n1. Open this URL in your web browser:")
    print(f"\n   {auth_url}\n")

    print("2. You will be redirected to OTP Bank Hungary's login page")
    print("   → Enter your online banking credentials")
    print("   → You may need to provide an OTP (One-Time Password)")
    print("   → The OTP is typically sent via SMS or generated by your token device")
    print("   → Follow the bank's authentication steps\n")

    print("3. After successful authentication, you will be redirected to:")
    print(f"   {jwt_token.split('.')[0]}...  (your redirect URL)")
    print("   → The page may show an error (this is normal if you don't have a server)")
    print("   → The important part is the URL in your browser's address bar\n")

    print("4. Copy the ENTIRE URL from your browser's address bar")
    print("   → It should look like: http://localhost:8080/auth_redirect?code=...")
    print("   → Make sure to copy the complete URL including all parameters\n")

    print("=" * 70 + "\n")

    # Wait for user to complete authentication
    redirected_url = input("Paste the complete redirect URL here: ").strip()

    # Extract the authorization code
    try:
        parsed_url = urlparse(redirected_url)
        query_params = parse_qs(parsed_url.query)

        if "code" not in query_params:
            print("\n✗ ERROR: No 'code' parameter found in the URL")
            print("Please make sure you copied the complete URL including ?code=...")
            return None

        auth_code = query_params["code"][0]
        print(f"\n✓ Authorization code extracted: {auth_code[:20]}...")

    except Exception as e:
        print(f"\n✗ ERROR: Failed to parse URL: {e}")
        return None

    # Create user session
    print("\nCreating user session...")

    headers = {"Authorization": f"Bearer {jwt_token}"}

    try:
        r = requests.post(
            f"{API_ORIGIN}/sessions",
            json={"code": auth_code},
            headers=headers
        )

        if r.status_code == 200:
            session = r.json()
            print("\n✓ Session created successfully!")
            print(f"\n  Session ID: {session.get('session_id', 'N/A')}")
            print(f"  Number of Accounts: {len(session.get('accounts', []))}")
            return session
        else:
            print(f"\n✗ ERROR: Failed to create session (HTTP {r.status_code})")
            print(f"Response: {r.text}")
            return None
    except requests.RequestException as e:
        print(f"\n✗ ERROR: Network error occurred: {e}")
        return None


def display_account_info(session, jwt_token):
    """
    Display account information including balances and recent transactions.

    Args:
        session (dict): Session details
        jwt_token (str): JWT authentication token
    """
    print_section("Step 6: Retrieving Account Information")

    if not session.get("accounts"):
        print("✗ No accounts found in session")
        return

    headers = {"Authorization": f"Bearer {jwt_token}"}

    # Display all accounts
    print(f"Found {len(session['accounts'])} account(s):\n")
    for idx, account in enumerate(session["accounts"], 1):
        print(f"{idx}. Account UID: {account['uid']}")
        print(f"   Currency: {account.get('currency', 'N/A')}")
        if 'iban' in account:
            print(f"   IBAN: {account['iban']}")
        print()

    # Use the first account for detailed information
    account_uid = session["accounts"][0]["uid"]
    print(f"Fetching details for account: {account_uid}\n")

    # Retrieve balances
    print("─" * 70)
    print("ACCOUNT BALANCES")
    print("─" * 70 + "\n")

    try:
        r = requests.get(
            f"{API_ORIGIN}/accounts/{account_uid}/balances",
            headers=headers
        )

        if r.status_code == 200:
            balances = r.json()
            pprint(balances)
        else:
            print(f"✗ Failed to retrieve balances (HTTP {r.status_code}): {r.text}")
    except requests.RequestException as e:
        print(f"✗ Error retrieving balances: {e}")

    # Retrieve recent transactions
    print("\n" + "─" * 70)
    print("RECENT TRANSACTIONS (last 30 days)")
    print("─" * 70 + "\n")

    try:
        query = {
            "date_from": (datetime.now(timezone.utc) - timedelta(days=30)).date().isoformat(),
        }

        r = requests.get(
            f"{API_ORIGIN}/accounts/{account_uid}/transactions",
            params=query,
            headers=headers,
        )

        if r.status_code == 200:
            transactions_data = r.json()
            transactions = transactions_data.get("transactions", [])

            if transactions:
                print(f"Found {len(transactions)} transaction(s):\n")
                pprint(transactions)

                if transactions_data.get("continuation_key"):
                    print(f"\n(More transactions available with continuation key)")
            else:
                print("No transactions found in the last 30 days")
        else:
            print(f"✗ Failed to retrieve transactions (HTTP {r.status_code}): {r.text}")
    except requests.RequestException as e:
        print(f"✗ Error retrieving transactions: {e}")


def main():
    """Main function to run the interactive authentication flow."""
    print_banner()

    # Step 1: Get configuration
    config = get_config()

    # Step 2: Create JWT token
    jwt_token = create_jwt(config)

    # Step 3: Verify application
    app = verify_application(jwt_token)
    if not app:
        print("\n✗ Authentication failed. Please check your credentials and try again.")
        sys.exit(1)

    # Step 4: Start authorization
    auth_url = start_authorization(jwt_token, app, config)
    if not auth_url:
        print("\n✗ Failed to start authorization. Please try again.")
        sys.exit(1)

    # Step 5: Complete authentication
    session = complete_authentication(auth_url, jwt_token)
    if not session:
        print("\n✗ Failed to complete authentication. Please try again.")
        sys.exit(1)

    # Step 6: Display account information
    display_account_info(session, jwt_token)

    # Success message
    print("\n" + "=" * 70)
    print("✓ AUTHENTICATION COMPLETED SUCCESSFULLY!")
    print("=" * 70)
    print(f"\nYour session ID: {session.get('session_id', 'N/A')}")
    print("You can use this session ID to make further API calls.")
    print("\nThank you for using OTP Bank Hungary Authentication CLI!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n✗ Process interrupted by user. Exiting...")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n✗ An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
