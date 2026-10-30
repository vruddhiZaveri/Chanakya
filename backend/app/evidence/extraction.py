import hashlib
import json
from pathlib import Path
import subprocess
import sys
from threading import BoundedSemaphore

from app.core.errors import BackendError

MAX_UPLOAD = 1048576
MEDIA = {".txt": "text/plain", ".md": "text/markdown", ".pdf": "application/pdf"}
_extraction_slot = BoundedSemaphore(1)


def validate_file(filename, media, raw):
    if (
        not filename
        or len(filename) > 120
        or filename != filename.strip()
        or any(c in filename for c in "/\\:")
        or any(ord(c) < 32 for c in filename)
        or Path(filename).suffix.lower() not in MEDIA
    ):
        raise BackendError(
            "invalid_filename",
            "Use a simple .txt, .md or .pdf filename without a path.",
            422,
        )
    if media != MEDIA[Path(filename).suffix.lower()]:
        raise BackendError(
            "unsupported_document_type",
            "Filename and Content-Type must match .txt, .md or .pdf.",
            415,
        )
    if not raw or len(raw) > MAX_UPLOAD:
        raise BackendError(
            "document_size_limit", "Upload between 1 byte and 1 MiB.", 413
        )


def extract_pages(filename, media, raw):
    if not _extraction_slot.acquire(blocking=False):
        raise BackendError(
            "extraction_busy",
            "One document extraction is already active. Retry when it finishes.",
            429,
            True,
        )
    try:
        return _extract_pages(filename, media, raw)
    finally:
        _extraction_slot.release()


def _extract_pages(filename, media, raw):
    validate_file(filename, media, raw)
    if media == "application/pdf":
        if not raw.startswith(b"%PDF-"):
            raise BackendError("invalid_pdf", "The file is not a supported PDF.", 422)
        try:
            result = subprocess.run(
                [sys.executable, "-m", "app.evidence.pdf_worker"],
                input=raw,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=15,
                cwd=Path(__file__).resolve().parents[2],
                check=False,
            )
            if result.returncode or len(result.stdout) > 1300000:
                raise ValueError("PDF worker failed")
            pages = json.loads(result.stdout)["pages"]
        except subprocess.TimeoutExpired as error:
            raise BackendError(
                "extraction_timeout",
                "PDF extraction exceeded 15 seconds; no document was saved.",
                422,
            ) from error
        except (ValueError, KeyError) as error:
            raise BackendError(
                "pdf_extraction_failed",
                "PDF could not be extracted within the limits. Use an unencrypted text PDF up to 20 pages or export UTF-8 text.",
                422,
            ) from error
    else:
        try:
            pages = [raw.decode("utf-8-sig")]
        except UnicodeDecodeError as error:
            raise BackendError(
                "invalid_text_encoding", "Text documents must use UTF-8.", 422
            ) from error
    # Normalized line endings, no whitespace collapsing. Offsets reference these
    # stored extracted pages, not original PDF byte offsets or rendered geometry.
    pages = [p.replace("\r\n", "\n").replace("\r", "\n") for p in pages]
    if sum(map(len, pages)) > 100000 or any("\x00" in p for p in pages):
        raise BackendError(
            "extracted_text_limit",
            "Use readable text without NUL bytes, up to 100,000 characters.",
            422,
        )
    if not any(p.strip() for p in pages):
        raise BackendError(
            "no_extractable_text",
            "No readable text was found. Scanned PDFs require OCR, which is not implemented.",
            422,
        )
    return pages


def chunks(version_id, pages):
    rows = []
    for page_number, text in enumerate(pages, 1):
        # Overlapping, reproducible 500-character windows; never cross pages.
        for start in range(0, len(text), 450):
            end = min(start + 500, len(text))
            if text[start:end].strip():
                identity = hashlib.sha256(
                    f"{version_id}:{page_number}:{start}:{end}".encode()
                ).hexdigest()[:32]
                rows.append(
                    {
                        "id": identity,
                        "page": page_number,
                        "start_char": start,
                        "end_char": end,
                        "excerpt": text[start:end],
                    }
                )
            if end == len(text):
                break
    return rows
