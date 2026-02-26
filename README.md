<p align="center">
  <img src="assets/logo.svg" width="150" alt="Lumos Logo">
</p>

<h1 align="center">Lumos</h1>
<p align="center"><b>A Python application designed to extract text from PDF documents using OCR technology and provide AI-powered translation capabilities.</b></p>

---

## Features

- **Project-based workflow** — every scan session is saved as a named project under `output/<project>/`. Open the app and pick up where you left off.
- **Project browser** — the home screen lists all projects with their current status, progress, and last-updated time. Create, open, or delete projects from one place.
- **OCR extraction** — converts PDF pages to images via Poppler and runs Tesseract OCR. Supports Portuguese, English, French, German, and Spanish (individually or combined).
- **AI translation** — translates the extracted text page by page using either a local [LM Studio](https://lmstudio.ai/) server or the OpenCode CLI. Partial results are streamed to the UI as each page completes.
- **Pause and resume** — pause an OCR or translation run at any time. Progress is saved to disk page by page (`pages/` for OCR, `translation_pages/` for translation), so resuming skips already-completed pages.
- **Live preview** — OCR and translation results appear in the UI as each page is processed, without waiting for the full document to finish.
- **Auto-save** — results are written to `output/<project>/ocr.txt` and `output/<project>/translation.txt` automatically as processing proceeds.

---

## Prerequisites

### System Dependencies

Ensure the following are installed on your system:

1. **Tesseract OCR** (for text extraction)
   ```bash
   # Ubuntu/Debian
   sudo apt-get install tesseract-ocr tesseract-ocr-por
   
   # macOS
   brew install tesseract
   ```

2. **Poppler** (for PDF processing)
   ```bash
   # Ubuntu/Debian
   sudo apt-get install poppler-utils
   
   # macOS
   brew install poppler
   ```

3. **Python 3.12.2** (managed via pyenv)
   ```bash
   pyenv install 3.12.2
   ```

## Setup

### 1. Clone/Navigate to Project

```bash
cd /home/io/workspace/lumos
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

## Project Structure

```
lumos/
├── pyproject.toml              # Project metadata and dependencies
├── .python-version             # Python version (3.12.2)
├── README.md                   # This file
├── main.py                     # Application entry point
├── src/
│   ├── ocr/                    # OCR extraction logic
│   ├── translation/            # Translation logic (LM Studio, OpenCode)
│   ├── projects/               # Project data model and manager
│   └── ui/                     # Flet UI (project browser + scan screen)
└── output/                     # One folder per project
    └── <project-name>/
        ├── project.json        # Metadata and progress state
        ├── ocr.txt             # Full OCR result
        ├── translation.txt     # Full translation result
        ├── pages/              # Per-page OCR cache (used for resume)
        │   ├── page_0000.txt
        │   └── ...
        └── translation_pages/  # Per-page translation cache (used for resume)
            ├── page_0000.txt
            └── ...
```

## Dependencies

- **flet** (>=0.25.0): UI framework
- **pytesseract** (>=0.3.13): OCR engine interface
- **pdf2image** (>=1.17.0): PDF page extraction
- **Pillow** (>=11.0.0): Image processing
- **openai** (>=1.0.0): LM Studio API client (OpenAI compatible)
- **httpx** (>=0.27.0): Async HTTP client

## License

MIT
