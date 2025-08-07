#!/usr/bin/env python3
# Script interactivo para listar, crear, eliminar grupos y ver miembros

import subprocess  # Para ejecutar comandos del sistema
import os          # Para verificar permisos y rutas
import grp         # Para obtener información de grupos

def ejecutar(comando):
    """Ejecuta un comando de shell y devuelve su salida o error"""
    try:
        resultado = subprocess.run(
            comando, shell=True, check=True, capture_output=True, text=True
        )
        return resultado.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"[!] Error ejecutando '{comando}':\n{e.stderr}")
        return None

def listar_grupos():
    """Lista todos los grupos del sistema"""
    print("\n📋 Lista de grupos del sistema:\n")
    salida = ejecutar("getent group")  # Comando que lista todos los grupos
    if salida:
        for linea in salida.split('\n'):
            nombre = linea.split(":")[0]
            print(f"- {nombre}")

def crear_grupo():
    """Solicita un nombre y crea un grupo nuevo"""
    grupo = input("Nombre del nuevo grupo: ")
    if grupo:
        ejecutar(f"groupadd {grupo}")
        print(f"[+] Grupo '{grupo}' creado exitosamente.")

def eliminar_grupo():
    """Solicita un grupo y lo elimina del sistema"""
    grupo = input("Nombre del grupo a eliminar: ")
    if grupo:
        ejecutar(f"groupdel {grupo}")
        print(f"[-] Grupo '{grupo}' eliminado.")

def ver_miembros_grupo():
    """Muestra los miembros de un grupo dado"""
    grupo = input("Nombre del grupo: ")
    try:
        datos = grp.getgrnam(grupo)  # Obtiene la info del grupo
        miembros = datos.gr_mem
        if miembros:
            print(f"👥 Miembros del grupo '{grupo}': {', '.join(miembros)}")
        else:
            print(f"👥 El grupo '{grupo}' no tiene miembros.")
    except KeyError:
        print(f"[!] El grupo '{grupo}' no existe.")

def menu():
    """Menú interactivo principal"""
    while True:
        print("\n--- Administración de Grupos ---")
        print("1) Listar todos los grupos")
        print("2) Crear un nuevo grupo")
        print("3) Eliminar un grupo")
        print("4) Ver miembros de un grupo")
        print("5) Salir")
        opcion = input("Selecciona una opción [1-5]: ")

        match opcion:
            case "1": listar_grupos()
            case "2": crear_grupo()
            case "3": eliminar_grupo()
            case "4": ver_miembros_grupo()
            case "5": print("Saliendo..."); break
            case _: print("Opción inválida.")

if __name__ == "__main__":
    # Verifica si el script se ejecuta como root
    if os.geteuid() != 0:
        print("⚠️ Este script debe ejecutarse como root.")
    else:
        menu()
