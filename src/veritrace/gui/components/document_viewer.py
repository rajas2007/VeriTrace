"""Side-by-side interactive document canvas and coordinate overlay viewer."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QPainter,
    QPen,
    QPixmap,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from veritrace.application.dto.investigation import EvidenceResponseDTO


class DocumentCanvasView(QGraphicsView):
    """Interactive QGraphicsView with smooth pan, zoom, and coordinate overlay rendering."""

    def __init__(self, title: str, parent: Any = None) -> None:
        super().__init__(parent)
        self._title = title
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setBackgroundBrush(QBrush(QColor("#141418")))
        self.setStyleSheet("border: 1px solid #2a2a36;")

        self._pixmap_item: QGraphicsPixmapItem | None = None
        self._highlight_rect: QGraphicsRectItem | None = None
        self._tag_item: QGraphicsSimpleTextItem | None = None
        self._current_image_width = 800
        self._current_image_height = 1100

    def wheelEvent(self, event: QWheelEvent) -> None:
        """Smooth zoom on mouse wheel."""
        factor = 1.15 if event.angleDelta().y() > 0 else 0.85
        self.scale(factor, factor)

    def load_page(
        self,
        image_path: str | None,
        doc_name: str = "",
        page_num: int = 1,
        evidence: EvidenceResponseDTO | None = None,
    ) -> None:
        """Render page image and overlay bounding box if evidence coordinates provided."""
        self._scene.clear()
        self._pixmap_item = None
        self._highlight_rect = None
        self._tag_item = None

        has_image = False
        if image_path and Path(image_path).exists():
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                self._pixmap_item = self._scene.addPixmap(pixmap)
                self._current_image_width = pixmap.width()
                self._current_image_height = pixmap.height()
                has_image = True

        if not has_image:
            # Fallback synthetic forensic canvas
            self._current_image_width = 800
            self._current_image_height = 1100
            self._scene.addRect(
                0,
                0,
                self._current_image_width,
                self._current_image_height,
                QPen(QColor("#3a3a4c"), 1),
                QBrush(QColor("#1e1e26")),
            )
            title_text = self._scene.addSimpleText(
                f"{doc_name or self._title} (Page {page_num})",
                QFont("Segoe UI", 14, QFont.Weight.Bold),
            )
            title_text.setBrush(QBrush(QColor("#0d6efd")))
            title_text.setPos(30, 40)

            sub_text = self._scene.addSimpleText(
                "Digital Structured Forensic Representation",
                QFont("Segoe UI", 10),
            )
            sub_text.setBrush(QBrush(QColor("#8e8e9c")))
            sub_text.setPos(30, 75)

        # Overlay evidence bounding box if present
        if evidence:
            ymin = evidence.norm_ymin
            xmin = evidence.norm_xmin
            ymax = evidence.norm_ymax
            xmax = evidence.norm_xmax

            px = xmin * self._current_image_width
            py = ymin * self._current_image_height
            pw = max(4.0, (xmax - xmin) * self._current_image_width)
            ph = max(4.0, (ymax - ymin) * self._current_image_height)

            box_pen = QPen(QColor("#dc3545"), 2.5, Qt.PenStyle.SolidLine)
            box_brush = QBrush(QColor(220, 53, 69, 45))  # Semi-transparent red
            self._highlight_rect = self._scene.addRect(px, py, pw, ph, box_pen, box_brush)

            tag = self._scene.addSimpleText(
                f"Anchor: [{xmin:.3f}, {ymin:.3f}] - [{xmax:.3f}, {ymax:.3f}]",
                QFont("Segoe UI", 9, QFont.Weight.DemiBold),
            )
            tag.setBrush(QBrush(QColor("#ffffff")))
            tag.setPos(px, max(0.0, py - 18))
            self._tag_item = tag

            # Center on discrepancy
            center = QPointF(px + pw / 2.0, py + ph / 2.0)
            self.centerOn(center)
        else:
            self.resetTransform()
            self.setSceneRect(0, 0, self._current_image_width, self._current_image_height)
            self.fitInView(
                self.sceneRect(),
                Qt.AspectRatioMode.KeepAspectRatio,
            )

    def reset_zoom(self) -> None:
        """Reset zoom to fit scene."""
        self.resetTransform()
        if self._scene.sceneRect().isValid():
            self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)


class SideBySideDocumentViewer(QWidget):
    """Dual-pane document viewer displaying compared documents side-by-side."""

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(4)

        # Header bar
        header_bar = QHBoxLayout()
        header_lbl = QLabel("SIDE-BY-SIDE EVIDENCE COMPARISON", self)
        header_lbl.setStyleSheet("color: #8e8e9c; font-weight: bold; font-size: 11px;")
        header_bar.addWidget(header_lbl)
        header_bar.addStretch()

        self._btn_reset_zoom = QPushButton("Reset Zoom", self)
        self._btn_reset_zoom.clicked.connect(self._reset_both_zooms)
        header_bar.addWidget(self._btn_reset_zoom)
        main_layout.addLayout(header_bar)

        # Splitter with 2 canvases
        self._splitter = QSplitter(Qt.Orientation.Horizontal, self)

        # Left: Source Document
        left_container = QWidget(self._splitter)
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(2)
        self._left_title = QLabel("Source Document", left_container)
        self._left_title.setStyleSheet("font-weight: 600; color: #0d6efd; padding: 2px 4px;")
        left_layout.addWidget(self._left_title)
        self._left_canvas = DocumentCanvasView("Source Document", left_container)
        left_layout.addWidget(self._left_canvas, 1)

        # Right: Target Document
        right_container = QWidget(self._splitter)
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(2)
        self._right_title = QLabel("Target Document", right_container)
        self._right_title.setStyleSheet("font-weight: 600; color: #fd7e14; padding: 2px 4px;")
        right_layout.addWidget(self._right_title)
        self._right_canvas = DocumentCanvasView("Target Document", right_container)
        right_layout.addWidget(self._right_canvas, 1)

        self._splitter.addWidget(left_container)
        self._splitter.addWidget(right_container)
        self._splitter.setSizes([500, 500])
        main_layout.addWidget(self._splitter, 1)

    def load_comparison(
        self,
        source_doc_name: str,
        source_img_path: str | None,
        source_evidence: EvidenceResponseDTO | None,
        target_doc_name: str,
        target_img_path: str | None,
        target_evidence: EvidenceResponseDTO | None,
    ) -> None:
        """Load source and target documents into dual canvases."""
        self._left_title.setText(f"Source: {source_doc_name}")
        self._left_canvas.load_page(
            source_img_path,
            doc_name=source_doc_name,
            evidence=source_evidence,
        )

        self._right_title.setText(f"Target: {target_doc_name}")
        self._right_canvas.load_page(
            target_img_path,
            doc_name=target_doc_name,
            evidence=target_evidence,
        )

    def _reset_both_zooms(self) -> None:
        self._left_canvas.reset_zoom()
        self._right_canvas.reset_zoom()
