import io
import logging
import pypdf

logger = logging.getLogger(__name__)

# Unsupported file extensions — rejected immediately
UNSUPPORTED_EXTENSIONS = {".txt", ".pages", ".odt", ".rtf", ".wps", ".wpd"}

async def parse_cv(pdf_bytes: bytes, filename: str = "") -> dict:
    """
    Extracts structured text from CV PDF bytes.
    Args:
        pdf_bytes: raw PDF file bytes
        filename:  original filename (used for unsupported format detection)
    Returns:
        dict with extracted cv_text and basic sections
    """

    # --- Error: no bytes received ---
    if not pdf_bytes or not isinstance(pdf_bytes, bytes):
        logger.error("parse_cv called with empty or invalid input.")
        return {"cv_text": "", "page_count": 0, "parse_error": "No file data received."}

    # --- Error: file too small to be a real PDF ---
    if len(pdf_bytes) < 10:
        logger.error(f"File too small to be a valid PDF ({len(pdf_bytes)} bytes).")
        return {"cv_text": "", "page_count": 0, "parse_error": "Uploaded file is too small or empty."}

    # --- Error: unsupported file format (.txt, .pages, .odt, etc.) ---
    if filename:
        ext = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""
        if ext in UNSUPPORTED_EXTENSIONS:
            logger.warning(f"Unsupported file format uploaded: '{filename}' (ext: {ext})")
            return {
                "cv_text": "", "page_count": 0,
                "parse_error": f"Unsupported file format '{ext}'. Please upload your CV as a PDF file."
            }

    # --- Error: not a PDF (wrong magic bytes) ---
    if not pdf_bytes[:4] == b"%PDF":
        logger.error("Uploaded file does not appear to be a valid PDF.")
        return {"cv_text": "", "page_count": 0, "parse_error": "Invalid file type. Please upload a PDF."}

    try:
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))

        # --- Error: zero pages ---
        if len(reader.pages) == 0:
            logger.warning("PDF has no pages.")
            return {"cv_text": "", "page_count": 0, "parse_error": "PDF contains no pages."}

        full_text = ""
        for i, page in enumerate(reader.pages):
            try:
                extracted = page.extract_text()
                if extracted:
                    full_text += extracted + "\n"
            except Exception as e:
                # Don't crash entire parse if one page fails — skip and log
                logger.warning(f"Failed to extract text from page {i + 1}: {e}")

        full_text = full_text.strip()

        # --- Error: scanned/image-based PDF with no extractable text ---
        if not full_text:
            logger.warning("PDF parsed but no text extracted — likely a scanned image.")
            return {
                "cv_text": "",
                "page_count": len(reader.pages),
                "parse_error": "No text could be extracted. This CV may be a scanned image. Please upload a text-based PDF."
            }

        # Truncate to 3000 chars to avoid token overflow
        if len(full_text) > 3000:
            full_text = full_text[:3000]

        return {
            "cv_text": full_text,
            "page_count": len(reader.pages),
            "parse_error": None
        }

    except pypdf.errors.PdfReadError as e:
        # --- Error: corrupt, truncated, or password-protected PDF ---
        logger.error(f"Corrupt or unreadable PDF: {e}")
        return {"cv_text": "", "page_count": 0, "parse_error": "PDF is corrupted or cannot be read. Please re-upload."}

    except Exception as e:
        logger.error(f"CV parsing error: {e}")
        return {"cv_text": "", "page_count": 0, "parse_error": str(e)}