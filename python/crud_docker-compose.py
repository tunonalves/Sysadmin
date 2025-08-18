#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

import yaml

SELECTIONS_PATH = Path("selections.yaml")
DEFAULT_OUTDIR = Path("out_stack")
DEFAULT_COMPOSE = "docker-compose.yml"


def load_yaml(p: Path) -> Dict[str, Any]:
    if not p.exists():
        return {}
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


def save_yaml(p: Path, data: Dict[str, Any]) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def selections() -> Dict[str, Any]:
    data = load_yaml(SELECTIONS_PATH)
    if "services" not in data:
        data["services"] = []
    return data


def to_compose(services: List[Dict[str, Any]]) -> Dict[str, Any]:
    compose: Dict[str, Any] = {"version": "3.9", "services": {}}
    for s in services:
        name = s["service_name"]
        entry: Dict[str, Any] = {
            "image": f"{s['image']}:{s['tag']}",
            "restart": s.get("restart", "unless-stopped")
        }
        if s.get("ports"):
            entry["ports"] = s["ports"]
        if s.get("volumes"):
            entry["volumes"] = s["volumes"]
        if s.get("environment"):
            entry["environment"] = s["environment"]
        compose["services"][name] = entry
    return compose


def find_service(svcs: List[Dict[str, Any]], svc_name: str) -> Optional[Dict[str, Any]]:
    for s in svcs:
        if s.get("service_name") == svc_name:
            return s
    return None


def cmd_create(args):
    sels = selections()
    svcs = sels["services"]
    if not svcs:
        print("No hay servicios en selections.yaml. Ejecuntá primero select_services.py")
        sys.exit(1)
    compose = to_compose(svcs)
    outdir = Path(args.out_dir or DEFAULT_OUTDIR)
    outpath = outdir / (args.filename or DEFAULT_COMPOSE)
    save_yaml(outpath, compose)
    print(f"[OK] Compose generado: {outpath.resolve()}")


def cmd_read(args):
    path = Path(args.path or DEFAULT_OUTDIR / DEFAULT_COMPOSE)
    data = load_yaml(path)
    if not data:
        print(f"No existe {path}. Generá uno con 'create'.")
        return
    print(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))


def cmd_list(args):
    sels = selections()
    for s in sels["services"]:
        print(f"- {s['service_name']}: {s['image']}:{s['tag']}  ports={s.get('ports', [])}")


def cmd_update_tag(args):
    sels = selections()
    svcs = sels["services"]
    s = find_service(svcs, args.service)
    if not s:
        print("Servicio no encontrado.")
        sys.exit(1)
    s["tag"] = args.tag
    save_yaml(SELECTIONS_PATH, sels)
    print(f"[OK] Tag actualizado. {s['service_name']} -> {s['image']}:{s['tag']}")


def cmd_update_ports(args):
    sels = selections()
    svcs = sels["services"]
    s = find_service(svcs, args.service)
    if not s:
        print("Servicio no encontrado.")
        sys.exit(1)
    s["ports"] = [p.strip() for p in (args.ports or "").split(",") if p.strip()]
    save_yaml(SELECTIONS_PATH, sels)
    print(f"[OK] Puertos actualizados: {s['service_name']} -> {s['ports']}")


def cmd_delete(args):
    sels = selections()
    before = len(sels["services"])
    sels["services"] = [x for x in sels["services"] if x.get("service_name") != args.service]
    after = len(sels["services"])
    save_yaml(SELECTIONS_PATH, sels)
    print(f"[OK] Eliminado '{args.service}' ({before - after} elemento/s).")


def cmd_deploy(args):
    outdir = Path(args.out_dir or DEFAULT_OUTDIR)
    compose_file = args.filename or DEFAULT_COMPOSE
    if not (outdir / compose_file).exists():
        print("Compose no encontrado. Corré primero 'create'.")
        sys.exit(1)

    base_cmd = ["docker", "compose", "-f", compose_file]
    if args.project:
        base_cmd += ["-p", args.project]

    print("[INFO] docker compose pull …")
    subprocess.call(base_cmd + ["pull"], cwd=str(outdir))

    print("[INFO] docker compose up -d …")
    rc = subprocess.call(base_cmd + ["up", "-d"], cwd=str(outdir))
    if rc == 0:
        print("[OK] Despliegue completado.")
    else:
        print(f"[ERROR] Código de salida: {rc}")
        sys.exit(rc)


def build_parser():
    p = argparse.ArgumentParser(description="CRUD de docker-compose a partir de selections.yaml")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("create", help="Generar docker-compose.yml desde selections.yaml")
    c.add_argument("-o", "--out-dir", type=str, default=str(DEFAULT_OUTDIR))
    c.add_argument("-f", "--filename", type=str, default=DEFAULT_COMPOSE)
    c.set_defaults(func=cmd_create)

    r = sub.add_parser("read", help="Mostrar un docker-compose existente")
    r.add_argument("path", nargs="?", help="Ruta al compose (por defecto out_stack/docker-compose.yml)")
    r.set_defaults(func=cmd_read)

    l = sub.add_parser("list", help="Listar servicios en selections.yaml")
    l.set_defaults(func=cmd_list)

    ut = sub.add_parser("update-tag", help="Actualizar tag de un servicio")
    ut.add_argument("service", help="Nombre de servicio (service_name)")
    ut.add_argument("tag", help="Nuevo tag")
    ut.set_defaults(func=cmd_update_tag)

    up = sub.add_parser("update-ports", help="Actualizar puertos de un servicio")
    up.add_argument("service")
    up.add_argument("ports", help="host:container separados por coma (ej 8080:80,8443:443)")
    up.set_defaults(func=cmd_update_ports)

    d = sub.add_parser("delete", help="Eliminar un servicio de selections.yaml")
    d.add_argument("service")
    d.set_defaults(func=cmd_delete)

    dep = sub.add_parser("deploy", help="Desplegar mediante docker compose")
    dep.add_argument("-o", "--out-dir", type=str, default=str(DEFAULT_OUTDIR))
    dep.add_argument("-f", "--filename", type=str, default=DEFAULT_COMPOSE)
    dep.add_argument("-p", "--project", type=str, default=None)
    dep.set_defaults(func=cmd_deploy)

    return p


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelado por el usuario.")
