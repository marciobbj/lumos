<p align="center">
  <img src="assets/logo.svg" width="150" alt="Lumos Logo">
</p>

<h1 align="center">Lumos</h1>
<p align="center"><b>A Python application for extracting text from PDFs with and translate it, backed by AI.</b></p>

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

### 💡 Tip for Large Documents
For documents with many pages, it is highly recommended to **split the PDF into smaller parts** (e.g., by chapters). Extract and translate them separately, and then merge the results if needed. This ensures better stability and allows you to review the progress incrementally.

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
│   └── ui/                     # Flet UI components
└── output/                     # Generated extracted text/translations
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
