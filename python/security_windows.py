# -*- coding: utf-8 -*-
"""
AUDITOR DE SEGURIDAD WINDOWS 10/11
Script para revisar y gestionar vulnerabilidades del sistema

Autor: Asistente IA
Versión: 2.0
Requiere: Permisos de Administrador
"""

import subprocess
import sys
import os
import winreg
import json
from datetime import datetime
import ctypes

class WindowsSecurityAuditor:
    def __init__(self):
        self.vulnerabilities_found = []
        self.fixes_applied = []
        self.scan_results = {}
        
        # Verificar permisos de administrador
        if not self.is_admin():
            print("[ERROR] Este script requiere permisos de administrador")
            print("Ejecuta como administrador y vuelve a intentar")
            input("Presiona Enter para salir...")
            sys.exit(1)
    
    def is_admin(self):
        """Verifica si el script se ejecuta con permisos de administrador"""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False
    
    def clear_screen(self):
        """Limpia la pantalla"""
        os.system('cls')
    
    def show_header(self):
        """Muestra el encabezado"""
        print("=" * 80)
        print("           AUDITOR DE SEGURIDAD WINDOWS 10/11")
        print("=" * 80)
        print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Usuario: {os.getenv('USERNAME')}")
        print(f"Sistema: {os.getenv('COMPUTERNAME')}")
        print("-" * 80)
    
    def show_main_menu(self):
        """Muestra el menú principal"""
        print("\nMENU PRINCIPAL - AUDITORIA DE SEGURIDAD")
        print("\n[ESCANEO Y ANALISIS]")
        print("1. Escaneo Completo de Vulnerabilidades")
        print("2. Verificar Estado de Windows Update")
        print("3. Análisis de Servicios Críticos")
        print("4. Revisar Configuración de Firewall")
        print("5. Verificar Antivirus y Windows Defender")
        
        print("\n[CONFIGURACIONES DE SEGURIDAD]")
        print("6. Gestionar UAC (Control de Cuentas de Usuario)")
        print("7. Configurar Actualizaciones Automáticas")
        print("8. Gestionar Servicios Remotos (RDP, WinRM)")
        print("9. Configurar Políticas de Contraseña")
        print("10. Gestionar Recursos Compartidos")
        
        print("\n[HARDENING Y PRIVACIDAD]")
        print("11. Aplicar Configuraciones de Hardening")
        print("12. Desactivar Servicios Innecesarios")
        print("13. Configurar Privacidad (Telemetría)")
        print("14. Gestionar Aplicaciones de Inicio")
        
        print("\n[REPORTES Y UTILIDADES]")
        print("15. Generar Reporte de Seguridad")
        print("16. Ver Historial de Cambios")
        print("17. Restaurar Configuración")
        print("18. Salir")
        print("-" * 80)
    
    def run_command(self, command, shell=True):
        """Ejecuta un comando y retorna el resultado"""
        try:
            result = subprocess.run(
                command, 
                shell=shell, 
                capture_output=True, 
                text=True,
                timeout=30
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "Timeout: Comando tardó más de 30 segundos"
        except Exception as e:
            return -1, "", str(e)
    
    def check_windows_updates(self):
        """Verifica el estado de Windows Update"""
        print("\n[VERIFICANDO] Windows Update...")
        
        # Verificar último update
        cmd = 'powershell "Get-HotFix | Sort-Object InstalledOn -Descending | Select-Object -First 5"'
        code, output, error = self.run_command(cmd)
        
        if code == 0:
            print("[OK] Últimas actualizaciones instaladas:")
            print(output)
        else:
            print("[WARNING] No se pudo verificar actualizaciones")
            self.vulnerabilities_found.append("Windows Update: Estado desconocido")
        
        # Verificar servicio de Windows Update
        cmd = 'sc query wuauserv'
        code, output, error = self.run_command(cmd)
        
        if "RUNNING" in output:
            print("[OK] Servicio Windows Update está ejecutándose")
        else:
            print("[WARNING] Servicio Windows Update no está ejecutándose")
            self.vulnerabilities_found.append("Servicio Windows Update detenido")
    
    def check_firewall_status(self):
        """Verifica el estado del firewall"""
        print("\n[VERIFICANDO] Estado del Firewall...")
        
        cmd = 'netsh advfirewall show allprofiles'
        code, output, error = self.run_command(cmd)
        
        if code == 0:
            if "State                                 ON" in output:
                print("[OK] Windows Firewall está activado")
            else:
                print("[CRITICAL] Windows Firewall está desactivado")
                self.vulnerabilities_found.append("Windows Firewall desactivado")
        else:
            print("[ERROR] No se pudo verificar el firewall")
    
    def check_antivirus_status(self):
        """Verifica el estado del antivirus"""
        print("\n[VERIFICANDO] Windows Defender...")
        
        cmd = 'powershell "Get-MpComputerStatus"'
        code, output, error = self.run_command(cmd)
        
        if code == 0:
            if "True" in output:
                print("[OK] Windows Defender está activo")
            else:
                print("[WARNING] Windows Defender podría estar desactivado")
                self.vulnerabilities_found.append("Windows Defender: Estado incierto")
        else:
            print("[WARNING] No se pudo verificar Windows Defender")
    
    def check_critical_services(self):
        """Verifica servicios críticos de seguridad"""
        print("\n[VERIFICANDO] Servicios Críticos...")
        
        critical_services = [
            ("wuauserv", "Windows Update"),
            ("MpsSvc", "Windows Firewall"),
            ("WinDefend", "Windows Defender"),
            ("EventLog", "Registro de Eventos"),
            ("CryptSvc", "Servicios Criptográficos")
        ]
        
        for service, name in critical_services:
            cmd = f'sc query {service}'
            code, output, error = self.run_command(cmd)
            
            if code == 0:
                if "RUNNING" in output:
                    print(f"[OK] {name} - Ejecutándose")
                else:
                    print(f"[WARNING] {name} - No está ejecutándose")
                    self.vulnerabilities_found.append(f"Servicio {name} detenido")
            else:
                print(f"[ERROR] No se pudo verificar {name}")
    
    def check_uac_status(self):
        """Verifica el estado del UAC"""
        print("\n[VERIFICANDO] Control de Cuentas de Usuario (UAC)...")
        
        try:
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System"
            )
            uac_value, _ = winreg.QueryValueEx(key, "EnableLUA")
            winreg.CloseKey(key)
            
            if uac_value == 1:
                print("[OK] UAC está activado")
            else:
                print("[CRITICAL] UAC está desactivado")
                self.vulnerabilities_found.append("UAC desactivado")
                
        except Exception as e:
            print(f"[ERROR] No se pudo verificar UAC: {e}")
    
    def check_remote_services(self):
        """Verifica servicios remotos"""
        print("\n[VERIFICANDO] Servicios Remotos...")
        
        # Verificar RDP
        cmd = 'reg query "HKEY_LOCAL_MACHINE\\SYSTEM\\CurrentControlSet\\Control\\Terminal Server" /v fDenyTSConnections'
        code, output, error = self.run_command(cmd)
        
        if "0x0" in output:
            print("[WARNING] Remote Desktop (RDP) está habilitado")
            self.vulnerabilities_found.append("RDP habilitado - riesgo de acceso remoto")
        else:
            print("[OK] Remote Desktop (RDP) está deshabilitado")
    
    def full_vulnerability_scan(self):
        """Ejecuta un escaneo completo"""
        print("\n" + "="*60)
        print("           ESCANEO COMPLETO DE VULNERABILIDADES")
        print("="*60)
        
        self.vulnerabilities_found = []  # Reset
        
        self.check_windows_updates()
        self.check_firewall_status()
        self.check_antivirus_status()
        self.check_critical_services()
        self.check_uac_status()
        self.check_remote_services()
        
        # Resumen final
        print(f"\n{'='*60}")
        print("RESUMEN DEL ESCANEO:")
        print(f"{'='*60}")
        
        if self.vulnerabilities_found:
            print(f"[ENCONTRADAS] {len(self.vulnerabilities_found)} vulnerabilidades:")
            for i, vuln in enumerate(self.vulnerabilities_found, 1):
                print(f"  {i}. {vuln}")
        else:
            print("[EXCELENTE] No se encontraron vulnerabilidades críticas")
    
    def manage_uac(self):
        """Gestiona la configuración de UAC"""
        print("\n[GESTION UAC] Control de Cuentas de Usuario")
        print("1. Activar UAC (Recomendado)")
        print("2. Desactivar UAC")
        print("3. Ver estado actual")
        print("4. Volver al menú principal")
        
        choice = input("\nSeleccione opción: ")
        
        if choice == "1":
            cmd = 'reg add "HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System" /v EnableLUA /t REG_DWORD /d 1 /f'
            code, _, error = self.run_command(cmd)
            if code == 0:
                print("[OK] UAC activado. Reinicie el sistema.")
                self.fixes_applied.append("UAC activado")
            else:
                print(f"[ERROR] No se pudo activar UAC: {error}")
        
        elif choice == "2":
            print("[WARNING] Desactivar UAC reduce la seguridad del sistema")
            confirm = input("¿Está seguro? (s/n): ")
            if confirm.lower() == 's':
                cmd = 'reg add "HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System" /v EnableLUA /t REG_DWORD /d 0 /f'
                code, _, error = self.run_command(cmd)
                if code == 0:
                    print("[OK] UAC desactivado. Reinicie el sistema.")
                    self.fixes_applied.append("UAC desactivado")
                else:
                    print(f"[ERROR] No se pudo desactivar UAC: {error}")
        
        elif choice == "3":
            self.check_uac_status()
    
    def manage_firewall(self):
        """Gestiona la configuración del firewall"""
        print("\n[GESTION FIREWALL] Windows Firewall")
        print("1. Activar Firewall (Todos los perfiles)")
        print("2. Desactivar Firewall")
        print("3. Ver estado actual")
        print("4. Configurar reglas básicas")
        print("5. Volver al menú principal")
        
        choice = input("\nSeleccione opción: ")
        
        if choice == "1":
            cmd = 'netsh advfirewall set allprofiles state on'
            code, _, error = self.run_command(cmd)
            if code == 0:
                print("[OK] Firewall activado en todos los perfiles")
                self.fixes_applied.append("Firewall activado")
            else:
                print(f"[ERROR] No se pudo activar el firewall: {error}")
        
        elif choice == "2":
            print("[CRITICAL] Desactivar el firewall es muy peligroso")
            confirm = input("¿Está absolutamente seguro? (s/n): ")
            if confirm.lower() == 's':
                cmd = 'netsh advfirewall set allprofiles state off'
                code, _, error = self.run_command(cmd)
                if code == 0:
                    print("[WARNING] Firewall desactivado")
                    self.fixes_applied.append("Firewall desactivado")
        
        elif choice == "3":
            self.check_firewall_status()
        
        elif choice == "4":
            self.configure_firewall_rules()
    
    def configure_firewall_rules(self):
        """Configura reglas básicas de firewall"""
        print("\n[CONFIGURANDO] Reglas básicas de firewall...")
        
        rules = [
            ('netsh advfirewall firewall add rule name="Block Telnet" dir=in action=block protocol=TCP localport=23', "Bloquear Telnet"),
            ('netsh advfirewall firewall add rule name="Block FTP" dir=in action=block protocol=TCP localport=21', "Bloquear FTP"),
            ('netsh advfirewall firewall add rule name="Block SNMP" dir=in action=block protocol=UDP localport=161', "Bloquear SNMP")
        ]
        
        for cmd, desc in rules:
            code, _, error = self.run_command(cmd)
            if code == 0:
                print(f"[OK] {desc}")
            else:
                print(f"[WARNING] No se pudo aplicar: {desc}")
    
    def disable_unnecessary_services(self):
        """Desactiva servicios innecesarios"""
        print("\n[HARDENING] Desactivando servicios innecesarios...")
        
        # Servicios que pueden ser desactivados para mejorar seguridad
        services_to_disable = [
            ("Fax", "Servicio de Fax"),
            ("TapiSrv", "Telefonía"),
            ("SCardSvr", "Tarjeta inteligente"),
            ("WMPNetworkSvc", "Windows Media Player Network"),
            ("RemoteRegistry", "Registro Remoto")
        ]
        
        print("Servicios que se pueden desactivar:")
        for i, (service, desc) in enumerate(services_to_disable, 1):
            print(f"  {i}. {desc} ({service})")
        
        print(f"  {len(services_to_disable) + 1}. Desactivar todos los listados")
        print(f"  {len(services_to_disable) + 2}. Cancelar")
        
        choice = input("\nSeleccione opción: ")
        
        if choice == str(len(services_to_disable) + 1):
            for service, desc in services_to_disable:
                cmd = f'sc config {service} start= disabled'
                code, _, error = self.run_command(cmd)
                if code == 0:
                    print(f"[OK] {desc} desactivado")
                    self.fixes_applied.append(f"Servicio {desc} desactivado")
                else:
                    print(f"[WARNING] No se pudo desactivar {desc}")
        
        elif choice.isdigit() and 1 <= int(choice) <= len(services_to_disable):
            idx = int(choice) - 1
            service, desc = services_to_disable[idx]
            cmd = f'sc config {service} start= disabled'
            code, _, error = self.run_command(cmd)
            if code == 0:
                print(f"[OK] {desc} desactivado")
                self.fixes_applied.append(f"Servicio {desc} desactivado")
    
    def configure_privacy_settings(self):
        """Configura opciones de privacidad"""
        print("\n[PRIVACIDAD] Configurando opciones de privacidad...")
        
        privacy_settings = [
            # Desactivar telemetría
            ('reg add "HKEY_LOCAL_MACHINE\\SOFTWARE\\Policies\\Microsoft\\Windows\\DataCollection" /v AllowTelemetry /t REG_DWORD /d 0 /f',
             "Desactivar telemetría"),
            
            # Desactivar publicidad personalizada
            ('reg add "HKEY_CURRENT_USER\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\AdvertisingInfo" /v Enabled /t REG_DWORD /d 0 /f',
             "Desactivar publicidad personalizada"),
            
            # Desactivar sincronización de configuraciones
            ('reg add "HKEY_CURRENT_USER\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\SettingSync" /v SyncPolicy /t REG_DWORD /d 5 /f',
             "Desactivar sincronización de configuraciones")
        ]
        
        for cmd, desc in privacy_settings:
            code, _, error = self.run_command(cmd)
            if code == 0:
                print(f"[OK] {desc}")
                self.fixes_applied.append(desc)
            else:
                print(f"[WARNING] No se pudo aplicar: {desc}")
    
    def generate_security_report(self):
        """Genera un reporte de seguridad"""
        print("\n[GENERANDO] Reporte de Seguridad...")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"security_report_{timestamp}.txt"
        
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write("REPORTE DE AUDITORIA DE SEGURIDAD WINDOWS\n")
                f.write("=" * 50 + "\n")
                f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Sistema: {os.getenv('COMPUTERNAME')}\n")
                f.write(f"Usuario: {os.getenv('USERNAME')}\n\n")
                
                f.write("VULNERABILIDADES ENCONTRADAS:\n")
                f.write("-" * 30 + "\n")
                if self.vulnerabilities_found:
                    for i, vuln in enumerate(self.vulnerabilities_found, 1):
                        f.write(f"{i}. {vuln}\n")
                else:
                    f.write("No se encontraron vulnerabilidades críticas.\n")
                
                f.write(f"\nCORRECCIONES APLICADAS:\n")
                f.write("-" * 25 + "\n")
                if self.fixes_applied:
                    for i, fix in enumerate(self.fixes_applied, 1):
                        f.write(f"{i}. {fix}\n")
                else:
                    f.write("No se aplicaron correcciones en esta sesión.\n")
            
            print(f"[OK] Reporte guardado en: {report_file}")
            
        except Exception as e:
            print(f"[ERROR] No se pudo generar el reporte: {e}")
    
    def run(self):
        """Ejecuta el programa principal"""
        while True:
            self.clear_screen()
            self.show_header()
            self.show_main_menu()
            
            try:
                choice = input("\nSeleccione una opción (1-18): ").strip()
                
                if choice == "1":
                    self.full_vulnerability_scan()
                elif choice == "2":
                    self.check_windows_updates()
                elif choice == "3":
                    self.check_critical_services()
                elif choice == "4":
                    self.manage_firewall()
                elif choice == "5":
                    self.check_antivirus_status()
                elif choice == "6":
                    self.manage_uac()
                elif choice == "7":
                    print("[INFO] Configuración de actualizaciones automáticas")
                    cmd = 'sconfig'  # Herramienta de configuración del servidor
                    os.system(cmd)
                elif choice == "8":
                    self.check_remote_services()
                elif choice == "9":
                    print("[INFO] Abrir configuración de directivas de grupo...")
                    os.system('gpedit.msc')
                elif choice == "10":
                    cmd = 'net share'
                    code, output, error = self.run_command(cmd)
                    print(f"\n[INFO] Recursos compartidos:\n{output}")
                elif choice == "11":
                    print("[HARDENING] Aplicando configuraciones de seguridad...")
                    self.configure_privacy_settings()
                    self.disable_unnecessary_services()
                elif choice == "12":
                    self.disable_unnecessary_services()
                elif choice == "13":
                    self.configure_privacy_settings()
                elif choice == "14":
                    print("[INFO] Abrir administrador de tareas...")
                    os.system('taskmgr')
                elif choice == "15":
                    self.generate_security_report()
                elif choice == "16":
                    print(f"\n[HISTORIAL] Cambios aplicados en esta sesión:")
                    if self.fixes_applied:
                        for i, fix in enumerate(self.fixes_applied, 1):
                            print(f"  {i}. {fix}")
                    else:
                        print("  No se han aplicado cambios.")
                elif choice == "17":
                    print("[INFO] Para restaurar configuración, use puntos de restauración del sistema")
                    os.system('rstrui')
                elif choice == "18":
                    print("\n¡Gracias por usar el Auditor de Seguridad!")
                    print("Recuerda reiniciar el sistema si se aplicaron cambios críticos.")
                    break
                else:
                    print("[ERROR] Opción no válida. Intente de nuevo.")
                
                if choice != "18":
                    input("\nPresiona Enter para continuar...")
                    
            except KeyboardInterrupt:
                print("\n\n[INTERRUMPIDO] Programa interrumpido por el usuario")
                print("¡Hasta luego!")
                break
            except Exception as e:
                print(f"\n[ERROR] Error inesperado: {e}")
                input("Presiona Enter para continuar...")

def main():
    """Función principal"""
    try:
        auditor = WindowsSecurityAuditor()
        auditor.run()
    except Exception as e:
        print(f"[ERROR FATAL] Error al inicializar: {e}")
        input("Presiona Enter para salir...")

if __name__ == "__main__":
    main()