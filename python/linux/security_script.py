#!/usr/bin/env python3
# ↑ Shebang: permite ejecutar el archivo directamente con Python 3 (./security_admin.py)

# ============================
#  MÓDULOS ESTÁNDAR DE PYTHON
# ============================

import os                  # ↑ Funciones del sistema operativo: UID efectivo, paths, permisos
import re                  # ↑ Expresiones regulares para buscar/reemplazar en archivos de config
import shlex               # ↑ Divide strings en listas seguras para subprocess (manejo de comillas)
import shutil              # ↑ Utilidades: which(), copy2() para backups
import subprocess          # ↑ Ejecutar comandos del sistema de forma controlada
from datetime import datetime  # ↑ Timestamps legibles para backups
from pathlib import Path       # ↑ Manejo de rutas de forma elegante y segura

# =========================================
#  FUNCIONES DE UTILIDAD (BASE / GENERALES)
# =========================================

def is_root():
    # Devuelve True si el script corre como root (UID 0)
    return os.geteuid() == 0

def run(cmd, check=False, capture=False):
    # Ejecuta un comando del sistema.
    # - cmd: string o lista; si es string lo partimos con shlex.split para seguridad.
    # - check: si True, lanza excepción si el comando devuelve código ≠ 0.
    # - capture: si True, devuelve stdout como string (también captura stderr).
    if isinstance(cmd, str):            # Si nos pasaron string...
        cmd = shlex.split(cmd)          # ...lo convertimos a lista segura (respeta comillas).
    kwargs = {}                         # Diccionario de argumentos adicionales para subprocess.run
    if capture:                         # Si queremos capturar salida...
        kwargs["stdout"] = subprocess.PIPE   # Capturamos stdout
        kwargs["stderr"] = subprocess.STDOUT # Enviamos stderr a stdout para tener todo junto
        kwargs["text"] = True                # Decodificar bytes a str (UTF-8 por defecto)
    try:
        proc = subprocess.run(cmd, check=check, **kwargs)  # Ejecutamos el comando
        return proc.stdout.strip() if capture else proc.returncode  # Devolvemos salida o código
    except FileNotFoundError:
        return None                        # Si el binario/comando no existe, devolvemos None

def which(bin_name):
    # Retorna la ruta del binario si existe en PATH; si no, None.
    return shutil.which(bin_name)

def backup_file(path: str):
    # Crea una copia de seguridad (backup) del archivo con timestamp.
    p = Path(path)                          # Creamos objeto Path del archivo
    if not p.exists():                      # Si no existe el archivo original...
        return None                         # ...no hacemos backup y devolvemos None
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")  # Timestamp legible AAAAMMDD-HHMMSS
    bkp = Path(f"{path}.bak-{ts}")         # Nombre del backup: archivo.bak-AAAAMMDD-HHMMSS
    shutil.copy2(p, bkp)                   # Copiamos preservando metadatos
    return str(bkp)                        # Devolvemos la ruta del backup (string)

def detect_distro():
    # Detecta la familia de distro (debian|rhel|unknown) leyendo /etc/os-release
    info = {}                               # Diccionario para pares clave-valor de os-release
    try:
        with open("/etc/os-release") as f:  # Abrimos el archivo de identificación de la distro
            for line in f:                  # Recorremos cada línea
                k, _, v = line.partition("=")  # Separamos clave = valor
                info[k.strip()] = v.strip().strip('"')  # Guardamos valor sin comillas
    except FileNotFoundError:
        return "unknown", "unknown"         # Si no existe os-release, devolvemos desconocido

    id_ = info.get("ID", "")                # ID (ej: ubuntu, debian, rocky)
    like = info.get("ID_LIKE", "")          # ID_LIKE (ej: debian, rhel)

    # Si ID o ID_LIKE contiene debian/ubuntu -> familia debian
    if any(x in (id_, like) for x in ["debian", "ubuntu"]):
        return "debian", (like or id_)
    # Si contiene rhel/fedora/centos/rocky/etc -> familia rhel
    if any(x in (id_, like) for x in ["rhel", "fedora", "centos", "rocky", "ol", "almalinux"]):
        return "rhel", (like or id_)
    # En otro caso, desconocido
    return "unknown", (like or id_)

