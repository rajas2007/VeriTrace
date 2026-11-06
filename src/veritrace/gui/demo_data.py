"""Industrial 4-Document Demonstration Seed Data Generator.

Provides the 4-document manufacturing and supply-chain procurement scenario:
1. PO: 1000 KG SS 316L, Rs 450,000 (Open Order)
2. Delivery Challan: 800 KG SS 304, Heat #H-8821-A (Challan)
3. Mill Test Certificate (MTC): Heat #H-8821-A, SS 304
4. Commercial Invoice: 1000 KG billed, Rs 450,000 + Rs 81,000 GST + Rs 5,000 freight = Rs 536,000
"""

from __future__ import annotations

from veritrace.application.services.demo_data import (
    generate_dc_document,
    generate_invoice_document,
    generate_mtc_document,
    generate_po_document,
    seed_industrial_demo,
)

__all__ = [
    "generate_dc_document",
    "generate_invoice_document",
    "generate_mtc_document",
    "generate_po_document",
    "seed_industrial_demo",
]
