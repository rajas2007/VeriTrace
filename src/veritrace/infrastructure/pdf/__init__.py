"""PDF processing and page rasterization infrastructure adapters."""

from veritrace.infrastructure.pdf.rasterizer import (
    DocumentRasterizerProtocol,
    PyMuPdfPageRasterizer,
)

__all__ = [
    "DocumentRasterizerProtocol",
    "PyMuPdfPageRasterizer",
]