def ensure_pkg(pkgs):
    # Instala una lista de paquetes según la distro detectada.
    distro, _ = detect_distro()             # Detectamos la familia de distro
    pkgs = [p for p in pkgs if p]           # Filtramos paquetes vacíos/None
    if not pkgs:                            # Si no hay nada para instalar...
        return                              # ...terminamos
    if distro == "debian":                  # En Debian/Ubuntu...
        run(["apt-get", "update"])          # Actualizamos índices
        run(["apt-get", "-y", "install", *pkgs], check=True)  # Instalamos paquetes
    elif distro == "rhel":                  # En RHEL/Fedora/CentOS/Rocky...
        installer = which("dnf") or which("yum")  # Preferimos dnf; si no, yum
        if not installer:                   # Si no hay ni dnf ni yum...
            print("No se encontró dnf/yum para instalar paquetes.")
            return
        run([installer, "-y", "install", *pkgs], check=True)  # Instalamos
    else:                                   # Si la distro no es conocida...
        print(f"Distro no reconocida para instalación automática: {pkgs}")

def press_enter():
    # Pausa la ejecución hasta que el usuario presione ENTER (útil entre pantallas)
    input("\nPresiona ENTER para continuar...")

# ===========================
#  SECCIÓN: FIREWALL (UFW/NFT/IPTABLES)
# ===========================

def firewall_status():
    # Muestra el estado actual de UFW, nftables y iptables si están disponibles.
    print("\n[ FIREWALL ]")                 # Título de sección
    if which("ufw"):                         # Si existe ufw en el sistema...
        out = run("ufw status", capture=True)  # Ejecutamos 'ufw status' y capturamos salida
        print("UFW:", out or "No disponible")  # Mostramos el resultado o mensaje
    if which("nft"):                         # Si existe nft (nftables)...
        out = run("nft list ruleset", capture=True)  # Listamos el ruleset
        print("\nNFTABLES ruleset:")         # Encabezado
        print(out if out else "(vacío o nft no disponible)")  # Mostramos ruleset o vacío
    if which("iptables"):                    # Si existe iptables...
        out = run("iptables -L -n -v", capture=True)  # Listamos reglas filter con contadores
        print("\nIPTABLES (filter):")        # Encabezado
        print(out if out else "(vacío o iptables no disponible)")  # Mostramos reglas o vacío

def firewall_manage():
    # Menú interactivo básico para manejar UFW y consultar nftables.
    while True:                              # Bucle del menú
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
        op = input("Opción: ").strip()       # Tomamos la opción del usuario
        if op == "1":                         # Opción: ver estado
            firewall_status()                 # Llamamos a la función de estado
            press_enter()                     # Pausa
        elif op == "2":                       # Opción: ufw enable
            if not which("ufw"):              # Si ufw no está instalado...
                ensure_pkg(["ufw"])           # ...lo instalamos
            run("ufw enable")                 # Habilitamos ufw
        elif op == "3":                       # Opción: ufw disable
            run("ufw disable")                # Deshabilitamos ufw
        elif op == "4":                       # Opción: permitir puerto/protocolo
            port = input("Especifica puerto/proto (ej. 22/tcp): ").strip()  # Pedimos puerto
            run(f"ufw allow {port}")          # Permitimos ese puerto
        elif op == "5":                       # Opción: denegar puerto
            port = input("Especifica puerto/proto (ej. 23/tcp): ").strip()  # Pedimos puerto
            run(f"ufw deny {port}")           # Denegamos ese puerto
        elif op == "6":                       # Opción: ver ruleset de nftables
            print(run("nft list ruleset", capture=True) or "nft no disponible")  # Mostramos ruleset
            press_enter()                     # Pausa
        elif op == "7":                       # Opción: volver al menú principal
            break                             # Salimos del bucle
        else:
            print("Opción inválida")          # Opción incorrecta

