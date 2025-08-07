#!/usr/bin/env python3
# Herramienta integral para revisar, auditar y cambiar configuraciones de seguridad en Linux.
# Cubre: firewall (ufw/nft/iptables), SELinux/AppArmor, escaneos (lynis/clamav/chkrootkit),
# actualizaciones de seguridad (unattended-upgrades/dnf-automatic/yum-cron),
# y control de acceso (sudoers, login.defs, PAM pwquality).
#
# Requisitos: ejecutar como root.

import os
import re
import shlex
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

# ------------- Utilidades básicas -------------

def is_root():
    return os.geteuid() == 0

def run(cmd, check=False, capture=False):
    """Ejecuta un comando. Si capture=True, devuelve stdout como str."""
    if isinstance(cmd, str):
        cmd = shlex.split(cmd)
    kwargs = {}
    if capture:
        kwargs["stdout"] = subprocess.PIPE
        kwargs["stderr"] = subprocess.STDOUT
        kwargs["text"] = True
    try:
        proc = subprocess.run(cmd, check=check, **kwargs)
        return proc.stdout.strip() if capture else proc.returncode
    except FileNotFoundError:
        return None

def which(bin_name):
    return shutil.which(bin_name)

def backup_file(path: str):
    """Crea backup con timestamp si el archivo existe, devuelve ruta del backup o None."""
    p = Path(path)
    if not p.exists():
        return None
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    bkp = Path(f"{path}.bak-{ts}")
    shutil.copy2(p, bkp)
    return str(bkp)

def detect_distro():
    """Devuelve ('debian'|'rhel'|'unknown', ID_LIKE/ID)"""
    info = {}
    try:
        with open("/etc/os-release") as f:
            for line in f:
                k, _, v = line.partition("=")
                info[k.strip()] = v.strip().strip('"')
    except FileNotFoundError:
        return "unknown", "unknown"

    id_ = info.get("ID", "")
    like = info.get("ID_LIKE", "")

    if any(x in (id_, like) for x in ["debian", "ubuntu"]):
        return "debian", (like or id_)
    if any(x in (id_, like) for x in ["rhel", "fedora", "centos", "rocky", "ol", "almalinux"]):
        return "rhel", (like or id_)
    return "unknown", (like or id_)

def ensure_pkg(pkgs):
    """Instala paquetes según la distro."""
    distro, _ = detect_distro()
    pkgs = [p for p in pkgs if p]  # limpia None
    if not pkgs:
        return
    if distro == "debian":
        run(["apt-get", "update"])
        run(["apt-get", "-y", "install", *pkgs], check=True)
    elif distro == "rhel":
        # Prefiere dnf; fallback a yum
        installer = which("dnf") or which("yum")
        if not installer:
            print("No se encontró dnf/yum para instalar paquetes.")
            return
        run([installer, "-y", "install", *pkgs], check=True)
    else:
        print(f"Distro no reconocida para instalación automática: {pkgs}")

def press_enter():
    input("\nPresiona ENTER para continuar...")

# ------------- FIREWALL -------------

def firewall_status():
    """Detecta y muestra estado de UFW/NFTABLES/IPTABLES."""
    print("\n[ FIREWALL ]")
    if which("ufw"):
        out = run("ufw status", capture=True)
        print("UFW:", out or "No disponible")
    if which("nft"):
        out = run("nft list ruleset", capture=True)
        print("\nNFTABLES ruleset:")
        print(out if out else "(vacío o nft no disponible)")
    if which("iptables"):
        out = run("iptables -L -n -v", capture=True)
        print("\nIPTABLES (filter):")
        print(out if out else "(vacío o iptables no disponible)")

