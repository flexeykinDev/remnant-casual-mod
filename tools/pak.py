# Remnant: From the Ashes - Casual Mod | flexeykinDEV
"""Unreal .pak reading (v3-v8) and writing (v3)."""
import hashlib
import os
import struct
import zlib

MAGIC = 0x5A6F12E1
MOUNT_POINT = "../../../"
WRITE_VERSION = 3  # Remnant runs UE 4.22 and rejects the newer pak layouts


def _read_fstring(f):
    (n,) = struct.unpack("<i", f.read(4))
    if n < 0:
        return f.read(-n * 2).decode("utf-16-le").rstrip("\0")
    return f.read(n).decode("utf-8").rstrip("\0")


def _fstring(s):
    data = s.encode("utf-8") + b"\0"
    return struct.pack("<i", len(data)) + data


def _read_entry(f, version):
    if version >= 8:  # 4.22 writes the compression method index as one byte
        offset, size, usize, comp = struct.unpack("<qqqB", f.read(25))
    else:
        offset, size, usize, comp = struct.unpack("<qqqi", f.read(28))
    f.read(20)  # sha1
    blocks = []
    if comp:
        (count,) = struct.unpack("<i", f.read(4))
        blocks = [struct.unpack("<qq", f.read(16)) for _ in range(count)]
    encrypted, _block_size = struct.unpack("<BI", f.read(5))
    return {"offset": offset, "size": size, "usize": usize, "comp": comp, "blocks": blocks,
            "encrypted": encrypted}


def _write_entry(offset, data, sha1):
    return (struct.pack("<qqqi", offset, len(data), len(data), 0) + sha1
            + struct.pack("<BI", 0, 0))


class Pak:
    """Open pak, list entries by full path, read file contents."""

    def __init__(self, path):
        self.file = open(path, "rb")
        self.file.seek(-300, os.SEEK_END)
        tail = self.file.read()
        i = tail.rfind(struct.pack("<I", MAGIC))
        if i < 0:
            raise ValueError(f"{path}: not a pak file")
        _, self.version, index_offset, _ = struct.unpack_from("<IIqq", tail, i)
        if self.version >= 7 and tail[i - 1]:
            raise ValueError(f"{path}: encrypted index")
        self.file.seek(index_offset)
        prefix = _read_fstring(self.file).replace(MOUNT_POINT, "", 1)  # chunk1 mounts deeper
        (count,) = struct.unpack("<i", self.file.read(4))
        self.entries = {}
        for _ in range(count):
            name = prefix + _read_fstring(self.file)
            self.entries[name] = _read_entry(self.file, self.version)

    def read(self, name):
        e = self.entries[name]
        if e["encrypted"]:
            raise ValueError(f"{name}: encrypted")
        if not e["comp"]:
            self.file.seek(e["offset"])
            _read_entry(self.file, self.version)  # skip the copy of the header before the data
            return self.file.read(e["size"])
        base = e["offset"] if self.version >= 5 else 0  # v5+ block offsets are entry-relative
        out = []
        for start, end in e["blocks"]:
            self.file.seek(base + start)
            out.append(zlib.decompress(self.file.read(end - start)))
        return b"".join(out)

    def extract(self, out_dir, needles):
        written = []
        for name in self.entries:
            if any(n in name.lower() for n in needles):
                path = os.path.join(out_dir, *name.split("/"))
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "wb") as out:
                    out.write(self.read(name))
                written.append(name)
        return written


def create(input_dir, pak_path):
    """Pack a folder as an uncompressed pak v3; paths inside are relative to input_dir."""
    files = sorted(
        os.path.relpath(os.path.join(root, f), input_dir).replace("\\", "/")
        for root, _, names in os.walk(input_dir) for f in names
    )
    index = [_fstring(MOUNT_POINT), struct.pack("<i", len(files))]
    os.makedirs(os.path.dirname(os.path.abspath(pak_path)), exist_ok=True)
    with open(pak_path, "wb") as pak:
        for name in files:
            with open(os.path.join(input_dir, name), "rb") as f:
                data = f.read()
            sha1 = hashlib.sha1(data).digest()
            offset = pak.tell()
            pak.write(_write_entry(0, data, sha1))  # inline header stores offset 0
            pak.write(data)
            index += [_fstring(name), _write_entry(offset, data, sha1)]
        index_data = b"".join(index)
        index_offset = pak.tell()
        pak.write(index_data)
        pak.write(struct.pack("<IIqq", MAGIC, WRITE_VERSION, index_offset, len(index_data)))
        pak.write(hashlib.sha1(index_data).digest())
    return files