# ======================================
#  SECCIÓN: MAC (SELinux / AppArmor)
# ======================================

def mac_status():
    # Muestra el estado de SELinux y AppArmor si los binarios están disponibles.
    print("\n[ MAC (SELinux/AppArmor) ]")    # Encabezado
    if which("getenforce"):                   # Si existe getenforce (SELinux)...
        ge = run("getenforce", capture=True)  # Consultamos el modo actual (Enforcing/Permissive)
        print("SELinux getenforce:", ge)      # Mostramos resultado
    if which("sestatus"):                     # Si existe sestatus...
        print(run("sestatus", capture=True) or "")  # Imprimimos su salida
    if which("aa-status"):                    # Si existe aa-status (AppArmor)...
        print(run("aa-status", capture=True) or "") # Mostramos estado
    if which("apparmor_status"):              # Binario alternativo para AppArmor
        print(run("apparmor_status", capture=True) or "")  # Mostramos estado

def mac_manage():
    # Menú de gestión básica de SELinux y AppArmor.
    while True:                               # Bucle del menú
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
        op = input("Opción: ").strip()        # Leemos opción
        if op == "1":                          # Ver estado
            mac_status()                       # Mostramos estado MAC
            press_enter()                      # Pausa
        elif op == "2":                        # SELinux -> Enforcing (temporal)
            run("setenforce 1")                # Cambia a Enforcing hasta reinicio
        elif op == "3":                        # SELinux -> Permissive (temporal)
            run("setenforce 0")                # Cambia a Permissive hasta reinicio
        elif op == "4":                        # Editar config permanente de SELinux
            mode = input("Nuevo modo (enforcing|permissive|disabled): ").strip().lower()  # Pedimos modo
            cfg = "/etc/selinux/config"        # Archivo de configuración
            bkp = backup_file(cfg)             # Hacemos backup previo
            if bkp:
                print(f"Backup creado: {bkp}") # Informamos del backup
            try:
                text = Path(cfg).read_text()   # Leemos contenido actual
                # Reemplazamos la línea SELINUX=...
                text = re.sub(r"^SELINUX=.*$", f"SELINUX={mode}", text, flags=re.M)
                Path(cfg).write_text(text)     # Escribimos de vuelta al archivo
                print(f"Actualizado {cfg}. (Requiere reinicio para aplicar completamente)")  # Aviso
            except Exception as e:
                print("Error editando config:", e)  # En caso de error lo reportamos
        elif op == "5":                        # AppArmor: listar perfiles y estado
            print(run("aa-status", capture=True) or "AppArmor no disponible")  # Mostramos
            press_enter()                      # Pausa
        elif op == "6":                        # AppArmor -> enforce para un perfil
            profile = input("Perfil a aplicar enforce (ruta o nombre): ").strip()  # Pedimos perfil
            if which("aa-enforce"):            # Si herramienta disponible...
                run(["aa-enforce", profile])   # Aplicamos enforce
            else:
                print("aa-enforce no disponible")  # Si no existe, avisamos
        elif op == "7":                        # AppArmor -> complain para un perfil
            profile = input("Perfil a aplicar complain (ruta o nombre): ").strip()  # Pedimos perfil
            if which("aa-complain"):           # Si herramienta disponible...
                run(["aa-complain", profile])  # Aplicamos complain
            else:
                print("aa-complain no disponible")  # Si no existe, avisamos
        elif op == "8":                        # Volver al menú principal
            break                              # Salimos del bucle
        else:
            print("Opción inválida")           # Opción incorrecta

# =======================================================
#  SECCIÓN: ESCÁNERES (Lynis / ClamAV / chkrootkit)
# =======================================================

