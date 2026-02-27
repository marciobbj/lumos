<p align="center">
  <img src="assets/logo.svg" width="150" alt="Lumos Logo">
</p>

<h1 align="center">Lumos</h1>
<p align="center"><b>A Python application designed to extract text from PDF documents using OCR technology and provide AI-powered translation capabilities.</b></p>

---

## Features

- **Project-based workflow** — every scan session is saved as a named project on disk. Open the app and pick up where you left off.
- **Project browser** — the home screen lists all projects with their current status, progress, and last-updated time. Create, open, or delete projects from one place.
- **OCR extraction** — converts PDF pages to images via Poppler and runs Tesseract OCR. Supports Portuguese, English, French, German, and Spanish (individually or combined).
- **AI translation** — translates the extracted text page by page using either a local [LM Studio](https://lmstudio.ai/) server or the OpenCode CLI. Partial results are streamed to the UI as each page completes.
- **Pause and resume** — pause an OCR or translation run at any time. Progress is saved to disk page by page (`pages/` for OCR, `translation_pages/` for translation), so resuming skips already-completed pages.
- **Live preview** — OCR and translation results appear in the UI as each page is processed, without waiting for the full document to finish.
- **Auto-save** — results are written to each project's folder automatically as processing proceeds.

---

## Platform Support

This app is currently supported on **Linux & macOS only** because it requires the **opencode** CLI to be installed (enforced by a startup check).

---

## Prerequisites

### System Dependencies

Ensure the following are installed on your system:

1. **Tesseract OCR** (for text extraction)
    ```bash
    # Ubuntu/Debian
    sudo apt-get install tesseract-ocr tesseract-ocr-por tesseract-ocr-eng tesseract-ocr-fra tesseract-ocr-deu tesseract-ocr-spa
   
    # macOS
    brew install tesseract
    ```

Optional (cross-platform): download language data into `./tessdata/`:

```bash
python scripts/download_tessdata.py
```

Note: `*.traineddata` files are large; many teams keep them out of git and download them as part of setup.

### Troubleshooting: Tesseract languages / TESSDATA_PREFIX

If you see errors like:

- `Please make sure the TESSDATA_PREFIX environment variable is set to your "tessdata" directory`
- `Failed loading language 'fra'`
- `Tesseract couldn't load any languages! Could not initialize tesseract.`

It means Tesseract cannot find the `*.traineddata` files for the languages you selected.

1. Check which languages are installed:
   ```bash
   tesseract --list-langs
   ```

2. Install missing language packs.
   - Ubuntu/Debian example:
     ```bash
     sudo apt-get install tesseract-ocr-por tesseract-ocr-eng tesseract-ocr-fra tesseract-ocr-deu tesseract-ocr-spa
     ```
   - macOS (Homebrew): language data is usually included with the install, but can vary by setup.

3. Point `TESSDATA_PREFIX` to the directory that contains the traineddata files:
   ```bash
   export TESSDATA_PREFIX="/path/to/tessdata"
   tesseract --list-langs
   ```

Notes:
- This app supports Portuguese (`por`), English (`eng`), French (`fra`), German (`deu`), and Spanish (`spa`).
- You can also provide your own `tessdata/` directory in the repo root and set `TESSDATA_PREFIX` to it (or run `python scripts/download_tessdata.py`).
- Prefer installing language packs via your OS package manager, or provide a local `tessdata/` directory in the repo.

2. **Poppler** (for PDF processing)
   ```bash
   # Ubuntu/Debian
   sudo apt-get install poppler-utils
   
   # macOS
   brew install poppler
   ```

3. **opencode** (required; Linux-only)
    - The app requires the opencode CLI to be installed and checks for it at startup.

4. **Python**
    ```bash
    pyenv install 3.12.2
    ```

## Setup

### 1. Clone/Navigate to Project

```bash
cd /path/to/lumos
```

### 2. Set Python Version

```bash
pyenv local lumos
```

This creates a `.python-version` file that tells pyenv to use the `lumos` virtualenv.

### 3. Create Virtual Environment

```bash
pyenv virtualenv 3.12.2 lumos
```

### 4. Install Dependencies

```bash
pip install -e .
```

This installs the project in editable mode with all dependencies specified in `pyproject.toml`.

### 5. Verify Installation

```bash
python -c "import flet; import pytesseract; import pdf2image; import openai; print('✓ All dependencies installed successfully')"
```

## Configuration

## Project Storage (Default Output Directory)

Projects are stored in a per-user application data directory by default (not inside this repository). Each project is a folder containing `project.json`, `ocr.txt`, `translation.txt`, plus page caches under `pages/` and `translation_pages/`.

The output directory is created automatically on first run.

Default locations:

- Linux: `$XDG_DATA_HOME/Lumos/output` (or `~/.local/share/Lumos/output`)
- macOS: `~/Library/Application Support/Lumos/output`
- Windows: `%APPDATA%\\Lumos\\output`

Override the output directory (useful for development) by setting:

```bash
export LUMOS_OUTPUT_DIR="/path/to/output"
```

### Translation Backend

Set environment variables to configure the LM Studio OpenAI-compatible API:

```bash
export OPENAI_API_KEY="your-key-here"
export OPENAI_BASE_URL="http://localhost:8000/v1"  # Default LM Studio endpoint
```

## Running the App

```bash
python main.py
```

The desktop application will launch in a new Flet window.

### 💡 Tips for Large Documents

- Use **Pause** to stop a long run and continue later — progress is saved after every page.
- For very large documents, consider splitting the PDF into chapters before creating a project. Smaller chunks are easier to review incrementally and recover from possible errors.

## Dependencies

- **flet** (>=0.25.0): UI framework
- **pytesseract** (>=0.3.13): OCR engine interface
- **pdf2image** (>=1.17.0): PDF page extraction
- **Pillow** (>=11.0.0): Image processing
- **openai** (>=1.0.0): LM Studio API client (OpenAI compatible)
- **httpx** (>=0.27.0): Async HTTP client
- **opencode** (CLI): required for translation (Linux & macOS only)

## License

MIT
