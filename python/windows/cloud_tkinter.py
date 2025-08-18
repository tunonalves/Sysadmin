# -*- coding: utf-8 -*-
"""
Instalador de librerías cloud con GUI (Tkinter)
Adaptado desde el instalador interactivo en consola.

Características principales:
- Panel de categorías y paquetes con descripciones.
- Botones para instalar paquete seleccionado, categoría completa o TODO.
- Buscador de paquetes por nombre/descripcion.
- Registro (log) en tiempo real y barra de progreso.
- Listas de paquetes instalados y fallidos.

Requisitos: Python 3.8+, pip disponible.

Ejecutar:  python cloud_library_installer_tk.py
"""

import os
import sys
import subprocess
import threading
import queue
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox

# ---------------------------
# MODELO DE DATOS (categorías)
# ---------------------------
LIBRARIES = {
    "google": {
        "name": "Google Cloud & Drive",
        "packages": [
            ("google-auth", "Autenticación Google"),
            ("google-auth-oauthlib", "OAuth2 para Google"),
            ("google-api-python-client", "Google APIs (Drive, Gmail, etc.)"),
            ("google-cloud-storage", "Google Cloud Storage"),
            ("google-cloud", "Google Cloud completo"),
            ("firebase-admin", "Firebase Admin SDK"),
        ],
    },
    "aws": {
        "name": "Amazon Web Services (AWS)",
        "packages": [
            ("boto3", "AWS SDK completo (S3, EC2, Lambda, etc.)"),
            ("awscli", "AWS Command Line Interface"),
            ("s3fs", "Sistema de archivos para S3"),
            ("aws-cdk-lib", "AWS Cloud Development Kit"),
        ],
    },
    "azure": {
        "name": "Microsoft Azure",
        "packages": [
            ("azure-storage-blob", "Azure Blob Storage"),
            ("azure-storage-file-share", "Azure File Share"),
            ("azure-identity", "Azure Identity"),
            ("azure", "Azure SDK completo"),
            ("msal", "Microsoft Authentication Library"),
        ],
    },
    "dropbox": {
        "name": "Dropbox",
        "packages": [
            ("dropbox", "Dropbox API oficial"),
            ("dropbox-sdk", "Dropbox SDK alternativo"),
        ],
    },
    "other_storage": {
        "name": "Otros Servicios de Almacenamiento",
        "packages": [
            ("boxsdk", "Box.com API"),
            ("pcloud", "pCloud API"),
            ("mega.py", "Mega.nz API"),
            ("oci", "Oracle Cloud Infrastructure"),
            ("b2sdk", "Backblaze B2 Storage"),
        ],
    },
    "universal": {
        "name": "Librerías Universales (Multi-Cloud)",
        "packages": [
            ("cloudstorage", "Almacenamiento multi-cloud"),
            ("apache-libcloud", "Apache Libcloud (multi-provider)"),
            ("cloud-storage-service", "Servicio de almacenamiento unificado"),
        ],
    },
    "media": {
        "name": "Servicios de Media y CDN",
        "packages": [
            ("cloudinary", "Cloudinary (imágenes y videos)"),
            ("imgurpython", "Imgur API"),
            ("flickrapi", "Flickr API"),
            ("wetransfer-python-sdk", "WeTransfer SDK"),
        ],
    },
    "utilities": {
        "name": "Utilidades y Herramientas",
        "packages": [
            ("requests", "HTTP requests avanzados"),
            ("requests-oauthlib", "OAuth para requests"),
            ("httpx", "Cliente HTTP asíncrono"),
            ("pyjwt", "JSON Web Tokens"),
            ("authlib", "Librería de autenticación"),
            ("python-dotenv", "Variables de entorno"),
            ("cryptography", "Criptografía"),
        ],
    },
    "recommended": {
        "name": "Paquete Recomendado (Lo más usado)",
        "packages": [
            ("boto3", "AWS S3 y más"),
            ("google-api-python-client", "Google Drive API"),
            ("dropbox", "Dropbox API"),
            ("azure-storage-blob", "Azure Storage"),
            ("requests", "HTTP requests"),
            ("cloudstorage", "Multi-cloud storage"),
            ("python-dotenv", "Variables de entorno"),
        ],
    },
}