def firewall_manage():
    """Menú básico para UFW/NFT."""
    while True:
        print("""
--- Firewall ---
1) Mostrar estado (ufw/nft/iptables)
2) UFW: enable
3) UFW: disable
4) UFW: permitir puerto (ej. 22/tcp)
5) UFW: denegar puerto
6) NFT: listar ruleset
7) Volver
""")
        op = input("Opción: ").strip()
        if op == "1":
            firewall_status()
            press_enter()
        elif op == "2":
            if not which("ufw"):
                ensure_pkg(["ufw"])
            run("ufw enable")
        elif op == "3":
            run("ufw disable")
        elif op == "4":
            port = input("Especifica puerto/proto (ej. 22/tcp): ").strip()
            run(f"ufw allow {port}")
        elif op == "5":
            port = input("Especifica puerto/proto (ej. 23/tcp): ").strip()
            run(f"ufw deny {port}")
        elif op == "6":
            print(run("nft list ruleset", capture=True) or "nft no disponible")
            press_enter()
        elif op == "7":
            break
        else:
            print("Opción inválida")

# ------------- SELinux / AppArmor -------------

def mac_status():
    """Muestra estado de SELinux/AppArmor si existen."""
    print("\n[ MAC (SELinux/AppArmor) ]")
    if which("getenforce"):
        ge = run("getenforce", capture=True)
        print("SELinux getenforce:", ge)
    if which("sestatus"):
        print(run("sestatus", capture=True) or "")
    if which("aa-status"):
        print(run("aa-status", capture=True) or "")
    if which("apparmor_status"):
        print(run("apparmor_status", capture=True) or "")

def mac_manage():
    """Cambios básicos: SELinux (temporal) y AppArmor (enforce/complain)."""
    while True:
        print("""
--- SELinux / AppArmor ---
1) Mostrar estado
2) SELinux: setenforce Enforcing
3) SELinux: setenforce Permissive
4) SELinux: cambiar /etc/selinux/config (enforcing|permissive|disabled)
5) AppArmor: listar perfiles
6) AppArmor: poner perfil en enforce
7) AppArmor: poner perfil en complain
8) Volver
""")
        op = input("Opción: ").strip()
        if op == "1":
            mac_status()
            press_enter()
        elif op == "2":
            run("setenforce 1")
        elif op == "3":
            run("setenforce 0")
        elif op == "4":
            mode = input("Nuevo modo (enforcing|permissive|disabled): ").strip().lower()
            cfg = "/etc/selinux/config"
            bkp = backup_file(cfg)
            if bkp:
                print(f"Backup creado: {bkp}")
            try:
                text = Path(cfg).read_text()
                text = re.sub(r"^SELINUX=.*$", f"SELINUX={mode}", text, flags=re.M)
                Path(cfg).write_text(text)
                print(f"Actualizado {cfg}. (Requiere reinicio para aplicar completamente)")
            except Exception as e:
                print("Error editando config:", e)
        elif op == "5":
            print(run("aa-status", capture=True) or "AppArmor no disponible")
            press_enter()
        elif op == "6":
            profile = input("Perfil a aplicar enforce (ruta o nombre): ").strip()
            if which("aa-enforce"):
                run(["aa-enforce", profile])
            else:
                print("aa-enforce no disponible")
        elif op == "7":
            profile = input("Perfil a aplicar complain (ruta o nombre): ").strip()
            if which("aa-complain"):
                run(["aa-complain", profile])
            else:
                print("aa-complain no disponible")
        elif op == "8":
            break
        else:
            print("Opción inválida")

# ------------- Escaneos (lynis, clamav, chkrootkit) -------------

def scanners_status():
    print("\n[ Escáneres de seguridad ]")
    for bin_ in ["lynis", "clamscan", "freshclam", "chkrootkit"]:
        print(f"- {bin_}: {'OK' if which(bin_) else 'NO ENCONTRADO'}")

def scanners_install():
    distro, _ = detect_distro()
    pkgs = []
    if distro == "debian":
        pkgs = ["lynis", "clamav", "clamav-freshclam", "chkrootkit"]
    elif distro == "rhel":
        # nombres pueden variar según repos habilitados
        pkgs = ["lynis", "clamav", "clamav-update", "chkrootkit"]
    ensure_pkg(pkgs)

