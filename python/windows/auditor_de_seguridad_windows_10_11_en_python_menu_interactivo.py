#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auditor de seguridad para Windows 10/11 con menú interactivo.
- Revisa configuraciones comunes relacionadas con endurecimiento del sistema.
- Permite activar/desactivar funcionalidades clave (firewall, RDP, SMBv1, UAC, etc.).

⚠️ Requisitos y notas:
- Ejecutar en Windows 10/11 con Python 3.8+.
- Muchas acciones requieren privilegios de Administrador.
- Algunos cambios requieren reiniciar el equipo para aplicarse.
- El script NO explota vulnerabilidades: sólo consulta y ajusta configuraciones defensivas.

Autor: Multimedios CNA + ChatGPT
"""

import ctypes
import os
import subprocess
import sys
import textwrap
from typing import Tuple
try:
    import winreg  # type: ignore
except Exception:
    winreg = None

# ---------------------------- Utilidades ---------------------------- #

def is_admin() -> bool:
    """Devuelve True si el proceso corre con privilegios de administrador."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def ensure_admin():
    """Re-ejecuta el script con privilegios elevados si no es admin."""
    if not is_admin():
        print("[!] Este script requiere privilegios de Administrador para muchas acciones.")
        respuesta = input("¿Desea re-ejecutarlo elevado ahora? (s/N): ").strip().lower()
        if respuesta == 's':
            params = ' '.join([f'"{arg}"' for arg in sys.argv])
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
            sys.exit(0)