def scanners_status():
    # Muestra disponibilidad de herramientas de escaneo de seguridad.
    print("\n[ Escáneres de seguridad ]")     # Encabezado
    for bin_ in ["lynis", "clamscan", "freshclam", "chkrootkit"]:  # Lista de binarios a verificar
        print(f"- {bin_}: {'OK' if which(bin_) else 'NO ENCONTRADO'}")  # Estado de cada uno

def scanners_install():
    # Instala escáneres según la distro.
    distro, _ = detect_distro()               # Detectamos distro
    pkgs = []                                  # Lista de paquetes a instalar
    if distro == "debian":                     # Debian/Ubuntu
        pkgs = ["lynis", "clamav", "clamav-freshclam", "chkrootkit"]  # Paquetes comunes
    elif distro == "rhel":                     # RHEL/Fedora/CentOS/Rocky
        pkgs = ["lynis", "clamav", "clamav-update", "chkrootkit"]     # Nombres pueden variar
    ensure_pkg(pkgs)                           # Instalamos los paquetes recopilados

def scanners_run():
    # Menú para gestionar instalación/ejecución de escáneres.
    while True:                                # Bucle del menú
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
        op = input("Opción: ").strip()         # Leemos opción
        if op == "1":                          # Ver estado
            scanners_status()                   # Mostramos estado de herramientas
            press_enter()                       # Pausa
        elif op == "2":                        # Instalar herramientas
            scanners_install()                  # Llamamos a instalación
        elif op == "3":                        # Actualizar firmas ClamAV
            if which("freshclam"):              # Si freshclam existe...
                print(run("freshclam", capture=True))  # Ejecutamos y mostramos salida
            else:
                print("freshclam no disponible")       # Avisamos si no está
            press_enter()                       # Pausa
        elif op == "4":                        # Ejecutar Lynis en modo rápido
            if which("lynis"):                  # Si lynis existe...
                print(run("lynis audit system --quick", capture=True))  # Auditoría y salida
            else:
                print("lynis no disponible")    # Aviso si falta
            press_enter()                       # Pausa
        elif op == "5":                        # ClamAV sobre /home (no recursivo pesado)
            if which("clamscan"):               # Si clamscan existe...
                print(run("clamscan -i /home", capture=True))  # Escaneo simple de /home
            else:
                print("clamscan no disponible") # Avisamos si falta
            press_enter()                       # Pausa
        elif op == "6":                        # Ejecutar chkrootkit
            if which("chkrootkit"):             # Si chkrootkit existe...
                print(run("chkrootkit", capture=True))  # Ejecutamos y mostramos salida
            else:
                print("chkrootkit no disponible")       # Aviso si falta
            press_enter()                       # Pausa
        elif op == "7":                        # Volver al menú principal
            break                               # Salimos del bucle
        else:
            print("Opción inválida")            # Opción incorrecta

# =====================================================
#  SECCIÓN: ACTUALIZACIONES DE SEGURIDAD (AUTO PATCH)
# =====================================================

