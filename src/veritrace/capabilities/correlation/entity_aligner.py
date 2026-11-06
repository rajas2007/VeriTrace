"""Standardized 4-tier entity aligner with conservative RapidFuzz candidate generation.

CRITICAL INVARIANTS:
1. Exact validated identifiers establish authoritative identity (similarity = 1.0).
2. Similarity >= 0.95 produces high-confidence candidates (zero identifier contradictions).
3. Similarity >= 0.80 and < 0.95 produces human-review candidates.
4. Similarity < 0.80 rejects candidates as distinct entities.
5. Strict anti-override: Fuzzy similarity NEVER overrides conflicting validated identifiers.
"""

from __future__ import annotations

from rapidfuzz import fuzz

from veritrace.capabilities.correlation.models import (
    AlignedEntityPair,
    AlignmentTier,
)
from veritrace.domain.rules.cross_document import (
    clean_corporate_name,
    clean_string_identifier,
)


class EntityAligner:
    """Aligns entities across documents using exact identifiers and conservative RapidFuzz."""

    HIGH_CONFIDENCE_THRESHOLD = 0.95
    REVIEW_THRESHOLD = 0.80

    @classmethod
    def align_entity_pair(
        cls,
        source_doc_id: str,
        source_field_id: str,
        source_name: str,
        source_identifier: str | None,
        target_doc_id: str,
        target_field_id: str,
        target_name: str,
        target_identifier: str | None,
    ) -> AlignedEntityPair:
        """Align two entity mentions enforcing the 4-tier policy and anti-override guardrail."""
        # 1. Authoritative identifier check (e.g. GSTIN, PAN, vendor ID)
        if source_identifier and target_identifier:
            clean_source_id = clean_string_identifier(source_identifier)
            clean_target_id = clean_string_identifier(target_identifier)

            if clean_source_id and clean_target_id:
                if clean_source_id == clean_target_id:
                    return AlignedEntityPair(
                        source_doc_id=source_doc_id,
                        source_field_id=source_field_id,
                        target_doc_id=target_doc_id,
                        target_field_id=target_field_id,
                        alignment_tier=AlignmentTier.AUTHORITATIVE_MATCH,
                        similarity_score=1.0,
                        source_entity_name=source_name,
                        target_entity_name=target_name,
                        source_identifier=source_identifier,
                        target_identifier=target_identifier,
                        explanation=(
                            f"Authoritative identity established via matching identifier: "
                            f"'{source_identifier}'."
                        ),
                    )
                else:
                    # Strict Anti-Override Guardrail: Conflicting identifiers veto fuzzy match
                    return AlignedEntityPair(
                        source_doc_id=source_doc_id,
                        source_field_id=source_field_id,
                        target_doc_id=target_doc_id,
                        target_field_id=target_field_id,
                        alignment_tier=AlignmentTier.CONFLICTING_IDENTIFIERS,
                        similarity_score=0.0,
                        source_entity_name=source_name,
                        target_entity_name=target_name,
                        source_identifier=source_identifier,
                        target_identifier=target_identifier,
                        explanation=(
                            f"Conflicting authoritative identifiers: '{source_identifier}' vs "
                            f"'{target_identifier}'. Anti-override guardrail prevents matching."
                        ),
                    )

        # 2. Exact normalized corporate name check
        norm_source = clean_corporate_name(source_name)
        norm_target = clean_corporate_name(target_name)

        if norm_source and norm_target and norm_source == norm_target:
            return AlignedEntityPair(
                source_doc_id=source_doc_id,
                source_field_id=source_field_id,
                target_doc_id=target_doc_id,
                target_field_id=target_field_id,
                alignment_tier=AlignmentTier.AUTHORITATIVE_MATCH,
                similarity_score=1.0,
                source_entity_name=source_name,
                target_entity_name=target_name,
                source_identifier=source_identifier,
                target_identifier=target_identifier,
                explanation=(
                    f"Authoritative identity established via exact normalized corporate name: "
                    f"'{norm_source}'."
                ),
            )

        # 3. Conservative RapidFuzz candidate evaluation
        if not norm_source or not norm_target:
            ratio = 0.0
        else:
            raw_ratio = fuzz.token_sort_ratio(norm_source, norm_target)
            ratio = raw_ratio / 100.0

        if ratio >= cls.HIGH_CONFIDENCE_THRESHOLD:
            tier = AlignmentTier.HIGH_CONFIDENCE_CANDIDATE
            exp = (
                f"High-confidence candidate match (similarity {ratio:.2%}). "
                f"Zero conflicting identifiers detected."
            )
        elif ratio >= cls.REVIEW_THRESHOLD:
            tier = AlignmentTier.REVIEW_CANDIDATE
            exp = (
                f"Candidate match requiring human examiner review (similarity {ratio:.2%}). "
                f"Does not automatically trigger contradiction findings."
            )
        else:
            tier = AlignmentTier.NO_MATCH
            exp = f"Distinct entities (similarity {ratio:.2%} below 80% threshold)."

        return AlignedEntityPair(
            source_doc_id=source_doc_id,
            source_field_id=source_field_id,
            target_doc_id=target_doc_id,
            target_field_id=target_field_id,
            alignment_tier=tier,
            similarity_score=round(ratio, 4),
            source_entity_name=source_name,
            target_entity_name=target_name,
            source_identifier=source_identifier,
            target_identifier=target_identifier,
            explanation=exp,
        )
