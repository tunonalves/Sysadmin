#!/usr/bin/env bash
# Script para generar claves SSH RSA 4096 y configurar authorized_keys.

set -euo pipefail  # Sale ante errores o variables no definidas.

#--- Verificación de permisos ---
if [[ $EUID -ne 0 ]]; then
  echo "Este script debe ejecutarse como root."
  exit 1
fi

#--- Obtiene el home de un usuario ---
home_de_usuario() {
  local u="$1"
  eval echo "~$u" 2>/dev/null || getent passwd "$u" | awk -F: '{print $6}'
}

#--- Genera clave SSH para un usuario ---
generar_para_usuario() {
  local usuario="$1"

  if ! id "$usuario" >/dev/null 2>&1; then
    echo "[!] El usuario '$usuario' no existe."
    return 1
  fi

  local home ssh_dir key_path auth_keys host tag
  home=$(home_de_usuario "$usuario")
  ssh_dir="$home/.ssh"
  key_path="$ssh_dir/id_rsa"
  auth_keys="$ssh_dir/authorized_keys"
  host=$(hostname -f 2>/dev/null || hostname)
  tag="${usuario}@${host}"

  mkdir -p "$ssh_dir"
  chmod 700 "$ssh_dir"
  chown "$usuario":"$usuario" "$ssh_dir"

  if [[ -e "$key_path" ]]; then
    echo "🔐 Ya existe una clave en '$key_path' para $usuario. Omitiendo generación."
  else
    echo "[+] Generando clave SSH para $usuario..."
    ssh-keygen -t rsa -b 4096 -f "$key_path" -N "" -C "$tag"
    chown "$usuario":"$usuario" "$key_path" "$key_path.pub"
    chmod 600 "$key_path"
    chmod 644 "$key_path.pub"
  fi

  touch "$auth_keys"
  chown "$usuario":"$usuario" "$auth_keys"
  chmod 600 "$auth_keys"

  if ! grep -Fq "$(cat "$key_path.pub")" "$auth_keys"; then
    cat "$key_path.pub" >> "$auth_keys"
  fi

  echo "[✓] Clave instalada para '$usuario' en $auth_keys"
}

#--- Genera clave para todos los usuarios de un grupo ---
generar_para_grupo() {
  local grupo="$1"

  if ! getent group "$grupo" >/dev/null; then
    echo "[!] El grupo '$grupo' no existe."
    return 1
  fi

  miembros=$(getent group "$grupo" | awk -F: '{print $4}')
  if [[ -n "$miembros" ]]; then
    IFS=',' read -r -a arr <<< "$miembros"
    for u in "${arr[@]}"; do
      [[ -z "$u" ]] && continue
      generar_para_usuario "$u"
    done
  fi

  gid=$(getent group "$grupo" | awk -F: '{print $3}')
  usuarios_prim=$(getent passwd | awk -F: -v G="$gid" '$4==G {print $1}')
  if [[ -n "$usuarios_prim" ]]; then
    for u in $usuarios_prim; do
      generar_para_usuario "$u"
    done
  fi
}

#--- Menú ---
menu() {
  while :; do
    cat <<'MENU'

--- Generador de claves SSH ---
1) Generar/instalar clave pa
