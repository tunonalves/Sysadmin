#!/usr/bin/env python3
import subprocess
import os

def ejecutar(comando):
    try:
        resultado = subprocess.run(comando, shell=True, check=True, capture_output=True, text=True)
        return resultado.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"[!] Error ejecutando '{comando}':\n{e.stderr}")
        return None

def listar_grupos():
    print("\n📋 Lista de grupos del sistema:\n")
    salida = ejecutar("getent group")
    if salida:
        for linea in salida.split('\n'):
            nombre = linea.split(":")[0]
            print(f"- {nombre}")

def crear_grupo():
    grupo = input("Nombre del nuevo grupo: ")
    if grupo:
        ejecutar(f"groupadd {grupo}")
        print(f"[+] Grupo '{grupo}' creado exitosamente.")

def eliminar_grupo():
    grupo = input("Nombre del grupo a eliminar: ")
    if grupo:
        ejecutar(f"groupdel {grupo}")
        print(f"[-] Grupo '{grupo}' eliminado.")

def ver_miembros_grupo():
    grupo = input("Nombre del grupo: ")
    salida = ejecutar(f"getent group {grupo}")
    if salida:
        partes = salida.split(":")
        miembros = partes[3] if len(partes) > 3 else ""
        print(f"👥 Miembros del grupo '{grupo}': {miembros or 'ninguno'}")

def menu():
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
    if os.geteuid() != 0:
        print("⚠️ Este script debe ejecutarse como root.")
    else:
        menu()
