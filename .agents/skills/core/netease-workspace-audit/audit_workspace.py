#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read-only audit for the NetEase mod component workspace.

Checks every versioned MCStudio project as a whole workspace: delivery ZIP
integrity, pack manifests and UUIDs, Python 2.7 syntax baseline, JSON UI risk
patterns, item/icon chains, pack noise, catalog references, immutable asset
hashes, and cross-project resource path collisions.

Writes nothing. Run with:

    python .agents/skills/core/netease-workspace-audit/audit_workspace.py

Exits non-zero only when a FAIL is reported. WARNING entries need judgement.
"""

from __future__ import print_function

import hashlib
import io
import tokenize
import json
import os
import re
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))

SKIP_DIRS = ("__pycache__", ".git", "docs", "tmp", "logs", "node_modules")

# Relative paths inside a pack that the engine merges across packs by inner key.
MERGEABLE_FILES = (
    "blocks.json",
    "textures/item_texture.json",
    "textures/terrain_texture.json",
    "ui/_ui_defs.json",
    "texts/languages.json",
)
MERGEABLE_PREFIXES = ("texts/",)

# Engine resolves these by file path, so two packs sharing a path conflict.
PATH_KEYED_PREFIXES = ("loot_tables/", "trading/", "particles/", "fogs/", "sounds/")

# Keyed by an identifier declared inside the file; sharing a path is safe while
# the identifiers differ.
IDENTIFIER_KEYED_PREFIXES = (
    "entities/",
    "netease_blocks/",
    "netease_recipes/",
    "models/",
    "render_controllers/",
    "spawn_rules/",
)

PY3_ONLY = (
    ("fstring", r"""(?<![A-Za-z0-9_])f['\"]"""),
    ("bare_super", r"super\s*\(\s*\)"),
    ("nonlocal", r"\bnonlocal\b"),
    ("yield_from", r"yield\s+from"),
    ("async_def", r"\basync\s+(def|with|for)\b"),
    ("raise_from", r"raise\s+\w+[^\n]*\sfrom\s"),
    ("kwonly", r"def\s+\w+\s*\([^)]*,\s*\*,"),
    ("exist_ok", r"exist_ok\s*="),
    ("annotation", r"def\s+\w+\s*\([^)]*:\s*\w+"),
)

UI_RISKS = (
    # Inherited templates and declared variables need a scope-aware project
    # check. Their mere presence is not evidence of an invalid control.
    # Bare-button text is checked structurally by check_json_ui below.
    ("enable_key", r"\"enable\""),
)

FORBIDDEN_RUNTIME = ("@minecraft/server", "@minecraft/server-ui", "import minecraft")

RESULTS = []


def record(level, area, message):
    RESULTS.append((level, area, message))


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def project_dirs(root):
    base = os.path.join(root, "mcstudio_project")
    if not os.path.isdir(base):
        return []
    return sorted(
        os.path.join(base, name)
        for name in os.listdir(base)
        if os.path.isdir(os.path.join(base, name))
    )


def pack_dir(project, kind):
    base = os.path.join(project, kind)
    if not os.path.isdir(base):
        return None
    entries = sorted(os.listdir(base))
    if not entries:
        return None
    return os.path.join(base, entries[0])


def walk_files(top):
    for dirpath, dirnames, filenames in os.walk(top):
        dirnames[:] = [d for d in dirnames if d not in ("__pycache__", ".git")]
        for name in sorted(filenames):
            yield os.path.join(dirpath, name)


def pack_relative_files(pack):
    out = {}
    for path in walk_files(pack):
        out[os.path.relpath(path, pack).replace(os.sep, "/")] = path
    return out


