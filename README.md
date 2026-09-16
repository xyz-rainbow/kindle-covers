# kindle-covers

**Agent skill for Kindle Paperwhite sideload covers** after Calibre send or a metadata/cover change. Stamps the Calibre UUID as MOBI/AZW3 EXTH 113, forces **PDOC**, and writes `system/thumbnails` from `cover.jpg`.

Works on **Windows** with a USB-mounted Kindle (stock Amazon reader). Jailbreak is not required for the cover fix; do not touch jailbreak files.

[![License: MIT](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)
[![skills.sh](https://img.shields.io/badge/skills.sh-kindle--covers-00f0ff.svg)](https://skills.sh)
[![npx skills add](https://img.shields.io/badge/npx%20skills%20add-xyz--rainbow%2Fkindle--covers-ff2bd6.svg)](#one-command-installation)

## One-command installation

```bash
npx skills add xyz-rainbow/kindle-covers
```

Or via URL:

```bash
npx skills add https://github.com/xyz-rainbow/kindle-covers
```

Global, every agent, non-interactive:

```bash
npx skills add xyz-rainbow/kindle-covers -g -y -a "*"
```

## What it does

- Diagnoses AZW3/MOBI on the mounted Kindle: EXTH 113 (UUID), EXTH 501 (`PDOC` vs `EBOK`), and thumbnail size.
- Patches **record 0 only** (never reads the whole book body).
- Writes `thumbnail_{EXTH113}_{PDOC|EBOK}_portrait.jpg` from Calibre `cover.jpg`.
- Named titles via `--only` (substring of title, author, or path).

The home grid **does not refresh while USB is mounted**. Eject without rebooting.

## Prerequisites

- Python 3 + Pillow (`pip install -r requirements.txt`)
- Calibre library on disk (defaults in `scripts/fix_kindle_covers.py`)
- Kindle connected as USB with `documents\` and `system\thumbnails\`
- Optional: [xyz-windows-notify](https://github.com/xyz-rainbow/xyz-windows-notify) for start/end toasts
- Optional: Calibre `ebook-convert` when a PDF→AZW3 has no EXTH 201/202 cover image

## Playbook

From the skill directory, or the global install path:

```powershell
python "$env:USERPROFILE\.agents\skills\kindle-covers\scripts\fix_kindle_covers.py" diag --only "hail mary" obligatorio
python "$env:USERPROFILE\.agents\skills\kindle-covers\scripts\fix_kindle_covers.py" fix --only "hail mary" obligatorio
```

Verify: EXTH 113 = UUID, EXTH 501 = `PDOC`, thumbs `>2 KB`, file size unchanged. Then **eject, no reboot**.

## Limits

- Do not stamp a real Amazon ASIN (`B` + 9 alphanumerics) as EXTH 113
- Do not rewrite image-heavy bodies; rec0 only
- Do not use `calibredb` while the Calibre GUI is open
- Do not reboot after eject (Amazon may overwrite thumbs with the “No hay disponible” stub)

## Multi-agent install path

Canonical copy: `%USERPROFILE%\.agents\skills\kindle-covers\`

Other agents get a junction/symlink to that folder (`npx skills add -g -a "*"`).

## GitHub topics

`skills-sh` `npx-skills-add` `kindle` `calibre` `azw3` `mobi` `ebooks` `ai-agent-skill` `windows`

## License

MIT. See [LICENSE](LICENSE).
