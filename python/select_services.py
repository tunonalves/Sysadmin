#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import sys
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional

API_SEARCH = "https://hub.docker.com/v2/search/repositories/"
API_TAGS = "https://hub.docker.com/v2/repositories/{namespace}/{name}/tags"

SELECTIONS_PATH = Path("selections.yaml")


def load_selections() -> Dict[str, Any]:
    if SELECTIONS_PATH.exists():
        return yaml.safe_load(SELECTIONS_PATH.read_text(encoding="utf-8")) or {"services": []}
    return {"services": []}


def save_selections(data: Dict[str, Any]) -> None:
    SELECTIONS_PATH.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print(f"[OK] Selecciones guardadas en {SELECTIONS_PATH.resolve()}")


def search_repos(query: str, page_size: int = 10) -> List[Dict[str, Any]]:
    params = {"query": query, "page_size": page_size, "page": 1}
    r = requests.get(API_SEARCH, params=params, timeout=15)
    r.raise_for_status()
    data = r.json()
    return data.get("results", [])


def list_tags(namespace: str, name: str, page_size: int = 15) -> List[Dict[str, Any]]:
    url = API_TAGS.format(namespace=namespace, name=name)
    params = {"page_size": page_size, "page": 1, "ordering": "last_updated"}  # recientes primero
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    data = r.json()
    return data.get("results", [])


def choose(options: List[str], prompt: str, allow_back: bool = True) -> Optional[int]:
    for i, opt in enumerate(options, 1):
        print(f"{i}. {opt}")
    if allow_back:
        print("0. Volver / Cancelar")
    while True:
        sel = input(f"{prompt} (número): ").strip()
        if sel.isdigit():
            idx = int(sel)
            if allow_back and idx == 0:
                return None
            if 1 <= idx <= len(options):
                return idx - 1
        print("Entrada inválida. Probá de nuevo.")


def main():
    print("=== Selector de servicios desde Docker Hub ===")
    selections = load_selections()

    while True:
        q = input("\nBuscar en Docker Hub (ej: nginx, postgres, traefik) o ENTER para terminar: ").strip()
        if not q:
            break

        print("\nBuscando repositorios...")
        results = search_repos(q)
        if not results:
            print("No se encontraron repos.")
            continue

        opts = []
        meta = []
        for r in results:
            ns = r.get("namespace") or "library"  # oficios suelen ir en library
            nm = r.get("name")
            desc = (r.get("short_description") or "").strip()
            pulls = r.get("pull_count") or 0
            stars = r.get("star_count") or 0
            opts.append(f"{ns}/{nm}  ⭐ {stars}  ⬇ {pulls}  — {desc[:80]}")
            meta.append((ns, nm))

        idx = choose(opts, "Elegí un repositorio")
        if idx is None:
            continue
        namespace, name = meta[idx]

        print(f"\nListando tags recientes de {namespace}/{name} ...")
        tags = list_tags(namespace, name)
        if not tags:
            print("No se encontraron tags.")
            continue

        tag_opts = []
        for t in tags:
            tag_name = t.get("name")
            last = t.get("last_updated", "")[:19].replace("T", " ")
            size = t.get("full_size", 0)
            tag_opts.append(f"{tag_name}  (actualizado: {last}, size: {size} bytes)")

        t_idx = choose(tag_opts, "Elegí un tag")
        if t_idx is None:
            continue
        tag_name = tags[t_idx].get("name")

        svc_name = input("Nombre del servicio en compose (ej: web, db, proxy): ").strip() or name
        # Campos opcionales
        ports = input("Puertos (formato host:container, separados por coma; ej 8080:80,8443:443) o vacío: ").strip()
        volumes = input("Volúmenes (formato host:container[:ro], separados por coma) o vacío: ").strip()
        env_input = input("Variables de entorno (KEY=VAL separadas por coma) o vacío: ").strip()

        port_list = [p.strip() for p in ports.split(",") if p.strip()] if ports else []
        vol_list = [v.strip() for v in volumes.split(",") if v.strip()] if volumes else []
        env_dict = {}
        if env_input:
            for kv in env_input.split(","):
                if "=" in kv:
                    k, v = kv.split("=", 1)
                    env_dict[k.strip()] = v.strip()

        # guardar selección (si existe, reemplaza por svc_name)
        services = selections["services"]
        # eliminar si existe el mismo svc_name
        services = [s for s in services if s.get("service_name") != svc_name]
        services.append({
            "service_name": svc_name,
            "namespace": namespace,
            "name": name,
            "image": f"{namespace}/{name}",
            "tag": tag_name,
            "ports": port_list,
            "volumes": vol_list,
            "environment": env_dict,
            "restart": "unless-stopped"
        })
        selections["services"] = services
        save_selections(selections)

    print("\nListo. Podés revisar/editar tus selecciones en selections.yaml")
    print("Luego usá compose_manager.py para crear/editar/desplegar tu docker-compose.")


if __name__ == "__main__":
    try:
        main()
    except requests.HTTPError as e:
        print(f"[HTTP ERROR] {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)
