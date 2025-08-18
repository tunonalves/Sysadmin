#!/usr/bin/env python3
"""
sys_monitor.py — Cross-platform hardware & resource monitor for Linux and Windows.

Features
- CPU: per-core usage, load averages, frequency
- Memory: RAM and swap
- Disk: per-partition usage & overall IO counters
- Network: per-interface stats
- GPU: NVIDIA via `nvidia-smi` if available; basic fallback via GPUtil (optional)
- OS / hardware: platform, boot time, battery (when available), temps (Linux/macOS with sensors)
- Output: human-readable table, or JSON/CSV exports
- Modes: one-shot (--once) or continuous with --interval seconds

Dependencies
- psutil (required)
- GPUtil (optional, for non-NVIDIA GPUs or fallback)

Install:
  python -m pip install psutil GPUtil

Examples:
  python sys_monitor.py --once
  python sys_monitor.py --interval 5
  python sys_monitor.py --once --json out.json
  python sys_monitor.py --interval 10 --csv metrics.csv
"""

import argparse
import csv
import datetime
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional

try:
    import psutil
except ImportError:
    print("This script requires 'psutil'. Install with: python -m pip install psutil", file=sys.stderr)
    sys.exit(1)

# Try optional GPUtil for GPU info fallback
try:
    import GPUtil  # type: ignore
except Exception:
    GPUtil = None  # type: ignore


def fmt_bytes(n: Optional[float]) -> str:
    if n is None:
        return "n/a"
    step = 1024.0
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    i = 0
    while n >= step and i < len(units) - 1:
        n /= step
        i += 1
    return f"{n:.1f} {units[i]}"


def safe_call(func, default=None):
    try:
        return func()
    except Exception:
        return default


def get_os_info() -> Dict[str, Any]:
    uname = platform.uname()
    return {
        "system": uname.system,
        "node": uname.node,
        "release": uname.release,
        "version": uname.version,
        "machine": uname.machine,
        "processor": uname.processor or platform.processor(),
        "python_version": platform.python_version(),
        "boot_time": datetime.datetime.fromtimestamp(psutil.boot_time()).isoformat(),
    }


def get_cpu_info() -> Dict[str, Any]:
    freq = safe_call(lambda: psutil.cpu_freq())
    load_avg = None
    if hasattr(os, "getloadavg"):
        try:
            la = os.getloadavg()
            load_avg = {"1min": la[0], "5min": la[1], "15min": la[2]}
        except Exception:
            load_avg = None
    return {
        "physical_cores": psutil.cpu_count(logical=False),
        "total_cores": psutil.cpu_count(logical=True),
        "usage_percent_total": psutil.cpu_percent(interval=None),
        "usage_percent_per_core": psutil.cpu_percent(interval=None, percpu=True),
        "frequency_mhz": freq.current if freq else None,
        "frequency_min_mhz": freq.min if freq else None,
        "frequency_max_mhz": freq.max if freq else None,
        "load_average": load_avg,
    }


def get_memory_info() -> Dict[str, Any]:
    vm = psutil.virtual_memory()
    sm = psutil.swap_memory()
    return {
        "ram_total": vm.total,
        "ram_available": vm.available,
        "ram_used": vm.used,
        "ram_percent": vm.percent,
        "swap_total": sm.total,
        "swap_used": sm.used,
        "swap_percent": sm.percent,
    }


def get_disks_info() -> Dict[str, Any]:
    partitions = []
    for p in psutil.disk_partitions(all=False):
        usage = safe_call(lambda: psutil.disk_usage(p.mountpoint))
        partitions.append({
            "device": p.device,
            "mountpoint": p.mountpoint,
            "fstype": p.fstype,
            "total": getattr(usage, "total", None),
            "used": getattr(usage, "used", None),
            "percent": getattr(usage, "percent", None),
        })
    io = safe_call(lambda: psutil.disk_io_counters(perdisk=True), {})
    return {"partitions": partitions, "io_counters": {k: v._asdict() for k, v in io.items()}}


def get_network_info() -> Dict[str, Any]:
    addrs = psutil.net_if_addrs()
    stats = psutil.net_if_stats()
    io = psutil.net_io_counters(pernic=True)
    interfaces = {}
    for name in addrs.keys():
        interfaces[name] = {
            "isup": getattr(stats.get(name), "isup", None),
            "speed_mbps": getattr(stats.get(name), "speed", None),
            "mtu": getattr(stats.get(name), "mtu", None),
            "addresses": [a.address for a in addrs[name] if a.address],
            "io": io.get(name)._asdict() if name in io else None,
        }
    return {"interfaces": interfaces}


