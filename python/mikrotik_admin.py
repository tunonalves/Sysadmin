#!/usr/bin/env python3
"""
mikrotik_admin.py — Script de administración para routers MikroTik via RouterOS API y SSH.

Funcionalidades:
- Conexión via RouterOS API (puerto 8728) o SSH (puerto 22)
- Gestión de interfaces de red
- Gestión de direcciones IP
- Gestión de reglas de firewall
- Gestión de usuarios del router
- Monitoreo de recursos (CPU, RAM, disco)
- Backup y restauración de configuración
- Gestión de rutas estáticas
- Listado de conexiones activas
- Menú interactivo en consola

Dependencias:
  pip install routeros-api paramiko netmiko

Uso:
  python mikrotik_admin.py
  python mikrotik_admin.py --host 192.168.88.1 --user admin --method api
  python mikrotik_admin.py --host 192.168.88.1 --user admin --method ssh
"""

import argparse
import getpass
import json
import os
import sys
import time
from datetime import datetime
from typing import Optional

# ─── Importaciones opcionales ────────────────────────────────────────────────

try:
    import routeros_api
    HAS_API = True
except ImportError:
    HAS_API = False

try:
    import paramiko
    HAS_SSH = True
except ImportError:
    HAS_SSH = False

try:
    from netmiko import ConnectHandler
    HAS_NETMIKO = True
except ImportError:
    HAS_NETMIKO = False


# ─── Colores ANSI ────────────────────────────────────────────────────────────

