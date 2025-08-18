#!/usr/bin/env python3  # Shebang: indica usar Python 3 del entorno para ejecutar el script

import subprocess  # Importa el módulo para ejecutar comandos del sistema
import os          # Importa utilidades del sistema operativo (p.ej., ver si somos root)

# Ejecuta un comando del sistema y maneja errores
def ejecutar_comando(comando):  # Define una función que recibe un string con el comando a ejecutar
    try:  # Intenta ejecutar el comando
        subprocess.run(comando, shell=True, check=True)  # Ejecuta el comando en la shell; check=True lanza excepción si el comando falla (código != 0)
    except subprocess.CalledProcessError as e:  # Captura errores de ejecución del comando
        print(f"Error: {e}")  # Muestra el error por pantalla

# Crea un nuevo usuario
def crear_usuario():  # Función para crear usuarios en el sistema
    usuario = input("Nombre del nuevo usuario: ")  # Pide el nombre del nuevo usuario por consola
    home = input(f"Directorio home (/home/{usuario}): ") or f"/home/{usuario}"  # Pide el directorio home; si se deja vacío, usa /home/<usuario>
    ejecutar_comando(f"useradd -m -d {home} {usuario}")  # Crea el usuario con su directorio home usando useradd
    ejecutar_comando(f"passwd {usuario}")  # Lanza el comando passwd para establecer la contraseña del usuario
    print(f"Usuario '{usuario}' creado con directorio {home}.")  # Confirma la creación al operador

# Elimina un usuario
def eliminar_usuario():  # Función para eliminar usuarios
    usuario = input("Usuario a eliminar: ")  # Pide el nombre del usuario a eliminar
    ejecutar_comando(f"userdel -r {usuario}")  # Elimina el usuario y su home (-r) usando userdel
    print(f"Usuario '{usuario}' eliminado.")  # Confirma la eliminación

# Crea un nuevo grupo
def crear_grupo():  # Función para crear grupos
    grupo = input("Nombre del nuevo grupo: ")  # Pide el nombre del grupo
    ejecutar_comando(f"groupadd {grupo}")  # Crea el grupo con groupadd
    print(f"Grupo '{grupo}' creado.")  # Confirma la creación

# Agrega usuario a grupo
def agregar_usuario_grupo():  # Función para añadir un usuario a un grupo secundario
    usuario = input("Usuario: ")  # Pide el nombre del usuario
    grupo = input("Grupo: ")  # Pide el nombre del grupo
    ejecutar_comando(f"usermod -aG {grupo} {usuario}")  # Añade al usuario al grupo con -aG (append a grupos suplementarios)
    print(f"Usuario '{usuario}' agregado al grupo '{grupo}'.")  # Confirma la operación

# Muestra información del usuario
def ver_info_usuario():  # Función para consultar datos de un usuario
    usuario = input("Usuario: ")  # Pide el nombre del usuario a consultar
    ejecutar_comando(f"id {usuario}")  # Muestra UID, GIDs y grupos del usuario
    ejecutar_comando(f"getent passwd {usuario}")  # Muestra la entrada del usuario en la base de cuentas (NSS)

# Cambia permisos de archivo
def cambiar_permisos():  # Función para cambiar permisos (modo) de un archivo/directorio
    archivo = input("Ruta del archivo/directorio: ")  # Pide la ruta de destino
    modo = input("Nuevo modo (ej: 755): ")  # Pide el modo en notación octal (p.ej., 644, 755)
    ejecutar_comando(f"chmod {modo} {archivo}")  # Aplica el cambio de permisos con chmod
    print(f"Permisos de {archivo} cambiados a {modo}.")  # Confirma la operación

# Cambia propietario de archivo
def cambiar_propietario():  # Función para cambiar propietario y grupo de un archivo/directorio
    archivo = input("Ruta del archivo/directorio: ")  # Pide la ruta de destino
    propietario = input("Nuevo propietario (usuario:grupo): ")  # Pide el nuevo propietario con formato usuario:grupo
    ejecutar_comando(f"chown {propietario} {archivo}")  # Cambia propietario y grupo con chown
    print(f"Propietario de {archivo} cambiado a {propietario}.")  # Confirma la operación

# Menú principal
def menu():  # Función que muestra el menú y gestiona la interacción
    while True:  # Bucle infinito hasta que el usuario elija salir
        print("\n--- Administración de Usuarios (Python) ---")  # Título del menú
        print("1) Crear usuario")  # Opción 1 del menú
        print("2) Eliminar usuario")  # Opción 2 del menú
        print("3) Crear grupo")  # Opción 3 del menú
        print("4) Agregar usuario a grupo")  # Opción 4 del menú
        print("5) Ver información de usuario")  # Opción 5 del menú
        print("6) Cambiar permisos de archivo")  # Opción 6 del menú
        print("7) Cambiar propietario de archivo")  # Opción 7 del menú
        print("8) Salir")  # Opción para salir del programa
        opcion = input("Seleccione una opción [1-8]: ")  # Lee la opción elegida

        match opcion:  # Estructura de patrones (Python 3.10+), evalúa la opción elegida
            case "1": crear_usuario()  # Si elige "1", llama a crear_usuario()
            case "2": eliminar_usuario()  # Si elige "2", elimina un usuario
            case "3": crear_grupo()  # Si elige "3", crea un grupo
            case "4": agregar_usuario_grupo()  # Si elige "4", añade un usuario a un grupo
            case "5": ver_info_usuario()  # Si elige "5", muestra info del usuario
            case "6": cambiar_permisos()  # Si elige "6", cambia permisos de un archivo/directorio
            case "7": cambiar_propietario()  # Si elige "7", cambia propietario/grupo de un archivo/directorio
            case "8": print("Saliendo..."); break  # Si elige "8", muestra mensaje y rompe el bucle para salir
            case _: print("Opción inválida")  # Cualquier otro valor: avisa que la opción no es válida

# Verifica permisos de root
if __name__ == "__main__":  # Punto de entrada: este bloque se ejecuta solo si el archivo se corre directamente
    if os.geteuid() != 0:  # Comprueba el UID efectivo; si no es 0 (root), no permite continuar (nota: os.geteuid existe en Unix/Linux)
        print("Este script debe ejecutarse como root.")  # Mensaje de advertencia si no somos root
    else:  # Si somos root
        menu()  # Inicia el menú interactivo
