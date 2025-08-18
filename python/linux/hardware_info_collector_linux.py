#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RECOLECTOR DE INFORMACIÓN DE HARDWARE (Linux)
Obtiene información detallada del hardware del sistema Linux y la guarda en YAML.

Basado en el script original multi-plataforma, simplificado y endurecido para Linux.
Incluye comprobaciones de dependencias y uso de utilidades del sistema.

Autor: Asistente IA
Versión: 1.1 (Linux)
Compatible: Linux (Debian/Ubuntu, RHEL/CentOS, Arch, etc.)
Licencia: MIT
"""

import argparse
import os
import platform
import socket
import subprocess
import sys
import uuid
import json
from datetime import datetime

import psutil
import yaml

# Dependencias opcionales
try:
    import cpuinfo  # py-cpuinfo
except Exception:
    cpuinfo = None

try:
    import GPUtil  # NVIDIA opcional
except Exception:
    GPUtil = None

try:
    import distro  # info de distribución
except Exception:
    distro = None

def bytes_to_gb(value: int) -> float:
    return round(value / (1024 ** 3), 2) if value is not None else 0.0

def bytes_to_mb(value: int) -> float:
    return round(value / (1024 ** 2), 2) if value is not None else 0.0

def which(cmd: str) -> bool:
    from shutil import which as _which
    return _which(cmd) is not None

def run(command: str):
    """Ejecuta un comando en shell, devuelve (ok, stdout)"""
    try:
        p = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=30
        )
        if p.returncode == 0:
            return True, p.stdout.strip()
        return False, p.stdout.strip() or p.stderr.strip()
    except Exception as e:
        return False, str(e)

class HardwareInfoCollectorLinux:
    def __init__(self):
        self.data = {
            "scan_info": {
                "timestamp": datetime.now().isoformat(),
                "scanner_version": "1.1-linux",
                "platform": platform.system(),
                "kernel": platform.release(),
            },
            "system": {},
            "cpu": {},
            "memory": {},
            "storage": {},
            "network": {},
            "gpu": {},
            "motherboard": {},
            "usb_devices": [],
        }

    # -------- Sistema --------
    def get_system_info(self):
        sysinfo = {
            "hostname": socket.gethostname(),
            "fqdn": socket.getfqdn(),
            "architecture": platform.architecture()[0],
            "machine": platform.machine(),
            "python_version": platform.python_version(),
            "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat(),
            "uptime_seconds": int(datetime.now().timestamp() - psutil.boot_time()),
            "timezone": str(datetime.now().astimezone().tzinfo),
            "user": os.getenv("USER") or os.getenv("LOGNAME") or "unknown",
            "uuid": str(uuid.uuid4()),
        }
        if distro:
            try:
                sysinfo["distro"] = distro.name(pretty=True)
                sysinfo["distro_version"] = distro.version(best=True)
                sysinfo["distro_codename"] = distro.codename()
            except Exception:
                pass
        else:
            # Fallback a /etc/os-release
            ok, out = run("cat /etc/os-release")
            if ok:
                osrel = {}
                for line in out.splitlines():
                    if "=" in line:
                        k, v = line.split("=", 1)
                        osrel[k] = v.strip().strip('"')
                sysinfo["distro"] = osrel.get("PRETTY_NAME") or osrel.get("NAME")
                sysinfo["distro_version"] = osrel.get("VERSION")

        self.data["system"] = sysinfo

    # -------- CPU --------
    def get_cpu_info(self):
        info = {
            "cores_physical": psutil.cpu_count(logical=False),
            "cores_logical": psutil.cpu_count(logical=True),
            "usage_percent": psutil.cpu_percent(interval=1),
            "usage_per_core": psutil.cpu_percent(interval=1, percpu=True),
        }
        try:
            freq = psutil.cpu_freq()
            if freq:
                info["current_frequency_mhz"] = f"{freq.current:.2f}"
                info["min_frequency_mhz"] = f"{freq.min:.2f}"
                info["max_frequency_mhz"] = f"{freq.max:.2f}"
        except Exception:
            pass

        if cpuinfo:
            try:
                c = cpuinfo.get_cpu_info()
                info.update(
                    {
                        "brand": c.get("brand_raw") or "Unknown",
                        "architecture": c.get("arch_string_raw") or platform.machine(),
                        "flags": c.get("flags", []),
                        "vendor": c.get("vendor_id_raw", "Unknown"),
                        "l1d_cache": c.get("l1_data_cache_size", "Unknown"),
                        "l2_cache": c.get("l2_cache_size", "Unknown"),
                        "l3_cache": c.get("l3_cache_size", "Unknown"),
                    }
                )
            except Exception:
                pass
        else:
            info["brand"] = platform.processor() or "Unknown"
        self.data["cpu"] = info

    # -------- Memoria --------
    def get_memory_info(self):
        vm = psutil.virtual_memory()
        sm = psutil.swap_memory()
        mem = {
            "total_gb": bytes_to_gb(vm.total),
            "available_gb": bytes_to_gb(vm.available),
            "used_gb": bytes_to_gb(vm.used),
            "free_gb": bytes_to_gb(vm.free),
            "usage_percent": vm.percent,
            "swap_total_gb": bytes_to_gb(sm.total),
            "swap_used_gb": bytes_to_gb(sm.used),
            "swap_free_gb": bytes_to_gb(sm.free),
            "swap_usage_percent": sm.percent,
        }
        # dmidecode para módulos (requiere privilegios)
        if which("dmidecode"):
            ok, out = run("dmidecode -t memory")
            if ok:
                mem["detailed_modules"] = self._parse_dmidecode_memory(out)
            else:
                mem["dmidecode_warning"] = (
                    "No se pudo leer información de dmidecode (requiere root)."
                )
        self.data["memory"] = mem

    def _parse_dmidecode_memory(self, text: str):
        modules = []
        current = {}
        for line in text.splitlines():
            if line.strip().startswith("Memory Device"):
                if current:
                    modules.append(current)
                    current = {}
            elif ":" in line:
                k, v = line.split(":", 1)
                k = k.strip().lower().replace(" ", "_")
                v = v.strip()
                if k in {"size", "speed", "manufacturer", "part_number", "serial_number", "form_factor", "type"}:
                    current[k] = v
        if current:
            modules.append(current)
        # filtrar vacíos
        return [m for m in modules if m.get("size") and m.get("size") != "No Module Installed"]

    # -------- Almacenamiento --------
    def get_storage_info(self):
        storage = {"partitions": [], "total_storage_gb": 0.0, "physical_disks": []}
        # Particiones montadas
        for p in psutil.disk_partitions(all=False):
            try:
                u = psutil.disk_usage(p.mountpoint)
            except PermissionError:
                continue
            info = {
                "device": p.device,
                "mountpoint": p.mountpoint,
                "filesystem": p.fstype,
                "total_gb": bytes_to_gb(u.total),
                "used_gb": bytes_to_gb(u.used),
                "free_gb": bytes_to_gb(u.free),
                "usage_percent": round((u.used / u.total) * 100, 2) if u.total else 0,
            }
            storage["partitions"].append(info)
            storage["total_storage_gb"] += info["total_gb"]

        # Discos físicos via lsblk (JSON)
        if which("lsblk"):
            ok, out = run("lsblk -J -o NAME,SIZE,TYPE,MODEL,SERIAL,ROTA,RM,TRAN,MOUNTPOINT")
            if ok:
                try:
                    data = json.loads(out)
                    storage["physical_disks"] = data.get("blockdevices", [])
                except Exception:
                    pass
        self.data["storage"] = storage

    # -------- Red --------
    def get_network_info(self):
        net = {"interfaces": [], "global_stats": {}}
        addrs = psutil.net_if_addrs()
        stats = psutil.net_if_stats()
        io = psutil.net_io_counters(pernic=True)

        for name, addr_list in addrs.items():
            iface = {
                "name": name,
                "is_up": stats.get(name).isup if name in stats else False,
                "speed_mbps": getattr(stats.get(name), "speed", 0) if name in stats else 0,
                "mtu": getattr(stats.get(name), "mtu", 0) if name in stats else 0,
                "addresses": [],
            }
            for a in addr_list:
                iface["addresses"].append(
                    {
                        "family": str(a.family),
                        "address": a.address,
                        "netmask": a.netmask,
                        "broadcast": a.broadcast,
                    }
                )
            if name in io:
                s = io[name]
                iface["io_stats"] = {
                    "bytes_sent": s.bytes_sent,
                    "bytes_received": s.bytes_recv,
                    "packets_sent": s.packets_sent,
                    "packets_received": s.packets_recv,
                    "errors_in": s.errin,
                    "errors_out": s.errout,
                    "drops_in": s.dropin,
                    "drops_out": s.dropout,
                }
            net["interfaces"].append(iface)

        g = psutil.net_io_counters()
        net["global_stats"] = {
            "bytes_sent": g.bytes_sent,
            "bytes_received": g.bytes_recv,
            "packets_sent": g.packets_sent,
            "packets_received": g.packets_recv,
        }
        self.data["network"] = net

    # -------- GPU --------
    def get_gpu_info(self):
        gpu = {"detected": [], "nvidia": [], "notes": []}
        # Preferir GPUtil si hay GPUs NVIDIA
        if GPUtil:
            try:
                gpus = GPUtil.getGPUs()
                for g in gpus:
                    gpu["nvidia"].append(
                        {
                            "name": g.name,
                            "id": g.id,
                            "memory_total_mb": g.memoryTotal,
                            "memory_used_mb": g.memoryUsed,
                            "memory_free_mb": g.memoryFree,
                            "gpu_usage_percent": round(g.load * 100, 2),
                            "temperature_celsius": g.temperature,
                            "driver_version": g.driver,
                            "uuid": g.uuid,
                        }
                    )
            except Exception:
                pass
        # Información genérica por lspci
        if which("lspci"):
            ok, out = run("lspci | egrep -i 'vga|3d|display'")
            if ok:
                gpu["detected"] = [line.strip() for line in out.splitlines() if line.strip()]
            else:
                if "not found" in out.lower():
                    gpu["notes"].append("lspci no disponible (instale pciutils).")
        else:
            gpu["notes"].append("Instale 'pciutils' para detección de GPU (lspci).")
        self.data["gpu"] = gpu

    # -------- Placa base / BIOS --------
    def get_motherboard_info(self):
        mb = {}
        if which("dmidecode"):
            ok, base = run("dmidecode -t baseboard")
            if ok:
                mb["dmi_baseboard"] = base
            else:
                mb["baseboard_warning"] = "No se pudo leer la baseboard (root necesario)."
            ok, bios = run("dmidecode -t bios")
            if ok:
                mb["dmi_bios"] = bios
            else:
                mb["bios_warning"] = "No se pudo leer la BIOS (root necesario)."
        else:
            mb["notes"] = "Instale 'dmidecode' para obtener información de placa y BIOS."
        self.data["motherboard"] = mb

    # -------- USB --------
    def get_usb_devices(self):
        devices = []
        if which("lsusb"):
            ok, out = run("lsusb")
            if ok:
                devices = [l.strip() for l in out.splitlines() if l.strip()]
        else:
            devices.append("Instale 'usbutils' para listar dispositivos USB (lsusb).")
        self.data["usb_devices"] = devices

    # -------- Guardado y resumen --------
    def save_yaml(self, path: str = None) -> str:
        if not path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            host = self.data.get("system", {}).get("hostname", "unknown")
            path = f"hardware_info_{host}_{timestamp}.yml"
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(self.data, f, allow_unicode=True, sort_keys=False, indent=2)
        return path

    def print_summary(self):
        s = self.data.get("system", {})
        c = self.data.get("cpu", {})
        m = self.data.get("memory", {})
        st = self.data.get("storage", {})
        g = self.data.get("gpu", {})
        n = self.data.get("network", {})

        print("=" * 60)
        print("              RESUMEN DE HARDWARE (Linux)")
        print("=" * 60)
        print(f"Sistema: {s.get('distro','Linux')}  Kernel: {self.data['scan_info'].get('kernel')}")
        print(f"Hostname: {s.get('hostname')}  Arquitectura: {s.get('architecture','')}")
        print(f"CPU: {c.get('brand','Unknown')}  Núcleos: {c.get('cores_physical')}/{c.get('cores_logical')}")
        print(f"RAM: {m.get('total_gb','?')} GB  Libre: {m.get('available_gb','?')} GB")
        print(f"Almacenamiento total: {st.get('total_storage_gb',0):.2f} GB  Particiones: {len(st.get('partitions',[]))}")
        print(f"Controladores gráficos: {len(g.get('detected',[]))}  NVIDIA: {len(g.get('nvidia',[]))}")
        print(f"Interfaces de red: {len(n.get('interfaces',[]))}")
        print("=" * 60)

def parse_args():
    p = argparse.ArgumentParser(description="Recolector de hardware para Linux (YAML)")
    p.add_argument("-o", "--output", help="Ruta del archivo YAML de salida", default=None)
    p.add_argument("--show", action="store_true", help="Imprimir el YAML al finalizar")
    return p.parse_args()

def ensure_tips():
    tips = []
    if not which("lsblk"):
        tips.append("Instale 'util-linux' para lsblk (normalmente ya viene instalado).")
    if not which("lspci"):
        tips.append("Instale 'pciutils' para lspci: sudo apt install pciutils")
    if not which("lsusb"):
        tips.append("Instale 'usbutils' para lsusb: sudo apt install usbutils")
    if not which("dmidecode"):
        tips.append("Instale 'dmidecode' (y ejecute con sudo para detalles de BIOS/RAM).")
    if tips:
        print("\n[RECOMENDACIONES]")
        for t in tips:
            print(f"- {t}")

def main():
    args = parse_args()
    collector = HardwareInfoCollectorLinux()

    print("Iniciando recolección de información de hardware (Linux)...")
    print("Esto puede tomar algunos segundos...\n")

    collector.get_system_info()
    collector.get_cpu_info()
    collector.get_memory_info()
    collector.get_storage_info()
    collector.get_network_info()
    collector.get_gpu_info()
    collector.get_motherboard_info()
    collector.get_usb_devices()

    collector.print_summary()
    path = collector.save_yaml(args.output)
    print(f"\n[GUARDADO] Información guardada en: {os.path.abspath(path)}")

    if args.show:
        print("\n=== CONTENIDO YAML ===")
        with open(path, "r", encoding="utf-8") as f:
            print(f.read())

    ensure_tips()

if __name__ == "__main__":
    main()
