"""Core cross-document correlation engine.

Orchestrates:
1. Deterministic normalization of extracted metrics and references.
2. 4-tier entity alignment with anti-override protection.
3. Multi-document line-item aggregation (combining partial deliveries and invoices).
4. Pure domain comparison rule execution across industrial transaction documents.
5. Structured reconciliation result assembly.
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from veritrace.capabilities.correlation.entity_aligner import EntityAligner
from veritrace.capabilities.correlation.models import (
    AlignedEntityPair,
    ComparisonResult,
    CrossDocumentCorrelationResult,
    DocumentCorrelationInput,
    LineItemAggregation,
)
from veritrace.capabilities.correlation.normalization import (
    normalize_amount,
    normalize_date,
    normalize_identifier,
    normalize_material_grade,
    normalize_quantity,
)
from veritrace.domain.entities.extracted_field import ExtractedField
from veritrace.domain.rules.cross_document import (
    BatchNumberConsistencyRule,
    ChronologicalSequenceRule,
    ExplicitDocumentReferenceCompletenessRule,
    FinancialTotalConsistencyRule,
    MaterialGradeConsistencyRule,
    QuantityConsistencyRule,
    ReferenceCodeConsistencyRule,
    RuleEvaluationResult,
)


class CrossDocumentCorrelationEngine:
    """Deterministic correlation and contradiction engine for cross-document intelligence."""

    def __init__(self, is_order_closed: bool = False) -> None:
        self.is_order_closed = is_order_closed

    def correlate(
        self,
        investigation_id: str,
        documents: list[DocumentCorrelationInput],
    ) -> CrossDocumentCorrelationResult:
        """Run complete cross-document correlation across all case documents."""
        aligned_entities: list[AlignedEntityPair] = []
        comparisons: list[ComparisonResult] = []
        discrepancies: list[ComparisonResult] = []
        corroborations: list[ComparisonResult] = []
        missing_references: list[ComparisonResult] = []

        # 1. Group documents by type
        docs_by_type: dict[str, list[DocumentCorrelationInput]] = defaultdict(list)
        for doc in documents:
            docs_by_type[doc.doc_type.upper()].append(doc)

        # 2. Align buyer and vendor identities across documents
        aligned_entities.extend(self._align_parties(documents))

        # 3. Line-item aggregation across PO, Challans, and Invoices
        line_items = self._aggregate_line_items(documents)

        # 4. Check explicit document references completeness
        missing_refs = self._check_explicit_reference_completeness(documents)
        missing_references.extend(missing_refs)
        for comp in missing_refs:
            comparisons.append(comp)
            if comp.is_discrepancy:
                discrepancies.append(comp)
            else:
                corroborations.append(comp)

        # 5. Evaluate Material Grade Consistency (PO vs MTC / Delivery Challan)
        grade_results = self._evaluate_material_grades(docs_by_type)
        for comp in grade_results:
            comparisons.append(comp)
            if comp.is_discrepancy:
                discrepancies.append(comp)
            else:
                corroborations.append(comp)

        # 6. Evaluate Reference Codes (Challan / Invoice citing PO Number)
        ref_results = self._evaluate_reference_codes(docs_by_type)
        for comp in ref_results:
            comparisons.append(comp)
            if comp.is_discrepancy:
                discrepancies.append(comp)
            else:
                corroborations.append(comp)

        # 7. Evaluate Chronological Sequence (PO date <= Challan date <= Invoice date)
        chrono_results = self._evaluate_chronology(docs_by_type)
        for comp in chrono_results:
            comparisons.append(comp)
            if comp.is_discrepancy:
                discrepancies.append(comp)
            else:
                corroborations.append(comp)

        # 8. Evaluate Heat / Batch Numbers (Challan vs MTC)
        batch_results = self._evaluate_batches(docs_by_type)
        for comp in batch_results:
            comparisons.append(comp)
            if comp.is_discrepancy:
                discrepancies.append(comp)
            else:
                corroborations.append(comp)

        # 9. Evaluate Quantity Discrepancies across line items
        qty_results = self._evaluate_quantity_discrepancies(docs_by_type, line_items)
        for comp in qty_results:
            comparisons.append(comp)
            if comp.is_discrepancy:
                discrepancies.append(comp)
            else:
                corroborations.append(comp)

        # 10. Evaluate Financial Arithmetic (within invoices)
        fin_results = self._evaluate_financials(docs_by_type)
        for comp in fin_results:
            comparisons.append(comp)
            if comp.is_discrepancy:
                discrepancies.append(comp)
            else:
                corroborations.append(comp)

        return CrossDocumentCorrelationResult(
            investigation_id=investigation_id,
            documents_analyzed=len(documents),
            aligned_entities=aligned_entities,
            line_items=line_items,
            comparisons=comparisons,
            discrepancies=discrepancies,
            corroborations=corroborations,
            missing_references=missing_references,
        )

    # --- Internal Evaluation Routines ---

    def _find_field(
        self,
        doc: DocumentCorrelationInput,
        *names: str,
    ) -> ExtractedField | None:
        """Find the first extracted field matching any of the candidate names."""
        canonical_names = {n.lower().strip() for n in names}
        for f in doc.extracted_fields:
            if f.field_name.lower().strip() in canonical_names:
                return f
        return None

    def _find_all_fields(
        self,
        doc: DocumentCorrelationInput,
        *names: str,
    ) -> list[ExtractedField]:
        """Find all extracted fields matching candidate names."""
        canonical_names = {n.lower().strip() for n in names}
        return [f for f in doc.extracted_fields if f.field_name.lower().strip() in canonical_names]

    def _align_parties(
        self,
        documents: list[DocumentCorrelationInput],
    ) -> list[AlignedEntityPair]:
        """Align buyer and supplier corporate names across distinct documents."""
        pairs: list[AlignedEntityPair] = []
        for i, doc_a in enumerate(documents):
            for doc_b in documents[i + 1 :]:
                for party_role in ("buyer_name", "supplier_name", "vendor_name"):
                    f_a = self._find_field(doc_a, party_role)
                    f_b = self._find_field(doc_b, party_role)
                    if f_a and f_b and f_a.field_value.strip() and f_b.field_value.strip():
                        pair = EntityAligner.align_entity_pair(
                            source_doc_id=doc_a.doc_id,
                            source_field_id=f_a.id,
                            source_name=f_a.field_value,
                            source_identifier=None,
                            target_doc_id=doc_b.doc_id,
                            target_field_id=f_b.id,
                            target_name=f_b.field_value,
                            target_identifier=None,
                        )
                        pairs.append(pair)
        return pairs

    def _aggregate_line_items(
        self,
        documents: list[DocumentCorrelationInput],
    ) -> list[LineItemAggregation]:
        """Aggregate line items across POs, Delivery Challans, and Invoices."""
        items: dict[str, LineItemAggregation] = {}

        # Determine if all documents represent a single-item consignment or multi-line order
        total_qty_fields_per_doc = {
            doc.doc_id: len(
                self._find_all_fields(
                    doc,
                    "quantity",
                    "line_quantity",
                    "item_quantity",
                    "ordered_quantity",
                    "delivered_quantity",
                    "billed_quantity",
                    "invoiced_quantity",
                )
            )
            for doc in documents
        }
        is_single_consignment = all(count <= 1 for count in total_qty_fields_per_doc.values())

        for doc in documents:
            doc_type = doc.doc_type.upper()
            qty_fields = self._find_all_fields(
                doc,
                "quantity",
                "line_quantity",
                "item_quantity",
                "ordered_quantity",
                "delivered_quantity",
                "billed_quantity",
                "invoiced_quantity",
            )
            item_code_field = self._find_field(
                doc, "item_code", "product_code", "part_number", "line_no"
            )
            grade_field = self._find_field(doc, "material_grade", "grade", "item_grade")
            desc_field = self._find_field(doc, "item_description", "description", "item_name")
            rate_field = self._find_field(doc, "unit_rate", "rate", "price")
            total_field = self._find_field(doc, "line_total", "total")

            for idx, qf in enumerate(qty_fields):
                norm_q = normalize_quantity(qf.field_value, confidence=qf.confidence)

                if is_single_consignment:
                    key = "CONSIGNMENT_LINE_01"
                elif item_code_field:
                    key = item_code_field.field_value.strip().upper()
                else:
                    key = f"LINE_ITEM_{idx + 1:02d}"

                if key not in items:
                    items[key] = LineItemAggregation(
                        item_key=key,
                        description=desc_field.field_value if desc_field else key,
                        material_grade=grade_field.field_value if grade_field else None,
                        unit=norm_q.unit if not norm_q.is_ambiguous else "KG",
                    )

                agg = items[key]
                if doc_type in ("PURCHASE_ORDER", "PO"):
                    agg.total_ordered_quantity += norm_q.value
                    agg.ordered_field_ids.append(qf.id)
                    if rate_field:
                        norm_rate = normalize_amount(rate_field.field_value)
                        agg.ordered_unit_rate = norm_rate.value
                elif doc_type in ("DELIVERY_CHALLAN", "CHALLAN", "DISPATCH"):
                    agg.total_delivered_quantity += norm_q.value
                    agg.delivered_field_ids.append(qf.id)
                elif doc_type in ("COMMERCIAL_INVOICE", "INVOICE", "BILL"):
                    agg.total_invoiced_quantity += norm_q.value
                    agg.invoiced_field_ids.append(qf.id)
                    if rate_field:
                        norm_rate = normalize_amount(rate_field.field_value)
                        agg.invoiced_unit_rate = norm_rate.value
                    if total_field:
                        norm_tot = normalize_amount(total_field.field_value)
                        agg.invoiced_line_total = norm_tot.value

        return list(items.values())

    def _check_explicit_reference_completeness(
        self,
        documents: list[DocumentCorrelationInput],
    ) -> list[ComparisonResult]:
        """Detect when Document A explicitly references Document B which is missing from case."""
        results: list[ComparisonResult] = []
        all_doc_refs: set[str] = set()

        for doc in documents:
            ref_f = self._find_field(
                doc,
                "document_number",
                "po_number",
                "invoice_number",
                "challan_number",
                "mtc_number",
                "certificate_number",
            )
            if ref_f and ref_f.field_value.strip():
                all_doc_refs.add(ref_f.field_value.strip())

        for doc in documents:
            # Check cited MTC numbers
            cited_mtc = self._find_field(doc, "cited_mtc_number", "mtc_ref", "test_cert_no")
            if cited_mtc and cited_mtc.field_value.strip():
                rule_res = ExplicitDocumentReferenceCompletenessRule.evaluate(
                    citing_doc_id=doc.doc_id,
                    citing_doc_type=doc.doc_type,
                    cited_doc_type="MILL_TEST_CERT",
                    cited_reference_code=cited_mtc.field_value.strip(),
                    available_doc_references=list(all_doc_refs),
                    evidence_field_ids=(cited_mtc.id,),
                    conf=cited_mtc.confidence,
                )
                results.append(self._to_comparison_result(rule_res, doc.doc_id, "CASE_SUBMISSION"))

            # Check cited PO numbers
            cited_po = self._find_field(doc, "cited_po_number", "po_ref", "order_number")
            if cited_po and cited_po.field_value.strip():
                rule_res = ExplicitDocumentReferenceCompletenessRule.evaluate(
                    citing_doc_id=doc.doc_id,
                    citing_doc_type=doc.doc_type,
                    cited_doc_type="PURCHASE_ORDER",
                    cited_reference_code=cited_po.field_value.strip(),
                    available_doc_references=list(all_doc_refs),
                    evidence_field_ids=(cited_po.id,),
                    conf=cited_po.confidence,
                )
                results.append(self._to_comparison_result(rule_res, doc.doc_id, "CASE_SUBMISSION"))

        return results

    def _evaluate_material_grades(
        self,
        docs_by_type: dict[str, list[DocumentCorrelationInput]],
    ) -> list[ComparisonResult]:
        """Compare ordered material grade with MTC or Challan material grade."""
        results: list[ComparisonResult] = []
        pos = docs_by_type.get("PURCHASE_ORDER", [])
        mtcs = docs_by_type.get("MILL_TEST_CERT", [])
        dcs = docs_by_type.get("DELIVERY_CHALLAN", [])

        for po in pos:
            po_grade = self._find_field(po, "material_grade", "grade", "alloy")
            if not po_grade or not po_grade.field_value.strip():
                continue
            norm_po_grade = normalize_material_grade(po_grade.field_value, po_grade.confidence)

            # Compare against MTCs
            for mtc in mtcs:
                mtc_grade = self._find_field(mtc, "material_grade", "grade", "alloy")
                if mtc_grade and mtc_grade.field_value.strip():
                    norm_mtc_grade = normalize_material_grade(
                        mtc_grade.field_value, mtc_grade.confidence
                    )
                    rule_res = MaterialGradeConsistencyRule.evaluate(
                        grade_a=norm_po_grade.canonical_grade,
                        raw_a=po_grade.raw_text,
                        field_id_a=po_grade.id,
                        conf_a=po_grade.confidence,
                        grade_b=norm_mtc_grade.canonical_grade,
                        raw_b=mtc_grade.raw_text,
                        field_id_b=mtc_grade.id,
                        conf_b=mtc_grade.confidence,
                        doc_type_a=po.doc_type,
                        doc_type_b=mtc.doc_type,
                    )
                    results.append(self._to_comparison_result(rule_res, po.doc_id, mtc.doc_id))

            # Compare against Delivery Challans
            for dc in dcs:
                dc_grade = self._find_field(dc, "material_grade", "grade", "alloy")
                if dc_grade and dc_grade.field_value.strip():
                    norm_dc_grade = normalize_material_grade(
                        dc_grade.field_value, dc_grade.confidence
                    )
                    rule_res = MaterialGradeConsistencyRule.evaluate(
                        grade_a=norm_po_grade.canonical_grade,
                        raw_a=po_grade.raw_text,
                        field_id_a=po_grade.id,
                        conf_a=po_grade.confidence,
                        grade_b=norm_dc_grade.canonical_grade,
                        raw_b=dc_grade.raw_text,
                        field_id_b=dc_grade.id,
                        conf_b=dc_grade.confidence,
                        doc_type_a=po.doc_type,
                        doc_type_b=dc.doc_type,
                    )
                    results.append(self._to_comparison_result(rule_res, po.doc_id, dc.doc_id))

        return results

    def _evaluate_reference_codes(
        self,
        docs_by_type: dict[str, list[DocumentCorrelationInput]],
    ) -> list[ComparisonResult]:
        """Validate cited PO numbers in Delivery Challans and Invoices."""
        results: list[ComparisonResult] = []
        pos = docs_by_type.get("PURCHASE_ORDER", [])
        if not pos:
            return results

        actual_po = pos[0]
        actual_po_f = self._find_field(actual_po, "po_number", "document_number", "order_number")
        if not actual_po_f or not actual_po_f.field_value.strip():
            return results

        norm_actual = normalize_identifier(actual_po_f.field_value, "PURCHASE_ORDER")

        # Compare cited references in Challans and Invoices
        for doc_type in ("DELIVERY_CHALLAN", "COMMERCIAL_INVOICE"):
            for doc in docs_by_type.get(doc_type, []):
                cited_f = self._find_field(doc, "cited_po_number", "po_ref", "order_number")
                if cited_f and cited_f.field_value.strip():
                    norm_cited = normalize_identifier(cited_f.field_value, "PURCHASE_ORDER")
                    rule_res = ReferenceCodeConsistencyRule.evaluate(
                        cited_code=norm_cited.canonical_id,
                        cited_raw=cited_f.raw_text,
                        cited_field_id=cited_f.id,
                        cited_conf=cited_f.confidence,
                        actual_code=norm_actual.canonical_id,
                        actual_raw=actual_po_f.raw_text,
                        actual_field_id=actual_po_f.id,
                        actual_conf=actual_po_f.confidence,
                        reference_type="Purchase Order",
                        citing_doc_type=doc.doc_type,
                        target_doc_type=actual_po.doc_type,
                    )
                    results.append(
                        self._to_comparison_result(rule_res, doc.doc_id, actual_po.doc_id)
                    )

        return results

    def _evaluate_chronology(
        self,
        docs_by_type: dict[str, list[DocumentCorrelationInput]],
    ) -> list[ComparisonResult]:
        """Verify timeline sequence: PO date <= Delivery Challan date <= Invoice date."""
        results: list[ComparisonResult] = []
        pos = docs_by_type.get("PURCHASE_ORDER", [])
        dcs = docs_by_type.get("DELIVERY_CHALLAN", [])
        invs = docs_by_type.get("COMMERCIAL_INVOICE", [])

        # 1. PO Date vs Challan Date
        for po in pos:
            po_date_f = self._find_field(po, "date", "po_date", "document_date")
            if not po_date_f:
                continue
            norm_po_date = normalize_date(po_date_f.field_value, po_date_f.confidence)
            if norm_po_date.is_ambiguous:
                continue

            for dc in dcs:
                dc_date_f = self._find_field(
                    dc, "date", "delivery_date", "challan_date", "dispatch_date"
                )
                if not dc_date_f:
                    continue
                norm_dc_date = normalize_date(dc_date_f.field_value, dc_date_f.confidence)
                if norm_dc_date.is_ambiguous:
                    continue

                rule_res = ChronologicalSequenceRule.evaluate(
                    date_earlier=norm_po_date.value,
                    raw_earlier=po_date_f.raw_text,
                    field_id_earlier=po_date_f.id,
                    conf_earlier=po_date_f.confidence,
                    event_earlier="Purchase Order Issuance",
                    doc_type_earlier=po.doc_type,
                    date_later=norm_dc_date.value,
                    raw_later=dc_date_f.raw_text,
                    field_id_later=dc_date_f.id,
                    conf_later=dc_date_f.confidence,
                    event_later="Delivery Dispatch",
                    doc_type_later=dc.doc_type,
                )
                results.append(self._to_comparison_result(rule_res, po.doc_id, dc.doc_id))

        # 2. PO Date vs Invoice Date
        for po in pos:
            po_date_f = self._find_field(po, "date", "po_date", "document_date")
            if not po_date_f:
                continue
            norm_po_date = normalize_date(po_date_f.field_value, po_date_f.confidence)
            if norm_po_date.is_ambiguous:
                continue

            for inv in invs:
                inv_date_f = self._find_field(inv, "date", "invoice_date", "document_date")
                if not inv_date_f:
                    continue
                norm_inv_date = normalize_date(inv_date_f.field_value, inv_date_f.confidence)
                if norm_inv_date.is_ambiguous:
                    continue

                rule_res = ChronologicalSequenceRule.evaluate(
                    date_earlier=norm_po_date.value,
                    raw_earlier=po_date_f.raw_text,
                    field_id_earlier=po_date_f.id,
                    conf_earlier=po_date_f.confidence,
                    event_earlier="Purchase Order Issuance",
                    doc_type_earlier=po.doc_type,
                    date_later=norm_inv_date.value,
                    raw_later=inv_date_f.raw_text,
                    field_id_later=inv_date_f.id,
                    conf_later=inv_date_f.confidence,
                    event_later="Invoice Issuance",
                    doc_type_later=inv.doc_type,
                )
                results.append(self._to_comparison_result(rule_res, po.doc_id, inv.doc_id))

        return results

    def _evaluate_batches(
        self,
        docs_by_type: dict[str, list[DocumentCorrelationInput]],
    ) -> list[ComparisonResult]:
        """Compare Challan batch/lot number with MTC heat/batch number."""
        results: list[ComparisonResult] = []
        dcs = docs_by_type.get("DELIVERY_CHALLAN", [])
        mtcs = docs_by_type.get("MILL_TEST_CERT", [])

        for dc in dcs:
            dc_batch_f = self._find_field(dc, "batch_number", "heat_number", "lot_number")
            if not dc_batch_f or not dc_batch_f.field_value.strip():
                continue
            norm_dc_batch = normalize_identifier(dc_batch_f.field_value, "BATCH_NUMBER")

            for mtc in mtcs:
                mtc_batch_f = self._find_field(mtc, "heat_number", "batch_number", "heat_no")
                if not mtc_batch_f or not mtc_batch_f.field_value.strip():
                    continue
                norm_mtc_batch = normalize_identifier(mtc_batch_f.field_value, "BATCH_NUMBER")

                rule_res = BatchNumberConsistencyRule.evaluate(
                    batch_a=norm_dc_batch.canonical_id,
                    raw_a=dc_batch_f.raw_text,
                    field_id_a=dc_batch_f.id,
                    conf_a=dc_batch_f.confidence,
                    batch_b=norm_mtc_batch.canonical_id,
                    raw_b=mtc_batch_f.raw_text,
                    field_id_b=mtc_batch_f.id,
                    conf_b=mtc_batch_f.confidence,
                    doc_type_a=dc.doc_type,
                    doc_type_b=mtc.doc_type,
                )
                results.append(self._to_comparison_result(rule_res, dc.doc_id, mtc.doc_id))

        return results

    def _evaluate_quantity_discrepancies(
        self,
        docs_by_type: dict[str, list[DocumentCorrelationInput]],
        line_items: list[LineItemAggregation],
    ) -> list[ComparisonResult]:
        """Evaluate line item quantities: PO vs Challan, and Challan vs Invoice."""
        results: list[ComparisonResult] = []
        pos = docs_by_type.get("PURCHASE_ORDER", [])
        dcs = docs_by_type.get("DELIVERY_CHALLAN", [])
        invs = docs_by_type.get("COMMERCIAL_INVOICE", [])

        po_doc_id = pos[0].doc_id if pos else "PO_DOC"
        dc_doc_id = dcs[0].doc_id if dcs else "DC_DOC"
        inv_doc_id = invs[0].doc_id if invs else "INV_DOC"

        for item in line_items:
            # 1. PO Ordered vs Challan Delivered (Check partial delivery or shortfall)
            if item.total_ordered_quantity > 0 and item.total_delivered_quantity > 0:
                ord_fid = item.ordered_field_ids[0] if item.ordered_field_ids else ""
                del_fid = item.delivered_field_ids[0] if item.delivered_field_ids else ""

                rule_res = QuantityConsistencyRule.evaluate(
                    qty_a=item.total_ordered_quantity,
                    unit_a=item.unit,
                    raw_a=f"{item.total_ordered_quantity} {item.unit}",
                    field_id_a=ord_fid,
                    conf_a=1.0,
                    qty_b=item.total_delivered_quantity,
                    unit_b=item.unit,
                    raw_b=f"{item.total_delivered_quantity} {item.unit}",
                    field_id_b=del_fid,
                    conf_b=1.0,
                    doc_type_a="PURCHASE_ORDER",
                    doc_type_b="DELIVERY_CHALLAN",
                    is_order_closed=self.is_order_closed,
                )
                results.append(self._to_comparison_result(rule_res, po_doc_id, dc_doc_id))

            # 2. Delivery Challan Delivered vs Invoice Invoiced (Detect over-billing!)
            if item.total_delivered_quantity > 0 and item.total_invoiced_quantity > 0:
                del_fid = item.delivered_field_ids[0] if item.delivered_field_ids else ""
                inv_fid = item.invoiced_field_ids[0] if item.invoiced_field_ids else ""

                rule_res = QuantityConsistencyRule.evaluate(
                    qty_a=item.total_delivered_quantity,
                    unit_a=item.unit,
                    raw_a=f"{item.total_delivered_quantity} {item.unit}",
                    field_id_a=del_fid,
                    conf_a=1.0,
                    qty_b=item.total_invoiced_quantity,
                    unit_b=item.unit,
                    raw_b=f"{item.total_invoiced_quantity} {item.unit}",
                    field_id_b=inv_fid,
                    conf_b=1.0,
                    doc_type_a="DELIVERY_CHALLAN",
                    doc_type_b="COMMERCIAL_INVOICE",
                    # When comparing delivery to invoice, an excess invoice is always evaluated
                    is_order_closed=True,
                )
                results.append(self._to_comparison_result(rule_res, dc_doc_id, inv_doc_id))

        return results

    def _evaluate_financials(
        self,
        docs_by_type: dict[str, list[DocumentCorrelationInput]],
    ) -> list[ComparisonResult]:
        """Verify internal arithmetic within commercial invoices."""
        results: list[ComparisonResult] = []
        invs = docs_by_type.get("COMMERCIAL_INVOICE", [])

        for inv in invs:
            rate_f = self._find_field(inv, "unit_rate", "rate", "price")
            qty_f = self._find_field(
                inv,
                "quantity",
                "line_quantity",
                "item_quantity",
                "ordered_quantity",
                "delivered_quantity",
                "billed_quantity",
                "invoiced_quantity",
            )
            tot_f = self._find_field(inv, "line_total", "total")
            subtot_f = self._find_field(inv, "subtotal", "sub_total", "taxable_value")
            tax_f = self._find_field(inv, "tax_amount", "tax", "gst_amount", "total_tax")
            grand_f = self._find_field(inv, "grand_total", "invoice_total", "total_amount")
            freight_f = self._find_field(inv, "freight", "shipping", "delivery_charges")
            disc_f = self._find_field(inv, "discount", "discounts", "rebate")

            # 1. Line Total Parity: Unit Rate * Quantity == Stated Line Total
            if rate_f and qty_f and tot_f:
                norm_r = normalize_amount(rate_f.field_value, rate_f.confidence)
                norm_q = normalize_quantity(qty_f.field_value, qty_f.confidence)
                norm_t = normalize_amount(tot_f.field_value, tot_f.confidence)

                if (
                    not norm_r.is_ambiguous
                    and not norm_q.is_ambiguous
                    and not norm_t.is_ambiguous
                    and norm_r.value > 0
                    and norm_q.value > 0
                ):
                    rule_res = FinancialTotalConsistencyRule.evaluate_line_total(
                        unit_rate=norm_r.value,
                        quantity=norm_q.value,
                        stated_total=norm_t.value,
                        raw_rate=rate_f.raw_text,
                        raw_qty=qty_f.raw_text,
                        raw_total=tot_f.raw_text,
                        field_ids=(rate_f.id, qty_f.id, tot_f.id),
                        conf=min(rate_f.confidence, qty_f.confidence, tot_f.confidence),
                        currency=norm_t.currency,
                        doc_type=inv.doc_type,
                    )
                    results.append(self._to_comparison_result(rule_res, inv.doc_id, inv.doc_id))

            # 2. Grand Total Parity: Subtotal + Taxes + Freight - Discounts == Stated Grand Total
            if subtot_f and tax_f and grand_f:
                norm_sub = normalize_amount(subtot_f.field_value, subtot_f.confidence)
                norm_tax = normalize_amount(tax_f.field_value, tax_f.confidence)
                norm_grand = normalize_amount(grand_f.field_value, grand_f.confidence)
                norm_freight = (
                    normalize_amount(freight_f.field_value, freight_f.confidence)
                    if freight_f
                    else None
                )
                norm_disc = (
                    normalize_amount(disc_f.field_value, disc_f.confidence) if disc_f else None
                )

                if (
                    not norm_sub.is_ambiguous
                    and not norm_tax.is_ambiguous
                    and not norm_grand.is_ambiguous
                ):
                    rule_res = FinancialTotalConsistencyRule.evaluate_grand_total(
                        subtotal=norm_sub.value,
                        taxes=norm_tax.value,
                        stated_grand_total=norm_grand.value,
                        freight=norm_freight.value if norm_freight else Decimal("0.0"),
                        discounts=norm_disc.value if norm_disc else Decimal("0.0"),
                        field_ids=(subtot_f.id, tax_f.id, grand_f.id),
                        conf=min(subtot_f.confidence, tax_f.confidence, grand_f.confidence),
                        currency=norm_grand.currency,
                        doc_type=inv.doc_type,
                    )
                    results.append(self._to_comparison_result(rule_res, inv.doc_id, inv.doc_id))

        return results

    def _to_comparison_result(
        self,
        rule_res: RuleEvaluationResult,
        source_doc_id: str,
        target_doc_id: str,
    ) -> ComparisonResult:
        """Map pure RuleEvaluationResult to capability ComparisonResult."""
        return ComparisonResult(
            rule_code=rule_res.rule_code,
            is_consistent=rule_res.is_consistent,
            category=rule_res.category,
            epistemic_tier=rule_res.epistemic_tier,
            severity=rule_res.severity,
            confidence=rule_res.confidence,
            title=rule_res.title,
            explanation=rule_res.explanation,
            source_doc_id=source_doc_id,
            target_doc_id=target_doc_id,
            evidence_field_ids=list(rule_res.evidence_field_ids),
            discrepancy_delta=rule_res.discrepancy_delta,
            discrepancy_percent=rule_res.discrepancy_percent,
        )
