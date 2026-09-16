# -*- coding: utf-8 -*-
"""Stamp Calibre UUID as EXTH 113 + PDOC and write Kindle thumbnails.

Kindle looks up covers at system/thumbnails/thumbnail_{EXTH113}_{PDOC|EBOK}_portrait.jpg.
Works for AZW3 and MOBI (same PalmDB/EXTH). Calibre Send-to-device of an existing
file often copies it without EXTH 113, or leaves 501 as EBOK.

The home grid does NOT refresh while USB is mounted. After writing thumbs, the
user must eject; huge books may need several disconnects. Do not reboot.

Only record 0 is rewritten. Never read/write the whole file (old Uzumaki AZW3 ~1.8 GB;
current MOBI ~430 MB). Never stamp a real Amazon ASIN.
"""
from __future__ import annotations

import argparse
import ctypes
import json
import re
import string
import struct
import sys
from pathlib import Path

from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")

FILE_ATTRIBUTE_NORMAL = 0x80
FILE_ATTRIBUTE_READONLY = 0x1
kernel32 = ctypes.windll.kernel32

DEFAULT_LIBRARY = Path(r"U:\Documents\ebooks")
CLONE_LIBRARY = Path(
    r"A:\[📚] [Documentos]\[14]-[Otros] [📂]\[01]-[Ebooks] [📖]"
)
AZW3_CFG = Path(r"C:\Users\rainb\AppData\Roaming\calibre\conversion\azw3_output.py")
SHARE_NOT_SYNC = 'json:{\n  "share_not_sync": true\n}\n'

SKIP_NAMES = {"spidercat.azw3"}
SKIP_DIR_PARTS = {
    "dictionaries",
    "downloads",
    "koreader",
    "jailbroken.sdr",
    ".caltrash",
}
AMAZON_ASIN_RE = re.compile(r"^B[0-9A-Z]{9}$")
UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I
)
UUID_OPF_RE = re.compile(
    r'opf:scheme="uuid"[^>]*>\s*([0-9a-f-]{36})\s*<', re.I
)
TITLE_OPF_RE = re.compile(r"<dc:title[^>]*>\s*([^<]+)\s*<", re.I)
STUB_MAX = 2000
SIDECAR_EXTS = {".azw3", ".mobi", ".azw", ".prc"}
BOOK_EXTS = SIDECAR_EXTS | {".pdf"}


def set_readonly(path: Path, ro: bool) -> None:
    kernel32.SetFileAttributesW(
        str(path), FILE_ATTRIBUTE_READONLY if ro else FILE_ATTRIBUTE_NORMAL
    )


def find_kindle(explicit: str | None = None) -> Path:
    if explicit:
        root = Path(explicit)
        if not (root / "documents").is_dir():
            raise SystemExit(f"not a Kindle root: {root}")
        return root
    for letter in string.ascii_uppercase:
        root = Path(f"{letter}:/")
        if (root / "system" / "thumbnails").is_dir() and (root / "documents").is_dir():
            return root
    raise SystemExit("Kindle not mounted (no drive with documents + system/thumbnails)")


def is_skipped_dir(path: Path) -> bool:
    parts = {p.casefold() for p in path.parts}
    return bool(parts & SKIP_DIR_PARTS)


def is_amazon_asin(value: str | None) -> bool:
    if not value:
        return False
    return bool(AMAZON_ASIN_RE.match(value.strip()))


def is_uuid(value: str | None) -> bool:
    if not value:
        return False
    return bool(UUID_RE.match(value.strip()))


