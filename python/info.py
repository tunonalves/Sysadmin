#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Recolector de información de hardware para Windows 10/11.

Características:
- Obtiene datos de BIOS, motherboard, CPU, RAM, discos, GPU, red, monitores, batería.
- Exporta únicamente la información de hardware a un archivo YAML (.yml).

Requisitos:
- Ejecutar en Windows 10/11 con Python 3.8+.
- Requiere PowerShell y privilegios de administrador (recomendado).
- No instala módulos externos, genera YAML de forma manual.

Uso:
  python win_hw_inventory.py --yml hardware.yml

Autor: Multimedios CNA + ChatGPT
"""

import argparse
import ctypes
import json
import os
import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Tuple

try:
    import winreg  # type: ignore
except Exception:
    winreg = None

# ---------------------------- Utilidades ---------------------------- #

def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def run_ps(cmd: str) -> Tuple[int, str, str]:
    """Ejecuta PowerShell y devuelve (rc, stdout, stderr)."""
    full_cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-Command", cmd,
    ]
    proc = subprocess.Popen(full_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, err = proc.communicate()
    return proc.returncode, out.strip(), err.strip()


def ps_json(cmd: str) -> Any:
    rc, out, err = run_ps(f"{cmd} | ConvertTo-Json -Depth 5")
    if rc != 0:
        return {"error": err or f"rc={rc}"}
    try:
        return json.loads(out) if out else None
    except json.JSONDecodeError:
        return out

# ---------------------------- Recolección Hardware ---------------------------- #

def collect_hardware() -> Dict[str, Any]:
    hw: Dict[str, Any] = {
        "datetime": datetime.now().isoformat(),
        "computername": os.environ.get("COMPUTERNAME"),
        "os_arch": platform.machine(),
    }
    hw["bios"] = ps_json("Get-CimInstance Win32_BIOS | Select-Object Manufacturer,SMBIOSBIOSVersion,ReleaseDate,SerialNumber")
    hw["baseboard"] = ps_json("Get-CimInstance Win32_BaseBoard | Select-Object Manufacturer,Product,SerialNumber")
    hw["computer_system"] = ps_json(
        "Get-CimInstance Win32_ComputerSystem | Select-Object Manufacturer,Model,TotalPhysicalMemory,NumberOfLogicalProcessors,NumberOfProcessors"
    )
    hw["processor"] = ps_json("Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors,MaxClockSpeed")
    hw["memory_modules"] = ps_json(
        "Get-CimInstance Win32_PhysicalMemory | Select-Object Manufacturer,Capacity,Speed,PartNumber,SerialNumber,BankLabel"
    )
    hw["disks"] = ps_json(
        "Get-CimInstance Win32_DiskDrive | Select-Object Model,InterfaceType,SerialNumber,Size,Partitions,MediaType"
    )
    hw["logical_disks"] = ps_json(
        "Get-CimInstance Win32_LogicalDisk | Select-Object DeviceID,DriveType,FileSystem,Size,FreeSpace,VolumeName"
    )
    hw["video"] = ps_json("Get-CimInstance Win32_VideoController | Select-Object Name,DriverVersion,AdapterRAM")
    hw["monitors"] = ps_json("Get-CimInstance Win32_DesktopMonitor | Select-Object Name,ScreenWidth,ScreenHeight")
    hw["battery"] = ps_json("Get-CimInstance Win32_Battery | Select-Object Name,BatteryStatus,EstimatedChargeRemaining")
    return hw

# ---------------------------- YAML Export ---------------------------- #

def dict_to_yaml(data: Dict[str, Any], indent: int = 0) -> str:
    lines = []
    ind = "  " * indent
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, (dict, list)):
                lines.append(f"{ind}{k}:")
                lines.append(dict_to_yaml(v, indent + 1))
            else:
                lines.append(f"{ind}{k}: {v}")
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, (dict, list)):
                lines.append(f"{ind}-")
                lines.append(dict_to_yaml(item, indent + 1))
            else:
                lines.append(f"{ind}- {item}")
    else:
        lines.append(f"{ind}{data}")
    return "\n".join(lines)


def write_yaml(path: Path, data: Dict[str, Any]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        f.write(dict_to_yaml(data))

# ---------------------------- CLI ---------------------------- #

def parse_args():
    p = argparse.ArgumentParser(description="Inventario Hardware Windows -> YAML")
    p.add_argument("--yml", default="hardware.yml", help="Ruta de salida YAML")
    return p.parse_args()


def main():
    if os.name != 'nt' or winreg is None:
        print("[!] Este script debe ejecutarse en Windows 10/11.")
        sys.exit(1)

    args = parse_args()
    hw = collect_hardware()

    out_yml = Path(args.yml)
    write_yaml(out_yml, hw)
    print(f"[+] YAML escrito en: {out_yml.resolve()}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Interrumpido por el usuario.")
