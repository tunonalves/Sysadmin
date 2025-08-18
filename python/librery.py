# -*- coding: utf-8 -*-
"""
INSTALADOR INTERACTIVO DE LIBRERIAS CLOUD
Permite instalar librerías de servicios cloud con un menú fácil de usar

Autor: Asistente IA
Versión: 1.0
"""

import subprocess
import sys
import os
from datetime import datetime

class CloudLibraryInstaller:
    def __init__(self):
        self.installed_packages = []
        self.failed_packages = []
        
        # Diccionario con todas las librerías organizadas por categoría
        self.libraries = {
            "google": {
                "name": "Google Cloud & Drive",
                "packages": [
                    ("google-auth", "Autenticación Google"),
                    ("google-auth-oauthlib", "OAuth2 para Google"),
                    ("google-api-python-client", "Google APIs (Drive, Gmail, etc.)"),
                    ("google-cloud-storage", "Google Cloud Storage"),
                    ("google-cloud", "Google Cloud completo"),
                    ("firebase-admin", "Firebase Admin SDK")
                ]
            },
            "aws": {
                "name": "Amazon Web Services (AWS)",
                "packages": [
                    ("boto3", "AWS SDK completo (S3, EC2, Lambda, etc.)"),
                    ("awscli", "AWS Command Line Interface"),
                    ("s3fs", "Sistema de archivos para S3"),
                    ("aws-cdk-lib", "AWS Cloud Development Kit")
                ]
            },
            "azure": {
                "name": "Microsoft Azure",
                "packages": [
                    ("azure-storage-blob", "Azure Blob Storage"),
                    ("azure-storage-file-share", "Azure File Share"),
                    ("azure-identity", "Azure Identity"),
                    ("azure", "Azure SDK completo"),
                    ("msal", "Microsoft Authentication Library")
                ]
            },
            "dropbox": {
                "name": "Dropbox",
                "packages": [
                    ("dropbox", "Dropbox API oficial"),
                    ("dropbox-sdk", "Dropbox SDK alternativo")
                ]
            },
            "other_storage": {
                "name": "Otros Servicios de Almacenamiento",
                "packages": [
                    ("boxsdk", "Box.com API"),
                    ("pcloud", "pCloud API"),
                    ("mega.py", "Mega.nz API"),
                    ("oci", "Oracle Cloud Infrastructure"),
                    ("b2sdk", "Backblaze B2 Storage")
                ]
            },
            "universal": {
                "name": "Librerías Universales (Multi-Cloud)",
                "packages": [
                    ("cloudstorage", "Almacenamiento multi-cloud"),
                    ("apache-libcloud", "Apache Libcloud (multi-provider)"),
                    ("cloud-storage-service", "Servicio de almacenamiento unificado")
                ]
            },
            "media": {
                "name": "Servicios de Media y CDN",
                "packages": [
                    ("cloudinary", "Cloudinary (imágenes y videos)"),
                    ("imgurpython", "Imgur API"),
                    ("flickrapi", "Flickr API"),
                    ("wetransfer-python-sdk", "WeTransfer SDK")
                ]
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
                    ("cryptography", "Criptografía")
                ]
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
                    ("python-dotenv", "Variables de entorno")
                ]
            }
        }
    
    def clear_screen(self):
        """Limpia la pantalla de la consola"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def show_header(self):
        """Muestra el encabezado del programa"""
        print("=" * 70)
        print("      INSTALADOR INTERACTIVO DE LIBRERIAS CLOUD")
        print("=" * 70)
        print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Python: {sys.version.split()[0]}")
        print("-" * 70)
    
    def show_main_menu(self):
        """Muestra el menú principal"""
        print("\nSeleccione una opción:")
        print("\nCATEGORIAS DE LIBRERIAS:")
        
        categories = [
            ("1", "recommended", "RECOMENDADO"),
            ("2", "google", "GOOGLE"),
            ("3", "aws", "AWS"), 
            ("4", "azure", "AZURE"),
            ("5", "dropbox", "DROPBOX"),
            ("6", "other_storage", "OTROS STORAGE"),
            ("7", "universal", "UNIVERSAL"),
            ("8", "media", "MEDIA"),
            ("9", "utilities", "UTILIDADES")
        ]
        
        for num, key, label in categories:
            name = self.libraries[key]["name"]
            count = len(self.libraries[key]["packages"])
            print(f"{num}. [{label}] {name} ({count} paquetes)")
        
        print(f"\nOPCIONES ESPECIALES:")
        print("10. [COMPLETO] Instalar TODO (Instalación completa)")
        print("11. [ESTADO] Ver estado de instalaciones")
        print("12. [BUSCAR] Buscar paquete específico")
        print("13. [SALIR] Salir")
        print("-" * 70)
    
    def install_package(self, package_name, description=""):
        """Instala un paquete individual"""
        try:
            print(f"\nInstalando {package_name}...")
            if description:
                print(f"   Descripción: {description}")
            
            # Ejecutar pip install
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", package_name, "--quiet"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print(f"   [OK] {package_name} instalado correctamente")
                self.installed_packages.append((package_name, description))
                return True
            else:
                print(f"   [ERROR] Error instalando {package_name}")
                if result.stderr:
                    print(f"      Error: {result.stderr.strip()}")
                self.failed_packages.append((package_name, result.stderr.strip()))
                return False
                
        except Exception as e:
            print(f"   [ERROR] Excepción instalando {package_name}: {e}")
            self.failed_packages.append((package_name, str(e)))
            return False
    
    def install_category(self, category_key):
        """Instala todas las librerías de una categoría"""
        if category_key not in self.libraries:
            print("[ERROR] Categoría no válida")
            return
        
        category = self.libraries[category_key]
        print(f"\nINSTALANDO: {category['name']}")
        print("=" * 50)
        
        total_packages = len(category['packages'])
        successful = 0
        
        for i, (package, description) in enumerate(category['packages'], 1):
            print(f"\n[{i}/{total_packages}]", end="")
            if self.install_package(package, description):
                successful += 1
        
        # Resumen de la instalación
        failed = total_packages - successful
        print(f"\nRESUMEN DE INSTALACION:")
        print(f"   Exitosos: {successful}")
        if failed > 0:
            print(f"   Fallidos: {failed}")
        print(f"   Total: {total_packages}")
    
    def install_all(self):
        """Instala todas las librerías disponibles"""
        print("\nINSTALACION COMPLETA DE TODAS LAS LIBRERIAS")
        print("=" * 60)
        print("ADVERTENCIA: Esto puede tomar varios minutos")
        
        confirm = input("\n¿Continuar con la instalación completa? (s/n): ").lower()
        if confirm not in ['s', 'si', 'sí', 'y', 'yes']:
            print("[CANCELADO] Instalación cancelada")
            return
        
        all_packages = []
        for category in self.libraries.values():
            all_packages.extend(category['packages'])
        
        # Remover duplicados manteniendo el orden
        seen = set()
        unique_packages = []
        for pkg, desc in all_packages:
            if pkg not in seen:
                seen.add(pkg)
                unique_packages.append((pkg, desc))
        
        total = len(unique_packages)
        print(f"\nInstalando {total} paquetes únicos...")
        
        successful = 0
        for i, (package, description) in enumerate(unique_packages, 1):
            print(f"\n[{i}/{total}]", end="")
            if self.install_package(package, description):
                successful += 1
        
        failed = total - successful
        print(f"\n[COMPLETADO] INSTALACION COMPLETA TERMINADA!")
        print(f"   Exitosos: {successful}")
        if failed > 0:
            print(f"   Fallidos: {failed}")
        print(f"   Total procesados: {total}")
    
    def show_installation_status(self):
        """Muestra el estado de las instalaciones"""
        print("\nESTADO DE INSTALACIONES")
        print("=" * 50)
        
        if self.installed_packages:
            print(f"\n[OK] PAQUETES INSTALADOS EXITOSAMENTE ({len(self.installed_packages)}):")
            for i, (package, desc) in enumerate(self.installed_packages, 1):
                print(f"   {i:2d}. {package}")
                if desc:
                    print(f"       └─ {desc}")
        
        if self.failed_packages:
            print(f"\n[ERROR] PAQUETES CON ERRORES ({len(self.failed_packages)}):")
            for i, (package, error) in enumerate(self.failed_packages, 1):
                print(f"   {i:2d}. {package}")
                if error:
                    print(f"       └─ Error: {error[:60]}...")
        
        if not self.installed_packages and not self.failed_packages:
            print("\n[INFO] No se han realizado instalaciones aún")
    
    def search_package(self):
        """Busca un paquete específico"""
        search_term = input("\nIngrese el nombre del paquete a buscar: ").lower()
        
        found_packages = []
        for category_key, category in self.libraries.items():
            for package, description in category['packages']:
                if search_term in package.lower() or search_term in description.lower():
                    found_packages.append((package, description, category['name']))
        
        if found_packages:
            print(f"\n[ENCONTRADO] RESULTADOS DE BUSQUEDA para '{search_term}':")
            print("-" * 50)
            for i, (package, desc, cat) in enumerate(found_packages, 1):
                print(f"{i}. {package}")
                print(f"   Descripción: {desc}")
                print(f"   Categoría: {cat}")
                print()
            
            # Opción para instalar paquetes encontrados
            choice = input("¿Desea instalar algún paquete? (número/n): ")
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(found_packages):
                    package, desc, _ = found_packages[idx]
                    self.install_package(package, desc)
        else:
            print(f"[NO ENCONTRADO] No se encontraron paquetes que coincidan con '{search_term}'")
    
    def show_package_list(self, category_key):
        """Muestra la lista de paquetes de una categoría"""
        category = self.libraries[category_key]
        print(f"\nPAQUETES EN: {category['name']}")
        print("-" * 50)
        
        for i, (package, description) in enumerate(category['packages'], 1):
            print(f"{i:2d}. {package}")
            print(f"    └─ {description}")
        
        print(f"\nTotal: {len(category['packages'])} paquetes")
    
    def run(self):
        """Ejecuta el programa principal"""
        while True:
            self.clear_screen()
            self.show_header()
            self.show_main_menu()
            
            try:
                choice = input("\nSeleccione una opción (1-13): ").strip()
                
                if choice == "1":
                    self.install_category("recommended")
                elif choice == "2":
                    self.install_category("google")
                elif choice == "3":
                    self.install_category("aws")
                elif choice == "4":
                    self.install_category("azure")
                elif choice == "5":
                    self.install_category("dropbox")
                elif choice == "6":
                    self.install_category("other_storage")
                elif choice == "7":
                    self.install_category("universal")
                elif choice == "8":
                    self.install_category("media")
                elif choice == "9":
                    self.install_category("utilities")
                elif choice == "10":
                    self.install_all()
                elif choice == "11":
                    self.show_installation_status()
                elif choice == "12":
                    self.search_package()
                elif choice == "13":
                    print("\n¡Gracias por usar el instalador!")
                    print("¡Feliz programación con la nube!")
                    break
                else:
                    print("[ERROR] Opción no válida. Intente de nuevo.")
                
                if choice != "13":
                    input("\nPresiona Enter para continuar...")
                    
            except KeyboardInterrupt:
                print("\n\n[INTERRUMPIDO] Instalación interrumpida por el usuario")
                print("¡Hasta luego!")
                break
            except Exception as e:
                print(f"\n[ERROR] Error inesperado: {e}")
                input("Presiona Enter para continuar...")

def main():
    """Función principal"""
    try:
        # Verificar que pip esté disponible
        subprocess.run([sys.executable, "-m", "pip", "--version"], 
                      capture_output=True, check=True)
        
        # Crear y ejecutar el instalador
        installer = CloudLibraryInstaller()
        installer.run()
        
    except subprocess.CalledProcessError:
        print("[ERROR] pip no está disponible en este sistema")
        print("   Instale pip antes de ejecutar este programa")
        input("Presiona Enter para salir...")
    except Exception as e:
        print(f"[ERROR] Error fatal: {e}")
        input("Presiona Enter para salir...")

if __name__ == "__main__":
    main()