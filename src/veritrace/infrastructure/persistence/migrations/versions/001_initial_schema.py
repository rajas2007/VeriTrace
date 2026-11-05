"""Initial database schema with 15 core entities and finding_evidence_map.

Revision ID: 001_initial_schema
Revises: None
Create Date: 2026-11-06 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. organizations
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("industry_sector", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # 2. authorized_subjects
    op.create_table(
        "authorized_subjects",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("designation", sa.String(length=128), nullable=False),
        sa.Column("id_reference", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_authorized_subjects_org_id", "authorized_subjects", ["organization_id"])

    # 3. signature_references
    op.create_table(
        "signature_references",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("subject_id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("crop_image_path", sa.String(length=512), nullable=False),
        sa.Column("sha256_hash", sa.String(length=64), nullable=False),
        sa.Column("embedding_vector", sa.LargeBinary(), nullable=True),
        sa.Column("enrollment_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_document_ref", sa.String(length=255), nullable=False),
        sa.Column("consent_mandate_ref", sa.String(length=255), nullable=False),
        sa.Column("retention_expiry_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("access_role_required", sa.String(length=64), nullable=False),
        sa.Column("provenance_json", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["subject_id"], ["authorized_subjects.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_signature_references_subject_id",
        "signature_references",
        ["subject_id"],
    )
    op.create_index(
        "idx_signature_references_org_id",
        "signature_references",
        ["organization_id"],
    )

    # 4. investigations
    op.create_table(
        "investigations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("reference_code", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("risk_score", sa.Float(), nullable=False),
        sa.Column("risk_classification", sa.String(length=32), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reference_code"),
    )
    op.create_index(
        "idx_investigations_reference_code",
        "investigations",
        ["reference_code"],
        unique=True,
    )
    op.create_index("idx_investigations_status", "investigations", ["status"])
    op.create_index("idx_investigations_org_id", "investigations", ["organization_id"])

    # 5. investigation_jobs
    op.create_table(
        "investigation_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("investigation_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("current_stage", sa.String(length=64), nullable=False),
        sa.Column("progress_pct", sa.Integer(), nullable=False),
        sa.Column("stage_message", sa.String(length=255), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("can_resume", sa.Boolean(), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("max_retries", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_investigation_jobs_inv_id", "investigation_jobs", ["investigation_id"])
    op.create_index("idx_investigation_jobs_status", "investigation_jobs", ["status"])

    # 6. documents
    op.create_table(
        "documents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("investigation_id", sa.String(length=36), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("file_hash_sha256", sa.String(length=64), nullable=False),
        sa.Column("mime_type", sa.String(length=64), nullable=False),
        sa.Column("document_type", sa.String(length=64), nullable=False),
        sa.Column("primary_language", sa.String(length=16), nullable=False),
        sa.Column("primary_script", sa.String(length=32), nullable=False),
        sa.Column("languages_json", sa.JSON(), nullable=True),
        sa.Column("classification_confidence", sa.Float(), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("storage_path", sa.String(length=512), nullable=False),
        sa.Column("quality_status", sa.String(length=32), nullable=False),
        sa.Column("structured_content", sa.JSON(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_documents_inv_id", "documents", ["investigation_id"])
    op.create_index("idx_documents_hash", "documents", ["file_hash_sha256"])

    # 7. document_pages
    op.create_table(
        "document_pages",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("width_pixels", sa.Integer(), nullable=False),
        sa.Column("height_pixels", sa.Integer(), nullable=False),
        sa.Column("dpi", sa.Integer(), nullable=False),
        sa.Column("image_storage_path", sa.String(length=512), nullable=False),
        sa.Column("has_digital_text", sa.Boolean(), nullable=False),
        sa.Column("text_layer_type", sa.String(length=32), nullable=False),
        sa.Column("primary_language", sa.String(length=16), nullable=False),
        sa.Column("primary_script", sa.String(length=32), nullable=False),
        sa.Column("languages_json", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "page_number", name="uq_document_pages_doc_num"),
    )
    op.create_index("idx_document_pages_doc_id", "document_pages", ["document_id"])

    # 8. entities
    op.create_table(
        "entities",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("investigation_id", sa.String(length=36), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("canonical_value", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_entities_inv_id", "entities", ["investigation_id"])

    # 9. extracted_fields
    op.create_table(
        "extracted_fields",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("page_id", sa.String(length=36), nullable=False),
        sa.Column("entity_id", sa.String(length=36), nullable=True),
        sa.Column("field_name", sa.String(length=128), nullable=False),
        sa.Column("field_value", sa.Text(), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("field_type", sa.String(length=64), nullable=True),
        sa.Column("language", sa.String(length=16), nullable=True),
        sa.Column("script", sa.String(length=32), nullable=True),
        sa.Column("lang_confidence", sa.Float(), nullable=True),
        sa.Column("normalized_bbox", sa.JSON(), nullable=True),
        sa.Column("extraction_source", sa.String(length=32), nullable=False),
        sa.Column("ocr_engine", sa.String(length=64), nullable=True),
        sa.Column("ocr_model_version", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(["page_id"], ["document_pages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_extracted_fields_page_id", "extracted_fields", ["page_id"])
    op.create_index("idx_extracted_fields_entity_id", "extracted_fields", ["entity_id"])
    op.create_index("idx_extracted_fields_name", "extracted_fields", ["field_name"])

    # 10. findings
    op.create_table(
        "findings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("investigation_id", sa.String(length=36), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("epistemic_tier", sa.String(length=32), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("narrative_explanation", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("investigator_guidance", sa.Text(), nullable=True),
        sa.Column("review_status", sa.String(length=32), nullable=False),
        sa.Column("signature_reference_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["signature_reference_id"], ["signature_references.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_findings_inv_id", "findings", ["investigation_id"])
    op.create_index("idx_findings_tier", "findings", ["epistemic_tier"])
    op.create_index("idx_findings_severity", "findings", ["severity"])
    op.create_index("idx_findings_sigref_id", "findings", ["signature_reference_id"])

    # 11. evidence
    op.create_table(
        "evidence",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("page_id", sa.String(length=36), nullable=False),
        sa.Column("crop_image_path", sa.String(length=512), nullable=False),
        sa.Column("normalized_bbox", sa.JSON(), nullable=False),
        sa.Column("pixel_x", sa.Integer(), nullable=False),
        sa.Column("pixel_y", sa.Integer(), nullable=False),
        sa.Column("pixel_width", sa.Integer(), nullable=False),
        sa.Column("pixel_height", sa.Integer(), nullable=False),
        sa.Column("heatmap_image_path", sa.String(length=512), nullable=True),
        sa.Column("grounding_explanation", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["page_id"], ["document_pages.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_evidence_page_id", "evidence", ["page_id"])

    # 12. finding_evidence_map
    op.create_table(
        "finding_evidence_map",
        sa.Column("finding_id", sa.String(length=36), nullable=False),
        sa.Column("evidence_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["finding_id"], ["findings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["evidence_id"], ["evidence.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("finding_id", "evidence_id"),
    )
    op.create_index("idx_finding_evidence_map_finding_id", "finding_evidence_map", ["finding_id"])
    op.create_index("idx_finding_evidence_map_evidence_id", "finding_evidence_map", ["evidence_id"])

    # 13. cross_document_relations
    op.create_table(
        "cross_document_relations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("investigation_id", sa.String(length=36), nullable=False),
        sa.Column("source_document_id", sa.String(length=36), nullable=False),
        sa.Column("target_document_id", sa.String(length=36), nullable=False),
        sa.Column("relation_type", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("finding_id", sa.String(length=36), nullable=True),
        sa.Column("similarity_score", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["finding_id"], ["findings.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_cross_document_relations_inv_id",
        "cross_document_relations",
        ["investigation_id"],
    )
    op.create_index(
        "idx_cross_document_relations_source_doc",
        "cross_document_relations",
        ["source_document_id"],
    )
    op.create_index(
        "idx_cross_document_relations_target_doc",
        "cross_document_relations",
        ["target_document_id"],
    )

    # 14. review_decisions
    op.create_table(
        "review_decisions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("finding_id", sa.String(length=36), nullable=False),
        sa.Column("reviewer_id", sa.String(length=64), nullable=False),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["finding_id"], ["findings.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_review_decisions_finding_id", "review_decisions", ["finding_id"])

    # 15. dossiers
    op.create_table(
        "dossiers",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("investigation_id", sa.String(length=36), nullable=False),
        sa.Column("dossier_data", sa.JSON(), nullable=False),
        sa.Column("pdf_storage_path", sa.String(length=512), nullable=False),
        sa.Column("pdf_hash_sha256", sa.String(length=64), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_dossiers_inv_id", "dossiers", ["investigation_id"])

    # 16. audit_events
    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("investigation_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("actor_type", sa.String(length=64), nullable=False),
        sa.Column("actor_id", sa.String(length=64), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_payload", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_audit_events_inv_id", "audit_events", ["investigation_id"])
    op.create_index("idx_audit_events_timestamp", "audit_events", ["timestamp"])

    # Append-only enforcement triggers for audit_events (SQLite)
    op.execute(
        sa.text(
            """
            CREATE TRIGGER prevent_audit_events_update
            BEFORE UPDATE ON audit_events
            BEGIN
                SELECT RAISE(
                    ABORT,
                    'AuditEvent records are immutable and append-only: UPDATE prohibited'
                );
            END;
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE TRIGGER prevent_audit_events_delete
            BEFORE DELETE ON audit_events
            BEGIN
                SELECT RAISE(
                    ABORT,
                    'AuditEvent records are immutable and append-only: DELETE prohibited'
                );
            END;
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP TRIGGER IF EXISTS prevent_audit_events_update"))
    op.execute(sa.text("DROP TRIGGER IF EXISTS prevent_audit_events_delete"))
    op.drop_table("audit_events")
    op.drop_table("dossiers")
    op.drop_table("review_decisions")
    op.drop_table("cross_document_relations")
    op.drop_table("finding_evidence_map")
    op.drop_table("evidence")
    op.drop_table("findings")
    op.drop_table("extracted_fields")
    op.drop_table("entities")
    op.drop_table("document_pages")
    op.drop_table("documents")
    op.drop_table("investigation_jobs")
    op.drop_table("investigations")
    op.drop_table("signature_references")
    op.drop_table("authorized_subjects")
    op.drop_table("organizations")
