#!/usr/bin/env python3
# Script para generar claves SSH automáticamente para usuarios o grupos en Linux

import os          # Módulo estándar para interactuar con el sistema de archivos
import subprocess  # Para ejecutar comandos de shell (ssh-keygen, chown, etc.)
import pwd         # Para obtener información de usuarios del sistema
import grp         # Para obtener información de grupos del sistema

def generar_clave_ssh(usuario):
    """Genera claves SSH para el usuario especificado y configura authorized_keys"""
    try:
        # Obtener información del usuario (home, UID, GID)
        user_info = pwd.getpwnam(usuario)
        home_dir = user_info.pw_dir
        uid = user_info.pw_uid
        gid = user_info.pw_gid

        # Definir rutas dentro del home del usuario
        ssh_dir = os.path.join(home_dir, ".ssh")
        key_path = os.path.join(ssh_dir, "id_rsa")
        authorized_keys = os.path.join(ssh_dir, "authorized_keys")

        # Crear la carpeta ~/.ssh si no existe
        os.makedirs(ssh_dir, mode=0o700, exist_ok=True)

        # Verificar si ya existe la clave privada
        if os.path.exists(key_path):
            print(f"🔐 Ya existe una clave SSH para {usuario} en {key_path}. Omitiendo generación.")
            return

        print(f"[+] Generando clave SSH para {usuario}...")

        # Generar el par de claves SSH sin passphrase
        subprocess.run([
            "ssh-keygen", "-t", "rsa", "-b", "4096",
            "-f", key_path,
            "-N", "",
            "-C", f"{usuario}@localhost"
        ], check=True)

        # Copiar la clave pública al archivo authorized_keys
        subprocess.run(["cp", f"{key_path}.pub", authorized_keys], check=True)

        # Establecer propietario y permisos correctos
        os.chown(ssh_dir, uid, gid)
        os.chmod(ssh_dir, 0o700)

        os.chown(key_path, uid, gid)
        os.chmod(key_path, 0o600)

        os.chown(f"{key_path}.pub", uid, gid)
        os.chmod(f"{key_path}.pub", 0o644)

        os.chown(authorized_keys, uid, gid)
        os.chmod(authorized_keys, 0o600)

        print(f"[✓] Clave generada e instalada correctamente para {usuario}")
        print(f"[📁] Ubicación: {key_path}")

    except KeyError:
        # Si el usuario no existe
        print(f"[!] El usuario '{usuario}' no existe.")
    except Exception as e:
        # Captura de cualquier otro error
        print(f"[!] Error al generar clave para {usuario}: {e}")

def seleccionar_usuarios_grupo():
    """Solicita un grupo y genera claves para todos sus miembros"""
    grupo = input("Nombre del grupo: ")
    try:
        # Obtener miembros del grupo
        miembros = grp.getgrnam(grupo).gr_mem
        if not miembros:
            print(f"⚠️  El grupo '{grupo}' no tiene miembros.")
        else:
            # Iterar sobre los usuarios del grupo y generar claves
            for usuario in miembros:
                generar_clave_ssh(usuario)
    except KeyError:
        print(f"[!] El grupo '{grupo}' no existe.")

def seleccionar_usuario_individual():
    """Solicita un nombre de usuario y genera su clave"""
    usuario = input("Nombre del usuario: ")
    generar_clave_ssh(usuario)

def menu():
    """Menú interactivo para elegir opciones"""
    while True:
        print("\n--- Generador de claves SSH ---")
        print("1) Generar clave para un usuario")
        print("2) Generar claves para todos los usuarios de un grupo")
        print("3) Salir")
        opcion = input("Seleccione una opción [1-3]: ")

        # Selección de opciones mediante match-case
        match opcion:
            case "1":
                seleccionar_usuario_individual()
            case "2":
                seleccionar_usuarios_grupo()
            case "3":
                print("Saliendo...")
                break
            case _:
                print("Opción inválida")

# Punto de entrada del script
if __name__ == "__main__":
    # Verifica que se ejecute como root (UID 0)
    if os.geteuid() != 0:
        print("⚠️ Este script debe ejecutarse como root.")
    else:
        menu()
