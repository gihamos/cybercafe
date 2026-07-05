import socket
import sys
import time
import uuid

import psutil

_DISK_ROOT = "C:\\" if sys.platform == "win32" else "/"


def get_ip() -> str | None:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return None


def get_mac() -> str:
    mac = uuid.getnode()
    return ":".join(f"{(mac >> ele) & 0xff:02x}" for ele in range(40, -8, -8))


def get_metrics() -> dict:
    return {
        "cpu_usage": psutil.cpu_percent(interval=None),
        "ram_usage": psutil.virtual_memory().percent,
        "disk_usage": psutil.disk_usage(_DISK_ROOT).percent,
        "ip": get_ip(),
        "mac_adresse": get_mac(),
        "uptime_seconds": int(time.time() - psutil.boot_time()),
    }
