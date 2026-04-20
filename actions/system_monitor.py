# actions/system_monitor.py
"""
System monitoring tool for JARVIS MK37.
Gathers CPU, RAM, disk, network, and process information.

Returns structured system health data. Uses psutil with fallback
to OS commands if psutil is not installed.

Cross-platform: Windows, Linux, macOS.
"""
import json
import os
import platform
import subprocess
import time

_OS = platform.system()


def _get_root_disk_path() -> str:
    """Return the root disk path for the current OS."""
    if _OS == "Windows":
        return os.environ.get("SystemDrive", "C:\\") + "\\"
    return "/"


def _get_psutil_info() -> dict:
    """Gather system info using psutil."""
    import psutil

    cpu_pct = psutil.cpu_percent(interval=1)
    cpu_count = psutil.cpu_count()
    cpu_freq = psutil.cpu_freq()

    mem = psutil.virtual_memory()

    # Cross-platform disk usage
    try:
        disk = psutil.disk_usage(_get_root_disk_path())
    except Exception:
        disk = None

    # Top 10 processes by memory
    top_procs = []
    try:
        for proc in sorted(
            psutil.process_iter(["pid", "name", "memory_percent", "cpu_percent"]),
            key=lambda p: p.info.get("memory_percent", 0) or 0,
            reverse=True,
        )[:10]:
            top_procs.append({
                "pid": proc.info["pid"],
                "name": proc.info["name"] or "unknown",
                "memory_pct": round(proc.info.get("memory_percent", 0) or 0, 1),
                "cpu_pct": round(proc.info.get("cpu_percent", 0) or 0, 1),
            })
    except (psutil.AccessDenied, psutil.NoSuchProcess):
        pass

    # Network
    try:
        net = psutil.net_io_counters()
        net_info = {
            "bytes_sent_mb": round(net.bytes_sent / (1024**2), 1),
            "bytes_recv_mb": round(net.bytes_recv / (1024**2), 1),
        }
    except Exception:
        net_info = {"bytes_sent_mb": "N/A", "bytes_recv_mb": "N/A"}

    try:
        boot = time.time() - psutil.boot_time()
        uptime_hours = round(boot / 3600, 1)
    except Exception:
        uptime_hours = "N/A"

    result = {
        "os": f"{platform.system()} {platform.release()} ({platform.machine()})",
        "hostname": platform.node(),
        "uptime_hours": uptime_hours,
        "cpu": {
            "cores": cpu_count,
            "usage_pct": cpu_pct,
            "freq_mhz": round(cpu_freq.current, 0) if cpu_freq else "N/A",
        },
        "memory": {
            "total_gb": round(mem.total / (1024**3), 1),
            "used_gb": round(mem.used / (1024**3), 1),
            "available_gb": round(mem.available / (1024**3), 1),
            "usage_pct": mem.percent,
        },
        "network": net_info,
        "top_processes": top_procs,
    }

    if disk:
        result["disk"] = {
            "total_gb": round(disk.total / (1024**3), 1),
            "used_gb": round(disk.used / (1024**3), 1),
            "free_gb": round(disk.free / (1024**3), 1),
            "usage_pct": disk.percent,
        }
    else:
        result["disk"] = {"error": "Could not read disk usage"}

    return result


def _get_fallback_info() -> dict:
    """Gather basic system info without psutil using OS commands."""
    info = {
        "os": f"{platform.system()} {platform.release()} ({platform.machine()})",
        "hostname": platform.node(),
    }

    if _OS == "Windows":
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "$cpu=(Get-CimInstance Win32_Processor).LoadPercentage;"
                 "$mem=Get-CimInstance Win32_OperatingSystem;"
                 "$total=[math]::Round($mem.TotalVisibleMemorySize/1MB,1);"
                 "$free=[math]::Round($mem.FreePhysicalMemory/1MB,1);"
                 "Write-Output \"$cpu|$total|$free\""],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                parts = result.stdout.strip().split("|")
                if len(parts) >= 3:
                    info["cpu_usage_pct"] = parts[0]
                    info["memory_total_gb"] = parts[1]
                    info["memory_free_gb"] = parts[2]
        except Exception:
            pass
    elif _OS == "Darwin":
        # macOS
        try:
            result = subprocess.run(["uptime"], capture_output=True, text=True, timeout=5)
            info["uptime"] = result.stdout.strip()
        except Exception:
            pass
        try:
            result = subprocess.run(["df", "-h", "/"], capture_output=True, text=True, timeout=5)
            info["disk"] = result.stdout.strip()
        except Exception:
            pass
    else:
        # Linux
        try:
            result = subprocess.run(["uptime"], capture_output=True, text=True, timeout=5)
            info["uptime"] = result.stdout.strip()
        except Exception:
            pass
        try:
            result = subprocess.run(["free", "-h"], capture_output=True, text=True, timeout=5)
            info["memory"] = result.stdout.strip()
        except Exception:
            pass
        try:
            result = subprocess.run(["df", "-h", "/"], capture_output=True, text=True, timeout=5)
            info["disk"] = result.stdout.strip()
        except Exception:
            pass

    return info


def system_monitor(parameters: dict = None, player=None) -> str:
    """
    Main entry point for the system_monitor tool.

    Parameters:
        action: "full" | "cpu" | "memory" | "disk" | "processes" | "quick"
    """
    params = parameters or {}
    action = params.get("action", "full").lower()

    try:
        try:
            data = _get_psutil_info()
        except ImportError:
            data = _get_fallback_info()
            return (
                f"System Info (basic — install psutil for full data):\n"
                f"{json.dumps(data, indent=2)}"
            )

        if action == "cpu":
            return f"CPU: {data['cpu']['cores']} cores, {data['cpu']['usage_pct']}% used, {data['cpu']['freq_mhz']} MHz"
        elif action == "memory":
            m = data["memory"]
            return f"RAM: {m['used_gb']}/{m['total_gb']} GB ({m['usage_pct']}% used), {m['available_gb']} GB free"
        elif action == "disk":
            d = data.get("disk", {})
            if "error" in d:
                return f"Disk: {d['error']}"
            return f"Disk: {d['used_gb']}/{d['total_gb']} GB ({d['usage_pct']}% used), {d['free_gb']} GB free"
        elif action == "processes":
            lines = ["Top 10 Processes by Memory:"]
            for p in data.get("top_processes", []):
                lines.append(f"  PID {p['pid']:6d} | {p['name']:25s} | MEM {p['memory_pct']:5.1f}% | CPU {p['cpu_pct']:5.1f}%")
            return "\n".join(lines)
        elif action == "quick":
            disk_pct = data.get("disk", {}).get("usage_pct", "?")
            return (
                f"System: {data['os']} | Up: {data.get('uptime_hours', '?')}h\n"
                f"CPU: {data['cpu']['usage_pct']}% | RAM: {data['memory']['usage_pct']}% | Disk: {disk_pct}%"
            )
        else:
            return json.dumps(data, indent=2)

    except Exception as e:
        return f"System monitor error: {e}"
