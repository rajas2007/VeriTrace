"""Audit ledger, actor, and organizational sector enums."""

from enum import StrEnum


class AuditEventType(StrEnum):
    """Immutable audit trail event classifications."""

    CASE_CREATED = "CASE_CREATED"
    DOC_UPLOADED = "DOC_UPLOADED"
    TEXT_EXTRACTED = "TEXT_EXTRACTED"
    OCR_EXTRACTED = "OCR_EXTRACTED"
    ANOMALY_FLAGGED = "ANOMALY_FLAGGED"
    HUMAN_REVIEW_CONFIRMED = "HUMAN_REVIEW_CONFIRMED"
    HUMAN_REVIEW_DISMISSED = "HUMAN_REVIEW_DISMISSED"
    HUMAN_REVIEW_ANNOTATED = "HUMAN_REVIEW_ANNOTATED"
    DOSSIER_COMPILED = "DOSSIER_COMPILED"
    SIGNATURE_ENROLLED = "SIGNATURE_ENROLLED"
    RETENTION_PURGE_TRIGGERED = "RETENTION_PURGE_TRIGGERED"


class ActorType(StrEnum):
    """Originator of a domain action or finding decision.

    INVARIANT: Findings can be proposed by SYSTEM_PIPELINE, but final confirmation
    or dismissal requires HUMAN_ANALYST. AI_SYNTHESIZER is strictly prohibited from
    altering finding severity or status.
    """

    SYSTEM_PIPELINE = "SYSTEM_PIPELINE"
    HUMAN_ANALYST = "HUMAN_ANALYST"
    AI_SYNTHESIZER = "AI_SYNTHESIZER"


class IndustrySector(StrEnum):
    """Target industrial sectors for multi-tenant workspace partitioning."""

    MANUFACTURING = "MANUFACTURING"
    SUPPLY_CHAIN = "SUPPLY_CHAIN"
    BFSI = "BFSI"
    INSURANCE = "INSURANCE"
    GOVERNMENT = "GOVERNMENT"
    CONSTRUCTION = "CONSTRUCTION"
    ENTERPRISE_HR = "ENTERPRISE_HR"


class EntityType(StrEnum):
    """Canonical cross-document entity classification."""

    PERSON_NAME = "PERSON_NAME"
    DATE_OF_BIRTH = "DATE_OF_BIRTH"
    GOVERNMENT_ID = "GOVERNMENT_ID"
    EMPLOYER_NAME = "EMPLOYER_NAME"
    FINANCIAL_TOTAL = "FINANCIAL_TOTAL"
    ORGANIZATION_NAME = "ORGANIZATION_NAME"
    ADDRESS = "ADDRESS"
    DATE_OF_ISSUE = "DATE_OF_ISSUE"
    TAX_IDENTIFIER = "TAX_IDENTIFIER"  # e.g., GSTIN, PAN
    ITEM_DESCRIPTION = "ITEM_DESCRIPTION"
    QUANTITY = "QUANTITY"
    MATERIAL_GRADE = "MATERIAL_GRADE"
    DOCUMENT_REFERENCE = "DOCUMENT_REFERENCE"
    BATCH_NUMBER = "BATCH_NUMBER"
    PRODUCT_CODE = "PRODUCT_CODE"
