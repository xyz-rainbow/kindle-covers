---
name: kindle-covers
description: >
  Fix Kindle Paperwhite sideload covers after Calibre send or metadata/cover
  changes. Stamps Calibre UUID as MOBI/AZW3 EXTH 113, forces PDOC, and writes
  system/thumbnails from cover.jpg. Use when Kindle home has no cover art,
  Calibre cover does not stick, portadas mal, sin portada, miniatura, PDOC,
  EBOK, thumbnail, cover art Kindle, MOBI cover, eject USB, or the user
  runs /kindle-covers.
---

# Kindle covers (Calibre sideloads)

Stock Amazon reader on a jailbroken Paperwhite 4. Covers are **not** Calibre's
`cover.jpg` on disk. Firmware looks up
`system/thumbnails/thumbnail_{EXTH113}_{PDOC|EBOK}_portrait.jpg`.

Same lookup for **AZW3 and MOBI** (PalmDB + EXTH). PDFs have no EXTH; convert
or accept a generic icon.

## Confirmed: USB must unmount

The home grid **does not refresh while the Kindle is a USB disk**. Injecting
UUID + thumbs can look like a no-op until the cable is gone. *Uzumaki* (MOBI)
showed its cover only after disconnect; huge books may need **several** safe
ejects. This is firmware indexing, not Calibre, not the jailbreak, not the
`author/title` folder layout.

Do **not** reboot after eject. A reboot lets Amazon overwrite EBOK thumbs
with the ~1167 B "No hay disponible" stub.

## Why Calibre "send" drops covers

Send of an existing AZW3/MOBI usually leaves 501 as **EBOK** even when EXTH 113
already has the Calibre UUID. Send of a *new* conversion (ebook-convert, then
Add/Send) often copies **with 113 and 501 both missing** (`asin=None cde=None`).
Thumbs may already exist; `diag` is still BROKEN until 113 is a UUID and 501 is
**PDOC**. Sideloads must be **PDOC** + Calibre **UUID** (never a real Amazon
`B0…` ASIN).

`share_not_sync: true` only helps a *conversion*, not a plain copy.

## This machine

| What | Path |
|---|---|
| Live Calibre library | `U:\Documents\ebooks` |
| Kindle (USB) | drive with `documents\` + `system\thumbnails\` (usually `D:`) |
| Clone (not live) | `A:\[📚] [Documentos]\[14]-[Otros] [📂]\[01]-[Ebooks] [📖]` |
| `share_not_sync` | `%APPDATA%\calibre\conversion\azw3_output.py` → `true` |

Paths, skip lists, and the EXTH patcher live in
`scripts/fix_kindle_covers.py`. Read the constants at the top before changing them.

Uzumaki: live MOBI is Calibre id **176** (`Uzumaki - Junji Ito.mobi`, ~430 MB).
The old deluxe AZW3 id 170 (~1.8 GB) is image-heavy, not corruption. Prefer
the MOBI. After send, the device folder may be `Ito, Junji & Desconocido` if
the file still has a leftover EXTH 100 `Desconocido`.

## Do / don't

- **Do** patch Kindle rec0 + matching library file (same extension) + thumbs
  from `cover.jpg`.
- **Do** keep an existing UUID already in EXTH 113 (working books like *Indigno*).
- **Do** tell the user to **eject, wait for the home grid, eject again** if the
  tile is still blank. Several disconnects are normal for big comics.
- **Do** follow `windows-notify` (Spanish title + one line; start and end).
- **Don't** stamp a real Amazon ASIN (`B` + 9 alphanumerics) as EXTH 113.
- **Don't** retarget Calibre to the A: clone. **Don't** send the whole library.
- **Don't** DRM-strip unique KFX. **Don't** touch jailbreak (`spidercat.azw3`,
  dictionaries, `JAILBROKEN.sdr`, `kmc` / `libkh` / `privesc_marker.txt`).
- **Don't** `read_bytes()` / rewrite image-heavy bodies. Rec0 only.
- **Don't** use `calibredb` while the Calibre GUI is open.
- **Don't** treat a still-plugged Kindle as proof the cover failed.
- **Don't** bulk-convert the library to MOBI to fix covers. Folder layout
  (`documents/libros` vs `{author_sort}/…`) does not change thumbnail lookup.

Library split (user): stock Amazon keeps novels as AZW3 in `{author_sort}/`.
KOReader gets manga/PDF/zoom titles in `documents/libros` as **CBZ/EPUB/PDF/MOBI**
(not AZW3 — KOReader cannot open it). Amazon still lists anything under
`documents/`. Recreate `/mnt/us/e-books` only if they want those titles off
the stock home. KOReader zoom + disable corner frontlight: later, when asked.

## Playbook

1. Confirm Kindle mounted (`documents` + `system\thumbnails`) and live library present.
2. Start toast. If the user named titles, `diag` then `fix` with the same `--only`
   fragments (case-insensitive substring of title, author, or path — `vida 3`
   matches *Vida 3.0*, `hail mary` matches *PROYECTO HAIL MARY*):

```powershell
python "$env:USERPROFILE\.agents\skills\kindle-covers\scripts\fix_kindle_covers.py" diag --only "hail mary" obligatorio sedados
python "$env:USERPROFILE\.agents\skills\kindle-covers\scripts\fix_kindle_covers.py" fix --only "hail mary" obligatorio sedados
```

The script is `scripts/fix_kindle_covers.py` next to this `SKILL.md`. Use that path if the skill is loaded from another tree.

`--only` also patches non-Calibre MOBI sideloads. Whole-library `diag` / `fix`
only when they did not name books.

3. Verify: EXTH 113 = UUID, EXTH 501 = `PDOC`, thumbs `>2 KB`, file size unchanged.
4. Success toast. **Eject without reboot.** Novels usually show after one eject.
   Re-sending from Calibre can leave 501 as EBOK (or drop 113); re-run this skill
   after a send, then eject again.
5. If `diag` is OK after eject but the tile still looks empty, the JPEG is too
   light for Paperwhite (yellow/white). Darken `cover.jpg` and rewrite both
   `thumbnail_{EXTH113}_{PDOC|EBOK}_portrait.jpg`. Do not re-send.
6. PDF→AZW3 often has **no EXTH 201/202** (cover image index). Stock reader then
   shows no tile even with system thumbs. `ebook-convert` with `--cover`, copy
   onto the Kindle, then `fix` again (convert drops 113/501). `ebook-meta --cover`
   does not add 201/202 on AZW3.

`fix` also writes `share_not_sync: true` so a *conversion* marks new files PDOC.

## Working reference

*Indigno de ser humano* and *El Psicoanalista*: UUID in EXTH 113, `PDOC`, both
PDOC and EBOK thumbs named with that UUID (which may differ from
`metadata.calibre`'s `uuid` field). Match thumbs to **EXTH 113**, not the
device-db uuid, when 113 is already a UUID.
