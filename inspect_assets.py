# Remnant: From the Ashes - Casual Mod | flexeykinDEV
"""Look inside unpacked game assets (build/vanilla) while writing rules.

    python inspect_assets.py asset  <file.uasset>            properties of every object
    python inspect_assets.py table  <file.uasset> [filter]   DataTable rows, one per line
    python inspect_assets.py fields <path part> [field]      numeric fields used by a folder
"""
import collections
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools import uasset

VANILLA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "build", "vanilla")
SKIP_CLASSES = {"Function", "BlueprintGeneratedClass", "WidgetBlueprintGeneratedClass", "EdGraph",
                "MetaData", "UserDefinedStruct", "UserDefinedEnum"}


def show_asset(path):
    _, _, _, exports = uasset.parse(path)
    for n, export in enumerate(exports, 1):
        if export["class"] in SKIP_CLASSES or export["class"].startswith("K2Node"):
            continue
        print(f"export #{n} {export['name']} ({export['class']})")
        for p in export["props"]:
            value = p["value"]
            if isinstance(value, float):
                value = f"{value:g}"
            text = p["name"] if value is None else f"{p['name']} = {value}"
            print(f"  [0x{p['value_pos']:04x}] {'  ' * p['depth']}{text}")


def show_table(path, needle=""):
    _, _, _, exports = uasset.parse(path)
    for export in exports:
        if export["class"] != "DataTable":
            continue
        row, fields = None, []
        for p in export["props"] + [{"type": "row", "name": "row <end>", "depth": 0}]:
            if p["type"] == "row":
                if row and needle.lower() in (row + " ".join(fields)).lower():
                    print(f"{row}: {', '.join(fields)}")
                row, fields = p["name"][4:], []
            elif p["depth"] == 1 and p["value"] not in (None, 0, 0.0, "", "None"):
                value = f"{p['value']:g}" if isinstance(p["value"], float) else p["value"]
                fields.append(f"{uasset.short_field(p['name'])}={value}")


def show_fields(needle, field=None):
    stats = collections.defaultdict(list)
    for f in glob.glob(f"{VANILLA}/**/*.uasset", recursive=True):
        if needle.lower() not in f.replace("\\", "/").lower() or not os.path.exists(f[:-7] + ".uexp"):
            continue
        try:
            _, _, _, exports = uasset.parse(f)
        except Exception:
            continue
        for export in exports:
            if not export["name"].startswith("Default__"):
                continue
            for p in export["props"]:
                if p["depth"] == 0 and p["type"] in ("FloatProperty", "IntProperty"):
                    stats[p["name"]].append((os.path.basename(f)[:-7], p["value"]))
    if field:
        for name, entries in stats.items():
            if field.lower() in name.lower():
                for item, value in entries:
                    print(f"{name}\t{item}\t{value:g}")
        return
    for name, entries in sorted(stats.items(), key=lambda kv: -len(kv[1])):
        values = sorted({round(v, 3) for _, v in entries})
        more = " ..." if len(values) > 8 else ""
        print(f"{len(entries):4d} {name}: {[f'{v:g}' for v in values[:8]]}{more}  e.g. {entries[0][0]}")


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    mode = sys.argv[1]
    if mode == "asset":
        show_asset(sys.argv[2])
    elif mode == "table":
        show_table(*sys.argv[2:4])
    elif mode == "fields":
        show_fields(*sys.argv[2:4])
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
