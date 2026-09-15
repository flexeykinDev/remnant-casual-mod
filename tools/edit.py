# Remnant: From the Ashes - Casual Mod | flexeykinDEV
"""Editable package: change property values, add properties and names, fix up offsets on save."""
import struct

from . import uasset


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
    """Name map hashes: FCrc::Strihash_DEPRECATED and FCrc::StrCrc32, both truncated to 16 bits.

    A wrong hash makes the engine file the name in another bucket, so property lookups miss it.
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


OFFSET_FIELDS = ["TotalHeaderSize", "GatherableTextDataOffset", "ExportOffset", "ImportOffset",
                 "DependsOffset", "SoftPackageReferencesOffset", "SearchableNamesOffset",
                 "ThumbnailTableOffset", "AssetRegistryDataOffset", "WorldTileInfoDataOffset",
                 "PreloadDependencyOffset"]


def read_summary_fields(ua):
    """Positions of the summary fields that have to be patched when the package grows."""
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
    fields["LastGenerationNameCount"] = p + 8 * generations - 4 if generations else None
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
        self.fields = read_summary_fields(self.ua)
        p = self.i32(self.fields["NameOffset"])
        for _ in range(self.i32(self.fields["NameCount"])):
            n = struct.unpack_from("<i", self.ua, p)[0]
            p += 4 + (n if n >= 0 else -n * 2) + 4
        self.name_map_end = p
        self.new_names = []
        self.inserts = []
        self.log = []

    def i32(self, pos):
        return struct.unpack_from("<i", self.ua, pos)[0]

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

    def insert_int(self, export_index, before_prop, name, value, note=""):
        export = self.exports[export_index]
        pos = before_prop["tag_start"] if before_prop else export["none_pos"]
        tag = struct.pack("<iiiiiiBi", self.name_index(name), 0, self.name_index("IntProperty"), 0,
                          4, 0, 0, int(value))
        self.inserts.append((pos, export_index, tag))
        self.log.append(f"{note}{name}: (default) -> {value} (added)")

    def save(self, out_path):
        ua, ue = bytearray(self.ua), bytearray(self.ue)
        growth = [0] * len(self.exports)
        for pos, n, data in sorted(self.inserts, key=lambda x: x[0], reverse=True):
            ue[pos:pos] = data
            growth[n] += len(data)

        name_bytes = b""
        for s in self.new_names:
            raw = s.encode("utf-8") + b"\0"
            name_bytes += struct.pack("<i", len(raw)) + raw + struct.pack("<HH", *name_hashes(s))
        delta = len(name_bytes)
        f = self.fields

        for field in OFFSET_FIELDS:
            value = self.i32(f[field])
            if value >= self.name_map_end:
                struct.pack_into("<i", ua, f[field], value + delta)
        struct.pack_into("<i", ua, f["NameCount"], len(self.names))
        if f["LastGenerationNameCount"] is not None:
            struct.pack_into("<i", ua, f["LastGenerationNameCount"], len(self.names))
        bulk = struct.unpack_from("<q", ua, f["BulkDataStartOffset"])[0]
        struct.pack_into("<q", ua, f["BulkDataStartOffset"], bulk + delta + sum(growth))

        export_offset = self.i32(f["ExportOffset"])
        shift = delta
        for i in range(len(self.exports)):
            field_pos = export_offset + i * uasset.EXPORT_ENTRY_SIZE + 28
            size, offset = struct.unpack_from("<qq", ua, field_pos)
            struct.pack_into("<qq", ua, field_pos, size + growth[i], offset + shift)
            shift += growth[i]

        ua[self.name_map_end:self.name_map_end] = name_bytes
        with open(out_path, "wb") as out:
            out.write(ua)
        with open(out_path[:-7] + ".uexp", "wb") as out:
            out.write(ue)
