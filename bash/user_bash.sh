#!/usr/bin/env bash
# Script interactivo para administrar usuarios, grupos y permisos en Linux.

set -euo pipefail  # Configura el script para salir ante errores o variables no definidas.

#--- Verificación de permisos ---
if [[ $EUID -ne 0 ]]; then  # Comprueba si el UID es distinto de 0 (root)
  echo "Este script debe ejecutarse como root."
  exit 1
fi

#--- Función para crear un usuario ---
crear_usuario() {
  read -rp "Nombre del nuevo usuario: " usuario
  read -rp "Directorio home (/home/$usuario): " home
  home=${home:-/home/$usuario}  # Si no se ingresa ruta, se usa la predeterminada.
  useradd -m -d "$home" -s /bin/bash "$usuario"  # Crea el usuario y su home.
  passwd "$usuario"  # Pide contraseña para el usuario.
  echo "Usuario '$usuario' creado con home '$home'."
}

#--- Función para eliminar un usuario ---
eliminar_usuario() {
  read -rp "Usuario a eliminar: " usuario
  userdel -r "$usuario"  # Elimina el usuario y su home.
  echo "Usuario '$usuario' eliminado."
}

#--- Función para crear un grupo ---
crear_grupo() {
  read -rp "Nombre del nuevo grupo: " grupo
  groupadd "$grupo"
  echo "Grupo '$grupo' creado."
}

#--- Función para agregar usuario a un grupo ---
agregar_usuario_grupo() {
  read -rp "Usuario: " usuario
  read -rp "Grupo: " grupo
  usermod -aG "$grupo" "$usuario"  # Añade usuario a un grupo sin quitar otros.
  echo "Usuario '$usuario' agregado al grupo '$grupo'."
}

#--- Función para ver información de un usuario ---
ver_info_usuario() {
  read -rp "Usuario: " usuario
  id "$usuario" || true  # Muestra UID, GID y grupos del usuario.
  getent passwd "$usuario" || true  # Muestra datos de /etc/passwd.
}

#--- Función para cambiar permisos ---
cambiar_permisos() {
  read -rp "Ruta del archivo/directorio: " ruta
  read -rp "Nuevo modo (ej: 755): " modo
  chmod "$modo" "$ruta"  # Cambia permisos.
  echo "Permisos de '$ruta' cambiados a $modo."
}

#--- Función para cambiar propietario ---
cambiar_propietario() {
  read -rp "Ruta del archivo/directorio: " ruta
  read -rp "Nuevo propietario (usuario:grupo): " prop
  chown "$prop" "$ruta"  # Cambia propietario y grupo.
  echo "Propietario de '$ruta' cambiado a $prop."
}

#--- Menú principal ---
while :; do
  cat <<'MENU'

------------------------------
   Administración de Linux
------------------------------
1) Crear usuario
2) Eliminar usuario
3) Crear grupo
4) Agregar usuario a grupo
5) Ver información de usuario
6) Cambiar permisos de archivo
7) Cambiar propietario de archivo
8) Salir
------------------------------
MENU
  read -rp "Seleccione una opción [1-8]: " op
  case "$op" in
    1) crear_usuario ;;
    2) eliminar_usuario ;;
    3) crear_grupo ;;
    4) agregar_usuario_grupo ;;
    5) ver_info_usuario ;;
    6) cambiar_permisos ;;
    7) cambiar_propietario ;;
    8) echo "Saliendo..."; exit 0 ;;
    *) echo "Opción inválida." ;;
  esac
done
