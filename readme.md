# 📄 LitePDF — Lightweight PDF Reader & Editor



A fast, low-resource PDF reader and editor for Windows.
Built with **Python + PyMuPDF + tkinter** and compiled to a single `.exe` via **GitHub Actions**.

---

## ✨ Features

| Feature | Details |
|---|---|
| 📖 View | Smooth rendering at 50 %–300 % zoom |
| 🗂️ Navigate | Page sidebar, keyboard arrows, page-number jump |
| ↩️ Rotate | CW / CCW per-session rotation |
| ✏️ Annotate | Click to place text directly on a page |
| 📋 Extract | Copy all text from the current page |
| 🔗 Merge | Combine any number of PDFs into one |
| ✂️ Split | Burst a PDF into single-page files |
| 🔐 Encrypt | AES-256 password protection |
| 💾 Save | Write a clean, optimised copy |

---

## 🚀 Download

Grab the latest **LitePDF.exe** from the [Releases](../../releases) page — no installer, no runtime dependencies.

---

## 🛠️ Build Locally

```bash
# 1. Clone
git clone https://github.com/YOUR_USERNAME/litepdf
cd litepdf

# 2. Install deps
pip install -r requirements.txt

# 3. Run from source
python main.py

# 4. Build .exe
pyinstaller litepdf.spec --clean --noconfirm
# Output: dist/LitePDF.exe
```

---

## 🤖 GitHub Actions CI/CD

Every push to `main` builds and uploads `LitePDF.exe` as a workflow artifact.
Pushing a version tag creates a public **GitHub Release** with the EXE attached:

```bash
git tag v1.0.0
git push origin v1.0.0
```

Workflow file: [`.github/workflows/build.yml`](.github/workflows/build.yml)

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+O` | Open PDF |
| `Ctrl+S` | Save copy |
| `← / →` | Previous / next page |
| `Home / End` | First / last page |
| `Ctrl++ / Ctrl+-` | Zoom in / out |
| `Ctrl+0` | Fit to width |
| `Ctrl+scroll` | Zoom with mouse wheel |
| `F9` | Toggle page sidebar |

---

## 🪶 Resource Usage

| Metric | Value |
|---|---|
| Idle RAM | ~25–40 MB |
| Peak RAM (large PDF) | ~80–120 MB |
| CPU (idle/reading) | < 3 % |
| EXE size | ~25–35 MB |

---

## 📦 Tech Stack

- **[PyMuPDF](https://pymupdf.readthedocs.io/)** — PDF rendering engine (fastest Python PDF lib)
- **tkinter** — native Windows GUI (built into Python, zero overhead)
- **Pillow** — image conversion for canvas rendering
- **PyInstaller** — packages everything into a single `.exe`
