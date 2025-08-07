#!/usr/bin/env python3

import subprocess
import os

# Ejecuta un comando del sistema y maneja errores
def ejecutar_comando(comando):
    try:
        subprocess.run(comando, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")

# Crea un nuevo usuario
def crear_usuario():
    usuario = input("Nombre del nuevo usuario: ")
    home = input(f"Directorio home (/home/{usuario}): ") or f"/home/{usuario}"
    ejecutar_comando(f"useradd -m -d {home} {usuario}")
    ejecutar_comando(f"passwd {usuario}")
    print(f"Usuario '{usuario}' creado con directorio {home}.")

# Elimina un usuario
def eliminar_usuario():
    usuario = input("Usuario a eliminar: ")
    ejecutar_comando(f"userdel -r {usuario}")
    print(f"Usuario '{usuario}' eliminado.")

# Crea un nuevo grupo
def crear_grupo():
    grupo = input("Nombre del nuevo grupo: ")
    ejecutar_comando(f"groupadd {grupo}")
    print(f"Grupo '{grupo}' creado.")

# Agrega usuario a grupo
def agregar_usuario_grupo():
    usuario = input("Usuario: ")
    grupo = input("Grupo: ")
    ejecutar_comando(f"usermod -aG {grupo} {usuario}")
    print(f"Usuario '{usuario}' agregado al grupo '{grupo}'.")

# Muestra información del usuario
def ver_info_usuario():
    usuario = input("Usuario: ")
    ejecutar_comando(f"id {usuario}")
    ejecutar_comando(f"getent passwd {usuario}")

# Cambia permisos de archivo
def cambiar_permisos():
    archivo = input("Ruta del archivo/directorio: ")
    modo = input("Nuevo modo (ej: 755): ")
    ejecutar_comando(f"chmod {modo} {archivo}")
    print(f"Permisos de {archivo} cambiados a {modo}.")

# Cambia propietario de archivo
def cambiar_propietario():
    archivo = input("Ruta del archivo/directorio: ")
    propietario = input("Nuevo propietario (usuario:grupo): ")
    ejecutar_comando(f"chown {propietario} {archivo}")
    print(f"Propietario de {archivo} cambiado a {propietario}.")

# Menú principal
def menu():
    while True:
        print("\n--- Administración de Usuarios (Python) ---")
        print("1) Crear usuario")
        print("2) Eliminar usuario")
        print("3) Crear grupo")
        print("4) Agregar usuario a grupo")
        print("5) Ver información de usuario")
        print("6) Cambiar permisos de archivo")
        print("7) Cambiar propietario de archivo")
        print("8) Salir")
        opcion = input("Seleccione una opción [1-8]: ")

        match opcion:
            case "1": crear_usuario()
            case "2": eliminar_usuario()
            case "3": crear_grupo()
            case "4": agregar_usuario_grupo()
            case "5": ver_info_usuario()
            case "6": cambiar_permisos()
            case "7": cambiar_propietario()
            case "8": print("Saliendo..."); break
            case _: print("Opción inválida")

# Verifica permisos de root
if __name__ == "__main__":
    if os.geteuid() != 0:
        print("Este script debe ejecutarse como root.")
    else:
        menu()