def parse_exth(path: Path) -> dict:
    out: dict = {
        "asin": None,
        "cdetype": None,
        "title": None,
        "calibre": False,
        "nrec": None,
        "size": path.stat().st_size,
        "err": None,
    }
    with path.open("rb") as f:
        header = f.read(78)
        if len(header) < 78:
            out["err"] = "short"
            return out
        nrec = struct.unpack(">H", header[76:78])[0]
        out["nrec"] = nrec
        infolist = f.read(8 * nrec)
        rec0 = struct.unpack(">I", infolist[0:4])[0]
        rec1 = struct.unpack(">I", infolist[8:12])[0] if nrec > 1 else rec0 + 65536
        f.seek(rec0)
        rec = f.read(min(max(rec1 - rec0, 0), 131072))
    if rec[16:20] != b"MOBI":
        out["err"] = "no-mobi"
        return out
    hlen = struct.unpack(">I", rec[20:24])[0]
    exth = rec[16 + hlen :]
    if exth[:4] != b"EXTH":
        out["err"] = "no-exth"
        return out
    n = struct.unpack(">I", exth[8:12])[0]
    pos = 12
    for _ in range(n):
        t, l = struct.unpack(">II", exth[pos : pos + 8])
        payload = exth[pos + 8 : pos + l]
        if t == 113:
            out["asin"] = payload.decode("utf-8", "replace")
        elif t == 501:
            out["cdetype"] = payload.decode("utf-8", "replace")
        elif t == 503:
            out["title"] = payload.decode("utf-8", "replace")
        elif t == 108 and b"calibre" in payload.lower():
            out["calibre"] = True
        pos += l
    return out


def patch_rec0_asin_pdoc(path: Path, asin: str) -> str:
    """Set EXTH 113 = asin and EXTH 501 = PDOC using rec0 padding. Size unchanged."""
    asin_b = asin.encode("ascii")
    size_before = path.stat().st_size
    with path.open("r+b") as f:
        header = f.read(78)
        nrec = struct.unpack(">H", header[76:78])[0]
        infolist = f.read(8 * nrec)
        rec0 = struct.unpack(">I", infolist[0:4])[0]
        rec1 = struct.unpack(">I", infolist[8:12])[0]
        rec0_size = rec1 - rec0
        f.seek(rec0)
        data = bytearray(f.read(rec0_size))
        if data[16:20] != b"MOBI":
            return "no-mobi"
        hlen = struct.unpack(">I", data[20:24])[0]
        exth_off = 16 + hlen
        if data[exth_off : exth_off + 4] != b"EXTH":
            return "no-exth"
        exth_len = struct.unpack(">I", data[exth_off + 4 : exth_off + 8])[0]
        n_exth = struct.unpack(">I", data[exth_off + 8 : exth_off + 12])[0]
        title_off = struct.unpack(">I", data[16 + 0x54 : 16 + 0x58])[0]
        limit = rec0_size
        if 0 < title_off < rec0_size:
            limit = min(limit, title_off)

        records: list[tuple[int, bytes]] = []
        pos = exth_off + 12
        has_113 = has_501 = False
        for _ in range(n_exth):
            rec_type, rec_len = struct.unpack(">II", data[pos : pos + 8])
            payload = bytes(data[pos + 8 : pos + rec_len])
            if rec_type == 113:
                has_113 = True
                records.append((113, asin_b))
            elif rec_type == 501:
                has_501 = True
                records.append((501, b"PDOC"))
            else:
                records.append((rec_type, payload))
            pos += rec_len
        actions = []
        if has_113:
            actions.append("set-113")
        else:
            records.append((113, asin_b))
            actions.append("ins-113")
        if has_501:
            actions.append("set-501")
        else:
            records.append((501, b"PDOC"))
            actions.append("ins-501")

        blob = b"".join(struct.pack(">II", t, 8 + len(p)) + p for t, p in records)
        new_exth = b"EXTH" + struct.pack(">II", 12 + len(blob), len(records)) + blob
        if exth_off + len(new_exth) > limit:
            return f"no-room:{exth_off + len(new_exth)}>{limit}"
        old_end = min(exth_off + exth_len, limit)
        data[exth_off : exth_off + len(new_exth)] = new_exth
        if old_end > exth_off + len(new_exth):
            data[exth_off + len(new_exth) : old_end] = b"\x00" * (
                old_end - exth_off - len(new_exth)
            )
        f.seek(rec0)
        f.write(data)
        f.flush()
    if path.stat().st_size != size_before:
        return f"SIZE-CHANGED {size_before}->{path.stat().st_size}"
    return "+".join(actions)


def write_thumbs(thumbs_dir: Path, asin: str, cover: Path) -> list[tuple[str, int]]:
    im = Image.open(cover).convert("RGB")
    im.thumbnail((333, 500), Image.Resampling.LANCZOS)
    thumbs_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for kind in ("PDOC", "EBOK"):
        dest = thumbs_dir / f"thumbnail_{asin}_{kind}_portrait.jpg"
        if dest.exists():
            set_readonly(dest, False)
        im.save(dest, "JPEG", quality=85, optimize=True, progressive=False)
        set_readonly(dest, True)
        written.append((dest.name, dest.stat().st_size))
    return written


