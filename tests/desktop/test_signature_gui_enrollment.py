"""Desktop GUI tests for Signature Reference Management and Workbench (Milestone 1.9 Part A & E)."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from veritrace.application.dto.signature_reference import (
    AuthorizedSubjectDTO,
    SignatureReferenceDTO,
)
from veritrace.application.services.cross_document_correlation_service import (
    CrossDocumentCorrelationService,
)
from veritrace.application.services.investigation_service import (
    InvestigationService,
)
from veritrace.gui.components.signature_workbench import (
    CreateAuthorizedSubjectDialog,
    EnrollSignatureReferenceDialog,
    SignatureWorkbenchWidget,
)
from veritrace.gui.views.main_window import MainWindow


def test_signature_workbench_widget_subject_and_reference_filtering(qtbot) -> None:
    widget = SignatureWorkbenchWidget()
    qtbot.addWidget(widget)

    # Initial state
    assert widget._combo_subjects.count() == 1  # "All Signatories"
    assert widget._combo_references.count() == 1  # "Auto"

    s1 = AuthorizedSubjectDTO(
        id="subj_1",
        organization_id="org_1",
        full_name="Elena Rostova",
        designation="CQO",
        id_reference="EMP-1",
        created_at=None,  # type: ignore[arg-type]
    )
    s2 = AuthorizedSubjectDTO(
        id="subj_2",
        organization_id="org_1",
        full_name="Marcus Vance",
        designation="Dir",
        id_reference="EMP-2",
        created_at=None,  # type: ignore[arg-type]
    )

    r1 = SignatureReferenceDTO(
        id="ref_1",
        subject_id="subj_1",
        organization_id="org_1",
        crop_image_path="dummy1.png",
        sha256_hash="a" * 64,
        source_document_ref="Specimen #1",
        consent_mandate_ref="Consent #1",
        enrollment_date=None,  # type: ignore[arg-type]
    )
    r2 = SignatureReferenceDTO(
        id="ref_2",
        subject_id="subj_2",
        organization_id="org_1",
        crop_image_path="dummy2.png",
        sha256_hash="b" * 64,
        source_document_ref="Specimen #2",
        consent_mandate_ref="Consent #2",
        enrollment_date=None,  # type: ignore[arg-type]
    )

    widget.set_subjects([s1, s2])
    assert widget._combo_subjects.count() == 3

    widget.set_references([r1, r2])
    # When "All Signatories" is selected, all references appear
    assert widget._combo_references.count() == 3

    # Filter to Subject 1
    widget._combo_subjects.setCurrentIndex(1)
    assert widget.get_selected_subject_id() == "subj_1"
    # References should now filter to r1 only (+ Auto)
    assert widget._combo_references.count() == 2

    # Select r1
    widget._combo_references.setCurrentIndex(1)
    assert widget.get_selected_reference_id() == "ref_1"


def test_create_authorized_subject_dialog(qtbot) -> None:
    dlg = CreateAuthorizedSubjectDialog()
    qtbot.addWidget(dlg)

    dlg._txt_name.setText("Arthur Pendelton")
    dlg._txt_desig.setText("Chief Executive Officer")
    dlg._txt_id_ref.setText("MANDATE-CEO-01")

    data = dlg.get_data()
    assert data == ("Arthur Pendelton", "Chief Executive Officer", "MANDATE-CEO-01")


def test_enroll_signature_reference_dialog(qtbot, tmp_path: Path) -> None:
    # Create valid synthetic image
    img = np.ones((80, 200, 3), dtype=np.uint8) * 255
    img_path = tmp_path / "specimen.png"
    cv2.imwrite(str(img_path), img)

    s1 = AuthorizedSubjectDTO(
        id="subj_10",
        organization_id="org_1",
        full_name="Clara Oswald",
        designation="Inspector",
        id_reference="EMP-INS-10",
        created_at=None,  # type: ignore[arg-type]
    )

    dlg = EnrollSignatureReferenceDialog(subjects=[s1], preselected_subject_id="subj_10")
    qtbot.addWidget(dlg)

    assert dlg._combo_subjects.currentData() == "subj_10"

    dlg._txt_path.setText(str(img_path))
    dlg._update_preview(str(img_path))
    dlg._txt_source_ref.setText("Form 84-A")
    dlg._txt_consent_ref.setText("CONSENT-84")

    data = dlg.get_data()
    assert data["subject_id"] == "subj_10"
    assert data["crop_image_path"] == str(img_path)
    assert data["source_document_ref"] == "Form 84-A"
    assert data["consent_mandate_ref"] == "CONSENT-84"


def test_main_window_enroll_and_verify_with_reference(
    app_instance, test_uow_factory, tmp_path: Path
) -> None:
    inv_service = InvestigationService(test_uow_factory)
    corr_service = CrossDocumentCorrelationService(test_uow_factory)

    org_id = "org_11111111111111111111111111111111"
    window = MainWindow(
        investigation_service=inv_service,
        correlation_service=corr_service,
        uow_factory=test_uow_factory,
        organization_id=org_id,
    )

    # 1. Create subject via GUI handler
    window._on_create_authorized_subject(
        full_name="Dr. Aris Thorne",
        designation="Chief Metallurgist",
        id_reference="EMP-MET-091",
    )
    assert len(window._signature_workbench._subjects) >= 1

    # 2. Enroll reference specimen crop via GUI handler
    img = np.ones((100, 250, 3), dtype=np.uint8) * 255
    cv2.ellipse(img, (120, 50), (80, 30), 15, 0, 360, (0, 0, 0), 2)
    specimen_path = tmp_path / "thorne_specimen.png"
    cv2.imwrite(str(specimen_path), img)

    subj_id = window._signature_workbench._subjects[0].id
    window._on_enroll_signature_reference(
        {
            "subject_id": subj_id,
            "crop_image_path": str(specimen_path),
            "source_document_ref": "Executive Card 2024",
            "consent_mandate_ref": "MANDATE-SIG-99",
        }
    )
    assert len(window._signature_workbench._references) >= 1

    # 3. Select reference specimen in workbench
    window._signature_workbench._combo_references.setCurrentIndex(1)
    selected_ref = window._signature_workbench.get_selected_reference_id()
    assert selected_ref is not None

    # 4. Trigger signature verification against enrolled reference
    window._on_run_signatures()
    assert window._signature_workbench._table.rowCount() >= 1

    # Selected comparison should use the enrolled specimen name
    item = window._signature_workbench._table.item(0, 1)
    assert item is not None
    assert "Enrolled Specimen" in item.text()

    window.close()