CATEGORIES_UI = [
    ("recommended", "RECOMENDADO"),
    ("google", "GOOGLE"),
    ("aws", "AWS"),
    ("azure", "AZURE"),
    ("dropbox", "DROPBOX"),
    ("other_storage", "OTROS STORAGE"),
    ("universal", "UNIVERSAL"),
    ("media", "MEDIA"),
    ("utilities", "UTILIDADES"),
]

# ---------------------------
# LÓGICA DE INSTALACIÓN (worker)
# ---------------------------
class InstallerWorker(threading.Thread):
    def __init__(self, tasks, log_queue, status_cb=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tasks = tasks  # lista de (package, description)
        self.log_queue = log_queue
        self.status_cb = status_cb
        self.success = []
        self.fail = []
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def run(self):
        total = len(self.tasks)
        for i, (pkg, desc) in enumerate(self.tasks, 1):
            if self._stop_event.is_set():
                break
            self._log(f"[{i}/{total}] Instalando {pkg} — {desc}")
            ok = self.install_package(pkg)
            if ok:
                self.success.append(pkg)
                self._log(f"   [OK] {pkg} instalado\n")
            else:
                self.fail.append(pkg)
                self._log(f"   [ERROR] Falló {pkg}\n")
            if self.status_cb:
                self.status_cb(i, total)
        self._log("Proceso finalizado.")

    def install_package(self, package_name) -> bool:
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", package_name, "--quiet"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                return True
            else:
                if result.stderr:
                    self._log(f"stderr: {result.stderr.strip()}")
                return False
        except Exception as e:
            self._log(f"Excepción instalando {package_name}: {e}")
            return False

    def _log(self, msg: str):
        self.log_queue.put(msg)

# ---------------------------
# INTERFAZ GRÁFICA
# ---------------------------
class CloudInstallerGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Instalador de Librerías Cloud")
        self.geometry("1100x700")
        self.minsize(900, 600)

        self.log_queue = queue.Queue()
        self.installed_list = []
        self.failed_list = []
        self.current_worker = None

        self._build_ui()
        self.after(100, self._poll_log_queue)

    def _build_ui(self):
        # Header
        header = ttk.Frame(self)
        header.pack(fill=tk.X, padx=10, pady=8)
        title = ttk.Label(header, text="Instalador de Librerías Cloud (Tkinter)", font=("Segoe UI", 14, "bold"))
        title.pack(side=tk.LEFT)
        info = ttk.Label(header, text=f"Python {sys.version.split()[0]} — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        info.pack(side=tk.RIGHT)

        # Main Paned Window
        paned = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)

        # Left: Categories and packages
        left = ttk.Frame(paned)
        paned.add(left, weight=1)

        # Categories list
        cat_frame = ttk.LabelFrame(left, text="Categorías")
        cat_frame.pack(fill=tk.BOTH, expand=False, pady=(0, 8))
        self.cat_list = tk.Listbox(cat_frame, height=10, exportselection=False)
        self.cat_list.pack(fill=tk.BOTH, expand=True)
        for key, label in CATEGORIES_UI:
            self.cat_list.insert(tk.END, f"[{label}] {LIBRARIES[key]['name']}")
        self.cat_list.bind("<<ListboxSelect>>", self._on_category_select)
        self.cat_list.selection_set(0)

        # Packages list
        pkg_frame = ttk.LabelFrame(left, text="Paquetes")
        pkg_frame.pack(fill=tk.BOTH, expand=True)
        self.pkg_list = tk.Listbox(pkg_frame, height=14, exportselection=False)
        self.pkg_list.pack(fill=tk.BOTH, expand=True)

        # Right: Controls, status, log
        right = ttk.Frame(paned)
        paned.add(right, weight=2)

        # Controls
        controls = ttk.LabelFrame(right, text="Acciones")
        controls.pack(fill=tk.X)

        self.btn_install_pkg = ttk.Button(controls, text="Instalar paquete seleccionado", command=self.install_selected_package)
        self.btn_install_pkg.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        self.btn_install_cat = ttk.Button(controls, text="Instalar categoría", command=self.install_category)
        self.btn_install_cat.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        self.btn_install_all = ttk.Button(controls, text="Instalar TODO", command=self.install_all)
        self.btn_install_all.grid(row=0, column=2, padx=5, pady=5, sticky="ew")

        # Search
        ttk.Label(controls, text="Buscar paquete:").grid(row=1, column=0, sticky="w", padx=5)
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(controls, textvariable=self.search_var)
        self.search_entry.grid(row=1, column=1, sticky="ew", padx=5)
        self.btn_search = ttk.Button(controls, text="Buscar y mostrar", command=self.search_packages)
        self.btn_search.grid(row=1, column=2, padx=5, pady=5)
        controls.columnconfigure(1, weight=1)

        # Progress
        prog = ttk.LabelFrame(right, text="Progreso")
        prog.pack(fill=tk.X, pady=(8, 0))
        self.progress = ttk.Progressbar(prog, orient=tk.HORIZONTAL, mode="determinate")
        self.progress.pack(fill=tk.X, padx=8, pady=8)

        # Status lists
        status = ttk.Panedwindow(right, orient=tk.HORIZONTAL)
        status.pack(fill=tk.BOTH, expand=False, pady=(8, 0))

        installed_frame = ttk.LabelFrame(status, text="Instalados")
        status.add(installed_frame, weight=1)
        self.lst_installed = tk.Listbox(installed_frame, height=6)
        self.lst_installed.pack(fill=tk.BOTH, expand=True)

        failed_frame = ttk.LabelFrame(status, text="Fallidos")
        status.add(failed_frame, weight=1)
        self.lst_failed = tk.Listbox(failed_frame, height=6)
        self.lst_failed.pack(fill=tk.BOTH, expand=True)

        # Log
        log_frame = ttk.LabelFrame(right, text="Log")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        self.log_text = tk.Text(log_frame, height=12)
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # Footer buttons
        footer = ttk.Frame(self)
        footer.pack(fill=tk.X, padx=10, pady=(0, 10))
        ttk.Button(footer, text="Limpiar log", command=self._clear_log).pack(side=tk.LEFT)
        ttk.Button(footer, text="Salir", command=self.destroy).pack(side=tk.RIGHT)

        # Inicializa la lista de paquetes según la categoría seleccionada inicialmente
        self._fill_packages_for_selected_category()

    # --------------------
    # Helpers de UI
    # --------------------
    def _on_category_select(self, event=None):
        self._fill_packages_for_selected_category()

    def _fill_packages_for_selected_category(self):
        sel = self.cat_list.curselection()
        if not sel:
            return
        idx = sel[0]
        cat_key = CATEGORIES_UI[idx][0]
        self.pkg_list.delete(0, tk.END)
        for pkg, desc in LIBRARIES[cat_key]["packages"]:
            self.pkg_list.insert(tk.END, f"{pkg} — {desc}")

    def _append_log(self, text: str):
        self.log_text.insert(tk.END, text + "\n")
        self.log_text.see(tk.END)

    def _clear_log(self):
        self.log_text.delete("1.0", tk.END)

    def _poll_log_queue(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self._append_log(msg)
        except queue.Empty:
            pass
        self.after(150, self._poll_log_queue)

    def _set_progress(self, current, total):
        self.progress["maximum"] = max(total, 1)
        self.progress["value"] = current
        if current >= total:
            # Al finalizar, refrescamos listas
            self._refresh_status_lists()
            self.current_worker = None
            messagebox.showinfo("Completado", "Proceso finalizado.")

    def _refresh_status_lists(self):
        # Rellena las listas visuales con el estado actual del worker
        self.lst_installed.delete(0, tk.END)
        self.lst_failed.delete(0, tk.END)
        if self.current_worker:
            for p in self.current_worker.success:
                self.lst_installed.insert(tk.END, p)
            for p in self.current_worker.fail:
                self.lst_failed.insert(tk.END, p)

    def _start_worker(self, tasks):
        if not tasks:
            messagebox.showwarning("Sin paquetes", "No hay paquetes para instalar.")
            return
        if self.current_worker and self.current_worker.is_alive():
            messagebox.showinfo("En progreso", "Ya hay una instalación en curso.")
            return
        self.progress["value"] = 0
        self.current_worker = InstallerWorker(tasks, self.log_queue, status_cb=self._set_progress)
        self.current_worker.daemon = True
        self.current_worker.start()

    # --------------------
    # Acciones
    # --------------------
    def install_selected_package(self):
        cat_sel = self.cat_list.curselection()
        pkg_sel = self.pkg_list.curselection()
        if not cat_sel or not pkg_sel:
            messagebox.showwarning("Selección inválida", "Elegí una categoría y un paquete.")
            return
        cat_key = CATEGORIES_UI[cat_sel[0]][0]
        pkg, desc = LIBRARIES[cat_key]["packages"][pkg_sel[0]]
        self._start_worker([(pkg, desc)])

    def install_category(self):
        sel = self.cat_list.curselection()
        if not sel:
            messagebox.showwarning("Sin categoría", "Elegí una categoría.")
            return
        cat_key = CATEGORIES_UI[sel[0]][0]
        tasks = LIBRARIES[cat_key]["packages"]
        if messagebox.askyesno("Confirmar", f"¿Instalar {len(tasks)} paquetes de '{LIBRARIES[cat_key]['name']}'?"):
            self._start_worker(tasks)

    def install_all(self):
        # Construir lista única (sin duplicados) en orden
        seen = set()
        tasks = []
        for cat in LIBRARIES.values():
            for pkg, desc in cat["packages"]:
                if pkg not in seen:
                    seen.add(pkg)
                    tasks.append((pkg, desc))
        if messagebox.askyesno("Confirmar", f"Esto instalará {len(tasks)} paquetes. ¿Continuar?"):
            self._start_worker(tasks)

    def search_packages(self):
        term = self.search_var.get().strip().lower()
        if not term:
            messagebox.showinfo("Buscar", "Escribí parte del nombre o descripción del paquete.")
            return
        matches = []
        for cat_key, cat in LIBRARIES.items():
            for pkg, desc in cat["packages"]:
                if term in pkg.lower() or term in (desc or "").lower():
                    matches.append((cat_key, pkg, desc))
        if not matches:
            messagebox.showinfo("Buscar", "No se encontraron coincidencias.")
            return
        # Mostrar resultados en la lista de paquetes y seleccionar categoría del primer match
        first_cat = matches[0][0]
        # Seleccionar categoría correspondiente
        idx = [i for i, (k, _) in enumerate(CATEGORIES_UI) if k == first_cat]
        if idx:
            self.cat_list.selection_clear(0, tk.END)
            self.cat_list.selection_set(idx[0])
            self._fill_packages_for_selected_category()
        # Filtrar la lista de paquetes temporalmente para mostrar sólo los matches
        self.pkg_list.delete(0, tk.END)
        for cat_key, pkg, desc in matches:
            self.pkg_list.insert(tk.END, f"{pkg} — {desc}")
        self._append_log(f"Encontrados {len(matches)} paquetes para '{term}'.")


if __name__ == "__main__":
    # Comprobación rápida de pip
    try:
        subprocess.run([sys.executable, "-m", "pip", "--version"], capture_output=True, check=True)
    except subprocess.CalledProcessError:
        messagebox.showerror("Error", "pip no está disponible en este sistema.")
        sys.exit(1)

    app = CloudInstallerGUI()
    app.mainloop()