def get_battery_info() -> Optional[Dict[str, Any]]:
    batt = safe_call(lambda: psutil.sensors_battery())
    if not batt:
        return None
    return {
        "percent": batt.percent,
        "secsleft": batt.secsleft,
        "power_plugged": batt.power_plugged,
    }


def get_temps_info() -> Optional[Dict[str, Any]]:
    temps = safe_call(lambda: psutil.sensors_temperatures())
    if not temps:
        return None
    out = {}
    for name, entries in temps.items():
        out[name] = [e._asdict() for e in entries]
    return out or None


def get_gpu_info() -> Optional[Dict[str, Any]]:
    # Prefer nvidia-smi if available
    nvidia_path = shutil.which("nvidia-smi")
    if nvidia_path:
        try:
            fmt = "--query-gpu=index,name,driver_version,memory.total,memory.used,utilization.gpu,temperature.gpu"
            cmd = [nvidia_path, fmt, "--format=csv,noheader,nounits"]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            gpus = []
            for line in result.stdout.strip().splitlines():
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 7:
                    gpus.append({
                        "index": int(parts[0]),
                        "name": parts[1],
                        "driver_version": parts[2],
                        "memory_total_mb": float(parts[3]),
                        "memory_used_mb": float(parts[4]),
                        "utilization_percent": float(parts[5]),
                        "temperature_c": float(parts[6]),
                    })
            return {"backend": "nvidia-smi", "gpus": gpus}
        except Exception:
            pass

    # Fallback to GPUtil if installed
    if GPUtil is not None:
        try:
            gpus = GPUtil.getGPUs()
            out = []
            for g in gpus:
                out.append({
                    "id": g.id,
                    "name": g.name,
                    "load_percent": round(g.load * 100, 1) if g.load is not None else None,
                    "memory_total_mb": g.memoryTotal,
                    "memory_used_mb": g.memoryUsed,
                    "temperature_c": g.temperature,
                    "uuid": g.uuid,
                })
            return {"backend": "GPUtil", "gpus": out}
        except Exception:
            pass

    return None


def collect_metrics() -> Dict[str, Any]:
    return {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "os": get_os_info(),
        "cpu": get_cpu_info(),
        "memory": get_memory_info(),
        "disks": get_disks_info(),
        "network": get_network_info(),
        "battery": get_battery_info(),
        "temperatures": get_temps_info(),
        "gpus": get_gpu_info(),
        "process_count": len(psutil.pids()),
        "top_processes": top_processes(10),
    }


def top_processes(n: int = 10) -> List[Dict[str, Any]]:
    procs = []
    for p in psutil.process_iter(attrs=["pid", "name"]):
        try:
            cpu = p.cpu_percent(interval=None)
            mem = p.memory_info().rss
            procs.append({"pid": p.pid, "name": p.info.get("name"), "cpu_percent": cpu, "rss_bytes": mem})
        except Exception:
            continue
    # Let CPU percents settle
    time.sleep(0.1)
    for p in psutil.process_iter(attrs=["pid", "name"]):
        try:
            # Re-sample for a short interval to get non-zero CPU
            cpu = p.cpu_percent(interval=0.1)
            for item in procs:
                if item["pid"] == p.pid:
                    item["cpu_percent"] = cpu
                    item["rss_bytes"] = p.memory_info().rss
                    break
        except Exception:
            continue
    procs.sort(key=lambda x: (x["cpu_percent"], x["rss_bytes"]), reverse=True)
    return procs[:n]


