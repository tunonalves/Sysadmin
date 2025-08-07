#!/bin/bash

# Verifica si el script se ejecuta como root
if [[ $EUID -ne 0 ]]; then
   echo "Este script debe ejecutarse como root." 
   exit 1
fi

# Función para crear un usuario
crear_usuario() {
    read -p "Nombre del nuevo usuario: " usuario
    read -p "Directorio home (/home/$usuario): " home
    home=${home:-/home/$usuario}
    useradd -m -d "$home" "$usuario"  # Crea usuario con home
    passwd "$usuario"                 # Establece la contraseña
    echo "Usuario '$usuario' creado con directorio $home."
}

# Función para eliminar un usuario y su home
eliminar_usuario() {
    read -p "Usuario a eliminar: " usuario
    userdel -r "$usuario"
    echo "Usuario '$usuario' eliminado."
}

# Función para crear un grupo
crear_grupo() {
    read -p "Nombre del nuevo grupo: " grupo
    groupadd "$grupo"
    echo "Grupo '$grupo' creado."
}

# Agrega un usuario a un grupo existente
agregar_usuario_grupo() {
    read -p "Usuario: " usuario
    read -p "Grupo: " grupo
    usermod -aG "$grupo" "$usuario"
    echo "Usuario '$usuario' agregado al grupo '$grupo'."
}

# Muestra información de un usuario
ver_info_usuario() {
    read -p "Usuario: " usuario
    id "$usuario"
    getent passwd "$usuario"
}

# Cambia los permisos de un archivo o directorio
cambiar_permisos() {
    read -p "Ruta del archivo/directorio: " archivo
    read -p "Nuevo modo (ej: 755): " modo
    chmod "$modo" "$archivo"
    echo "Permisos cambiados a $modo para $archivo."
}

# Cambia el propietario de un archivo/directorio
cambiar_propietario() {
    read -p "Ruta del archivo/directorio: " archivo
    read -p "Nuevo propietario (usuario:grupo): " propietario
    chown "$propietario" "$archivo"
    echo "Propietario cambiado a $propietario en $archivo."
}

# Menú interactivo principal
while true; do
    echo "------------------------------"
    echo "  Administración de Usuarios"
    echo "------------------------------"
    echo "1) Crear usuario"
    echo "2) Eliminar usuario"
    echo "3) Crear grupo"
    echo "4) Agregar usuario a grupo"
    echo "5) Ver información de usuario"
    echo "6) Cambiar permisos de archivo"
    echo "7) Cambiar propietario de archivo"
    echo "8) Salir"
    echo "------------------------------"
    read -p "Seleccione una opción [1-8]: " opcion

    case $opcion in
        1) crear_usuario ;;
        2) eliminar_usuario ;;
        3) crear_grupo ;;
        4) agregar_usuario_grupo ;;
        5) ver_info_usuario ;;
        6) cambiar_permisos ;;
        7) cambiar_propietario ;;
        8) echo "Saliendo..."; break ;;
        *) echo "Opción inválida" ;;
    esac
done