def scanners_run():
    while True:
        print("""
--- Escáneres ---
1) Estado/instalación de herramientas
2) Instalar herramientas (lynis/clamav/chkrootkit)
3) Actualizar firmas ClamAV (freshclam)
4) Ejecutar LYNIS (auditoría rápida)
5) Ejecutar ClamAV sobre /home (rápido)
6) Ejecutar chkrootkit
7) Volver
""")
        op = input("Opción: ").strip()
        if op == "1":
            scanners_status()
            press_enter()
        elif op == "2":
            scanners_install()
        elif op == "3":
            if which("freshclam"):
                print(run("freshclam", capture=True))
            else:
                print("freshclam no disponible")
            press_enter()
        elif op == "4":
            if which("lynis"):
                # Auditoría rápida (no interactiva)
                print(run("lynis audit system --quick", capture=True))
            else:
                print("lynis no disponible")
            press_enter()
        elif op == "5":
            if which("clamscan"):
                # Rápido: sin recursivo pesado, pero útil. Cambia a -r si querés completo.
                print(run("clamscan -i /home", capture=True))
            else:
                print("clamscan no disponible")
            press_enter()
        elif op == "6":
            if which("chkrootkit"):
                print(run("chkrootkit", capture=True))
            else:
                print("chkrootkit no disponible")
            press_enter()
        elif op == "7":
            break
        else:
            print("Opción inválida")

# ------------- Actualizaciones de seguridad -------------

def security_updates():
    distro, _ = detect_distro()
    print(f"\n[ Actualizaciones de seguridad ] Distro detectada: {distro}")
    if distro == "debian":
        print("""
Opciones Debian/Ubuntu:
- unattended-upgrades: instala aut. parches de seguridad.
- dpkg-reconfigure unattended-upgrades (asistente).
- systemctl status unattended-upgrades.service
""")
        while True:
            print("""
1) Instalar y habilitar unattended-upgrades
2) Ejecutar reconfiguración (asistente)
3) Ver estado del servicio
4) Volver
""")
            op = input("Opción: ").strip()
            if op == "1":
                ensure_pkg(["unattended-upgrades"])
                # habilitar
                Path("/etc/apt/apt.conf.d/20auto-upgrades").write_text(
                    'APT::Periodic::Update-Package-Lists "1";\nAPT::Periodic::Unattended-Upgrade "1";\n'
                )
                run("systemctl enable --now unattended-upgrades.service")
                print("unattended-upgrades instalado y habilitado.")
            elif op == "2":
                run("dpkg-reconfigure -plow unattended-upgrades")
            elif op == "3":
                print(run("systemctl status unattended-upgrades.service", capture=True))
                press_enter()
            elif op == "4":
                break
            else:
                print("Opción inválida")

    elif distro == "rhel":
        print("""
Opciones RHEL/CentOS/Rocky:
- dnf-automatic (nuevo) o yum-cron (antiguo).
- systemctl enable --now dnf-automatic.timer
""")
        while True:
            print("""
1) Instalar y habilitar dnf-automatic (recomendado)
2) Instalar y habilitar yum-cron (alternativo)
3) Ver estado de dnf-automatic.timer
4) Volver
""")
            op = input("Opción: ").strip()
            if op == "1":
                ensure_pkg(["dnf-automatic"])
                run("systemctl enable --now dnf-automatic.timer")
                print("dnf-automatic habilitado (timer activo).")
            elif op == "2":
                ensure_pkg(["yum-cron"])
                run("systemctl enable --now yum-cron.service")
                print("yum-cron habilitado.")
            elif op == "3":
                print(run("systemctl status dnf-automatic.timer", capture=True))
                press_enter()
            elif op == "4":
                break
            else:
                print("Opción inválida")
    else:
        print("Distro no soportada automáticamente para actualizaciones.")
        press_enter()

# ------------- Control de acceso (sudoers, login.defs, PAM) -------------

SUDOERS_DIR = "/etc/sudoers.d"
SUDOERS_MAIN = "/etc/sudoers"
LOGIN_DEFS = "/etc/login.defs"
PWQUALITY = "/etc/security/pwquality.conf"

