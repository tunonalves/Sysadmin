# 🐧 Linux Admin Scripts

Este repositorio contiene una colección de **scripts en Bash y Python** diseñados para facilitar la administración de sistemas Linux. Incluye utilidades para gestionar usuarios, grupos, permisos, monitoreo, red y más.

---

## 🚀 Funcionalidades destacadas

### 🧑‍💼 Gestión de usuarios y grupos
- Crear y eliminar usuarios.
- Asignar usuarios a grupos.
- Configurar claves SSH.
- Cambiar permisos y propietarios.

### 🔐 Seguridad y permisos
- Modificar permisos con `chmod`, `chown`.
- Scripts para aplicar permisos por lotes.
- Generar contraseñas cifradas.

### 🔄 Automatización y mantenimiento
- Respaldo automático de directorios home.
- Monitoreo básico de recursos (RAM, CPU, disco).
- Ejecución programada vía `cron`.

---

## 🛠️ Requisitos

- Distribución Linux basada en Debian, RedHat o Arch.
- Python 3.6+ para scripts Python.
- Permisos de administrador (`sudo`) para tareas del sistema.
- Módulos necesarios:
  - `subprocess` (incluido por defecto)
  - `crypt` (opcional para cifrado de contraseñas)

---

## 📦 Instalación y uso

Clona el repositorio:

```bash
git clone https://github.com/tunonalves/Sysadmin.git
cd linux-admin-scripts
