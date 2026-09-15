# Remnant: From the Ashes - Casual Mod | flexeykinDEV
"""Editable package: change values, add properties, names, imports and whole objects.

Saving rebuilds the package section by section (names, imports, exports, depends, asset registry,
preload dependencies) and recomputes every offset, so sections can grow.
"""
import struct

from . import uasset

IMPORT_ENTRY_SIZE = 28


def _crc_tables():
    reflected, normal = [], []
    for i in range(256):
        c = i
        for _ in range(8):
            c = (c >> 1) ^ 0xEDB88320 if c & 1 else c >> 1
        reflected.append(c)
        c = i << 24
        for _ in range(8):
            c = ((c << 1) ^ 0x04C11DB7) & 0xFFFFFFFF if c & 0x80000000 else (c << 1) & 0xFFFFFFFF
        normal.append(c)
    return reflected, normal


CRC_REFLECTED, CRC_NORMAL = _crc_tables()


def name_hashes(s):
    """Name map hashes: FCrc::Strihash_DEPRECATED and FCrc::StrCrc32, both cut to 16 bits.

    A wrong hash files the name in another bucket, so property lookups miss it.
    """
    h = 0
    for ch in s.upper().encode("latin-1"):
        h = ((h >> 8) & 0x00FFFFFF) ^ CRC_NORMAL[(h ^ ch) & 0xFF]
    c = 0xFFFFFFFF
    for ch in s:
        o = ord(ch)
        for b in (o & 0xFF, (o >> 8) & 0xFF, (o >> 16) & 0xFF, (o >> 24) & 0xFF):
            c = (c >> 8) ^ CRC_REFLECTED[(c ^ b) & 0xFF]
    return h & 0xFFFF, (~c) & 0xFFFF


def read_summary_fields(ua):
    """Positions of the summary fields that have to be patched when the package changes size."""
    p = 0

    def take(fmt):
        nonlocal p
        v = struct.unpack_from(fmt, ua, p)
        pos = p
        p += struct.calcsize(fmt)
        return pos, v[0]

    def fstring():
        nonlocal p
        n = struct.unpack_from("<i", ua, p)[0]
        p += 4 + (n if n >= 0 else -n * 2)

    fields = {}
    p = 20
    _, custom = take("<i")
    p += 20 * custom
    fields["TotalHeaderSize"] = take("<i")[0]
    fstring()
    p += 4
    for name in ["NameCount", "NameOffset", "GatherableTextDataCount", "GatherableTextDataOffset",
                 "ExportCount", "ExportOffset", "ImportCount", "ImportOffset", "DependsOffset",
                 "SoftPackageReferencesCount", "SoftPackageReferencesOffset", "SearchableNamesOffset",
                 "ThumbnailTableOffset"]:
        fields[name] = take("<i")[0]
    p += 16
    _, generations = take("<i")
    if generations:
        fields["LastGenerationExportCount"] = p + 8 * generations - 8
        fields["LastGenerationNameCount"] = p + 8 * generations - 4
    p += 8 * generations
    for _ in range(2):
        p += 10
        fstring()
    p += 4
    _, chunks = take("<i")
    if chunks:
        raise ValueError("compressed packages are not supported")
    p += 4
    _, extra = take("<i")
    for _ in range(extra):
        fstring()
    fields["AssetRegistryDataOffset"] = take("<i")[0]
    fields["BulkDataStartOffset"] = take("<q")[0]
    fields["WorldTileInfoDataOffset"] = take("<i")[0]
    _, chunk_ids = take("<i")
    p += 4 * chunk_ids
    fields["PreloadDependencyCount"] = take("<i")[0]
    fields["PreloadDependencyOffset"] = take("<i")[0]
    return fields