def access_status():
    print("\n[ Acceso / Autenticación ]")
    # sudoers
    print(f"- sudoers principal: {SUDOERS_MAIN} {'OK' if Path(SUDOERS_MAIN).exists() else 'NO'}")
    print(f"- includes en {SUDOERS_DIR}:")
    for p in sorted(Path(SUDOERS_DIR).glob("*")):
        if p.is_file():
            print("  -", p)
    # login.defs
    if Path(LOGIN_DEFS).exists():
        txt = Path(LOGIN_DEFS).read_text()
        for key in ["PASS_MAX_DAYS", "PASS_MIN_DAYS", "PASS_MIN_LEN", "PASS_WARN_AGE", "UMASK"]:
            m = re.search(rf"^\s*{key}\s+(\S+)", txt, flags=re.M)
            if m:
                print(f"  {key} = {m.group(1)}")
    # PAM pwquality
    if Path(PWQUALITY).exists():
        print(f"- pwquality: {PWQUALITY}")
        print("  (ej. minlen/dcredit/ucredit/lcredit/ocredit/difok)")

def sudoers_manage():
    while True:
        print(f"""
--- SUDOERS ---
1) Agregar usuario a sudo (Debian) o wheel (RHEL)
2) Crear regla en {SUDOERS_DIR}/USUARIO (NOPASSWD opcional)
3) Validar sintaxis con visudo
4) Volver
""")
        op = input("Opción: ").strip()
        distro, _ = detect_distro()
        if op == "1":
            user = input("Usuario: ").strip()
            group = "sudo" if distro == "debian" else "wheel"
            run(["usermod", "-aG", group, user])
            print(f"Usuario {user} agregado al grupo {group}.")
        elif op == "2":
            user = input("Usuario: ").strip()
            nop = input("¿NOPASSWD? (s/n): ").strip().lower().startswith("s")
            entry = f"{user} ALL=(ALL) {'NOPASSWD:' if nop else ''}ALL\n"
            Path(SUDOERS_DIR).mkdir(parents=True, exist_ok=True)
            dest = f"{SUDOERS_DIR}/{user}"
            bkp = backup_file(dest)
            if bkp:
                print(f"Backup: {bkp}")
            Path(dest).write_text(entry)
            # validar
            rc = run(["visudo", "-cf", dest])
            if rc == 0:
                print(f"Regla escrita en {dest} y validada.")
            else:
                print("Error de sintaxis en sudoers; revisa el archivo.")
        elif op == "3":
            rc = run(["visudo", "-c"])
            print("visudo -c exit code:", rc)
        elif op == "4":
            break
        else:
            print("Opción inválida")

def login_defs_manage():
    if not Path(LOGIN_DEFS).exists():
        print(f"No existe {LOGIN_DEFS}")
        return
    params = {
        "PASS_MAX_DAYS": None,
        "PASS_MIN_DAYS": None,
        "PASS_MIN_LEN": None,
        "PASS_WARN_AGE": None,
        "UMASK": None,
    }
    print("\n--- login.defs --- valores actuales ---")
    txt = Path(LOGIN_DEFS).read_text()
    for k in params:
        m = re.search(rf"^\s*{k}\s+(\S+)", txt, flags=re.M)
        print(f"{k} = {m.group(1) if m else '(no definido)'}")

    print("\nDeja en blanco para no cambiar:")
    for k in params:
        val = input(f"{k}: ").strip()
        if val:
            params[k] = val

    bkp = backup_file(LOGIN_DEFS)
    if bkp:
        print(f"Backup: {bkp}")
    # aplica cambios
    new = txt
    for k, v in params.items():
        if v is None:
            continue
        if re.search(rf"^\s*{k}\s+\S+", new, flags=re.M):
            new = re.sub(rf"^\s*{k}\s+\S+", f"{k} {v}", new, flags=re.M)
        else:
            new += f"\n{k} {v}\n"
    Path(LOGIN_DEFS).write_text(new)
    print("login.defs actualizado.")

