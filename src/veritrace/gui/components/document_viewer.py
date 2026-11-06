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
    QComboBox,
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
        self.setBackgroundBrush(QBrush(QColor("#090d16")))
        self.setStyleSheet("border: 1px solid #21262d; border-radius: 6px;")

        self._pixmap_item: QGraphicsPixmapItem | None = None
        self._highlight_rect: QGraphicsRectItem | None = None
        self._tag_item: QGraphicsSimpleTextItem | None = None
        self._current_image_width = 800
        self._current_image_height = 1100

        self._original_image_path: str | None = None
        self._ela_image_path: str | None = None
        self._current_evidence: EvidenceResponseDTO | None = None
        self._active_layer_mode: str = "visual"

    def wheelEvent(self, event: QWheelEvent) -> None:
        """Smooth zoom on mouse wheel."""
        factor = 1.15 if event.angleDelta().y() > 0 else 0.85
        self.scale(factor, factor)

    def zoom_in(self) -> None:
        """Zoom in canvas by 20%."""
        self.scale(1.2, 1.2)

    def zoom_out(self) -> None:
        """Zoom out canvas by 20%."""
        self.scale(0.833, 0.833)

    def load_page(
        self,
        image_path: str | None,
        doc_name: str = "",
        page_num: int = 1,
        evidence: EvidenceResponseDTO | None = None,
        ela_path: str | None = None,
    ) -> None:
        """Render page image and overlay bounding box if evidence coordinates provided."""
        self._original_image_path = image_path
        self._ela_image_path = ela_path
        self._current_evidence = evidence

        self._render_active_layer(doc_name=doc_name, page_num=page_num)

    def set_layer_mode(self, mode: str) -> None:
        """Switch active render layer (visual / ela / bbox_only)."""
        self._active_layer_mode = mode
        self._render_active_layer()

    def _render_active_layer(self, doc_name: str = "", page_num: int = 1) -> None:
        """Render selected layer pixmap and bounding overlays."""
        self._scene.clear()
        self._pixmap_item = None
        self._highlight_rect = None
        self._tag_item = None

        target_path = self._original_image_path
        if self._active_layer_mode == "ela" and self._ela_image_path:
            target_path = self._ela_image_path

        has_image = False
        if target_path and Path(target_path).exists():
            pixmap = QPixmap(target_path)
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
                QPen(QColor("#30363d"), 1),
                QBrush(QColor("#161b22")),
            )
            title_text = self._scene.addSimpleText(
                f"{doc_name or self._title} (Page {page_num})",
                QFont("Segoe UI", 14, QFont.Weight.Bold),
            )
            title_text.setBrush(QBrush(QColor("#58a6ff")))
            title_text.setPos(30, 40)

            sub_text = self._scene.addSimpleText(
                "Digital Structured Forensic Representation",
                QFont("Segoe UI", 10),
            )
            sub_text.setBrush(QBrush(QColor("#8b949e")))
            sub_text.setPos(30, 75)

        # Overlay evidence bounding box if present
        if self._current_evidence:
            ymin = self._current_evidence.norm_ymin
            xmin = self._current_evidence.norm_xmin
            ymax = self._current_evidence.norm_ymax
            xmax = self._current_evidence.norm_xmax

            px = xmin * self._current_image_width
            py = ymin * self._current_image_height
            pw = max(6.0, (xmax - xmin) * self._current_image_width)
            ph = max(6.0, (ymax - ymin) * self._current_image_height)

            box_pen = QPen(QColor("#f85149"), 2.5, Qt.PenStyle.SolidLine)
            box_brush = QBrush(QColor(248, 81, 73, 50))  # Semi-transparent crimson
            self._highlight_rect = self._scene.addRect(px, py, pw, ph, box_pen, box_brush)

            # High-tech tag badge
            tag = self._scene.addSimpleText(
                f"ROI: [{xmin:.3f}, {ymin:.3f}] - [{xmax:.3f}, {ymax:.3f}]",
                QFont("Segoe UI", 9, QFont.Weight.DemiBold),
            )
            tag.setBrush(QBrush(QColor("#58a6ff")))
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
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(6)

        # Header toolbar bar
        header_bar = QHBoxLayout()
        header_bar.setSpacing(8)

        header_lbl = QLabel("DUAL-CANVAS FORENSIC COMPARATOR", self)
        header_lbl.setStyleSheet(
            "color: #58a6ff; font-weight: bold; font-size: 11px; letter-spacing: 0.5px;"
        )
        header_bar.addWidget(header_lbl)
        header_bar.addStretch()

        # Layer mode selector
        self._combo_layer = QComboBox(self)
        self._combo_layer.addItem("📸 High-DPI Visual (300 DPI)", "visual")
        self._combo_layer.addItem("🔥 ELA Heatmap Differential", "ela")
        self._combo_layer.currentIndexChanged.connect(self._on_layer_changed)
        header_bar.addWidget(self._combo_layer)

        # Zoom buttons
        self._btn_zoom_in = QPushButton("+ Zoom In", self)
        self._btn_zoom_in.clicked.connect(self._zoom_in_both)
        header_bar.addWidget(self._btn_zoom_in)

        self._btn_zoom_out = QPushButton("- Zoom Out", self)
        self._btn_zoom_out.clicked.connect(self._zoom_out_both)
        header_bar.addWidget(self._btn_zoom_out)

        self._btn_reset_zoom = QPushButton("Fit to Screen", self)
        self._btn_reset_zoom.clicked.connect(self._reset_both_zooms)
        header_bar.addWidget(self._btn_reset_zoom)

        main_layout.addLayout(header_bar)

        # Splitter with 2 canvases
        self._splitter = QSplitter(Qt.Orientation.Horizontal, self)

        # Left: Source Document
        left_container = QWidget(self._splitter)
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(4)
        self._left_title = QLabel("Source Document", left_container)
        self._left_title.setStyleSheet(
            "font-weight: 600; color: #58a6ff; padding: 3px 6px; "
            "background: #161b22; border-radius: 4px;"
        )
        left_layout.addWidget(self._left_title)
        self._left_canvas = DocumentCanvasView("Source Document", left_container)
        left_layout.addWidget(self._left_canvas, 1)

        # Right: Target Document
        right_container = QWidget(self._splitter)
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(4)
        self._right_title = QLabel("Target Document", right_container)
        self._right_title.setStyleSheet(
            "font-weight: 600; color: #f0883e; padding: 3px 6px; "
            "background: #161b22; border-radius: 4px;"
        )
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
        source_ela_path: str | None = None,
        target_ela_path: str | None = None,
    ) -> None:
        """Load source and target documents into dual canvases."""
        self._left_title.setText(f"Primary Evidence: {source_doc_name}")
        self._left_canvas.load_page(
            source_img_path,
            doc_name=source_doc_name,
            evidence=source_evidence,
            ela_path=source_ela_path,
        )

        self._right_title.setText(f"Comparison Evidence: {target_doc_name}")
        self._right_canvas.load_page(
            target_img_path,
            doc_name=target_doc_name,
            evidence=target_evidence,
            ela_path=target_ela_path,
        )

    def _on_layer_changed(self) -> None:
        mode = self._combo_layer.currentData()
        self._left_canvas.set_layer_mode(mode)
        self._right_canvas.set_layer_mode(mode)

    def _zoom_in_both(self) -> None:
        self._left_canvas.zoom_in()
        self._right_canvas.zoom_in()

    def _zoom_out_both(self) -> None:
        self._left_canvas.zoom_out()
        self._right_canvas.zoom_out()

    def _reset_both_zooms(self) -> None:
        self._left_canvas.reset_zoom()
        self._right_canvas.reset_zoom()