def security_updates():
    # Configura actualizaciones automáticas según la distro.
    distro, _ = detect_distro()                 # Detectamos la distro
    print(f"\n[ Actualizaciones de seguridad ] Distro detectada: {distro}")  # Encabezado

    if distro == "debian":                      # Debian/Ubuntu
        print("""
Opciones Debian/Ubuntu:
- unattended-upgrades: instala aut. parches de seguridad.
- dpkg-reconfigure unattended-upgrades (asistente).
- systemctl status unattended-upgrades.service
""")
        while True:                             # Menú Debian/Ubuntu
            print("""
1) Instalar y habilitar unattended-upgrades
2) Ejecutar reconfiguración (asistente)
3) Ver estado del servicio
4) Volver
""")
            op = input("Opción: ").strip()      # Tomamos opción
            if op == "1":                       # Instalar y habilitar unattended-upgrades
                ensure_pkg(["unattended-upgrades"])  # Instalamos paquete
                # Creamos/forzamos archivo de auto-updates diario (Update y Unattended)
                Path("/etc/apt/apt.conf.d/20auto-upgrades").write_text(
                    'APT::Periodic::Update-Package-Lists "1";\nAPT::Periodic::Unattended-Upgrade "1";\n'
                )
                run("systemctl enable --now unattended-upgrades.service")  # Habilitamos servicio
                print("unattended-upgrades instalado y habilitado.")       # Informamos
            elif op == "2":                     # Reconfigurar asistente
                run("dpkg-reconfigure -plow unattended-upgrades")          # Lanzamos asistente
            elif op == "3":                     # Ver estado del servicio
                print(run("systemctl status unattended-upgrades.service", capture=True))  # Mostramos estado
                press_enter()                   # Pausa
            elif op == "4":                     # Volver
                break                            # Salimos del menú
            else:
                print("Opción inválida")        # Opción incorrecta

    elif distro == "rhel":                      # RHEL/CentOS/Rocky/Alma
        print("""
Opciones RHEL/CentOS/Rocky:
- dnf-automatic (nuevo) o yum-cron (antiguo).
- systemctl enable --now dnf-automatic.timer
""")
        while True:                             # Menú RHEL-like
            print("""
1) Instalar y habilitar dnf-automatic (recomendado)
2) Instalar y habilitar yum-cron (alternativo)
3) Ver estado de dnf-automatic.timer
4) Volver
""")
            op = input("Opción: ").strip()      # Tomamos opción
            if op == "1":                       # Instalar y habilitar dnf-automatic
                ensure_pkg(["dnf-automatic"])   # Instalamos paquete
                run("systemctl enable --now dnf-automatic.timer")  # Habilitamos timer
                print("dnf-automatic habilitado (timer activo).")  # Informamos
            elif op == "2":                     # Instalar y habilitar yum-cron (legacy)
                ensure_pkg(["yum-cron"])        # Instalamos paquete
                run("systemctl enable --now yum-cron.service")     # Habilitamos servicio
                print("yum-cron habilitado.")   # Informamos
            elif op == "3":                     # Ver estado del timer dnf-automatic
                print(run("systemctl status dnf-automatic.timer", capture=True))  # Mostramos estado
                press_enter()                   # Pausa
            elif op == "4":                     # Volver
                break                            # Salimos del menú
            else:
                print("Opción inválida")        # Opción incorrecta
    else:
        print("Distro no soportada automáticamente para actualizaciones.")  # Si no es debian/rhel
        press_enter()                            # Pausa

# ===========================================================
#  SECCIÓN: CONTROL DE ACCESO (sudoers, login.defs, PAM)
# ===========================================================

SUDOERS_DIR = "/etc/sudoers.d"                  # Directorio de includes de sudoers
SUDOERS_MAIN = "/etc/sudoers"                   # Archivo sudoers principal
LOGIN_DEFS = "/etc/login.defs"                  # Configuración de políticas básicas de login
PWQUALITY = "/etc/security/pwquality.conf"      # Políticas de calidad de contraseñas (PAM)

def access_status():
    # Muestra un resumen del estado de configuración de acceso/autenticación.
    print("\n[ Acceso / Autenticación ]")       # Encabezado
    # sudoers principal
    print(f"- sudoers principal: {SUDOERS_MAIN} {'OK' if Path(SUDOERS_MAIN).exists() else 'NO'}")
    # Listado de archivos en sudoers.d
    print(f"- includes en {SUDOERS_DIR}:")
    for p in sorted(Path(SUDOERS_DIR).glob("*")):   # Iteramos por archivos del directorio
        if p.is_file():                             # Solo archivos regulares
            print("  -", p)                         # Mostramos su ruta
    # Mostrar valores clave de /etc/login.defs si existe
    if Path(LOGIN_DEFS).exists():                   # Verificamos existencia
        txt = Path(LOGIN_DEFS).read_text()          # Leemos contenido
        for key in ["PASS_MAX_DAYS", "PASS_MIN_DAYS", "PASS_MIN_LEN", "PASS_WARN_AGE", "UMASK"]:
            m = re.search(rf"^\s*{key}\s+(\S+)", txt, flags=re.M)  # Buscamos valor
            if m:
                print(f"  {key} = {m.group(1)}")    # Mostramos valor encontrado
    # Indicar ubicación de pwquality (PAM)
    if Path(PWQUALITY).exists():                    # Si existe archivo de pwquality
        print(f"- pwquality: {PWQUALITY}")          # Mostramos ruta
        print("  (ej. minlen/dcredit/ucredit/lcredit/ocredit/difok)")  # Sugerimos claves

