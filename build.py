# Remnant: From the Ashes - Casual Mod | flexeykinDEV
"""Build the mod: unpack the assets it touches, apply the rules, verify, pack a pak.

    python build.py [--game "<path to Remnant>"] [--refresh] [--verbose]
"""
import argparse
import os
import shutil
import sys
import winreg

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from tools import pak, rules, validate
from tools.edit import Asset

ROOT = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(ROOT, "build")
VANILLA = os.path.join(WORK, "vanilla")
MODDED = os.path.join(WORK, "modded")
DIST = os.path.join(ROOT, "dist", config.PAK_NAME)


def steam_libraries():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam")
        steam = winreg.QueryValueEx(key, "SteamPath")[0]
    except OSError:
        return []
    libraries = [steam]
    vdf = os.path.join(steam, "steamapps", "libraryfolders.vdf")
    if os.path.exists(vdf):
        with open(vdf, encoding="utf-8", errors="replace") as f:
            for line in f:
                if '"path"' in line:
                    libraries.append(line.split('"')[3].replace("\\\\", "\\"))
    return libraries


def find_game():
    for library in steam_libraries():
        path = os.path.join(library, "steamapps", "common", "Remnant")
        if os.path.isdir(os.path.join(path, "Remnant", "Content", "Paks")):
            return path
    return None


def unpack(game_dir):
    paks_dir = os.path.join(game_dir, "Remnant", "Content", "Paks")
    count = 0
    for name in config.GAME_PAKS:
        path = os.path.join(paks_dir, name)
        if not os.path.exists(path):
            sys.exit(f"missing {path}")
        count += len(pak.Pak(path).extract(VANILLA, config.ASSET_FILTERS))
    return count


def apply_rules(verbose):
    if os.path.exists(MODDED):
        shutil.rmtree(MODDED)
    changed, edits = 0, 0
    for root, _, files in os.walk(VANILLA):
        for f in sorted(files):
            if not f.endswith(".uasset"):
                continue
            path = os.path.join(root, f)
            rel = os.path.relpath(path, VANILLA)
            rule = rules.plan(rel)
            if not rule or not os.path.exists(path[:-7] + ".uexp"):
                continue
            asset = Asset(path)
            rule(asset, f[:-7])
            if not asset.log:
                continue
            target = os.path.join(MODDED, rel)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            asset.save(target)
            changed += 1
            edits += len(asset.log)
            if verbose:
                print(rel.replace("\\", "/"))
                for line in asset.log:
                    print("   ", line)
    return changed, edits


def main():
    parser = argparse.ArgumentParser(description="Build Casual Mod for Remnant: From the Ashes")
    parser.add_argument("--game", help="path to the Remnant folder (auto-detected from Steam)")
    parser.add_argument("--refresh", action="store_true", help="unpack the game assets again")
    parser.add_argument("--verbose", action="store_true", help="print every change")
    args = parser.parse_args()

    print("Casual Mod | flexeykinDEV")
    game_dir = args.game or find_game()
    if not game_dir:
        sys.exit("Remnant not found, pass --game \"<path>\"")
    print(f"game: {game_dir}")

    if args.refresh and os.path.exists(VANILLA):
        shutil.rmtree(VANILLA)
    if not os.path.exists(VANILLA):
        print("unpacking vanilla assets...")
        print(f"  {unpack(game_dir)} files -> {os.path.relpath(VANILLA, ROOT)}")

    changed, edits = apply_rules(args.verbose)
    print(f"edited {changed} assets, {edits} values")

    files, added, failures = validate.run(MODDED, VANILLA)
    for path, problems in failures:
        print(f"  BROKEN {path}: {problems[:3]}")
    if failures:
        sys.exit(f"{len(failures)} assets failed validation, nothing packed")
    print(f"verified {files} assets against vanilla, {added} properties added")

    packed = pak.create(MODDED, DIST)
    print(f"packed {len(packed)} files -> {os.path.relpath(DIST, ROOT)}")


if __name__ == "__main__":
    main()
