# Remnant: From the Ashes - Casual Mod | flexeykinDEV
"""Reader for cooked UE 4.22 packages (.uasset header + .uexp object data)."""
import re
import struct

EXPORT_ENTRY_SIZE = 104
_FIELD_SUFFIX = re.compile(r"_\d+_[0-9A-F]{32}$")


def short_field(name):
    """DataTable fields are stored as EnemyHealthScalar_13_<GUID>."""
    return _FIELD_SUFFIX.sub("", name)


class Reader:
    def __init__(self, data):
        self.d, self.p = data, 0

    def unpack(self, fmt):
        v = struct.unpack_from(fmt, self.d, self.p)
        self.p += struct.calcsize(fmt)
        return v[0] if len(v) == 1 else v

    def i32(self):
        return self.unpack("<i")

    def fstring(self):
        n = self.i32()
        if n < 0:
            s = self.d[self.p:self.p - n * 2].decode("utf-16-le")
            self.p += -n * 2
        else:
            s = self.d[self.p:self.p + n].decode("utf-8", "replace")
            self.p += n
        return s.rstrip("\0")


def read_summary(uasset):
    """Return (names, exports). Each export carries its object name, class and map position."""
    r = Reader(uasset)
    r.p = 4
    if r.i32() != -4:
        r.i32()
    r.i32(); r.i32()
    custom_versions = r.i32()
    r.p += 20 * custom_versions
    r.i32()
    r.fstring()
    r.i32()
    name_count, name_offset = r.i32(), r.i32()
    r.i32(); r.i32()
    export_count, export_offset = r.i32(), r.i32()
    import_count, import_offset = r.i32(), r.i32()

    r.p = name_offset
    names = []
    for _ in range(name_count):
        names.append(r.fstring())
        r.p += 4  # two uint16 hashes

    def name_at(pos):
        idx, num = struct.unpack_from("<ii", uasset, pos)
        return names[idx] if num == 0 else f"{names[idx]}_{num - 1}"

    imports = [name_at(import_offset + i * 28 + 20) for i in range(import_count)]
    objects = [name_at(export_offset + i * EXPORT_ENTRY_SIZE + 16) for i in range(export_count)]

    exports = []
    for i in range(export_count):
        base = export_offset + i * EXPORT_ENTRY_SIZE
        class_index = struct.unpack_from("<i", uasset, base)[0]
        if class_index < 0:
            class_name = imports[-class_index - 1]
        elif class_index > 0:
            class_name = objects[class_index - 1]
        else:
            class_name = "Class"
        size, offset = struct.unpack_from("<qq", uasset, base + 28)
        exports.append({"size": size, "offset": offset, "field_pos": base + 28,
                        "name": objects[i], "class": class_name})
    return names, exports


def parse_properties(r, names, depth, out):
    """Read tagged properties up to the None terminator; return the terminator position."""
    def fname():
        idx, num = r.i32(), r.i32()
        return names[idx] if num == 0 else f"{names[idx]}_{num - 1}"

    while True:
        tag_start = r.p
        name = fname()
        if name == "None":
            return tag_start
        ptype = fname()
        size = r.i32()
        r.i32()
        inner = None
        if ptype == "StructProperty":
            inner = fname(); r.p += 16
        elif ptype in ("ByteProperty", "EnumProperty", "ArrayProperty", "SetProperty"):
            inner = fname()
        elif ptype == "MapProperty":
            inner = (fname(), fname())
        elif ptype == "BoolProperty":
            bool_val = r.unpack("<B")
        if r.unpack("<B"):
            r.p += 16  # property guid
        start = r.p
        prop = {"name": name, "type": ptype, "depth": depth, "tag_start": tag_start,
                "value_pos": start, "value": None}
        out.append(prop)

        if ptype == "IntProperty":
            prop["value"] = r.i32()
        elif ptype == "FloatProperty":
            prop["value"] = r.unpack("<f")
        elif ptype == "BoolProperty":
            prop["value"] = bool(bool_val)
        elif ptype in ("NameProperty", "EnumProperty") or (ptype == "ByteProperty" and size == 8):
            prop["value"] = fname()
        elif ptype == "ObjectProperty":
            prop["value"] = f"object#{r.i32()}"
        elif ptype == "SoftObjectProperty":
            prop["value"] = f"{fname()} {r.fstring()}".strip()
        elif ptype == "ArrayProperty" and inner == "ObjectProperty":
            prop["value"] = [f"object#{r.i32()}" for _ in range(r.i32())]
        elif ptype == "ArrayProperty" and inner == "NameProperty":
            prop["value"] = [fname() for _ in range(r.i32())]
        elif ptype == "ArrayProperty" and inner == "StructProperty":
            count = r.i32()
            fname(); fname(); r.i32(); r.i32()
            struct_name = fname()
            r.p += 17
            prop["value"] = f"{count} x {struct_name}"
            for i in range(count):
                out.append({"name": f"[{i}]", "type": "element", "depth": depth + 1,
                            "tag_start": r.p, "value_pos": r.p, "value": None})
                parse_properties(r, names, depth + 2, out)
        else:
            prop["value"] = f"({ptype}, {size} bytes, not decoded)"
        r.p = start + size


def parse(uasset_path):
    """Return (uasset bytes, uexp bytes, names, exports with parsed properties)."""
    with open(uasset_path, "rb") as f:
        uasset = f.read()
    with open(uasset_path[:-7] + ".uexp", "rb") as f:
        uexp = f.read()
    names, exports = read_summary(uasset)
    r = Reader(uexp)
    for export in exports:
        r.p = export["offset"] - len(uasset)
        export["props"] = []
        try:
            export["none_pos"] = parse_properties(r, names, 0, export["props"])
            if export["class"] == "DataTable":
                r.p += 4
                for _ in range(r.i32()):
                    idx, num = r.i32(), r.i32()
                    row = names[idx] if num == 0 else f"{names[idx]}_{num - 1}"
                    export["props"].append({"name": f"row {row}", "type": "row", "depth": 0,
                                            "tag_start": r.p, "value_pos": r.p, "value": None})
                    parse_properties(r, names, 1, export["props"])
        except (IndexError, struct.error, UnicodeDecodeError):
            export["props"], export["none_pos"] = [], None  # bytecode, not tagged properties
    return uasset, uexp, names, exports