def sudoers_manage():
    # Menú para gestionar permisos sudo de forma segura.
    while True:                                     # Bucle del menú
        print(f"""
--- SUDOERS ---
1) Agregar usuario a sudo (Debian) o wheel (RHEL)
2) Crear regla en {SUDOERS_DIR}/USUARIO (NOPASSWD opcional)
3) Validar sintaxis con visudo
4) Volver
""")
        op = input("Opción: ").strip()              # Leemos opción
        distro, _ = detect_distro()                 # Detectamos familia de distro
        if op == "1":                               # Agregar usuario al grupo sudo/wheel
            user = input("Usuario: ").strip()       # Pedimos usuario
            group = "sudo" if distro == "debian" else "wheel"  # Grupo depende de distro
            run(["usermod", "-aG", group, user])    # Agregamos al grupo sin quitar otros
            print(f"Usuario {user} agregado al grupo {group}.")  # Informamos
        elif op == "2":                             # Crear regla personalizada en sudoers.d
            user = input("Usuario: ").strip()       # Pedimos usuario
            nop = input("¿NOPASSWD? (s/n): ").strip().lower().startswith("s")  # NOPASSWD opcional
            entry = f"{user} ALL=(ALL) {'NOPASSWD:' if nop else ''}ALL\n"       # Línea de sudoers
            Path(SUDOERS_DIR).mkdir(parents=True, exist_ok=True)  # Creamos dir si falta
            dest = f"{SUDOERS_DIR}/{user}"          # Ruta del archivo de regla
            bkp = backup_file(dest)                 # Backup si existía
            if bkp:
                print(f"Backup: {bkp}")             # Informamos backup
            Path(dest).write_text(entry)            # Escribimos la regla
            rc = run(["visudo", "-cf", dest])       # Validamos sintaxis con visudo -cf
            if rc == 0:                              # Si retorno 0 => OK
                print(f"Regla escrita en {dest} y validada.")
            else:                                    # Si no, hay error de sintaxis
                print("Error de sintaxis en sudoers; revisa el archivo.")
        elif op == "3":                             # Validar sintaxis de todo sudoers
            rc = run(["visudo", "-c"])              # visudo -c valida configuración completa
            print("visudo -c exit code:", rc)       # Mostramos código de salida
        elif op == "4":                             # Volver
            break                                   # Salimos del menú
        else:
            print("Opción inválida")                # Opción incorrecta

