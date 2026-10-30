"""One bounded PDF extraction subprocess; no document code or URLs are executed."""

import io
import json
import sys


def main():
    # POSIX memory ceiling. Windows uses the timeout/output/input bounds but has no
    # equivalent process RAM limit here; this local prototype accepts trusted PDFs.
    if sys.platform != "win32":
        import resource

        resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024,) * 2)
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(sys.stdin.buffer.read(1048577)), strict=True)
    if reader.is_encrypted:
        raise ValueError("encrypted_pdf")
    if not 1 <= len(reader.pages) <= 20:
        raise ValueError("pdf_page_limit")
    pages, total = [], 0
    for page in reader.pages:
        content = page.get_contents()
        if content is not None and len(content.get_data()) > 2 * 1024 * 1024:
            raise ValueError("pdf_stream_limit")
        text = page.extract_text() or ""
        total += len(text)
        if total > 100000:
            raise ValueError("extracted_text_limit")
        pages.append(text)
    print(json.dumps({"pages": pages}, ensure_ascii=True))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Never echo document contents or parser errors.
        print(json.dumps({"error": "pdf_extraction_failed"}))
        sys.exit(1)
