#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZORO  Complete Network Bypass & TOKEN Manager
Telegram: @ZORO55222

Replaces offline key system with HMAC-signed token system.
Tokens include username and expiry timestamp.
"""

import sys
import os
import time
import socket
import json
import base64
import hmac
import hashlib
import subprocess
import argparse
import logging
from typing import Dict, Tuple, Optional

# ============================================================
#       
#   
#            
#            
#     
#        
# ============================================================

LOGO = r"""
      
  
           
           
    
       
"""

CONTACT = "Telegram: @ZORO55222"
VERSION = "2.1.0-TOKEN"

# ============================================================
# CONFIGURATION
# ============================================================
DEFAULT_INTERFACE = "wlan0"
DEFAULT_INTERVAL = 30
TOKEN_FILE = "token.dat"
TOKEN_SECRET = b"zoro_bypass_hmac_salt_2025"  # CHANGE THIS IF DEPLOYING

# ============================================================
# LOGGING
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("ZORO")

# ============================================================
# 1. TOKEN SYSTEM (HMAC-Signed + Expiry)
# ============================================================
class TokenManager:
    """Manages tokens instead of license keys."""

    @staticmethod
    def _load_token() -> Optional[Dict]:
        """Load saved token data."""
        try:
            with open(TOKEN_FILE, 'r') as f:
                return json.load(f)
        except:
            return None

    @staticmethod
    def _save_token(data: Dict) -> bool:
        """Save token data."""
        try:
            with open(TOKEN_FILE, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info("Token saved successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to save token: {e}")
            return False

    @staticmethod
    def generate_token(username: str, expiry_days: int = 30) -> str:
        """
        Generate a new signed token.
        Format: base64(payload):hmac_hex
        """
        payload = {
            "username": username,
            "exp": int(time.time()) + (expiry_days * 86400),
            "type": "zoro_access"
        }
        payload_b64 = base64.b64encode(json.dumps(payload).encode()).decode()
        sig = hmac.new(TOKEN_SECRET, payload_b64.encode(), hashlib.sha256).hexdigest()
        token = f"{payload_b64}:{sig}"
        logger.info(f"Token generated for {username} (valid {expiry_days} days)")
        return token

    @staticmethod
    def verify_token(token_str: str) -> Tuple[bool, Dict]:
        """
        Verify token.
        Checks signature AND expiration.
        """
        try:
            if ':' not in token_str:
                return False, {}

            payload_b64, sig_hex = token_str.split(':', 1)
            expected_sig = hmac.new(TOKEN_SECRET, payload_b64.encode(), hashlib.sha256).hexdigest()

            if not hmac.compare_digest(expected_sig, sig_hex):
                logger.error("Token signature invalid.")
                return False, {}

            payload = json.loads(base64.b64decode(payload_b64).decode())
            if payload.get('exp', 0) < time.time():
                logger.error("Token expired.")
                return False, {}

            return True, payload

        except Exception as e:
            logger.error(f"Token verification error: {e}")
            return False, {}

    @staticmethod
    def prompt_for_token() -> bool:
        """Interactive token entry."""
        print("\n[!] TOKEN REQUIRED")
        print("    Enter your access token (get from @ZORO55222)")
        token = input("Token: ").strip()
        if not token:
            return False

        valid, payload = TokenManager.verify_token(token)
        if valid:
            data = {
                "token": token,
                "username": payload.get("username"),
                "exp": payload.get("exp"),
                "activated_at": time.time()
            }
            TokenManager._save_token(data)
            print(f"[+] Token activated for user: {payload.get('username')}")
            return True
        else:
            print("[-] Invalid or expired token.")
            return False

    @staticmethod
    def check_token() -> bool:
        """Check saved token validity."""
        data = TokenManager._load_token()
        if not data:
            return False

        token = data.get("token")
        if not token:
            return False

        valid, payload = TokenManager.verify_token(token)
        if valid:
            logger.info(f"Token valid. User: {payload.get('username')}")
            return True
        else:
            logger.warning("Token invalid/expired. Please re-enter.")
            return False

# ============================================================
# 2. NETWORK UTILITIES
# ============================================================
def get_gateway() -> str:
    try:
        out = subprocess.check_output(["ip", "route", "show", "default"], text=True, stderr=subprocess.DEVNULL)
        return out.split()[2]
    except:
        try:
            out = subprocess.check_output(["route", "-n"], text=True, stderr=subprocess.DEVNULL)
            for line in out.splitlines():
                if "UG" in line and "0.0.0.0" in line:
                    return line.split()[1]
        except:
            pass
    return "192.168.1.1"

def ping_host(host: str, timeout: int = 1) -> bool:
    try:
        subprocess.check_call(["ping", "-c", "1", "-W", str(timeout), host],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except:
        return False

def check_internet(host: str = "8.8.8.8", port: int = 53, timeout: int = 2) -> bool:
    try:
        socket.create_connection((host, port), timeout=timeout)
        return True
    except:
        return False

def classify_connectivity() -> Tuple[str, str]:
    gw = get_gateway()
    if ping_host(gw):
        if check_internet():
            return ('online', 'Internet is working.')
        else:
            return ('auth_drop', 'Gateway up, but internet blocked (portal).')
    else:
        return ('link_down', 'Gateway unreachable. Check WiFi.')

# ============================================================
# 3. BYPASS LOGIC
# ============================================================
def get_portal_url_silent() -> Optional[str]:
    gw = get_gateway()
    try:
        cmd = ["curl", "-s", "-L", "-o", "/dev/null", "-w", "%{url_effective}", f"http://{gw}/"]
        out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, timeout=3).decode().strip()
        if out and "portal" in out.lower():
            return out
    except:
        pass
    return f"http://{gw}/portal"

def trigger_bypass(interface: str, new_mac: str = None):
    logger.info("Starting bypass sequence...")
    if new_mac is None:
        new_mac = "00:11:22:33:44:55"

    # MAC Change
    try:
        subprocess.run(["ifconfig", interface, "down"], check=False, stderr=subprocess.DEVNULL)
        subprocess.run(["ifconfig", interface, "hw", "ether", new_mac], check=False, stderr=subprocess.DEVNULL)
        subprocess.run(["ifconfig", interface, "up"], check=False, stderr=subprocess.DEVNULL)
        logger.info(f"MAC changed to {new_mac}")
    except Exception as e:
        logger.error(f"MAC change failed: {e}. Need root.")
        return

    # DHCP
    try:
        subprocess.run(["dhclient", "-r", interface], stderr=subprocess.DEVNULL)
        subprocess.run(["dhclient", interface], stderr=subprocess.DEVNULL)
        logger.info("DHCP renewed.")
    except:
        logger.warning("DHCP renew failed.")

    # Portal hit
    portal_url = get_portal_url_silent()
    logger.info(f"Triggering portal: {portal_url}")
    try:
        subprocess.check_call(["curl", "-s", portal_url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        logger.info("Portal triggered.")
    except:
        logger.warning("Could not reach portal URL.")

# ============================================================
# 4. MONITOR LOOP
# ============================================================
def monitor_loop(interface: str, interval: int, auto_bypass: bool):
    logger.info(f"Monitoring {interface} (interval: {interval}s)")
    state_history = ""
    while True:
        try:
            state, label = classify_connectivity()
            if state != state_history:
                logger.info(f"State: {state} -> {label}")
                state_history = state

            if state == "online":
                time.sleep(interval)
            elif state == "auth_drop":
                if auto_bypass:
                    logger.warning("Auth drop. Bypassing...")
                    trigger_bypass(interface)
                    time.sleep(5)
                else:
                    time.sleep(interval)
            else:  # link_down
                time.sleep(10)
        except KeyboardInterrupt:
            logger.info("Stopped.")
            break
        except Exception as e:
            logger.error(f"Monitor error: {e}")
            time.sleep(10)

# ============================================================
# 5. CLI
# ============================================================
def parse_args():
    parser = argparse.ArgumentParser(description="ZORO Token-Based Network Tool")
    parser.add_argument("-i", "--interface", default=DEFAULT_INTERFACE, help="Network interface")
    parser.add_argument("-t", "--interval", type=int, default=DEFAULT_INTERVAL, help="Check interval")
    parser.add_argument("--token", action="store_true", help="Enter token and exit")
    parser.add_argument("--generate-token", help="Generate token for username (admin only)")
    parser.add_argument("--expiry", type=int, default=30, help="Token expiry in days (default: 30)")
    parser.add_argument("--bypass", action="store_true", help="Auto-bypass")
    parser.add_argument("--one-shot", action="store_true", help="Run bypass once")
    parser.add_argument("--debug", action="store_true", help="Debug mode")
    return parser.parse_args()

def main():
    args = parse_args()

    if args.debug:
        logger.setLevel(logging.DEBUG)

    print(LOGO)
    print(f" {CONTACT}  |  v{VERSION}\n")
    print("=" * 60)
    print(" ZORO Complete Token-Based Bypass Suite")
    print("=" * 60 + "\n")

    if os.geteuid() != 0:
        logger.warning("Not root. MAC/DHCP will fail.")

    # Admin: Generate Token
    if args.generate_token:
        token = TokenManager.generate_token(args.generate_token, args.expiry)
        print("\n[+] Generated Token:")
        print(f"\n{token}\n")
        print(f"Valid for {args.expiry} days for user: {args.generate_token}")
        sys.exit(0)

    # User: Set Token
    if args.token:
        if TokenManager.prompt_for_token():
            sys.exit(0)
        else:
            sys.exit(1)

    # Check Token
    if not TokenManager.check_token():
        logger.warning("No valid token found.")
        print("[!] You need a valid token.")
        print("[!] Run with --token to enter one.")
        sys.exit(1)

    # One-shot
    if args.one_shot:
        logger.info("One-shot bypass...")
        trigger_bypass(args.interface)
        state, label = classify_connectivity()
        print(f"Result: {state} - {label}")
        return

    # Monitor
    monitor_loop(args.interface, args.interval, args.bypass)

if __name__ == "__main__":
    main()