class Asset:
    def __init__(self, uasset_path):
        self.path = uasset_path
        ua, ue, self.names, self.exports = uasset.parse(uasset_path)
        self.ua, self.ue = bytearray(ua), bytearray(ue)
        self.uasset_size = len(ua)
        self.fields = read_summary_fields(self.ua)
        f = self.fields

        name_offset = self.i32("NameOffset")
        import_offset, import_count = self.i32("ImportOffset"), self.i32("ImportCount")
        export_offset, export_count = self.i32("ExportOffset"), self.i32("ExportCount")
        depends_offset = self.i32("DependsOffset")
        registry_offset = self.i32("AssetRegistryDataOffset")
        preload_offset, preload_count = self.i32("PreloadDependencyOffset"), self.i32("PreloadDependencyCount")

        self.header = bytearray(ua[:name_offset])
        self.imports = [bytearray(ua[import_offset + i * IMPORT_ENTRY_SIZE:
                                     import_offset + (i + 1) * IMPORT_ENTRY_SIZE])
                        for i in range(import_count)]
        self.export_entries = [bytearray(ua[export_offset + i * uasset.EXPORT_ENTRY_SIZE:
                                            export_offset + (i + 1) * uasset.EXPORT_ENTRY_SIZE])
                               for i in range(export_count)]
        self.depends = bytearray(ua[depends_offset:registry_offset])
        self.registry = bytearray(ua[registry_offset:preload_offset])
        self.preload = list(struct.unpack_from(f"<{preload_count}i", ua, preload_offset))

        self.new_names = []
        self.inserts = []       # (uexp position, export index, bytes)
        self.new_objects = []   # {"entry", "serial", "deps"}
        self.log = []

    def i32(self, field):
        return struct.unpack_from("<i", self.ua, self.fields[field])[0]

    # ---- names, values --------------------------------------------------------------------------
    def name_index(self, s):
        if s in self.names:
            return self.names.index(s)
        self.names.append(s)
        self.new_names.append(s)
        return len(self.names) - 1

    def set(self, prop, value, note=""):
        fmts = {"IntProperty": "<i", "FloatProperty": "<f"}
        if prop["type"] not in fmts:
            raise TypeError(f"cannot set {prop['type']}")
        if prop["type"] == "IntProperty":
            value = int(round(value))
        if value == prop["value"]:
            return
        struct.pack_into(fmts[prop["type"]], self.ue, prop["value_pos"], value)
        old = f"{prop['value']:g}" if isinstance(prop["value"], float) else prop["value"]
        new = f"{value:g}" if isinstance(value, float) else value
        self.log.append(f"{note}{uasset.short_field(prop['name'])}: {old} -> {new}")

    def set_name(self, prop, value, note=""):
        """Repoint a name-valued property. A SoftObjectProperty keeps its (empty) sub path."""
        if prop["type"] not in ("NameProperty", "SoftObjectProperty", "EnumProperty"):
            raise TypeError(f"cannot set {prop['type']}")
        struct.pack_into("<ii", self.ue, prop["value_pos"], self.name_index(value), 0)
        self.log.append(f"{note}{prop['name']}: {prop['value']} -> {value}")

    def insert_int(self, export_index, before_prop, name, value, note=""):
        export = self.exports[export_index]
        pos = before_prop["tag_start"] if before_prop else export["none_pos"]
        tag = struct.pack("<iiiiiiBi", self.name_index(name), 0, self.name_index("IntProperty"), 0,
                          4, 0, 0, int(value))
        self.inserts.append((pos, export_index, tag))
        self.log.append(f"{note}{name}: (default) -> {value} (added)")

    def append_object_refs(self, export_index, prop, indices, note=""):
        """Append entries to an ArrayProperty of ObjectProperty (e.g. a recipe list)."""
        count = len(prop["value"])
        data = b"".join(struct.pack("<i", i) for i in indices)
        self.inserts.append((prop["value_pos"] + 4 + 4 * count, export_index, data))
        struct.pack_into("<i", self.ue, prop["value_pos"], count + len(indices))
        size_pos = prop["tag_start"] + 16
        size = struct.unpack_from("<i", self.ue, size_pos)[0]
        struct.pack_into("<i", self.ue, size_pos, size + len(data))
        self.log.append(f"{note}{prop['name']}: {count} -> {count + len(indices)} entries")

    # ---- imports and objects --------------------------------------------------------------------
    def _fname(self, s):
        return struct.pack("<ii", self.name_index(s), 0)

    def import_index(self, class_package, class_name, outer, object_name):
        """Index (as a negative package index) of an import, adding it if it is not there yet."""
        entry = self._fname(class_package) + self._fname(class_name) + struct.pack("<i", outer) \
            + self._fname(object_name)
        for i, existing in enumerate(self.imports):
            if existing == entry:
                return -(i + 1)
        self.imports.append(bytearray(entry))
        return -len(self.imports)

    def class_import(self, asset_path, class_name):
        """Import a blueprint class, e.g. ("/Game/.../Mod_Undying", "Mod_Undying_C")."""
        package = self.import_index("/Script/CoreUObject", "Package", 0, asset_path)
        return self.import_index("/Script/Engine", "BlueprintGeneratedClass", package, class_name)

    def export_serial(self, export_index):
        """Raw object data of an export plus its start position in the .uexp."""
        export = self.exports[export_index]
        start = export["offset"] - self.uasset_size
        return bytearray(self.ue[start:start + export["size"]]), start

    def add_object(self, template_index, object_name, serial, deps, note=""):
        """Append a new export cloned from an existing one, with its own data and preload deps."""
        entry = bytearray(self.export_entries[template_index])
        struct.pack_into("<ii", entry, 16, self.name_index(object_name), 0)
        struct.pack_into("<q", entry, 28, len(serial))
        struct.pack_into("<iiiii", entry, 84, len(self.preload), 0,
                         *self._dep_counts(template_index))
        self.preload.extend(deps)
        self.new_objects.append({"entry": entry, "serial": bytearray(serial)})
        self.depends += b"\0\0\0\0"  # no hard depends entries for the new object
        self.log.append(f"{note}{object_name}: new object (added)")
        return len(self.export_entries) + len(self.new_objects)  # 1-based export index

    def _dep_counts(self, template_index):
        return struct.unpack_from("<iii", self.export_entries[template_index], 88 + 4)

    def template_deps(self, template_index):
        """The preload dependency entries an export declares, as a flat list."""
        first = struct.unpack_from("<i", self.export_entries[template_index], 84)[0]
        total = sum(self._dep_counts(template_index)) + \
            struct.unpack_from("<i", self.export_entries[template_index], 88)[0]
        return self.preload[first:first + total]

    # ---- save -----------------------------------------------------------------------------------
    def save(self, out_path):
        ue = bytearray(self.ue)
        growth = [0] * len(self.export_entries)
        for pos, n, data in sorted(self.inserts, key=lambda x: x[0], reverse=True):
            ue[pos:pos] = data
            growth[n] += len(data)

        tag = ue[-4:]  # package tag closes the .uexp
        ue = ue[:-4]
        new_positions = []
        for obj in self.new_objects:
            new_positions.append(len(ue))
            ue += obj["serial"]
        ue += tag

        name_bytes = bytearray()
        for s in self.names:
            raw = s.encode("utf-8") + b"\0"
            name_bytes += struct.pack("<i", len(raw)) + raw + struct.pack("<HH", *name_hashes(s))

        entries = [bytearray(e) for e in self.export_entries] + [o["entry"] for o in self.new_objects]

        name_offset = len(self.header)
        import_offset = name_offset + len(name_bytes)
        export_offset = import_offset + len(self.imports) * IMPORT_ENTRY_SIZE
        depends_offset = export_offset + len(entries) * uasset.EXPORT_ENTRY_SIZE
        registry_offset = depends_offset + len(self.depends)
        preload_offset = registry_offset + len(self.registry)
        header_size = preload_offset + len(self.preload) * 4

        position = 0
        for i, entry in enumerate(entries):
            if i < len(self.export_entries):
                size = self.exports[i]["size"] + growth[i]
            else:
                size = struct.unpack_from("<q", entry, 28)[0]
                position = new_positions[i - len(self.export_entries)]
            struct.pack_into("<qq", entry, 28, size, header_size + position)
            position += size

        ua = bytearray(self.header) + name_bytes
        for entry in self.imports:
            ua += entry
        for entry in entries:
            ua += entry
        ua += self.depends + self.registry
        ua += struct.pack(f"<{len(self.preload)}i", *self.preload)

        f = self.fields
        for field, value in [("NameCount", len(self.names)), ("NameOffset", name_offset),
                             ("ImportCount", len(self.imports)), ("ImportOffset", import_offset),
                             ("ExportCount", len(entries)), ("ExportOffset", export_offset),
                             ("DependsOffset", depends_offset),
                             ("AssetRegistryDataOffset", registry_offset),
                             ("PreloadDependencyCount", len(self.preload)),
                             ("PreloadDependencyOffset", preload_offset),
                             ("TotalHeaderSize", header_size),
                             ("LastGenerationNameCount", len(self.names)),
                             ("LastGenerationExportCount", len(entries))]:
            if f.get(field) is not None:
                struct.pack_into("<i", ua, f[field], value)
        struct.pack_into("<q", ua, f["BulkDataStartOffset"], header_size + len(ue) - 4)

        with open(out_path, "wb") as out:
            out.write(ua)
        with open(out_path[:-7] + ".uexp", "wb") as out:
            out.write(ue)