def login_defs_manage():
    # Editor guiado para /etc/login.defs (políticas de contraseñas/UMASK/etc).
    if not Path(LOGIN_DEFS).exists():               # Si no existe el archivo...
        print(f"No existe {LOGIN_DEFS}")            # ...avisamos
        return                                      # ...y salimos

    params = {                                      # Claves que permitimos tocar
        "PASS_MAX_DAYS": None,                      # Máx. días de validez de contraseña
        "PASS_MIN_DAYS": None,                      # Mín. días antes de poder cambiarla
        "PASS_MIN_LEN": None,                       # Longitud mínima de contraseña
        "PASS_WARN_AGE": None,                      # Días de aviso antes de expirar
        "UMASK": None,                              # Permisos por defecto de creación
    }

    print("\n--- login.defs --- valores actuales ---")  # Encabezado
    txt = Path(LOGIN_DEFS).read_text()                  # Leemos el archivo actual
    for k in params:                                    # Para cada clave conocida...
        m = re.search(rf"^\s*{k}\s+(\S+)", txt, flags=re.M)  # Buscamos su valor
        print(f"{k} = {m.group(1) if m else '(no definido)'}")  # Mostramos valor o vacío

    print("\nDeja en blanco para no cambiar:")         # Instrucción
    for k in params:                                    # Recorremos las claves...
        val = input(f"{k}: ").strip()                   # Pedimos nuevo valor
        if val:
            params[k] = val                             # Guardamos valor si no está vacío

    bkp = backup_file(LOGIN_DEFS)                       # Hacemos backup del archivo
    if bkp:
        print(f"Backup: {bkp}")                         # Informamos del backup

    new = txt                                           # Copia del contenido original
    for k, v in params.items():                         # Iteramos cambios solicitados
        if v is None:                                   # Si no se pidió cambio...
            continue                                    # ...saltamos
        if re.search(rf"^\s*{k}\s+\S+", new, flags=re.M):  # Si la clave ya existe...
            new = re.sub(rf"^\s*{k}\s+\S+", f"{k} {v}", new, flags=re.M)  # Reemplazamos línea
        else:                                           # Si no existe la clave...
            new += f"\n{k} {v}\n"                       # ...la agregamos al final
    Path(LOGIN_DEFS).write_text(new)                    # Escribimos cambios al archivo
    print("login.defs actualizado.")                    # Confirmamos actualización

def pam_pwquality_manage():
    # Edita /etc/security/pwquality.conf con parámetros básicos de calidad de contraseña.
    if not Path(PWQUALITY).exists():                    # Si el archivo no existe...
        print(f"No existe {PWQUALITY}. Instalando módulo si es necesario...")  # Aviso
        distro, _ = detect_distro()                     # Detectamos distro
        if distro == "debian":                          # En Debian/Ubuntu...
            ensure_pkg(["libpam-pwquality"])            # Instalamos módulo PAM de calidad
        elif distro == "rhel":                          # En RHEL-like...
            ensure_pkg(["pam"])                         # Paquete base PAM
        Path(PWQUALITY).touch(exist_ok=True)            # Creamos el archivo si aún no existe

    print(f"\n--- {PWQUALITY} ---")                     # Encabezado
    txt = Path(PWQUALITY).read_text()                   # Leemos contenido actual
    # Mostramos valores típicos si están definidos
    for key in ["minlen", "dcredit", "ucredit", "lcredit", "ocredit", "difok", "retry"]:
        m = re.search(rf"^\s*{key}\s*=\s*(-?\d+)", txt, flags=re.M)  # Buscamos valor
        print(f"{key} = {m.group(1) if m else '(no definido)'}")     # Mostramos estado

    print("\nDeja en blanco para no cambiar (usa enter). Ejemplos: minlen=12, dcredit=-1 (requiere dígito)")  # Guía
    changes = {}                                        # Diccionario de cambios solicitados
    for key in ["minlen", "dcredit", "ucredit", "lcredit", "ocredit", "difok", "retry"]:
        val = input(f"{key}=: ").strip()                # Pedimos nuevo valor
        if val:
            changes[key] = val                          # Guardamos cambio

    if not changes:                                     # Si no se pidieron cambios...
        print("Sin cambios.")                           # ...informamos
        return                                          # ...y salimos

    bkp = backup_file(PWQUALITY)                        # Hacemos backup previo
    if bkp:
        print(f"Backup: {bkp}")                         # Informamos backup

    # Aplicamos cambios reemplazando líneas existentes o agregándolas nuevas
    lines = txt.splitlines()                            # Partimos archivo por líneas
    for k, v in changes.items():                        # Iteramos cada cambio
        replaced = False                                # Bandera si reemplazamos línea
        for i, line in enumerate(lines):                # Recorremos líneas existentes
            if re.match(rf"^\s*{k}\s*=", line):         # Si la línea es la clave buscada...
                lines[i] = f"{k} = {v}"                 # Reemplazamos con valor nuevo
                replaced = True                         # Marcamos como reemplazado
                break                                   # Salimos del loop interno
        if not replaced:                                # Si no existía la clave...
            lines.append(f"{k} = {v}")                  # La añadimos al final
    Path(PWQUALITY).write_text("\n".join(lines) + "\n") # Escribimos de vuelta al archivo
    print("pwquality actualizado. Cambios aplican en próximos logins/cambios de contraseña.")  # Aviso