def run_ps(cmd: str) -> Tuple[int, str, str]:
    """Ejecuta un comando de PowerShell y retorna (rc, stdout, stderr)."""
    full_cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-Command", cmd,
    ]
    proc = subprocess.Popen(full_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, err = proc.communicate()
    return proc.returncode, out.strip(), err.strip()


def press_enter():
    input("\nPresione Enter para continuar...")


# ---------------------------- Comprobaciones ---------------------------- #

def check_firewall() -> str:
    # Usa PowerShell porque es más consistente que netsh para perfiles múltiples
    cmd = "Get-NetFirewallProfile | Select-Object Name,Enabled | ConvertTo-Json"
    rc, out, err = run_ps(cmd)
    if rc != 0:
        return f"Error consultando firewall: {err}"
    return out


def set_firewall(enable: bool) -> str:
    state = 'True' if enable else 'False'
    cmd = f"Get-NetFirewallProfile | ForEach-Object {{ Set-NetFirewallProfile -Name $_.Name -Enabled {state} }}"
    rc, out, err = run_ps(cmd)
    return "Firewall actualizado." if rc == 0 else f"Error: {err}"


def check_defender() -> str:
    cmd = "Get-MpComputerStatus | Select-Object AMServiceEnabled,AntivirusEnabled,RealTimeProtectionEnabled | ConvertTo-Json"
    rc, out, err = run_ps(cmd)
    if rc != 0:
        return f"Error consultando Defender: {err}"
    return out


def set_defender_rt(enable: bool) -> str:
    # Nota: Desactivar RT puede estar bloqueado por directivas; habilitarlo suele requerir quitar la desactivación.
    val = '$false' if enable else '$true'
    cmd = f"Set-MpPreference -DisableRealtimeMonitoring {val}"
    rc, out, err = run_ps(cmd)
    return "Protección en tiempo real actualizada." if rc == 0 else f"Error: {err}"


def check_smb1() -> str:
    cmd = "(Get-WindowsOptionalFeature -Online -FeatureName SMB1Protocol).State"
    rc, out, err = run_ps(cmd)
    if rc != 0:
        return f"Error consultando SMBv1: {err}"
    return f"SMBv1: {out} (Disabled=Recomendado)"


def set_smb1(enable: bool) -> str:
    if enable:
        cmd = "Enable-WindowsOptionalFeature -Online -FeatureName SMB1Protocol -NoRestart -All"
    else:
        cmd = "Disable-WindowsOptionalFeature -Online -FeatureName SMB1Protocol -NoRestart"
    rc, out, err = run_ps(cmd)
    return "SMBv1 actualizado. Reinicio puede ser requerido." if rc == 0 else f"Error: {err}"


def check_rdp() -> str:
    # fDenyTSConnections: 1 = deshabilita conexiones RDP; 0 = habilita
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\\CurrentControlSet\\Control\\Terminal Server") as k:
            val, _ = winreg.GetValueEx(k, "fDenyTSConnections") if hasattr(winreg, 'GetValueEx') else (None, None)
    except Exception:
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\\CurrentControlSet\\Control\\Terminal Server") as k:
                val, _ = winreg.QueryValueEx(k, "fDenyTSConnections")
        except Exception as e:
            return f"Error consultando RDP: {e}"
    estado = "HABILITADO" if val == 0 else "DESHABILITADO"
    nla = check_nla()
    return f"RDP: {estado}. {nla}"


def set_rdp(enable: bool) -> str:
    # Ajusta firewall y NLA cuando corresponde
    value = 0 if enable else 1
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\\CurrentControlSet\\Control\\Terminal Server", 0, winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, "fDenyTSConnections", 0, winreg.REG_DWORD, value)
    except Exception as e:
        return f"Error cambiando RDP: {e}"
    if enable:
        # Abrir regla de firewall para RDP
        run_ps("Enable-NetFirewallRule -DisplayGroup 'Remote Desktop'")
    else:
        run_ps("Disable-NetFirewallRule -DisplayGroup 'Remote Desktop'")
    return "RDP actualizado. Considere habilitar NLA si usa RDP."


def check_nla() -> str:
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\\CurrentControlSet\\Control\\Terminal Server\\WinStations\\RDP-Tcp") as k:
            val, _ = winreg.QueryValueEx(k, "UserAuthentication")
    except Exception as e:
        return f"Error consultando NLA: {e}"
    estado = "NLA ACTIVADO" if val == 1 else "NLA DESACTIVADO"
    return estado


def set_nla(enable: bool) -> str:
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\\CurrentControlSet\\Control\\Terminal Server\\WinStations\\RDP-Tcp", 0, winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, "UserAuthentication", 0, winreg.REG_DWORD, 1 if enable else 0)
        return "NLA actualizado. Puede requerir reinicio del servicio de Escritorio Remoto."
    except Exception as e:
        return f"Error cambiando NLA: {e}"


def check_uac() -> str:
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System") as k:
            val, _ = winreg.QueryValueEx(k, "EnableLUA")
    except Exception as e:
        return f"Error consultando UAC: {e}"
    return "UAC: ACTIVADO" if val == 1 else "UAC: DESACTIVADO (no recomendado)"


def set_uac(enable: bool) -> str:
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System", 0, winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, "EnableLUA", 0, winreg.REG_DWORD, 1 if enable else 0)
        return "UAC actualizado. Se requiere reiniciar para aplicar."
    except Exception as e:
        return f"Error cambiando UAC: {e}"


def check_smartscreen() -> str:
    # SmartScreen para Windows Explorer
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Explorer") as k:
            val, _ = winreg.QueryValueEx(k, "SmartScreenEnabled")
            if isinstance(val, str):
                return f"SmartScreen (Explorer): {val} (Warn/RequireAdmin recomendado)"
            else:
                return "SmartScreen (Explorer): valor no estándar"
    except FileNotFoundError:
        return "SmartScreen (Explorer): No configurado (podría estar controlado por políticas)."
    except Exception as e:
        return f"Error consultando SmartScreen: {e}"


def set_smartscreen(mode: str) -> str:
    # mode: "Off" | "Warn" | "RequireAdmin"
    if mode not in {"Off", "Warn", "RequireAdmin"}:
        return "Modo inválido. Use Off, Warn o RequireAdmin."
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Explorer", 0, winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, "SmartScreenEnabled", 0, winreg.REG_SZ, mode)
        return "SmartScreen actualizado."
    except Exception as e:
        return f"Error cambiando SmartScreen: {e}"


def check_windows_update() -> str:
    # Estado del servicio wuauserv y si hay actualizaciones pendientes (simplificado)
    rc, out, err = run_ps("Get-Service wuauserv | Select-Object Status, StartType | ConvertTo-Json")
    if rc != 0:
        return f"Error consultando Windows Update: {err}"
    return out


def set_windows_update_starttype(start_type: str) -> str:
    # start_type: Automatic | Manual | Disabled
    if start_type not in {"Automatic", "Manual", "Disabled"}:
        return "Tipo inválido. Use Automatic, Manual o Disabled."
    # PowerShell: Set-Service no cambia StartType; usar sc.exe o Set-Service con -StartupType en PS 6+
    rc, out, err = run_ps(f"Set-Service -Name wuauserv -StartupType {start_type}")
    return "Windows Update actualizado." if rc == 0 else f"Error: {err}"


def check_bitlocker() -> str:
    # Requiere manage-bde (disponible en Windows). Sólo lectura.
    try:
        out = subprocess.check_output(["manage-bde", "-status"], text=True, stderr=subprocess.STDOUT)
        # Mostrar sólo líneas clave
        resumen = []
        for line in out.splitlines():
            if any(k in line for k in ["Unidad", "Conversion", "Estado de protección", "Método de cifrado"]):
                resumen.append(line.strip())
        return "\n".join(resumen) if resumen else out
    except FileNotFoundError:
        return "BitLocker no disponible (manage-bde no encontrado)."
    except subprocess.CalledProcessError as e:
        return f"Error consultando BitLocker: {e.output}"


# ---------------------------- Menú UI ---------------------------- #

MENU = textwrap.dedent(
    """
    ========== Auditor de Seguridad Windows 10/11 ==========
    1) Revisar estado del Firewall
    2) Activar Firewall (todas los perfiles)
    3) Desactivar Firewall (NO recomendado)

    4) Revisar Microsoft Defender
    5) Activar Protección en tiempo real (Defender)
    6) Desactivar Protección en tiempo real (NO recomendado)

    7) Revisar SMBv1
    8) Deshabilitar SMBv1 (recomendado)
    9) Habilitar SMBv1 (NO recomendado)

    10) Revisar RDP y NLA
    11) Habilitar RDP
    12) Deshabilitar RDP
    13) Activar NLA (para RDP)
    14) Desactivar NLA

    15) Revisar UAC
    16) Activar UAC (recomendado)
    17) Desactivar UAC (NO recomendado)

    18) Revisar SmartScreen (Explorer)
    19) SmartScreen -> Warn
    20) SmartScreen -> RequireAdmin
    21) SmartScreen -> Off (NO recomendado)

    22) Revisar servicio Windows Update
    23) Windows Update -> Automatic
    24) Windows Update -> Manual
    25) Windows Update -> Disabled (NO recomendado)

    26) Revisar estado BitLocker (solo lectura)

    0) Salir
    """
)


def main():
    os.system('cls')
    print("Auditor de seguridad Windows 10/11\n")
    if winreg is None or os.name != 'nt':
        print("[!] Este script debe ejecutarse en Windows (winreg no disponible).")
        return
    ensure_admin()

    while True:
        print(MENU)
        opcion = input("Seleccione una opción: ").strip()
        os.system('cls')
        if opcion == '1':
            print(check_firewall())
            press_enter()
        elif opcion == '2':
            print(set_firewall(True))
            press_enter()
        elif opcion == '3':
            print(set_firewall(False))
            press_enter()
        elif opcion == '4':
            print(check_defender())
            press_enter()
        elif opcion == '5':
            print(set_defender_rt(True))
            press_enter()
        elif opcion == '6':
            print(set_defender_rt(False))
            press_enter()
        elif opcion == '7':
            print(check_smb1())
            press_enter()
        elif opcion == '8':
            print(set_smb1(False))
            press_enter()
        elif opcion == '9':
            print(set_smb1(True))
            press_enter()
        elif opcion == '10':
            print(check_rdp())
            press_enter()
        elif opcion == '11':
            print(set_rdp(True))
            press_enter()
        elif opcion == '12':
            print(set_rdp(False))
            press_enter()
        elif opcion == '13':
            print(set_nla(True))
            press_enter()
        elif opcion == '14':
            print(set_nla(False))
            press_enter()
        elif opcion == '15':
            print(check_uac())
            press_enter()
        elif opcion == '16':
            print(set_uac(True))
            press_enter()
        elif opcion == '17':
            print(set_uac(False))
            press_enter()
        elif opcion == '18':
            print(check_smartscreen())
            press_enter()
        elif opcion == '19':
            print(set_smartscreen("Warn"))
            press_enter()
        elif opcion == '20':
            print(set_smartscreen("RequireAdmin"))
            press_enter()
        elif opcion == '21':
            print(set_smartscreen("Off"))
            press_enter()
        elif opcion == '22':
            print(check_windows_update())
            press_enter()
        elif opcion == '23':
            print(set_windows_update_starttype("Automatic"))
            press_enter()
        elif opcion == '24':
            print(set_windows_update_starttype("Manual"))
            press_enter()
        elif opcion == '25':
            print(set_windows_update_starttype("Disabled"))
            press_enter()
        elif opcion == '26':
            print(check_bitlocker())
            press_enter()
        elif opcion == '0':
            print("Saliendo...")
            break
        else:
            print("Opción no válida.")
            press_enter()
        os.system('cls')


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrumpido por el usuario.")
