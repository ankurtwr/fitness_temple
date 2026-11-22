"""
CLI tool to simulate RFID card taps and attendance marking.

Usage:
  # 1. Just tap a card (marks attendance if assigned):
  python simulate_rfid.py --uid CARD123

  # 2. Assign a card to a member and mark attendance in one go:
  python simulate_rfid.py --member 1 --uid CARD123
"""

import argparse
import json
import urllib.parse
import urllib.request
import sys

BASE_URL = "http://localhost:8000"
DEVICE_KEY = "testdevice123"

def post_json(url, payload, headers=None):
    hdrs = {"Content-Type": "application/json", "Accept": "application/json"}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=hdrs)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())

def post_form(url, form_data, headers=None):
    hdrs = {"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"}
    if headers:
        hdrs.update(headers)
    data = urllib.parse.urlencode(form_data).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=hdrs)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())

def scan_card(uid):
    url = f"{BASE_URL}/scan"
    payload = {"uid": uid.upper().strip(), "device_key": DEVICE_KEY}
    status, data = post_json(url, payload)
    return data

def assign_and_scan(member_id, uid):
    # Step 1: Login to get token
    status, login_res = post_form(f"{BASE_URL}/api/login", {"username": "admin", "password": "admin123"})
    if "token" not in login_res:
        print("❌ Login failed:", login_res)
        return
    token = login_res["token"]

    # Step 2: Trigger card assignment
    status, assign_res = post_form(
        f"{BASE_URL}/api/members/{member_id}/assign-card",
        {"csrf_token": ""},
        headers={"Authorization": f"Bearer {token}"}
    )
    if not assign_res.get("success"):
        print("❌ Could not start assignment:", assign_res)
        return
    print(f"📡 Card assignment initiated for Member #{member_id}...")

    # Step 3: Tap card to link
    tap1 = scan_card(uid)
    print(f"🏷️ Tap 1 (Link Card): {tap1.get('status')} - {tap1.get('message') or tap1.get('name')}")

    # Step 4: Tap card to mark attendance
    tap2 = scan_card(uid)
    print(f"✅ Tap 2 (Attendance): {tap2.get('status')} - Member: {tap2.get('name')}, Expiry: {tap2.get('expiry_date')}")

def main():
    parser = argparse.ArgumentParser(description="Simulate RFID Card Tap from Terminal")
    parser.add_argument("--uid", default="DUMMY8888", help="RFID UID string (e.g. A1B2C3D4 or DUMMY123)")
    parser.add_argument("--member", type=int, default=None, help="Member ID to assign this card to first")
    args = parser.parse_args()

    if args.member:
        assign_and_scan(args.member, args.uid)
    else:
        print(f"📡 Simulating RFID Tap for UID '{args.uid}'...")
        res = scan_card(args.uid)
        print("Result:", json.dumps(res, indent=2))

if __name__ == "__main__":
    main()