def pam_pwquality_manage():
    if not Path(PWQUALITY).exists():
        print(f"No existe {PWQUALITY}. Instalando módulo si es necesario...")
        distro, _ = detect_distro()
        if distro == "debian":
            ensure_pkg(["libpam-pwquality"])
        elif distro == "rhel":
            ensure_pkg(["pam"])
        Path(PWQUALITY).touch(exist_ok=True)

    print(f"\n--- {PWQUALITY} ---")
    txt = Path(PWQUALITY).read_text()
    # Muestra valores típicos si existen
    for key in ["minlen", "dcredit", "ucredit", "lcredit", "ocredit", "difok", "retry"]:
        m = re.search(rf"^\s*{key}\s*=\s*(-?\d+)", txt, flags=re.M)
        print(f"{key} = {m.group(1) if m else '(no definido)'}")

    print("\nDeja en blanco para no cambiar (usa enter). Ejemplos: minlen=12, dcredit=-1 (requiere dígito)")
    changes = {}
    for key in ["minlen", "dcredit", "ucredit", "lcredit", "ocredit", "difok", "retry"]:
        val = input(f"{key}=: ").strip()
        if val:
            changes[key] = val

    if not changes:
        print("Sin cambios.")
        return

    bkp = backup_file(PWQUALITY)
    if bkp:
        print(f"Backup: {bkp}")

    # Aplica cambios con reemplazo o append
    lines = txt.splitlines()
    for k, v in changes.items():
        replaced = False
        for i, line in enumerate(lines):
            if re.match(rf"^\s*{k}\s*=", line):
                lines[i] = f"{k} = {v}"
                replaced = True
                break
        if not replaced:
            lines.append(f"{k} = {v}")
    Path(PWQUALITY).write_text("\n".join(lines) + "\n")
    print("pwquality actualizado. Cambios aplican en próximos logins/cambios de contraseña.")

def access_manage():
    while True:
        print("""
--- Control de Acceso ---
1) Ver estado (sudoers, login.defs, pwquality)
2) Gestionar sudoers
3) Editar parámetros de /etc/login.defs
4) Configurar políticas en /etc/security/pwquality.conf (PAM)
5) Volver
""")
        op = input("Opción: ").strip()
        if op == "1":
            access_status()
            press_enter()
        elif op == "2":
            sudoers_manage()
        elif op == "3":
            login_defs_manage()
        elif op == "4":
            pam_pwquality_manage()
        elif op == "5":
            break
        else:
            print("Opción inválida")

# ------------- Auditoría rápida -------------

def quick_audit():
    print("\n=== AUDITORÍA RÁPIDA ===")
    firewall_status()
    mac_status()
    scanners_status()
    access_status()
    print("\nSugerencias:")
    print("- Habilitar actualizaciones automáticas de seguridad.")
    print("- Aplicar políticas de contraseña (pwquality/login.defs).")
    print("- Revisar que el firewall tenga reglas mínimas.")
    print("- Mantener SELinux/AppArmor en enforcing si es posible.")
    press_enter()

# ------------- Menú principal -------------

def main_menu():
    if not is_root():
        print("⚠️  Este script debe ejecutarse como root.")
        return
    while True:
        print("""
========== Seguridad Linux ==========
1) Auditoría rápida (lectura)
2) Firewall (ufw/nft/iptables)
3) SELinux / AppArmor (MAC)
4) Escaneo de vulnerabilidades (lynis/clamav/chkrootkit)
5) Actualizaciones de seguridad (unattended/dnf-automatic/yum-cron)
6) Control de acceso (sudoers, login.defs, PAM)
7) Salir
""")
        op = input("Elige una opción: ").strip()
        if op == "1":
            quick_audit()
        elif op == "2":
            firewall_manage()
        elif op == "3":
            mac_manage()
        elif op == "4":
            scanners_run()
        elif op == "5":
            security_updates()
        elif op == "6":
            access_manage()
        elif op == "7":
            print("Saliendo...")
            break
        else:
            print("Opción inválida.")

if __name__ == "__main__":
    main_menu()
