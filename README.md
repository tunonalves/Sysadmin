# Sysadmin — scripts de administración

Colección de herramientas independientes en **Bash y Python** para Linux y Windows: usuarios, grupos, permisos, claves SSH, inventario de hardware, monitoreo, seguridad y preparación de Docker Compose. Conserva el enfoque del README original de administración Linux, pero también incluye utilidades específicas de Windows y gestión de paquetes Python.

> **No ejecutar todo el repositorio ni iniciar sus menús como prueba.** Hay opciones que eliminan usuarios y sus directorios personales, cambian controles de seguridad, sobrescriben archivos o despliegan contenedores. Revisar primero el archivo elegido y probar en una VM descartable, sin acceso a infraestructura de producción.

## Mapa de herramientas

| Ruta | Función y efectos |
| --- | --- |
| [bash/detail_info.sh](bash/detail_info.sh) | Consulta sistema, red, usuarios y uso de disco; guarda un archivo `reporte_sistema_*.txt` en el directorio actual. |
| [bash/group_admin.sh](bash/group_admin.sh) | Menú para listar, crear o eliminar grupos y consultar miembros. |
| [bash/user_bash.sh](bash/user_bash.sh) | Administración de usuarios, grupos, permisos y propietarios. La eliminación usa `userdel -r`. |
| [bash/user_group_keys.sh](bash/user_group_keys.sh) | Generación de claves SSH y modificación de `authorized_keys` para usuarios o grupos. |
| [python/linux/user_python.py](python/linux/user_python.py), [group_admin.py](python/linux/group_admin.py) | Menús de usuarios, grupos y permisos; pese al nombre, `group_admin.py` también administra usuarios. |
| [python/linux/user_group_keys.py](python/linux/user_group_keys.py) | Variante Python de gestión de claves SSH; copia la clave pública sobre `authorized_keys`. |
| [python/linux/sys_monitor.py](python/linux/sys_monitor.py) | Métricas de CPU, memoria, discos, red y otros recursos; admite una muestra o monitoreo periódico y exportación JSON/CSV. |
| [python/linux/hardware_info_collector_linux.py](python/linux/hardware_info_collector_linux.py) | Inventario de hardware con salida YAML; algunas consultas dependen de herramientas o permisos del sistema. |
| [python/linux/security_script.py](python/linux/security_script.py) | Menús de firewall, SELinux/AppArmor, herramientas de auditoría y actualizaciones; puede instalar paquetes, editar configuración y activar servicios. |
| [python/select_services.py](python/select_services.py) | Busca imágenes y etiquetas en Docker Hub y escribe `selections.yaml`. Realiza solicitudes de red. |
| [python/crud_docker-compose.py](python/crud_docker-compose.py) | Genera y administra Compose a partir de selecciones; el subcomando `deploy` descarga imágenes y arranca contenedores. |
| [python/librery_cloud_pip.py](python/librery_cloud_pip.py) | Instalador interactivo de paquetes Python por categorías; modifica el entorno de Python elegido. |
| [python/windows/](python/windows/) | Inventario, menús de seguridad y una interfaz Tkinter para instalar paquetes. Requieren revisar las condiciones de cada script. |

## Requisitos

- Git para obtener una copia; Bash para los scripts de `bash/`.
- **Python 3.10 o superior para los menús Linux que usan `match/case`** (`user_python.py` y `group_admin.py`). El requisito anterior de Python 3.6 no cubría el código actual. No hay una matriz de compatibilidad validada para toda la colección.
- Linux con utilidades como `getent`, `useradd`, `userdel`, `usermod`, `groupadd`, `groupdel`, `chmod`, `chown` y OpenSSH según la función. No todos los scripts son portables entre distribuciones.
- Windows y PowerShell para los auditores de `python/windows/`; usan, entre otros, `winreg` y comandos de administración del sistema. `cloud_tkinter.py` requiere además Tkinter y pip.
- Privilegios de administrador **solo cuando una operación revisada lo requiera**. No ejecutar herramientas de inventario o instaladores de paquetes con privilegios elevados por defecto.

### Dependencias Python por utilidad

No se incluye un archivo de requisitos con versiones fijadas. Instalar solo lo necesario en un entorno virtual, no en el Python del sistema:

| Utilidad | Paquetes externos observados en los imports |
| --- | --- |
| `python/linux/sys_monitor.py` | `psutil`; `GPUtil` opcional. |
| `python/linux/hardware_info_collector_linux.py` | `psutil`, `PyYAML`; `py-cpuinfo`, `GPUtil` y `distro` opcionales. |
| `python/select_services.py` | `requests`, `PyYAML`. |
| `python/crud_docker-compose.py` | `PyYAML`; Docker con el plugin `docker compose` solo para desplegar. |

`os`, `subprocess`, `argparse`, `pwd` y `grp` forman parte de la biblioteca estándar, aunque los dos últimos son propios de Unix. No se requiere instalar `crypt` para los scripts descritos.

## Uso orientativo

```bash
git clone git@github.com:tunonalves/Sysadmin.git
cd Sysadmin
```

Antes de continuar, leer el código del archivo elegido, identificar entradas y salidas y preparar un entorno de laboratorio. Los siguientes ejemplos documentan interfaces existentes; **no se ejecutaron durante esta revisión**.

### Una muestra de monitoreo en Linux

Después de revisar `sys_monitor.py`, preparar un entorno virtual y su dependencia:

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install psutil
python3 python/linux/sys_monitor.py --once
```

`--once` termina después de una muestra; sin él, el monitor repite las consultas hasta interrumpirlo. `--json ruta` sobrescribe la salida JSON y `--csv ruta` añade filas. Los reportes pueden revelar direcciones, nombres de equipo y procesos: revisarlos antes de compartirlos.

El recolector de hardware admite `--output ruta` y `--show` y guarda YAML incluso sin esas opciones. El script Bash de inventario también escribe un reporte; no debe tratarse como una comprobación sin efectos sobre el disco.

### Selecciones y Compose, sin despliegue

Con un entorno virtual activo y después de autorizar las consultas a Docker Hub:

```bash
python3 -m pip install requests PyYAML
python3 python/select_services.py
python3 python/crud_docker-compose.py list
python3 python/crud_docker-compose.py create
```

Ejecutar ambos scripts desde el mismo directorio: las rutas `selections.yaml` y `out_stack/docker-compose.yml` son relativas al directorio de trabajo. `create` escribe o sobrescribe el Compose y necesita selecciones previas. El nombre real del gestor es `crud_docker-compose.py`, aunque el mensaje final del selector menciona `compose_manager.py`.

El gestor también tiene `read`, `update-tag`, `update-ports` y `delete`. Estos últimos modifican las selecciones; volver a generar el Compose para reflejar los cambios. **No usar `deploy` como validación:** llama a `docker compose pull` y `docker compose up -d`. Revisar imágenes, volúmenes, puertos y variables antes de autorizarlo. No introducir secretos en selecciones que puedan terminar en Git o en la salida de `read`.

## Riesgos y limitaciones

- Los menús de usuarios pueden borrar el home; no existe un respaldo automático general que haga segura esa operación. La colección tampoco incluye una programación general de tareas por `cron` lista para activar.
- Las herramientas SSH modifican acceso y permisos. La variante Bash genera claves sin frase de paso; la variante Python puede reemplazar `authorized_keys`. Revisar políticas de acceso y recuperación antes de usarlas.
- Algunos menús Python interpolan entradas en comandos con `shell=True`; no admitir entradas no confiables ni tratarlos como interfaces multiusuario seguras.
- Los menús de seguridad de Windows permiten cambiar firewall, Defender, SMBv1, RDP, UAC y otros controles. No son auditores exclusivamente de lectura; algunas opciones reducen la protección del equipo.
- Los instaladores de bibliotecas descargan paquetes y alteran el entorno. No son una instalación obligatoria de este repositorio ni fijan un conjunto reproducible de dependencias.
- No se identificó una suite automatizada de pruebas. Las consultas de inventario dependen de permisos, herramientas disponibles, hardware y sistema operativo; pueden devolver información parcial.

## Verificación documental

Se revisaron estáticamente archivos, imports, argumentos y operaciones relevantes, junto con las rutas del README y el formato del diff. **No se ejecutaron scripts ni menús, no se instalaron paquetes, no se crearon respaldos y no se modificaron usuarios, permisos, claves, redes, servicios o contenedores.** La ejecución y compatibilidad quedan pendientes de pruebas explícitas en un laboratorio; esta revisión no certifica seguridad operativa.