def print_table(metrics: Dict[str, Any]) -> None:
    osinfo = metrics["os"]
    cpu = metrics["cpu"]
    mem = metrics["memory"]
    print("=" * 80)
    print(f"{osinfo['node']} — {osinfo['system']} {osinfo['release']} ({osinfo['machine']}) | Python {osinfo['python_version']}")
    print(f"Boot: {osinfo['boot_time']} | Time: {metrics['timestamp']}")
    print("-" * 80)
    print(f"CPU: {cpu['physical_cores']} phys / {cpu['total_cores']} total | Freq: {cpu['frequency_mhz'] or 'n/a'} MHz")
    if cpu.get("load_average"):
        la = cpu["load_average"]
        print(f"CPU Usage: {cpu['usage_percent_total']}% | Load avg: {la['1min']:.2f} {la['5min']:.2f} {la['15min']:.2f}")
    else:
        print(f"CPU Usage: {cpu['usage_percent_total']}%")
    print("Per-core:", ", ".join(f"{p:.1f}%" for p in cpu["usage_percent_per_core"]))
    print("-" * 80)
    print(f"RAM: {fmt_bytes(mem['ram_used'])}/{fmt_bytes(mem['ram_total'])} ({mem['ram_percent']}%) | Swap: {fmt_bytes(mem['swap_used'])}/{fmt_bytes(mem['swap_total'])} ({mem['swap_percent']}%)")
    print("-" * 80)
    print("Disks:")
    for p in metrics["disks"]["partitions"]:
        total = fmt_bytes(p['total']) if p['total'] is not None else "n/a"
        used = fmt_bytes(p['used']) if p['used'] is not None else "n/a"
        percent = f"{p['percent']}%" if p['percent'] is not None else "n/a"
        print(f"  {p['device']} -> {p['mountpoint']} [{p['fstype']}] {used}/{total} ({percent})")
    print("-" * 80)
    print("Network:")
    for name, iface in metrics["network"]["interfaces"].items():
        state = "UP" if iface["isup"] else "DOWN"
        speed = f"{iface['speed_mbps']}Mbps" if iface["speed_mbps"] is not None else "n/a"
        addrs = ", ".join(iface["addresses"][:3])
        io = iface["io"]
        if io:
            print(f"  {name} [{state}] {speed} MTU {iface['mtu']} | {addrs}")
            print(f"    Sent: {fmt_bytes(io['bytes_sent'])}, Recv: {fmt_bytes(io['bytes_recv'])}, Pkts: {io['packets_sent']}/{io['packets_recv']}")
        else:
            print(f"  {name} [{state}] {speed} MTU {iface['mtu']} | {addrs}")
    if metrics["battery"]:
        b = metrics["battery"]
        print("-" * 80)
        print(f"Battery: {b['percent']}% | Plugged: {b['power_plugged']} | Secs left: {b['secsleft']}")
    if metrics["temperatures"]:
        print("-" * 80)
        print("Temperatures:")
        for name, entries in metrics["temperatures"].items():
            temps = ", ".join(f"{e.get('label') or name}: {e.get('current')}°C" for e in entries[:3])
            print(f"  {name}: {temps}")
    if metrics["gpus"]:
        print("-" * 80)
        print(f"GPU ({metrics['gpus']['backend']}):")
        for g in metrics["gpus"]["gpus"]:
            fields = ", ".join(f"{k}={v}" for k, v in g.items())
            print(f"  - {fields}")
    print("-" * 80)
    print("Top processes (by CPU, then RSS):")
    for p in metrics["top_processes"]:
        print(f"  PID {p['pid']:<6} {p['name']:<22} CPU {p['cpu_percent']:>5.1f}%  RSS {fmt_bytes(p['rss_bytes'])}")
    print("=" * 80)


def write_json(path: str, metrics: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)


def append_csv(path: str, metrics: Dict[str, Any]) -> None:
    # Flatten a subset of metrics for time-series CSV
    row = {
        "timestamp": metrics["timestamp"],
        "host": metrics["os"]["node"],
        "cpu_usage_percent": metrics["cpu"]["usage_percent_total"],
        "ram_percent": metrics["memory"]["ram_percent"],
        "swap_percent": metrics["memory"]["swap_percent"],
        "process_count": metrics["process_count"],
    }
    fieldnames = list(row.keys())
    exists = os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Cross-platform system monitor (Linux & Windows).")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--once", action="store_true", help="Run a single sample and exit.")
    p.add_argument("--interval", type=int, default=0, help="Sample every N seconds (if >0).")
    p.add_argument("--json", type=str, help="Write full metrics to a JSON file (overwrites per run).")
    p.add_argument("--csv", type=str, help="Append a compact time-series row to CSV on each sample.")
    p.add_argument("--quiet", action="store_true", help="Suppress console table output.")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    if args.once:
        metrics = collect_metrics()
        if not args.quiet:
            print_table(metrics)
        if args.json:
            write_json(args.json, metrics)
        if args.csv:
            append_csv(args.csv, metrics)
        return

    interval = args.interval if args.interval and args.interval > 0 else 5
    try:
        while True:
            metrics = collect_metrics()
            if not args.quiet:
                print_table(metrics)
            if args.json:
                write_json(args.json, metrics)
            if args.csv:
                append_csv(args.csv, metrics)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nStopped.", file=sys.stderr)


if __name__ == "__main__":
    main()
