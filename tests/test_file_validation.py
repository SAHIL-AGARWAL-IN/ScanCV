"""File validation and type dispatch — size limits, MIME checks, extension fallback."""
import pytest

from backend.core.config import MAX_FILE_SIZE_BYTES
from backend.services.resume_parser import (
    FileParsingError,
    extract_text,
    validate_file,
)

# Minimal but structurally valid PDF — python-magic detects it by the %PDF header.
MINIMAL_PDF = (
    b'%PDF-1.4\n'
    b'1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n'
    b'2 0 obj\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\n'
    b'trailer\n<< /Root 1 0 R >>\n'
)


class TestValidateFile:
    def test_valid_pdf(self):
        is_valid, error, file_type = validate_file(MINIMAL_PDF, 'resume.pdf')
        assert is_valid and file_type == 'pdf'

    def test_empty_file_rejected(self):
        is_valid, error, _ = validate_file(b'', 'resume.pdf')
        assert not is_valid
        assert 'empty' in error.lower()

    def test_oversized_file_rejected(self):
        is_valid, error, _ = validate_file(b'x' * (MAX_FILE_SIZE_BYTES + 1), 'resume.pdf')
        assert not is_valid
        assert 'exceeds' in error.lower()

    def test_plain_text_rejected(self):
        is_valid, error, _ = validate_file(b'just some text', 'resume.txt')
        assert not is_valid
        assert 'unsupported' in error.lower()

    def test_docx_extension_fallback(self):
        # python-magic-bin on Windows reports OOXML as octet-stream; the
        # extension fallback must accept a genuine .docx filename.
        # Random bytes stand in for the (undetectable) docx content.
        is_valid, error, file_type = validate_file(b'\x50\x4b\x03\x04' + b'0' * 100, 'resume.docx')
        assert is_valid and file_type == 'docx'

    def test_fake_extension_still_rejected(self):
        # Same octet-stream bytes but with a non-resume extension: rejected.
        is_valid, error, _ = validate_file(b'\x50\x4b\x03\x04' + b'0' * 100, 'resume.zip')
        assert not is_valid


class TestExtractDispatch:
    def test_doc_raises_unsupported(self):
        with pytest.raises(FileParsingError, match='not supported'):
            extract_text(b'legacy', 'doc')

    def test_unknown_type_raises(self):
        from backend.services.resume_parser import FileValidationError
        with pytest.raises(FileValidationError):
            extract_text(b'data', 'txt')
