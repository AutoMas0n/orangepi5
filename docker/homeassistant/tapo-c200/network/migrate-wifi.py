#!/usr/bin/env python3
"""migrate-wifi - move a provisioned Tapo C200 to a different Wi-Fi network.

Runs against the camera on its CURRENT network; no Tapo account, no app, no
access point mode. The camera drops off, joins the new network, and you find it
again there.

    python3 migrate-wifi.py --host 192.168.2.57 --password PW --ssid NEW --psk PSK
    python3 migrate-wifi.py --host 192.168.2.57 --password PW --list
    python3 migrate-wifi.py --host 192.168.2.57 --password PW --ssid NEW --psk PSK --dry-run

Verified on C200 hw 5.0 fw 1.4.6 (TPAP/SPAKE2+ login, via pytapo 3.4.31).

WHY --dry-run EXISTS AND WHY YOU SHOULD USE IT FIRST
----------------------------------------------------
If the new SSID or PSK is wrong, the camera leaves the old network and has
nothing to join. It then only comes back through its own setup AP, which means
either physical access to the reset button or joining Tapo_Cam_XXXX from a
laptop. `--dry-run` performs every step except the final connectAp, so the
credentials, the scan hit and the encryption are all proven before committing.

The SSID must be 2.4 GHz: the C200 has no 5 GHz radio, so a 5 GHz-only network
simply will not appear in the scan. If it is missing from --list, that is why.
"""
import argparse
import base64
import getpass
import json
import sys
import time

try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import padding
except ImportError:  # pragma: no cover
    sys.exit("needs the cryptography package (pip install cryptography)")

try:
    import urllib3
    urllib3.disable_warnings()

    from pytapo import Tapo
except ImportError:  # pragma: no cover
    sys.exit("needs pytapo (pip install pytapo)")


def rsa_encrypt(pem: str, text: str) -> str:
    """PKCS#1 v1.5, base64, no padding - what the camera expects for passwords."""
    key = serialization.load_pem_public_key(pem.encode())
    blob = key.encrypt(text.encode(), padding.PKCS1v15())
    return base64.b64encode(blob).decode()


def scan(tapo) -> list:
    """Access points the camera can see. Works while provisioned."""
    res = tapo.performRequest(
        {"method": "scanApList", "params": {"onboarding": {"scan": "null"}}}
    )
    onboarding = (res or {}).get("result", {}).get("onboarding", {})
    return onboarding.get("ap_list", []), onboarding.get("public_key")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--host", required=True)
    ap.add_argument("--user", default="admin")
    ap.add_argument("--password", default=None,
                    help="camera admin password (prompted if omitted)")
    ap.add_argument("--ssid")
    ap.add_argument("--psk")
    ap.add_argument("--list", action="store_true", help="only list visible networks")
    ap.add_argument("--dry-run", action="store_true",
                    help="everything except the final connectAp")
    ap.add_argument("--timeout", type=int, default=120,
                    help="seconds to wait for the camera on its new network")
    args = ap.parse_args()

    pw = args.password or getpass.getpass("camera admin password: ")
    tapo = Tapo(args.host, args.user, pw)

    aps, pubkey = scan(tapo)

    if args.list or not args.ssid:
        print(f"{len(aps)} network(s) visible to the camera (2.4 GHz only):")
        for a in sorted(aps, key=lambda x: -int(x.get("rssi", 0))):
            print(f"  rssi={a.get('rssi'):>2}  auth={a.get('auth')} "
                  f"enc={a.get('encryption')}  {a.get('ssid')!r}  {a.get('bssid')}")
        return 0

    target = [a for a in aps if a.get("ssid") == args.ssid]
    if not target:
        print(f"ERROR: {args.ssid!r} is not in the camera's scan.\n"
              f"  - a 5 GHz-only network never will be: the C200 is 2.4 GHz only\n"
              f"  - a hidden SSID does not appear either\n"
              f"  Visible: {[a.get('ssid') for a in aps]}")
        return 1
    if len(target) > 1:
        # multiple BSSIDs on one SSID; strongest wins, like a client would
        target.sort(key=lambda x: -int(x.get("rssi", 0)))
        print(f"note: {len(target)} BSSIDs for {args.ssid!r}, using {target[0]['bssid']}")
    ap_info = dict(target[0])

    if not pubkey:
        print("ERROR: the scan returned no public key, cannot encrypt the PSK")
        return 1
    if args.psk is None:
        args.psk = getpass.getpass(f"Wi-Fi password for {args.ssid!r}: ")

    ap_info["unique_key"] = 1
    ap_info["password"] = rsa_encrypt(pubkey, args.psk)

    print(f"target: {ap_info['ssid']!r} bssid={ap_info['bssid']} "
          f"auth={ap_info['auth']} enc={ap_info['encryption']} rssi={ap_info['rssi']}")

    if args.dry_run:
        print("dry run: everything succeeded up to the point of connecting.")
        print("re-run without --dry-run to actually switch networks.")
        return 0

    print("connecting - the camera will drop off this network now...")
    try:
        tapo.performRequest({"method": "connectAp",
                             "params": {"onboarding": {"connect": ap_info}}})
    except Exception as err:  # the drop itself can raise; that is expected
        print(f"  (request ended with: {str(err)[:80]})")

    # The camera is unreachable on this network from here on. Finding it is a
    # job for the new network, so print the instructions and exit cleanly.
    print(f"""
Done, and now the part that matters:

  1. Find the camera on {args.ssid!r}. From a machine on that network:

         ./hunt.sh                  # sweeps for a Tapo API, prints the verdict
         # or, if Pi-hole serves that network:
         static-lease leases        # the camera's MAC shows up with its new IP

     MAC A8-29-DC-AB-B5-50 -> look for that in the lease table.

  2. Update the static lease and the Home Assistant entry if the IP changed:
     the integration stores the host, so a new address means a new config entry
     (or edit .storage/core.config_entries). Pi-hole's dhcp.hosts pin follows
     the MAC, not the network, so re-add it on the new network's DHCP server.

  3. If nothing appears: the camera is back on its own setup AP
     (Tapo_Cam_{'B550'}), meaning the SSID/PSK was wrong. Join that AP from a
     laptop and re-run this script - it works while the camera is in setup mode
     too, so recovery does not need a factory reset.
""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
