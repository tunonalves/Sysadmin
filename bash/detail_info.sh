#!/bin/bash

# Script: detalles_sistema.sh
# Info general del sistema + usuarios + IP/MACs + uso del home

timestamp=$(date '+%Y-%m-%d_%H-%M-%S')
outfile="reporte_sistema_$timestamp.txt"

{
echo "📋 INFORMACIÓN DEL SISTEMA - $(date '+%Y-%m-%d %H:%M:%S')"
echo "---------------------------------------------------------"

# Información del sistema
echo -e "\n🖥️  HOSTNAME: $(hostname)"
echo "🧠 CPU: $(lscpu | grep 'Nombre del modelo' | sed 's/Nombre del modelo:[ \t]*//')"
echo "💾 RAM total: $(free -h | awk '/Mem:/ {print $2}')"
echo "💽 Disco total: $(df -h --total | grep total | awk '{print $2}')"
echo "🖥️ SO: $(lsb_release -d | cut -f2)"
echo "🧮 Kernel: $(uname -r)"

# IP y Red
echo -e "\n🌐 RED (IP + MAC)"
for iface in $(ip -o -4 addr show | awk '{print $2}'); do
  ip_addr=$(ip -o -4 addr show $iface | awk '{print $4}')
  mac_addr=$(ip link show $iface | awk '/link\/ether/ {print $2}')
  echo "$iface → IP: $ip_addr | MAC: $mac_addr"
done

# Uptime
echo -e "\n⏳ Tiempo encendido:"
uptime -p

# Usuarios conectados
echo -e "\n👥 Usuarios conectados:"
who

# Dispositivos en red (ARP)
echo -e "\n📡 Dispositivos en la red detectados (ARP):"
ip neigh | grep -i "lladdr" | awk '{printf "IP: %-16s MAC: %s\n", $1, $5}'

# Procesos activos
echo -e "\n🔍 Procesos activos: $(ps aux --no-heading | wc -l)"

# Espacio en disco
echo -e "\n📂 Espacio en disco (excluyendo tmpfs):"
df -h | grep -v tmpfs

# Directorio actual
echo -e "\n📌 Directorio actual (pwd):"
pwd

# Listado ordenado por tamaño
echo -e "\n🗃️ Archivos en el directorio actual ordenados por tamaño:"
ls -lSh

# Uso de espacio en $HOME
echo -e "\n🏠 Uso total del directorio $HOME:"
du -sh ~

echo -e "\n✅ Fin del reporte"
} | tee "$outfile"

echo -e "\n📄 Reporte guardado en: $(pwd)/$outfile"

