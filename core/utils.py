# -*- coding: utf-8 -*-
import ipaddress
import requests
import logging
from functools import lru_cache

logger = logging.getLogger("NetWatch")

@lru_cache(maxsize=1024)
def get_ip_info(ip_str):
    """Fetch Country Code and ISP for a given IP address."""
    try:
        # Using ip-api.com (free for non-commercial)
        # We request 'countryCode' for flag representation and 'isp'
        # ip-api.com free tier only supports HTTP (HTTPS requires Pro plan)
        response = requests.get(f"http://ip-api.com/json/{ip_str}?fields=status,countryCode,isp", timeout=3)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                country_code = data.get("countryCode", "")
                isp = data.get("isp", "Unknown ISP")
                
                flag = ""
                if country_code and len(country_code) == 2:
                    # Regional Indicator Symbol Letters: U+1F1E6 (A) through U+1F1FF (Z)
                    flag = "".join(chr(0x1F1E6 + ord(c) - ord('A')) for c in country_code.upper())
                
                return f"{flag} {isp}".strip()
    except (requests.RequestException, ValueError, KeyError):
        pass
    return None

def validate_process_name(name):
    """Basic validation for process name. Returns stripped name or None."""
    if not name:
        return None
    name = name.strip()
    return name if name else None

def process_and_collapse_networks(ips_set):
    """
    Groups individual IP addresses into larger subnets where possible.
    Returns a sorted list of ipaddress.IPv4Network or IPv6Network objects.
    collapse_addresses requires same-version networks, so we split by version.
    """
    if not ips_set:
        return []

    v4 = [n for n in ips_set if n.version == 4]
    v6 = [n for n in ips_set if n.version == 6]

    collapsed = []
    if v4:
        collapsed.extend(ipaddress.collapse_addresses(sorted(v4)))
    if v6:
        collapsed.extend(ipaddress.collapse_addresses(sorted(v6)))

    return sorted(collapsed, key=lambda x: (x.version, x))

def save_subnets_to_file(subnets, file_path):
    """Saves a list of subnets to a text file. Returns True on success."""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            sorted_subs = sorted(subnets, key=lambda x: (x.version, x))
            for net in sorted_subs:
                f.write(f"{net}\n")
        return True
    except PermissionError:
        logger.warning(f"Permission denied writing to: {file_path}")
        return False
    except OSError as e:
        logger.exception(f"Error saving to file: {e}")
        return False
