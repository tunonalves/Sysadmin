#!/usr/bin/env bash
# Script para listar, crear, eliminar grupos y ver sus miembros.

set -euo pipefail  # Finaliza si hay errores o variables no definidas.

#--- Verificación de permisos ---
if [[ $EUID -ne 0 ]]; then
  echo "Este script debe ejecutarse como root."
  exit 1
fi

#--- Lista todos los grupos del sistema ---
listar_grupos() {
  echo -e "\n📋 Lista de grupos del sistema:\n"
  getent group | cut -d: -f1 | sort  # Obtiene nombres de todos los grupos y los ordena.
}

#--- Crea un nuevo grupo ---
crear_grupo() {
  read -rp "Nombre del nuevo grupo: " grupo
  groupadd "$grupo"
  echo "[+] Grupo '$grupo' creado."
}

#--- Elimina un grupo ---
eliminar_grupo() {
  read -rp "Nombre del grupo a eliminar: " grupo
  groupdel "$grupo"
  echo "[-] Grupo '$grupo' eliminado."
}

#--- Muestra miembros de un grupo ---
ver_miembros_grupo() {
  read -rp "Nombre del grupo: " grupo
  linea=$(getent group "$grupo" || true)  # Obtiene la línea del grupo en /etc/group.
  if [[ -z "$linea" ]]; then
    echo "[!] El grupo '$grupo' no existe."
    return
  fi
  miembros=$(echo "$linea" | awk -F: '{print $4}')  # Campo 4 = miembros explícitos.
  if [[ -n "$miembros" ]]; then
    echo "👥 Miembros de '$grupo': $miembros"
  else
    echo "👥 El grupo '$grupo' no tiene miembros explícitos."
  fi
}

#--- Menú ---
while :; do
  cat <<'MENU'

--- Administración de Grupos ---
1) Listar todos los grupos
2) Crear un nuevo grupo
3) Eliminar un grupo
4) Ver miembros de un grupo
5) Salir
MENU
  read -rp "Selecciona una opción [1-5]: " op
  case "$op" in
    1) listar_grupos ;;
    2) crear_grupo ;;
    3) eliminar_grupo ;;
    4) ver_miembros_grupo ;;
    5) echo "Saliendo..."; exit 0 ;;
    *) echo "Opción inválida." ;;
  esac
done
