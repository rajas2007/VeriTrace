"""Unit tests for Signature Model Training Pipeline and Scientific Integrity Invariants."""

from pathlib import Path

import cv2
import numpy as np

from scripts.training.train_signature_siamese import (
    calculate_roc_and_eer,
    discover_cedar_dataset,
    generate_pairs_from_subjects,
    load_and_preprocess_image,
    split_subjects_disjoint,
)


def test_subject_disjoint_splitting():
    """Verify train, validation, and test subjects have strictly zero identity overlap."""
    subject_ids = [f"signer_{i:03d}" for i in range(1, 51)]  # 50 subjects

    train_s, val_s, test_s = split_subjects_disjoint(
        subject_ids, train_ratio=0.70, val_ratio=0.15, seed=42
    )

    # Check total count
    assert len(train_s) + len(val_s) + len(test_s) == 50

    # Strict disjointness invariant
    set_train = set(train_s)
    set_val = set(val_s)
    set_test = set(test_s)

    assert set_train.isdisjoint(set_val)
    assert set_train.isdisjoint(set_test)
    assert set_val.isdisjoint(set_test)


def test_discover_dataset_and_generate_pairs(tmp_path: Path):
    """Verify CEDAR directory structure indexing and genuine/forgery pair generation."""
    # Create fake CEDAR folder layout
    org_dir = tmp_path / "full_org"
    forg_dir = tmp_path / "full_forg"
    org_dir.mkdir()
    forg_dir.mkdir()

    # Generate dummy signature tif files for 3 subjects
    for s_idx in range(1, 4):
        for sample_idx in range(1, 5):
            p_org = org_dir / f"original_{s_idx}_{sample_idx}.tif"
            p_org.write_bytes(b"dummy_org_image_bytes")

            p_forg = forg_dir / f"forgeries_{s_idx}_{sample_idx}.tif"
            p_forg.write_bytes(b"dummy_forg_image_bytes")

    indexed = discover_cedar_dataset(tmp_path)
    assert len(indexed) == 3
    assert "1" in indexed
    assert len(indexed["1"]["genuine"]) == 4
    assert len(indexed["1"]["forgery"]) == 4

    # Generate pairs
    pairs = generate_pairs_from_subjects(indexed, ["1", "2"])
    assert len(pairs) > 0

    genuine_pairs = [p for p in pairs if p.label == 0]
    forgery_pairs = [p for p in pairs if p.label == 1]

    assert len(genuine_pairs) > 0
    assert len(forgery_pairs) > 0
    assert all(p.pair_type == "genuine" for p in genuine_pairs)
    assert any(p.pair_type in ("skilled_forgery", "random_imposter") for p in forgery_pairs)


def test_load_and_preprocess_image(tmp_path: Path):
    """Verify image loading converts to normalized float32 tensor of target resolution."""
    img_path = tmp_path / "test_sig.png"
    dummy_img = np.full((100, 200, 3), 128, dtype=np.uint8)
    cv2.imwrite(str(img_path), dummy_img)

    processed = load_and_preprocess_image(img_path, target_size=(128, 128))
    assert processed.shape == (128, 128)
    assert processed.dtype == np.float32
    assert 0.0 <= processed.min() <= processed.max() <= 1.0


def test_calculate_roc_and_eer_controlled_inputs():
    """Verify ROC-AUC and EER formulas on perfectly separated distance inputs."""
    # Genuine pairs: low distance (0.1, 0.2)
    # Forged pairs: high distance (0.8, 0.9)
    dists = np.array([0.1, 0.2, 0.8, 0.9], dtype=np.float32)
    labels = np.array([0, 0, 1, 1], dtype=np.int32)

    res = calculate_roc_and_eer(dists, labels)
    assert res["eer"] == 0.0  # Perfect separation
    assert res["roc_auc"] == 1.0
    assert res["far_at_eer"] == 0.0
    assert res["frr_at_eer"] == 0.0
    assert res["precision_at_eer"] == 1.0
    assert res["recall_at_eer"] == 1.0