def load_json(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except Exception as exc:  # noqa: BLE001 - report, do not raise
        record("FAIL", "json", "%s: %s" % (path, exc))
        return None


def check_archives(root):
    for project in project_dirs(root):
        for path in walk_files(project):
            if not path.lower().endswith(".zip"):
                continue
            rel = os.path.relpath(path, root)
            try:
                with zipfile.ZipFile(path) as archive:
                    names = archive.namelist()
                    if len(names) != len(set(names)):
                        record("FAIL", "zip", "%s: duplicate entries" % rel)
                    bad = archive.testzip()
                    if bad:
                        record("FAIL", "zip", "%s: CRC failure %s" % (rel, bad))
                    noise = [
                        n for n in names
                        if n.endswith((".pyc", ".pyo", ".tmp", ".bak"))
                        or "__pycache__/" in n
                        or n.endswith(".gitkeep")
                    ]
                    if noise:
                        record("FAIL", "zip", "%s: %d cache/temp entries" % (rel, len(noise)))
                    wrapped = any(n.startswith("behavior_packs/") for n in names) and \
                        any(n.startswith("resource_packs/") for n in names)
                    name = os.path.basename(path)
                    direct = [n for n in names if n.endswith('/manifest.json') and n.count('/') == 1]
                    wrapped_manifests = [n for n in names if n.endswith('/manifest.json')
                                         and n.count('/') == 2
                                         and n.startswith(('behavior_packs/', 'resource_packs/'))]
                    if 'DeveloperProject' in name:
                        # Full editable source archives have their own documented purpose.
                        # They are neither game imports nor submission archives.
                        if not wrapped or len(wrapped_manifests) != 2:
                            record('FAIL', 'zip', '%s: developer source archive lost its BP/RP layout' % rel)
                    elif 'MCStudio' in name:
                        if not wrapped or len(wrapped_manifests) != 2:
                            record('FAIL', 'zip', '%s: MCStudio archive lost its pack wrappers' % rel)
                    elif 'Addon' in name or 'Developer_Submission' in name:
                        if wrapped:
                            record('FAIL', 'zip', '%s: submission archive must not wrap packs' % rel)
                        if len(direct) != 2:
                            record('FAIL', 'zip', '%s: submission archive requires two direct pack manifests' % rel)
                    else:
                        record('WARNING', 'zip', '%s: archive purpose not declared by its filename; integrity checked only' % rel)
            except zipfile.BadZipFile as exc:
                record("FAIL", "zip", "%s: %s" % (rel, exc))
    record("PASS", "zip", "delivery archive structure, CRC and noise checked")


def check_manifests(root):
    seen = {}
    for project in project_dirs(root):
        versions = {}
        for kind in ("behavior_packs", "resource_packs"):
            pack = pack_dir(project, kind)
            if not pack:
                continue
            manifest_path = os.path.join(pack, "manifest.json")
            if not os.path.isfile(manifest_path):
                record("FAIL", "manifest", "%s: %s has no manifest.json" % (project, kind))
                continue
            manifest = load_json(manifest_path)
            if not isinstance(manifest, dict):
                continue
            header = manifest.get("header", {})
            versions[kind] = (pack, manifest)
            if manifest.get("format_version") != 1:
                record("FAIL", "manifest", "%s: format_version must stay numeric 1"
                       % os.path.basename(pack))
            if "min_engine_version" not in header:
                record("WARNING", "manifest", "%s: no min_engine_version; developer-platform "
                       "packaging error 37 is caused by this omission"
                       % os.path.basename(pack))
            for key in ("uuid",):
                seen.setdefault(header.get(key), []).append(os.path.basename(pack))
            for module in manifest.get("modules", []):
                seen.setdefault(module.get("uuid"), []).append(
                    "%s:module" % os.path.basename(pack))
        bp = versions.get("behavior_packs")
        rp = versions.get("resource_packs")
        if bp and rp:
            if bp[1]["header"].get("version") != rp[1]["header"].get("version"):
                record("FAIL", "manifest", "%s: BP/RP version mismatch" % os.path.basename(project))
            target = rp[1]["header"]
            deps = bp[1].get("dependencies", [])
            if not any(d.get("uuid") == target.get("uuid")
                       and d.get("version") == target.get("version") for d in deps):
                record("FAIL", "manifest", "%s: BP does not depend on its RP header version"
                       % os.path.basename(project))
    for uuid, owners in seen.items():
        names = sorted(set(owners))
        # Same pack name in several versions of one component is the intended
        # upgrade path; different components must never share a UUID.
        if len(names) > 1:
            record("FAIL", "manifest", "UUID %s shared by %s" % (uuid, names))
    record("PASS", "manifest", "versions, dependencies and UUID ownership checked")


def print_baseline_findings(text):
    """Inspect top-level print arguments, ignoring literals and nested tuples."""
    try:
        tokens = [t for t in tokenize.generate_tokens(io.StringIO(text).readline)
                  if t.type not in (tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE,
                                    tokenize.INDENT, tokenize.DEDENT)]
    except tokenize.TokenError as error:
        location = error.args[1] if len(error.args) > 1 else (1, 0)
        return [("tokenize_error", location[0])]
    except IndentationError as error:
        return [("tokenize_error", error.lineno or 1)]
    findings = set()
    for i, token in enumerate(tokens[:-1]):
        if token.type != tokenize.NAME or token.string != "print" or tokens[i+1].string != "(":
            continue
        depth = 0
        for j in range(i+1, len(tokens)):
            current = tokens[j]
            if current.type == tokenize.OP:
                if current.string in ("(", "[", "{"):
                    depth += 1
                elif current.string in (")", "]", "}"):
                    depth -= 1
                    if depth == 0:
                        break
                elif depth == 1 and current.string == ",":
                    findings.add(("print_multi", token.start[0]))
            if depth == 1 and current.type == tokenize.NAME and current.string in ("end", "flush", "file"):
                if j+1 < len(tokens) and tokens[j+1].type == tokenize.OP and tokens[j+1].string == "=":
                    findings.add(("print_kw", token.start[0]))
    return sorted(findings)


def check_python_baseline(root):
    hits = 0
    for project in project_dirs(root):
        for path in walk_files(project):
            if not path.endswith(".py"):
                continue
            parts = path.replace(os.sep, "/").split("/")
            if any(p in ("tools", "tests", "deliverables", "dist") for p in parts):
                continue
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
            for label, pattern in PY3_ONLY:
                match = re.search(pattern, text)
                if match:
                    line = text[:match.start()].count("\n") + 1
                    record("FAIL", "python2", "%s:%d %s"
                           % (os.path.relpath(path, root), line, label))
                    hits += 1
            for label, line in print_baseline_findings(text):
                record("FAIL", "python2", "%s:%d %s"
                       % (os.path.relpath(path, root), line, label))
                hits += 1
            for token in FORBIDDEN_RUNTIME:
                if token in text:
                    record("FAIL", "python2", "%s uses %s"
                           % (os.path.relpath(path, root), token))
                    hits += 1
    if not hits:
        record("PASS", "python2", "shipped behavior code is Python 2.7 clean")


def check_json_ui(root):
    checked = 0
    for project in project_dirs(root):
        pack = pack_dir(project, "resource_packs")
        if not pack:
            continue
        ui = os.path.join(pack, "ui")
        if not os.path.isdir(ui):
            continue
        defs_path = os.path.join(ui, "_ui_defs.json")
        declared = []
        if os.path.isfile(defs_path):
            declared = load_json(defs_path).get("ui_defs", [])
        for entry in declared:
            if not os.path.isfile(os.path.join(pack, entry.replace("/", os.sep))):
                record("FAIL", "ui", "%s references missing %s"
                       % (os.path.basename(project), entry))
        listed = set(os.path.basename(e) for e in declared)
        for name in sorted(os.listdir(ui)):
            if not name.endswith(".json") or name == "_ui_defs.json":
                continue
            if name not in listed:
                record("FAIL", "ui", "%s/%s is not registered in _ui_defs.json"
                       % (os.path.basename(project), name))
            checked += 1
            with open(os.path.join(ui, name), encoding="utf-8") as handle:
                text = handle.read()
            for label, pattern in UI_RISKS:
                if re.search(pattern, text):
                    record("WARNING", "ui", "%s/%s contains %s"
                           % (os.path.basename(project), name, label))
            document = load_json(os.path.join(ui, name))
            if document is not None:
                bare = []

                def walk(node):
                    if isinstance(node, dict):
                        if "button" in str(node.get("type", "")) and "text" in node:
                            bare.append(1)
                        for value in node.values():
                            walk(value)
                    elif isinstance(node, list):
                        for value in node:
                            walk(value)

                walk(document)
                if bare:
                    record("WARNING", "ui", "%s/%s has %d bare-button text controls"
                           % (os.path.basename(project), name, len(bare)))
    record("PASS", "ui", "JSON UI registrations and risk patterns checked (%d files)" % checked)


def icon_keys(icon):
    """Normalize minecraft:icon, which may be a string or a template dict."""
    if isinstance(icon, str):
        return [icon]
    if isinstance(icon, dict):
        keys = [icon.get("texture")]
        textures = icon.get("textures")
        if isinstance(textures, str):
            keys.append(textures)
        elif isinstance(textures, list):
            for entry in textures:
                if isinstance(entry, str):
                    keys.append(entry)
                elif isinstance(entry, dict):
                    keys.append(entry.get("path"))
        return [k for k in keys if isinstance(k, str)]
    return []


def check_item_chain(root):
    for project in project_dirs(root):
        bp = pack_dir(project, "behavior_packs")
        rp = pack_dir(project, "resource_packs")
        name = os.path.basename(project)
        if bp:
            marker = os.path.join(bp, "entities")
            if not os.path.isdir(marker) or not os.listdir(marker):
                record("FAIL", "items", "%s: behavior pack has no entities/ marker" % name)
        if not rp:
            continue
        atlas_path = os.path.join(rp, "textures", "item_texture.json")
        atlas = {}
        if os.path.isfile(atlas_path):
            atlas = load_json(atlas_path).get("texture_data", {})
        for key, entry in sorted(atlas.items()):
            texture = entry.get("textures") if isinstance(entry, dict) else None
            # Values are pack-root relative and already carry the textures/ prefix.
            if not texture or not os.path.isfile(os.path.join(rp, texture + ".png")):
                record("FAIL", "items", "%s: atlas key %s has no PNG (%s)"
                       % (name, key, texture))
        behavior_ids = set()
        behavior_dir = os.path.join(bp, "netease_items_beh") if bp else None
        if behavior_dir and os.path.isdir(behavior_dir):
            for path in walk_files(behavior_dir):
                doc = load_json(path)
                if isinstance(doc, dict):
                    behavior_ids.add(
                        doc.get("minecraft:item", {}).get("description", {}).get("identifier"))
        resource_ids = set()
        resource_dir = os.path.join(rp, "netease_items_res")
        if os.path.isdir(resource_dir):
            for path in walk_files(resource_dir):
                doc = load_json(path)
                if not isinstance(doc, dict):
                    continue
                identifier = doc.get("minecraft:item", {}).get("description", {}).get("identifier")
                resource_ids.add(identifier)
                icon = doc.get("minecraft:item", {}).get("components", {}).get("minecraft:icon")
                keys = icon_keys(icon)
                if not keys:
                    record("FAIL", "items", "%s: %s has no usable minecraft:icon"
                           % (name, os.path.basename(path)))
                    continue
                for key in keys:
                    if key not in atlas:
                        record("FAIL", "items", "%s: %s bound to unknown atlas key %s"
                               % (name, os.path.basename(path), key))
        for missing in sorted(behavior_ids - resource_ids):
            record("FAIL", "items", "%s: %s has no resource-pack item definition"
                   % (name, missing))
        for missing in sorted(resource_ids - behavior_ids):
            record("FAIL", "items", "%s: %s has no behavior-pack item definition"
                   % (name, missing))
    record("PASS", "items", "entities markers and item/icon chains checked")


def check_pack_noise(root):
    for project in project_dirs(root):
        for kind in ("behavior_packs", "resource_packs"):
            pack = pack_dir(project, kind)
            if not pack:
                continue
            for path in walk_files(pack):
                base = os.path.basename(path)
                if base == ".gitkeep":
                    record("WARNING", "noise", "stray .gitkeep in %s"
                           % os.path.relpath(path, root))
                elif base.endswith((".pyc", ".pyo", ".tmp", ".bak")):
                    record("WARNING", "noise", "stray %s" % os.path.relpath(path, root))
    record("PASS", "noise", "pack contents scanned for stray files")


def check_catalog(root):
    catalog_path = os.path.join(root, "components", "catalog.json")
    if not os.path.isfile(catalog_path):
        record("FAIL", "catalog", "components/catalog.json is missing")
        return
    catalog = load_json(catalog_path)
    for component in catalog.get("components", []):
        references = [component.get("runtime_project"), component.get("component_document")]
        references += component.get("archived_runtime_projects", [])
        references += component.get("source_assets", [])
        references += component.get("design_documents", [])
        references += component.get("skills", [])
        references += component.get("deliverables", [])
        references += component.get("retained_baseline_projects", [])

        def evidence_refs(node):
            if isinstance(node, dict):
                for key, value in node.items():
                    if key in ('record', 'confirmation', 'cleanup_record') and isinstance(value, str):
                        references.append(value)
                    else:
                        evidence_refs(value)
            elif isinstance(node, list):
                for value in node:
                    evidence_refs(value)

        evidence_refs(component)
        for reference in references:
            if not reference:
                continue
            if not os.path.exists(os.path.join(root, reference.replace("/", os.sep))):
                record("FAIL", "catalog", "%s points at missing %s"
                       % (component.get("component_id"), reference))
    record("PASS", "catalog", "catalog references all resolve")


def check_immutable_assets(root):
    source = os.path.join(root, "source_structures")
    if not os.path.isdir(source):
        return
    originals = {}
    for path in walk_files(source):
        originals[os.path.basename(path)] = (path, sha256(path))
    for project in project_dirs(root):
        bp = pack_dir(project, "behavior_packs")
        if not bp:
            continue
        for path in walk_files(bp):
            if not path.lower().endswith(".mcstructure"):
                continue
            known = originals.get(os.path.basename(path))
            if known and known[1] != sha256(path):
                record("FAIL", "assets", "%s differs from source_structures/%s"
                       % (os.path.relpath(path, root), os.path.basename(path)))
    record("PASS", "assets", "runtime structure copies match immutable originals")


def classify(rel):
    if rel in MERGEABLE_FILES or rel.startswith(MERGEABLE_PREFIXES):
        return "mergeable"
    if rel.startswith(PATH_KEYED_PREFIXES):
        return "path-keyed"
    if rel.startswith(IDENTIFIER_KEYED_PREFIXES):
        return "identifier-keyed"
    return "review"


def identifiers(path):
    found = set()
    try:
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
    except Exception:  # noqa: BLE001
        return found
    for match in re.finditer(r'"identifier"\s*:\s*"([^"]+)"', text):
        found.add(match.group(1))
    for match in re.finditer(r'"(geometry\.[A-Za-z0-9_.]+)"', text):
        found.add(match.group(1))
    return found


def component_key(project_name):
    """Map a project directory name to its component identity.

    Two versions of one component share UUIDs, resource paths and pack names by
    design, so they are never compared; only different components are.
    """
    name = project_name
    if name.startswith("Netease"):
        name = name[len("Netease"):]
    return re.sub(r"_v[0-9][0-9A-Za-z_.]*$", "", name)


def check_cross_project(root):
    packs = []
    for project in project_dirs(root):
        name = os.path.basename(project)
        for kind in ("behavior_packs", "resource_packs"):
            pack = pack_dir(project, kind)
            if pack:
                packs.append((name, component_key(name), kind, pack))
    index = {}
    for name, key, kind, pack in packs:
        index[(name, kind)] = (key, pack_relative_files(pack))
    keys = sorted(index)
    compared = 0
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            left, right = keys[i], keys[j]
            if left[1] != right[1]:
                continue
            left_key = index[left][0]
            right_key = index[right][0]
            if left_key == right_key:
                continue
            left_files = index[left][1]
            right_files = index[right][1]
            common = set(left_files) & set(right_files)
            if not common:
                continue
            compared += 1
            for rel in sorted(common):
                if rel == "manifest.json":
                    continue
                a = left_files[rel]
                b = right_files[rel]
                if sha256(a) == sha256(b):
                    continue
                kind = classify(rel)
                if kind == "mergeable":
                    continue
                if kind == "identifier-keyed":
                    shared = identifiers(a) & identifiers(b)
                    if shared:
                        record("FAIL", "coexist", "%s and %s both declare %s with a shared "
                               "identifier: %s" % (left[0], right[0], rel, sorted(shared)))
                    continue
                level = "FAIL" if kind == "path-keyed" else "WARNING"
                record(level, "coexist", "%s and %s define different %s at the same path (%s); "
                       "the engine resolves it by path, so only one survives"
                       % (left[0], right[0], kind, rel))
    record("PASS", "coexist", "cross-component resource paths compared (%d component pairs)"
           % compared)


def main():
    root = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_ROOT
    print("WORKSPACE=%s" % root)
    print("")
    check_archives(root)
    check_manifests(root)
    check_python_baseline(root)
    check_json_ui(root)
    check_item_chain(root)
    check_pack_noise(root)
    check_catalog(root)
    check_immutable_assets(root)
    check_cross_project(root)
    print("")
    order = ("FAIL", "WARNING", "PASS")
    for level in order:
        group = [entry for entry in RESULTS if entry[0] == level]
        if not group:
            continue
        print("--- %s (%d) ---" % (level, len(group)))
        for _, area, message in group:
            print("  [%s] %s" % (area, message))
        print("")
    failures = [entry for entry in RESULTS if entry[0] == "FAIL"]
    print("RESULT=%s  failures=%d  warnings=%d"
          % ("FAIL" if failures else "PASS", len(failures),
             len([e for e in RESULTS if e[0] == "WARNING"])))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
