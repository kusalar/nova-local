import psutil
import platform
import time
from typing import Dict, Any

class SystemMonitor:
    """Non-blocking hardware and system telemetry engine using psutil."""

    @staticmethod
    def get_metrics() -> Dict[str, Any]:
        # Non-blocking CPU reading (uses interval=None so it returns immediately)
        cpu_percent = psutil.cpu_percent(interval=None)
        
        # Virtual memory (RAM)
        vmem = psutil.virtual_memory()
        ram_percent = vmem.percent
        ram_used_gb = round(vmem.used / (1024 ** 3), 2)
        ram_total_gb = round(vmem.total / (1024 ** 3), 2)
        ram_avail_gb = round(vmem.available / (1024 ** 3), 2)

        # Disk usage (primary system drive)
        try:
            # On Windows, use system root (usually C:)
            disk_root = "C:\\" if platform.system() == "Windows" else "/"
            disk = psutil.disk_usage(disk_root)
            disk_percent = disk.percent
            disk_used_gb = round(disk.used / (1024 ** 3), 1)
            disk_total_gb = round(disk.total / (1024 ** 3), 1)
        except Exception:
            disk_percent = 0.0
            disk_used_gb = 0.0
            disk_total_gb = 0.0

        # Battery status
        battery_info = {
            "has_battery": False,
            "percent": 100,
            "is_plugged": True,
            "status": "A/C Connected"
        }
        try:
            battery = psutil.sensors_battery()
            if battery is not None:
                battery_info = {
                    "has_battery": True,
                    "percent": round(battery.percent, 1),
                    "is_plugged": battery.power_plugged,
                    "status": "Charging" if battery.power_plugged else "Discharging"
                }
        except Exception:
            pass

        # Platform details
        boot_time = psutil.boot_time()
        uptime_seconds = int(time.time() - boot_time)
        uptime_hours = round(uptime_seconds / 3600, 1)

        return {
            "cpu": {
                "percent": round(cpu_percent, 1),
                "core_count": psutil.cpu_count(logical=True),
                "physical_cores": psutil.cpu_count(logical=False)
            },
            "ram": {
                "percent": round(ram_percent, 1),
                "used_gb": ram_used_gb,
                "total_gb": ram_total_gb,
                "available_gb": ram_avail_gb
            },
            "disk": {
                "percent": round(disk_percent, 1),
                "used_gb": disk_used_gb,
                "total_gb": disk_total_gb
            },
            "battery": battery_info,
            "system": {
                "os": platform.system(),
                "release": platform.release(),
                "machine": platform.machine(),
                "node": platform.node(),
                "uptime_hours": uptime_hours
            }
        }
