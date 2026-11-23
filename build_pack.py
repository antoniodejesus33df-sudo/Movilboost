#!/usr/bin/env python3
"""Arma MovilBoost: baja los mods de Modrinth y genera .mrpack + zip de respaldo."""
import json, os, subprocess, sys, urllib.parse, urllib.request, zipfile

MC = "1.21.11"
NAME = "MovilBoost"
VERSION = os.environ.get("PACK_VERSION", "1.0.0")
# (slug, obligatorio)
MODS = [
    ("fabric-api", True),
    ("sodium", True),
    ("sodium-extra", False),
    ("lithium", False),
    ("ferrite-core", False),
    ("immediatelyfast", False),
    ("entityculling", False),
    ("modernfix", False),
]
UA = {"User-Agent": "MovilBoost-build/1.0 (github actions)"}


def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()


def latest(project):
    q = urllib.parse.urlencode({
        "game_versions": json.dumps([MC]),
        "loaders": json.dumps(["fabric"]),
    })
    versions = json.loads(get(f"https://api.modrinth.com/v2/project/{project}/version?{q}"))
    for kind in ("release", "beta", "alpha"):
        found = [v for v in versions if v["version_type"] == kind]
        if found:
            return found[0]
    return None


def main():
    chosen = {}  # project_id -> version
    queue = list(MODS)
    while queue:
        slug, required = queue.pop(0)
        v = latest(slug)
        if v is None:
            if required:
                sys.exit(f"ERROR: {slug} no tiene version para {MC}")
            print(f"AVISO: {slug} no tiene version para {MC}, se omite")
            continue
        if v["project_id"] in chosen:
            continue
        chosen[v["project_id"]] = v
        print("OK", slug, v["version_number"])
        for d in v.get("dependencies", []):
            if d.get("dependency_type") == "required" and d.get("project_id") and d["project_id"] not in chosen:
                queue.append((d["project_id"], True))

    os.makedirs("out/mods", exist_ok=True)
    files = []
    for v in chosen.values():
        f = next((x for x in v["files"] if x.get("primary")), v["files"][0])
        data = get(f["url"])
        with open(os.path.join("out/mods", f["filename"]), "wb") as fh:
            fh.write(data)
        files.append({
            "path": "mods/" + f["filename"],
            "hashes": {"sha1": f["hashes"]["sha1"], "sha512": f["hashes"]["sha512"]},
            "env": {"client": "required", "server": "unsupported"},
            "downloads": [f["url"]],
            "fileSize": f["size"],
        })

    loaders = json.loads(get("https://meta.fabricmc.net/v2/versions/loader"))
    loader = next(x["version"] for x in loaders if x.get("stable"))

    index = {
        "formatVersion": 1,
        "game": "minecraft",
        "versionId": VERSION,
        "name": NAME,
        "summary": "Cliente de FPS para celular: mods de rendimiento y ajustes basicos.",
        "files": files,
        "dependencies": {"minecraft": MC, "fabric-loader": loader},
    }

    opts = open("overrides/options.txt", "rb").read()
    with zipfile.ZipFile(f"out/{NAME}-{VERSION}.mrpack", "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("modrinth.index.json", json.dumps(index, indent=2))
        z.writestr("overrides/options.txt", opts)

    # Respaldo: carpeta lista para copiar a la instancia (mods + options.txt)
    with zipfile.ZipFile(f"out/{NAME}-{VERSION}-manual.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for fn in os.listdir("out/mods"):
            z.write(os.path.join("out/mods", fn), "mods/" + fn)
        z.writestr("options.txt", opts)
        z.writestr("LEEME.txt",
                   f"{NAME} para Minecraft {MC} con Fabric {loader}.\n"
                   "Copia la carpeta mods y options.txt a la carpeta de tu instancia.\n"
                   "Renderizador recomendado: MobileGlues.\n")

    # ---- Un solo .jar: MovilBoost con todos los mods adentro (jar-in-jar) ----
    lib = f"out/fabric-loader-{loader}.jar"
    with open(lib, "wb") as fh:
        fh.write(get(f"https://maven.fabricmc.net/net/fabricmc/fabric-loader/{loader}/fabric-loader-{loader}.jar"))
    os.makedirs("out/classes", exist_ok=True)
    subprocess.check_call(["javac", "--release", "17", "-cp", lib, "-d", "out/classes",
                           "src/com/movilboost/MovilBoostPreLaunch.java"])
    nested = sorted(os.listdir("out/mods"))
    mod_json = {
        "schemaVersion": 1,
        "id": "movilboost",
        "version": VERSION,
        "name": "MovilBoost",
        "description": "Cliente de FPS para celular: Sodium, Lithium y mas, todo en un solo .jar.",
        "authors": ["MovilBoost"],
        "license": "MIT",
        "environment": "client",
        "entrypoints": {"preLaunch": ["com.movilboost.MovilBoostPreLaunch"]},
        "depends": {"fabricloader": ">=0.16.0", "minecraft": MC},
        "jars": [{"file": "META-INF/jars/" + n} for n in nested],
    }
    with zipfile.ZipFile(f"out/{NAME}-{VERSION}.jar", "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("fabric.mod.json", json.dumps(mod_json, indent=2))
        z.write("out/classes/com/movilboost/MovilBoostPreLaunch.class", "com/movilboost/MovilBoostPreLaunch.class")
        for n in nested:
            z.write(os.path.join("out/mods", n), "META-INF/jars/" + n)
    print("LISTO. Fabric loader", loader, "mods:", len(files))


main()