class Color:
    HEADER  = "\033[95m"
    BLUE    = "\033[94m"
    CYAN    = "\033[96m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    RED     = "\033[91m"
    BOLD    = "\033[1m"
    RESET   = "\033[0m"

def c(text: str, color: str) -> str:
    """Aplica color ANSI al texto."""
    return f"{color}{text}{Color.RESET}"

def header(title: str) -> None:
    width = 60
    print("\n" + c("═" * width, Color.CYAN))
    print(c(f"  {title}", Color.BOLD + Color.CYAN))
    print(c("═" * width, Color.CYAN))

def ok(msg: str)   -> None: print(c(f"  [✔] {msg}", Color.GREEN))
def err(msg: str)  -> None: print(c(f"  [✘] {msg}", Color.RED))
def warn(msg: str) -> None: print(c(f"  [!] {msg}", Color.YELLOW))
def info(msg: str) -> None: print(c(f"  [i] {msg}", Color.BLUE))


# ─── Clase base de conexión ──────────────────────────────────────────────────

class MikroTikBase:
    """Interfaz abstracta para conexiones MikroTik."""

    def __init__(self, host: str, user: str, password: str):
        self.host     = host
        self.user     = user
        self.password = password

    def connect(self) -> bool:
        raise NotImplementedError

    def disconnect(self) -> None:
        raise NotImplementedError

    def run(self, command: str) -> str:
        raise NotImplementedError


# ─── Conexión via RouterOS API ───────────────────────────────────────────────

class MikroTikAPI(MikroTikBase):
    """Conexión usando la librería routeros-api (puerto 8728/8729)."""

    def __init__(self, host: str, user: str, password: str, port: int = 8728):
        super().__init__(host, user, password)
        self.port       = port
        self._pool      = None
        self._conn      = None

    def connect(self) -> bool:
        if not HAS_API:
            err("Módulo 'routeros-api' no instalado. Ejecuta: pip install routeros-api")
            return False
        try:
            self._pool = routeros_api.RouterOsApiPool(
                self.host,
                username=self.user,
                password=self.password,
                port=self.port,
                plaintext_login=True,
            )
            self._conn = self._pool.get_api()
            ok(f"Conectado via API a {self.host}:{self.port}")
            return True
        except Exception as e:
            err(f"No se pudo conectar via API: {e}")
            return False

    def disconnect(self) -> None:
        if self._pool:
            self._pool.disconnect()
            info("Conexión API cerrada.")

    def get_resource(self, path: str) -> list:
        """Obtiene una lista de recursos de la API."""
        try:
            resource = self._conn.get_resource(path)
            return resource.get()
        except Exception as e:
            err(f"Error al consultar '{path}': {e}")
            return []

    def run_command(self, path: str, command: str, **kwargs) -> list:
        """Ejecuta un comando en la API."""
        try:
            resource = self._conn.get_resource(path)
            method   = getattr(resource, command)
            return method(**kwargs) or []
        except Exception as e:
            err(f"Error al ejecutar '{path}/{command}': {e}")
            return []

    # Alias para compatibilidad con el menú
    def run(self, command: str) -> str:
        return str(self.get_resource(command))


# ─── Conexión via SSH (paramiko) ─────────────────────────────────────────────

class MikroTikSSH(MikroTikBase):
    """Conexión SSH directa con paramiko."""

    def __init__(self, host: str, user: str, password: str, port: int = 22):
        super().__init__(host, user, password)
        self.port    = port
        self._client = None

    def connect(self) -> bool:
        if not HAS_SSH:
            err("Módulo 'paramiko' no instalado. Ejecuta: pip install paramiko")
            return False
        try:
            self._client = paramiko.SSHClient()
            self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self._client.connect(
                self.host,
                port=self.port,
                username=self.user,
                password=self.password,
                timeout=10,
            )
            ok(f"Conectado via SSH a {self.host}:{self.port}")
            return True
        except Exception as e:
            err(f"No se pudo conectar via SSH: {e}")
            return False

    def disconnect(self) -> None:
        if self._client:
            self._client.close()
            info("Conexión SSH cerrada.")

    def run(self, command: str) -> str:
        """Ejecuta un comando RouterOS y devuelve la salida."""
        if not self._client:
            err("Sin conexión SSH activa.")
            return ""
        try:
            _, stdout, stderr = self._client.exec_command(command, timeout=15)
            output = stdout.read().decode("utf-8", errors="replace")
            error  = stderr.read().decode("utf-8", errors="replace")
            return output or error
        except Exception as e:
            err(f"Error al ejecutar comando SSH: {e}")
            return ""


# ─── Conexión via Netmiko ────────────────────────────────────────────────────

class MikroTikNetmiko(MikroTikBase):
    """Conexión SSH usando Netmiko (RouterOS driver)."""

    def __init__(self, host: str, user: str, password: str, port: int = 22):
        super().__init__(host, user, password)
        self.port    = port
        self._client = None

    def connect(self) -> bool:
        if not HAS_NETMIKO:
            err("Módulo 'netmiko' no instalado. Ejecuta: pip install netmiko")
            return False
        try:
            self._client = ConnectHandler(
                device_type="mikrotik_routeros",
                host=self.host,
                port=self.port,
                username=self.user,
                password=self.password,
            )
            ok(f"Conectado via Netmiko (SSH) a {self.host}:{self.port}")
            return True
        except Exception as e:
            err(f"No se pudo conectar via Netmiko: {e}")
            return False

    def disconnect(self) -> None:
        if self._client:
            self._client.disconnect()
            info("Conexión Netmiko cerrada.")

    def run(self, command: str) -> str:
        if not self._client:
            err("Sin conexión Netmiko activa.")
            return ""
        try:
            return self._client.send_command(command)
        except Exception as e:
            err(f"Error al ejecutar comando Netmiko: {e}")
            return ""


# ─── Módulos de administración ───────────────────────────────────────────────

class MikroTikAdmin:
    """Capa de alto nivel para tareas de administración MikroTik."""

    def __init__(self, conn: MikroTikBase):
        self.conn    = conn
        self.is_api  = isinstance(conn, MikroTikAPI)

    # ── Recursos del sistema ──────────────────────────────────────────────

    def show_resources(self) -> None:
        header("Recursos del Sistema")
        if self.is_api:
            data = self.conn.get_resource("/system/resource")
            if data:
                r = data[0]
                fields = [
                    ("Versión RouterOS",  r.get("version", "N/A")),
                    ("Arquitectura",      r.get("architecture-name", "N/A")),
                    ("Plataforma",        r.get("platform", "N/A")),
                    ("Board",             r.get("board-name", "N/A")),
                    ("CPU",               r.get("cpu", "N/A")),
                    ("CPU Carga",         r.get("cpu-load", "N/A") + "%"),
                    ("Frec. CPU",         r.get("cpu-frequency", "N/A") + " MHz"),
                    ("RAM Total",         _bytes_hr(int(r.get("total-memory", 0)))),
                    ("RAM Libre",         _bytes_hr(int(r.get("free-memory", 0)))),
                    ("HDD Total",         _bytes_hr(int(r.get("total-hdd-space", 0)))),
                    ("HDD Libre",         _bytes_hr(int(r.get("free-hdd-space", 0)))),
                    ("Uptime",            r.get("uptime", "N/A")),
                ]
                for label, value in fields:
                    print(f"  {c(label + ':', Color.CYAN):<35} {value}")
        else:
            output = self.conn.run("/system resource print")
            print(output)

    def show_identity(self) -> None:
        header("Identidad del Router")
        if self.is_api:
            data = self.conn.get_resource("/system/identity")
            if data:
                print(f"  {c('Nombre:', Color.CYAN):<35} {data[0].get('name', 'N/A')}")
        else:
            output = self.conn.run("/system identity print")
            print(output)

    # ── Interfaces ────────────────────────────────────────────────────────

    def show_interfaces(self) -> None:
        header("Interfaces de Red")
        if self.is_api:
            ifaces = self.conn.get_resource("/interface")
            if not ifaces:
                warn("Sin interfaces encontradas.")
                return
            fmt = "  {:<20} {:<12} {:<15} {:<10} {}"
            print(c(fmt.format("Nombre", "Tipo", "MAC Address", "MTU", "Estado"), Color.BOLD))
            print("  " + "─" * 72)
            for i in ifaces:
                status = c("activo", Color.GREEN) if i.get("running") == "true" else c("inactivo", Color.RED)
                disabled = c(" [DIS]", Color.YELLOW) if i.get("disabled") == "true" else ""
                print(fmt.format(
                    i.get("name", ""),
                    i.get("type", ""),
                    i.get("mac-address", "N/A"),
                    i.get("mtu", ""),
                    status + disabled,
                ))
        else:
            print(self.conn.run("/interface print"))

    def show_ip_addresses(self) -> None:
        header("Direcciones IP")
        if self.is_api:
            addresses = self.conn.get_resource("/ip/address")
            if not addresses:
                warn("Sin direcciones IP configuradas.")
                return
            fmt = "  {:<20} {:<20} {:<20} {}"
            print(c(fmt.format("Dirección", "Red", "Interfaz", "Estado"), Color.BOLD))
            print("  " + "─" * 65)
            for a in addresses:
                status = c("activa", Color.GREEN) if a.get("disabled") != "true" else c("deshabilitada", Color.RED)
                print(fmt.format(
                    a.get("address", ""),
                    a.get("network", ""),
                    a.get("interface", ""),
                    status,
                ))
        else:
            print(self.conn.run("/ip address print"))

    # ── Rutas ─────────────────────────────────────────────────────────────

    def show_routes(self) -> None:
        header("Tabla de Rutas")
        if self.is_api:
            routes = self.conn.get_resource("/ip/route")
            if not routes:
                warn("Sin rutas encontradas.")
                return
            fmt = "  {:<20} {:<20} {:<15} {:<6} {}"
            print(c(fmt.format("Destino", "Gateway", "Interfaz", "Dist.", "Estado"), Color.BOLD))
            print("  " + "─" * 75)
            for r in routes:
                if r.get("active") == "true":
                    status = c("activa", Color.GREEN)
                elif r.get("disabled") == "true":
                    status = c("deshabilitada", Color.RED)
                else:
                    status = c("inactiva", Color.YELLOW)
                print(fmt.format(
                    r.get("dst-address", ""),
                    r.get("gateway", ""),
                    r.get("gateway-status", ""),
                    r.get("distance", ""),
                    status,
                ))
        else:
            print(self.conn.run("/ip route print"))

    # ── Firewall ──────────────────────────────────────────────────────────

    def show_firewall_filter(self) -> None:
        header("Reglas de Firewall - Filter")
        if self.is_api:
            rules = self.conn.get_resource("/ip/firewall/filter")
            if not rules:
                warn("Sin reglas de filtro.")
                return
            for idx, r in enumerate(rules):
                disabled = c(" [DIS]", Color.YELLOW) if r.get("disabled") == "true" else ""
                action_color = Color.GREEN if r.get("action") == "accept" else Color.RED
                print(
                    f"  {c(str(idx), Color.BOLD):<8}"
                    f"chain={r.get('chain',''):<12}"
                    f"action={c(r.get('action',''), action_color):<20}"
                    f"proto={r.get('protocol','any'):<8}"
                    f"src={r.get('src-address','any'):<20}"
                    f"dst={r.get('dst-address','any')}"
                    + disabled
                )
        else:
            print(self.conn.run("/ip firewall filter print"))

    def show_firewall_nat(self) -> None:
        header("Reglas de Firewall - NAT")
        if self.is_api:
            rules = self.conn.get_resource("/ip/firewall/nat")
            if not rules:
                warn("Sin reglas NAT.")
                return
            for idx, r in enumerate(rules):
                disabled = c(" [DIS]", Color.YELLOW) if r.get("disabled") == "true" else ""
                print(
                    f"  {c(str(idx), Color.BOLD):<8}"
                    f"chain={r.get('chain',''):<15}"
                    f"action={r.get('action',''):<20}"
                    f"src={r.get('src-address','any'):<20}"
                    f"to-addr={r.get('to-addresses','')}"
                    + disabled
                )
        else:
            print(self.conn.run("/ip firewall nat print"))

    def show_connections(self) -> None:
        header("Conexiones Activas")
        if self.is_api:
            conns = self.conn.get_resource("/ip/firewall/connection")
            total = len(conns)
            info(f"Total de conexiones activas: {total}")
            if total == 0:
                return
            # Muestra las primeras 20
            print()
            fmt = "  {:<10} {:<22} {:<22} {:<10} {}"
            print(c(fmt.format("Proto", "Origen", "Destino", "Estado", "Timeout"), Color.BOLD))
            print("  " + "─" * 80)
            for conn in conns[:20]:
                print(fmt.format(
                    conn.get("protocol", ""),
                    conn.get("orig-src-address", ""),
                    conn.get("orig-dst-address", ""),
                    conn.get("tcp-state", conn.get("connection-state", "")),
                    conn.get("timeout", ""),
                ))
            if total > 20:
                warn(f"Mostrando 20 de {total} conexiones.")
        else:
            print(self.conn.run("/ip firewall connection print count-only"))
            print(self.conn.run("/ip firewall connection print"))

    # ── Usuarios ──────────────────────────────────────────────────────────

    def show_users(self) -> None:
        header("Usuarios del Router")
        if self.is_api:
            users = self.conn.get_resource("/user")
            if not users:
                warn("Sin usuarios.")
                return
            fmt = "  {:<20} {:<20} {:<30}"
            print(c(fmt.format("Usuario", "Grupo", "Comentario"), Color.BOLD))
            print("  " + "─" * 60)
            for u in users:
                disabled = c(" [DIS]", Color.YELLOW) if u.get("disabled") == "true" else ""
                print(fmt.format(
                    u.get("name", ""),
                    u.get("group", ""),
                    u.get("comment", ""),
                ) + disabled)
        else:
            print(self.conn.run("/user print"))

    # ── DHCP ─────────────────────────────────────────────────────────────

    def show_dhcp_leases(self) -> None:
        header("DHCP - Leases Activos")
        if self.is_api:
            leases = self.conn.get_resource("/ip/dhcp-server/lease")
            if not leases:
                warn("Sin leases DHCP.")
                return
            fmt = "  {:<18} {:<20} {:<20} {:<15} {}"
            print(c(fmt.format("IP", "MAC", "Hostname", "Estado", "Expira"), Color.BOLD))
            print("  " + "─" * 82)
            for lease in leases:
                status_txt = lease.get("status", "")
                status_col = Color.GREEN if status_txt == "bound" else Color.YELLOW
                print(fmt.format(
                    lease.get("address", ""),
                    lease.get("mac-address", ""),
                    lease.get("host-name", "N/A"),
                    c(status_txt, status_col),
                    lease.get("expires-after", "estático"),
                ))
        else:
            print(self.conn.run("/ip dhcp-server lease print"))

    def show_dhcp_servers(self) -> None:
        header("Servidores DHCP")
        if self.is_api:
            servers = self.conn.get_resource("/ip/dhcp-server")
            if not servers:
                warn("Sin servidores DHCP configurados.")
                return
            for s in servers:
                status = c("activo", Color.GREEN) if s.get("disabled") != "true" else c("deshabilitado", Color.RED)
                print(f"  Nombre: {s.get('name','')}  Interfaz: {s.get('interface','')}  "
                      f"Pool: {s.get('address-pool','')}  Estado: {status}")
        else:
            print(self.conn.run("/ip dhcp-server print"))

    # ── Wireless ──────────────────────────────────────────────────────────

    def show_wireless(self) -> None:
        header("Interfaces Wireless")
        if self.is_api:
            wlans = self.conn.get_resource("/interface/wireless")
            if not wlans:
                warn("Sin interfaces wireless.")
                return
            for w in wlans:
                print(f"  Nombre:  {w.get('name','')}")
                print(f"  SSID:    {w.get('ssid','N/A')}")
                print(f"  Banda:   {w.get('band','N/A')}")
                print(f"  Modo:    {w.get('mode','N/A')}")
                print(f"  MAC:     {w.get('mac-address','N/A')}")
                print(f"  Canal:   {w.get('frequency','N/A')} MHz")
                print()
        else:
            print(self.conn.run("/interface wireless print"))

    def show_wireless_clients(self) -> None:
        header("Clientes Wireless Conectados")
        if self.is_api:
            clients = self.conn.get_resource("/interface/wireless/registration-table")
            if not clients:
                warn("Sin clientes wireless conectados.")
                return
            fmt = "  {:<20} {:<20} {:<10} {:<10} {:<10} {}"
            print(c(fmt.format("MAC", "Interfaz", "Señal", "Tx (Mbps)", "Rx (Mbps)", "Uptime"), Color.BOLD))
            print("  " + "─" * 80)
            for cl in clients:
                signal = int(cl.get("signal-strength", "0").split("@")[0]) if cl.get("signal-strength") else 0
                sig_color = Color.GREEN if signal > -65 else (Color.YELLOW if signal > -80 else Color.RED)
                print(fmt.format(
                    cl.get("mac-address", ""),
                    cl.get("interface", ""),
                    c(f"{signal} dBm", sig_color),
                    cl.get("tx-rate", ""),
                    cl.get("rx-rate", ""),
                    cl.get("uptime", ""),
                ))
        else:
            print(self.conn.run("/interface wireless registration-table print"))

    # ── Logs ─────────────────────────────────────────────────────────────

    def show_logs(self, lines: int = 30) -> None:
        header(f"Últimas {lines} Entradas del Log")
        if self.is_api:
            logs = self.conn.get_resource("/log")
            entries = logs[-lines:] if len(logs) > lines else logs
            for entry in entries:
                topics = entry.get("topics", "")
                msg    = entry.get("message", "")
                time_  = entry.get("time", "")
                if "error" in topics or "critical" in topics:
                    color = Color.RED
                elif "warning" in topics:
                    color = Color.YELLOW
                else:
                    color = Color.RESET
                print(f"  {c(time_, Color.CYAN):<25} {c(topics, color):<20} {msg}")
        else:
            print(self.conn.run("/log print count-only"))
            print(self.conn.run(f"/log print without-paging where count={lines}"))

    # ── Backup ───────────────────────────────────────────────────────────

    def create_backup(self, name: Optional[str] = None) -> None:
        header("Crear Backup de Configuración")
        if not name:
            name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        if self.is_api:
            result = self.conn.run_command("/system/backup", "save", name=name)
            ok(f"Backup '{name}.backup' creado en el router.")
            info("Descarga el archivo desde Winbox o via FTP/SCP.")
        else:
            output = self.conn.run(f"/system backup save name={name}")
            print(output)
            ok(f"Backup '{name}.backup' iniciado.")

    def export_config(self) -> None:
        header("Exportar Configuración (texto plano)")
        if self.is_api:
            warn("La exportación completa requiere conexión SSH.")
        else:
            output = self.conn.run("/export")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename  = f"mikrotik_export_{timestamp}.rsc"
            with open(filename, "w") as f:
                f.write(output)
            ok(f"Configuración exportada a: {filename}")
            info(f"Líneas guardadas: {len(output.splitlines())}")

    # ── Agregar Dirección IP ──────────────────────────────────────────────

    def add_ip_address(self) -> None:
        header("Agregar Dirección IP")
        address   = input(c("  Dirección (ej. 192.168.10.1/24): ", Color.CYAN)).strip()
        interface = input(c("  Interfaz (ej. ether1): ", Color.CYAN)).strip()
        comment   = input(c("  Comentario (opcional): ", Color.CYAN)).strip()

        if not address or not interface:
            err("Dirección e interfaz son obligatorios.")
            return

        if self.is_api:
            params = {"address": address, "interface": interface}
            if comment:
                params["comment"] = comment
            self.conn.run_command("/ip/address", "add", **params)
            ok(f"Dirección {address} agregada en {interface}.")
        else:
            cmd = f"/ip address add address={address} interface={interface}"
            if comment:
                cmd += f" comment=\"{comment}\""
            output = self.conn.run(cmd)
            print(output)
            ok("Comando ejecutado.")

    # ── Agregar Ruta Estática ─────────────────────────────────────────────

    def add_static_route(self) -> None:
        header("Agregar Ruta Estática")
        dst     = input(c("  Destino (ej. 10.0.0.0/8): ", Color.CYAN)).strip()
        gateway = input(c("  Gateway (ej. 192.168.1.1): ", Color.CYAN)).strip()
        comment = input(c("  Comentario (opcional): ", Color.CYAN)).strip()

        if not dst or not gateway:
            err("Destino y gateway son obligatorios.")
            return

        if self.is_api:
            params = {"dst-address": dst, "gateway": gateway}
            if comment:
                params["comment"] = comment
            self.conn.run_command("/ip/route", "add", **params)
            ok(f"Ruta {dst} via {gateway} agregada.")
        else:
            cmd = f"/ip route add dst-address={dst} gateway={gateway}"
            if comment:
                cmd += f" comment=\"{comment}\""
            output = self.conn.run(cmd)
            print(output)
            ok("Comando ejecutado.")

    # ── Ejecutar comando libre ─────────────────────────────────────────────

    def run_custom_command(self) -> None:
        header("Ejecutar Comando Personalizado")
        if self.is_api:
            warn("Para comandos personalizados se recomienda usar SSH.")
        cmd = input(c("  Comando RouterOS: ", Color.CYAN)).strip()
        if cmd:
            if self.is_api:
                result = self.conn.run(cmd)
            else:
                result = self.conn.run(cmd)
            print()
            print(result)


# ─── Utilidades ──────────────────────────────────────────────────────────────

def _bytes_hr(n: int) -> str:
    """Convierte bytes a formato legible."""
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n //= 1024
    return f"{n:.1f} TB"


# ─── Menú interactivo ────────────────────────────────────────────────────────

MENU_OPTIONS = [
    ("1",  "Recursos del sistema",           "show_resources"),
    ("2",  "Identidad del router",           "show_identity"),
    ("3",  "Interfaces de red",              "show_interfaces"),
    ("4",  "Direcciones IP",                 "show_ip_addresses"),
    ("5",  "Tabla de rutas",                 "show_routes"),
    ("6",  "Firewall - Filter",              "show_firewall_filter"),
    ("7",  "Firewall - NAT",                 "show_firewall_nat"),
    ("8",  "Conexiones activas",             "show_connections"),
    ("9",  "Usuarios del router",            "show_users"),
    ("10", "DHCP - Servidores",              "show_dhcp_servers"),
    ("11", "DHCP - Leases",                  "show_dhcp_leases"),
    ("12", "Interfaces Wireless",            "show_wireless"),
    ("13", "Clientes Wireless",              "show_wireless_clients"),
    ("14", "Logs del sistema",               "show_logs"),
    ("15", "Agregar dirección IP",           "add_ip_address"),
    ("16", "Agregar ruta estática",          "add_static_route"),
    ("17", "Crear backup",                   "create_backup"),
    ("18", "Exportar configuración (.rsc)",  "export_config"),
    ("19", "Ejecutar comando personalizado", "run_custom_command"),
]

def print_menu() -> None:
    print("\n" + c("═" * 60, Color.CYAN))
    print(c("       MIKROTIK ADMIN — Menú Principal", Color.BOLD + Color.CYAN))
    print(c("═" * 60, Color.CYAN))
    col = 0
    for key, label, _ in MENU_OPTIONS:
        print(f"  {c(key.rjust(3) + '.', Color.YELLOW)} {label:<35}", end="")
        col += 1
        if col % 2 == 0:
            print()
    if col % 2 != 0:
        print()
    print(c("\n   0. Salir\n", Color.RED))

def interactive_loop(admin: MikroTikAdmin) -> None:
    """Bucle principal del menú."""
    dispatch = {key: method for key, _, method in MENU_OPTIONS}
    while True:
        print_menu()
        choice = input(c("  Selecciona una opción: ", Color.BOLD)).strip()
        if choice == "0":
            ok("Cerrando sesión.")
            break
        if choice not in dispatch:
            warn("Opción no válida.")
            continue
        method_name = dispatch[choice]
        method = getattr(admin, method_name, None)
        if method:
            try:
                method()
            except KeyboardInterrupt:
                print()
                warn("Operación cancelada.")
        input(c("\n  Presiona Enter para continuar...", Color.CYAN))


# ─── Punto de entrada ────────────────────────────────────────────────────────

def build_connection(host: str, user: str, password: str, method: str) -> Optional[MikroTikBase]:
    """Instancia y conecta según el método elegido."""
    if method == "api":
        conn = MikroTikAPI(host, user, password)
    elif method == "netmiko":
        conn = MikroTikNetmiko(host, user, password)
    else:  # ssh
        conn = MikroTikSSH(host, user, password)

    if conn.connect():
        return conn
    return None

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Administración de routers MikroTik via API o SSH",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python mikrotik_admin.py
  python mikrotik_admin.py --host 192.168.88.1 --user admin --method api
  python mikrotik_admin.py --host 192.168.88.1 --user admin --method ssh
  python mikrotik_admin.py --host 192.168.88.1 --user admin --method netmiko
        """,
    )
    parser.add_argument("--host",     "-H", default=None, help="IP o hostname del router")
    parser.add_argument("--user",     "-u", default=None, help="Usuario de RouterOS")
    parser.add_argument("--password", "-p", default=None, help="Contraseña (no recomendado en CLI)")
    parser.add_argument("--method",   "-m",
                        choices=["api", "ssh", "netmiko"], default="api",
                        help="Método de conexión (default: api)")
    args = parser.parse_args()

    # Banner
    print(c("""
  ╔══════════════════════════════════════════════════╗
  ║         MikroTik Admin Script — Python           ║
  ║         Conexión via RouterOS API / SSH          ║
  ╚══════════════════════════════════════════════════╝
""", Color.CYAN + Color.BOLD))

    # Verificar dependencias
    info("Verificando dependencias:")
    print(f"  routeros-api : {c('disponible', Color.GREEN) if HAS_API else c('no instalado', Color.YELLOW)}")
    print(f"  paramiko     : {c('disponible', Color.GREEN) if HAS_SSH else c('no instalado', Color.YELLOW)}")
    print(f"  netmiko      : {c('disponible', Color.GREEN) if HAS_NETMIKO else c('no instalado', Color.YELLOW)}")

    # Parámetros de conexión
    host     = args.host     or input(c("\n  Host del router (IP/hostname): ", Color.CYAN)).strip()
    user     = args.user     or input(c("  Usuario: ", Color.CYAN)).strip()
    password = args.password or getpass.getpass(c("  Contraseña: ", Color.CYAN))
    method   = args.method

    if not host or not user:
        err("Host y usuario son requeridos.")
        sys.exit(1)

    info(f"Conectando a {host} via {method.upper()}...")
    conn = build_connection(host, user, password, method)
    if not conn:
        err("No se pudo establecer conexión. Verifica host, credenciales y método.")
        sys.exit(1)

    admin = MikroTikAdmin(conn)
    try:
        interactive_loop(admin)
    except KeyboardInterrupt:
        print()
        warn("Interrumpido por el usuario.")
    finally:
        conn.disconnect()


if __name__ == "__main__":
    main()