def access_manage():
    # Menú de control de acceso: estado, sudoers, login.defs y pwquality.
    while True:                                         # Bucle del menú
        print("""
--- Control de Acceso ---
1) Ver estado (sudoers, login.defs, pwquality)
2) Gestionar sudoers
3) Editar parámetros de /etc/login.defs
4) Configurar políticas en /etc/security/pwquality.conf (PAM)
5) Volver
""")
        op = input("Opción: ").strip()                  # Tomamos opción
        if op == "1":                                   # Ver estado general de acceso
            access_status()                              # Mostramos
            press_enter()                                # Pausa
        elif op == "2":                                 # Gestionar sudoers
            sudoers_manage()                             # Entramos al submenú
        elif op == "3":                                 # Editar login.defs
            login_defs_manage()                          # Editor guiado
        elif op == "4":                                 # Editar pwquality.conf
            pam_pwquality_manage()                       # Editor guiado
        elif op == "5":                                 # Volver al menú principal
            break                                        # Salimos del bucle
        else:
            print("Opción inválida")                    # Opción incorrecta

# ==================================
#  SECCIÓN: AUDITORÍA RÁPIDA
# ==================================

def quick_audit():
    # Ejecuta un resumen de estado de seguridad para diagnóstico rápido.
    print("\n=== AUDITORÍA RÁPIDA ===")                # Encabezado
    firewall_status()                                   # Estado firewall
    mac_status()                                        # Estado MAC
    scanners_status()                                   # Estado escáneres
    access_status()                                     # Estado acceso/sudoers/login.defs/pwquality
    print("\nSugerencias:")                             # Consejos generales
    print("- Habilitar actualizaciones automáticas de seguridad.")
    print("- Aplicar políticas de contraseña (pwquality/login.defs).")
    print("- Revisar que el firewall tenga reglas mínimas.")
    print("- Mantener SELinux/AppArmor en enforcing si es posible.")
    press_enter()                                       # Pausa

# ================================
#  MENÚ PRINCIPAL DEL PROGRAMA
# ================================

def main_menu():
    # Despliega el menú principal y coordina cada sección.
    if not is_root():                                   # Verificamos privilegios root
        print("⚠️  Este script debe ejecutarse como root.")  # Avisamos si no es root
        return                                          # Salimos
    while True:                                         # Bucle principal
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
        op = input("Elige una opción: ").strip()        # Leemos opción elegida
        if op == "1":                                   # Auditoría rápida
            quick_audit()                                # Ejecuta diagnóstico
        elif op == "2":                                  # Firewall
            firewall_manage()                             # Abre submenú de firewall
        elif op == "3":                                  # MAC
            mac_manage()                                  # Abre submenú MAC
        elif op == "4":                                  # Escáneres
            scanners_run()                                 # Abre submenú escáneres
        elif op == "5":                                  # Actualizaciones
            security_updates()                             # Abre submenú updates
        elif op == "6":                                  # Control de acceso
            access_manage()                                # Abre submenú acceso
        elif op == "7":                                  # Salir del programa
            print("Saliendo...")                          # Mensaje de salida
            break                                         # Rompe el bucle principal
        else:
            print("Opción inválida.")                    # Opción incorrecta

# ===============================
#  PUNTO DE ENTRADA DEL SCRIPT
# ===============================

if __name__ == "__main__":                               # Si se ejecuta directamente...
    main_menu()                                          # ...iniciamos el menú principal