def thumb_ok(thumbs_dir: Path, asin: str) -> bool:
    hits = list(thumbs_dir.glob(f"thumbnail_{asin}_*_portrait.jpg"))
    return any(p.stat().st_size > STUB_MAX for p in hits)


def load_device_meta(kindle: Path) -> list[dict]:
    meta = kindle / "metadata.calibre"
    if not meta.exists():
        return []
    data = json.loads(meta.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else []


def norm_lpath(value: str) -> str:
    s = value.replace("\\", "/").lstrip("/")
    low = s.casefold()
    if low.startswith("documents/"):
        s = s[10:]
    return s.casefold()


def index_device_by_lpath(rows: list[dict]) -> dict[str, dict]:
    out = {}
    for row in rows:
        lpath = row.get("lpath") or ""
        if lpath:
            out[norm_lpath(str(lpath))] = row
    return out


def index_calibre(lib: Path) -> dict[str, Path]:
    idx: dict[str, Path] = {}
    if not lib.is_dir():
        return idx
    for opf in lib.rglob("metadata.opf"):
        if ".caltrash" in opf.parts:
            continue
        text = opf.read_text(encoding="utf-8", errors="replace")
        m = UUID_OPF_RE.search(text)
        if m:
            idx[m.group(1).strip().casefold()] = opf.parent
        t = TITLE_OPF_RE.search(text)
        if t:
            idx.setdefault("title:" + t.group(1).strip().casefold(), opf.parent)
    return idx


def cover_in(folder: Path | None) -> Path | None:
    if folder is None:
        return None
    c = folder / "cover.jpg"
    return c if c.exists() else None


def library_book(folder: Path | None, prefer: str | None = None) -> Path | None:
    if folder is None:
        return None
    if prefer:
        hits = sorted(folder.glob(f"*{prefer}"))
        if hits:
            return hits[0]
    for ext in (".azw3", ".mobi", ".azw", ".prc"):
        hits = sorted(folder.glob(f"*{ext}"))
        if hits:
            return hits[0]
    return None


def wanted(name: str, needles: list[str] | None) -> bool:
    if not needles:
        return True
    blob = name.casefold()
    return any(n.casefold() in blob for n in needles)


def ensure_share_not_sync() -> None:
    AZW3_CFG.parent.mkdir(parents=True, exist_ok=True)
    AZW3_CFG.write_text(SHARE_NOT_SYNC, encoding="utf-8")


def iter_kindle_books(docs: Path):
    for path in docs.rglob("*"):
        if not path.is_file():
            continue
        if is_skipped_dir(path.parent):
            continue
        if path.name.casefold() in SKIP_NAMES:
            continue
        if path.suffix.lower() not in BOOK_EXTS:
            continue
        yield path


def resolve_calibre_folder(
    uuid: str | None,
    title: str | None,
    live: dict[str, Path],
    clone: dict[str, Path],
) -> Path | None:
    keys = []
    if uuid:
        keys.append(uuid.casefold())
    if title:
        keys.append("title:" + title.casefold())
    for idx in (live, clone):
        for k in keys:
            if k in idx:
                return idx[k]
    return None


def pick_asin(existing: str | None, uuid: str | None) -> str | None:
    if is_uuid(existing) and not is_amazon_asin(existing):
        return existing
    if is_uuid(uuid):
        return uuid
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["diag", "fix"])
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--kindle", default=None)
    ap.add_argument("--library", default=None)
    args = ap.parse_args()

    kindle = find_kindle(args.kindle)
    library = Path(args.library) if args.library else DEFAULT_LIBRARY
    docs = kindle / "documents"
    thumbs = kindle / "system" / "thumbnails"
    print(f"kindle={kindle}")
    print(f"library={library} exists={library.is_dir()}")
    print(f"thumbs={thumbs.exists()}")

    device_rows = load_device_meta(kindle)
    by_lpath = index_device_by_lpath(device_rows)
    live_idx = index_calibre(library)
    clone_idx = index_calibre(CLONE_LIBRARY)

    if args.cmd == "fix":
        ensure_share_not_sync()
        print("share_not_sync=true")

    stats = {"ok": 0, "fixed": 0, "skip": 0, "fail": 0, "pdf": 0}

    for path in sorted(iter_kindle_books(docs), key=lambda p: str(p).casefold()):
        rel = path.relative_to(docs).as_posix()
        row = by_lpath.get(rel.casefold()) or by_lpath.get(norm_lpath(rel))
        title = (row or {}).get("title") or path.stem
        authors = (row or {}).get("authors") or []
        if isinstance(authors, list):
            author_s = ", ".join(str(a) for a in authors)
        else:
            author_s = str(authors)
        label = f"{title} — {author_s}"
        if not wanted(label + " " + rel, args.only):
            continue

        uuid = (row or {}).get("uuid")
        ids = (row or {}).get("identifiers") or {}
        amazon = ids.get("mobi-asin") or ids.get("amazon") or ids.get("asin")
        folder = resolve_calibre_folder(uuid, str(title), live_idx, clone_idx)
        cover = cover_in(folder)
        lib_book = library_book(folder, path.suffix.lower())

        if path.suffix.lower() == ".pdf":
            stats["pdf"] += 1
            asin = uuid if is_uuid(uuid) else None
            has_thumb = bool(asin) and thumb_ok(thumbs, asin)
            print(f"PDF {label}")
            print(f"  file={path}")
            print(f"  uuid={uuid} cover={bool(cover)} thumbs={has_thumb}")
            if args.cmd == "fix" and asin and cover:
                for name, size in write_thumbs(thumbs, asin, cover):
                    print(f"  thumb {name} {size} B")
                stats["fixed"] += 1
            elif has_thumb:
                stats["ok"] += 1
            else:
                stats["skip"] += 1
            continue

        meta = parse_exth(path)
        if meta["err"]:
            print(f"FAIL {label} {meta['err']}")
            stats["fail"] += 1
            continue
        if not meta["calibre"] and not args.only:
            print(f"SKIP non-calibre {label} asin={meta['asin']} cde={meta['cdetype']}")
            stats["skip"] += 1
            continue

        asin = pick_asin(meta["asin"], uuid)
        if is_amazon_asin(amazon) and not is_uuid(meta["asin"]):
            # Device metadata may still hold B0… — never stamp it.
            asin = pick_asin(None, uuid)
        if not asin:
            print(f"SKIP no-uuid {label}")
            stats["skip"] += 1
            continue

        need_asin = meta["asin"] != asin
        need_pdoc = meta["cdetype"] != "PDOC"
        need_thumbs = not thumb_ok(thumbs, asin)
        broken = need_asin or need_pdoc or need_thumbs

        print(f"{'FIX' if (args.cmd == 'fix' and broken) else ('OK' if not broken else 'BROKEN')} {label}")
        print(
            f"  asin={meta['asin']} -> {asin}  cde={meta['cdetype']}  "
            f"cover={bool(cover)} thumbs={not need_thumbs} size={meta['size']}"
        )

        if args.cmd != "fix" or not broken:
            stats["ok" if not broken else "skip"] += 1
            continue

        try:
            result = patch_rec0_asin_pdoc(path, asin)
            after = parse_exth(path)
            print(f"  kindle {result} now asin={after.get('asin')} cde={after.get('cdetype')}")
            if after.get("asin") != asin or after.get("cdetype") != "PDOC":
                print("  VERIFY FAIL kindle")
                stats["fail"] += 1
                continue
            if lib_book and lib_book.exists() and lib_book.resolve() != path.resolve():
                try:
                    r2 = patch_rec0_asin_pdoc(lib_book, asin)
                    print(f"  calibre {r2}")
                except OSError as e:
                    print(f"  calibre skip {e}")
            if cover:
                for name, size in write_thumbs(thumbs, asin, cover):
                    print(f"  thumb {name} {size} B")
            else:
                print("  no cover.jpg")
            stats["fixed"] += 1
        except Exception as e:
            print(f"  FAIL {e}")
            stats["fail"] += 1

    print("STATS", stats)
    return 0 if stats["fail"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
