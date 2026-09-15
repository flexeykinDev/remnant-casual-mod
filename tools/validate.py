# Remnant: From the Ashes - Casual Mod | flexeykinDEV
"""Compare every edited asset with its vanilla original before packing."""
import glob
import struct

from . import edit, uasset

ALLOWED_ADDED = {"Chance", "QuantityMin", "QuantityMax"}


def check(path, original):
    problems = []
    ua, ue, names, exports = uasset.parse(path)
    _, orig_ue, orig_names, orig_exports = uasset.parse(original)
    fields = edit.read_summary_fields(bytearray(ua))

    if exports[0]["offset"] != len(ua):
        problems.append("first export does not start after the header")
    if any(exports[i]["offset"] + exports[i]["size"] != exports[i + 1]["offset"]
           for i in range(len(exports) - 1)):
        problems.append("exports are not contiguous")
    if exports[-1]["offset"] + exports[-1]["size"] + 4 != len(ua) + len(ue):
        problems.append("last export does not end at the package tag")
    if struct.unpack_from("<q", ua, fields["BulkDataStartOffset"])[0] != len(ua) + len(ue) - 4:
        problems.append("BulkDataStartOffset")
    if struct.unpack_from("<i", ua, fields["TotalHeaderSize"])[0] != len(ua):
        problems.append("TotalHeaderSize")
    if ue[-4:] != orig_ue[-4:] or names[:len(orig_names)] != orig_names:
        problems.append("package tag or name map changed")
    if [(e["name"], e["class"]) for e in exports[:len(orig_exports)]] != \
            [(e["name"], e["class"]) for e in orig_exports]:
        problems.append("export names or classes changed")
    for export in exports[len(orig_exports):]:  # objects this mod adds must still read back
        if export["none_pos"] is None or not export["props"]:
            problems.append(f"{export['name']}: added object does not parse")

    added = 0
    for export, original_export in zip(exports, orig_exports):
        extra = [p["name"] for p in export["props"]]
        for p in original_export["props"]:
            if p["name"] in extra:
                extra.remove(p["name"])
            else:
                problems.append(f"{export['name']}: lost {p['name']}")
        if set(extra) - ALLOWED_ADDED:
            problems.append(f"{export['name']}: unexpected {extra}")
        if (export["none_pos"] is None) != (original_export["none_pos"] is None):
            problems.append(f"{export['name']}: parse status changed")
        added += len(extra)
    return problems, added


def run(mod_dir, src_dir):
    """Return (files, added properties, list of failures)."""
    files = glob.glob(f"{mod_dir}/**/*.uasset", recursive=True)
    total_added, failures = 0, []
    for f in files:
        problems, added = check(f, src_dir + f[len(mod_dir):])
        total_added += added
        if problems:
            failures.append((f, problems))
    return len(files), total_added, failures
