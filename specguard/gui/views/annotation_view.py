"""
Annotation Studio View for SpecGuard.
Enables local visual and textual labeling of engineering documents:
Entity recognition (Component, Parameter, Value, Unit, Tolerance),
Domain classification, and statement contradiction labeling.
"""

from typing import List, Dict, Optional, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton,
    QComboBox, QListWidget, QListWidgetItem, QFrame, QMessageBox, QLineEdit
)
from PySide6.QtCore import Qt, Signal

from specguard.training.annotation_manager import (
    AnnotationManager, DocumentAnnotation, EntityAnnotation,
    SUPPORTED_ENTITY_LABELS, SUPPORTED_CLASSIFICATION_LABELS
)


class AnnotationStudioWidget(QWidget):
    annotation_saved = Signal(str)

    def __init__(self, annotation_manager: Optional[AnnotationManager] = None, parent=None):
        super().__init__(parent)
        self.manager = annotation_manager or AnnotationManager()
        self.current_entities: List[EntityAnnotation] = []
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # Document & Meta Header
        header_row = QHBoxLayout()
        self.doc_id_input = QLineEdit()
        self.doc_id_input.setPlaceholderText("Document ID (e.g. MECH_001)...")
        self.doc_id_input.setText("DOC_MANUAL_001")
        header_row.addWidget(QLabel("Document ID:"))
        header_row.addWidget(self.doc_id_input)

        self.domain_combo = QComboBox()
        self.domain_combo.addItems(["Mechanical", "Electrical", "Chemical"])
        header_row.addWidget(QLabel("Domain:"))
        header_row.addWidget(self.domain_combo)

        self.class_combo = QComboBox()
        self.class_combo.addItems(SUPPORTED_CLASSIFICATION_LABELS)
        header_row.addWidget(QLabel("Class:"))
        header_row.addWidget(self.class_combo)

        layout.addLayout(header_row)

        # Main Text Input Area
        lbl_text = QLabel("Engineering Text Sample (Select text to label entity):")
        lbl_text.setStyleSheet("font-weight: 600; color: #cbd5e1;")
        layout.addWidget(lbl_text)

        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("Paste or type engineering sentence here...\nExample: The centrifugal pump shaft operates at a rated voltage of 415 V with tolerance ±0.05 mm.")
        self.text_edit.setStyleSheet("background-color: #0f172a; border: 1px solid #334155; color: #f8fafc; font-size: 13px;")
        self.text_edit.setFixedHeight(110)
        layout.addWidget(self.text_edit)

        # Second sentence for logical contradiction pairs
        lbl_pair = QLabel("Second Statement (Optional, for Logical Contradiction training):")
        lbl_pair.setStyleSheet("color: #94a3b8; font-size: 12px;")
        layout.addWidget(lbl_pair)

        self.text_b_edit = QLineEdit()
        self.text_b_edit.setPlaceholderText("Optional second statement to pair for contradiction detection...")
        layout.addWidget(self.text_b_edit)

        pair_meta_row = QHBoxLayout()
        pair_meta_row.addWidget(QLabel("Logical Relationship:"))
        self.logical_combo = QComboBox()
        self.logical_combo.addItems(["CONSISTENT", "CONTRADICTORY", "UNCERTAIN"])
        pair_meta_row.addWidget(self.logical_combo)
        pair_meta_row.addStretch()
        layout.addLayout(pair_meta_row)

        # Entity Label Buttons
        tag_box = QFrame()
        tag_box.setStyleSheet("background-color: #1e293b; border-radius: 6px; padding: 8px;")
        tag_layout = QVBoxLayout(tag_box)
        lbl_tags = QLabel("Assign Label to Selected Text:")
        lbl_tags.setStyleSheet("font-weight: bold; color: #38bdf8;")
        tag_layout.addWidget(lbl_tags)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        for label in ["COMPONENT", "PARAMETER", "VALUE", "UNIT", "TOLERANCE", "PRESSURE", "TEMPERATURE", "VOLTAGE", "CURRENT"]:
            btn = QPushButton(label)
            btn.setProperty("class", "secondary")
            btn.setStyleSheet("font-size: 11px; padding: 4px 8px;")
            btn.clicked.connect(lambda _, l=label: self._tag_selected_text(l))
            btn_row.addWidget(btn)
        tag_layout.addLayout(btn_row)
        layout.addWidget(tag_box)

        # Current Entities List
        lbl_ent_list = QLabel("Annotated Entities for Sample:")
        lbl_ent_list.setStyleSheet("font-weight: 600; color: #cbd5e1;")
        layout.addWidget(lbl_ent_list)

        self.entity_list = QListWidget()
        self.entity_list.setStyleSheet("background-color: #0f172a; border: 1px solid #334155; border-radius: 6px;")
        self.entity_list.setFixedHeight(120)
        layout.addWidget(self.entity_list)

        # Action Buttons
        act_row = QHBoxLayout()
        clear_btn = QPushButton("Clear Current")
        clear_btn.setProperty("class", "secondary")
        clear_btn.clicked.connect(self._clear_all)
        act_row.addWidget(clear_btn)

        act_row.addStretch()

        save_btn = QPushButton("💾 Save Ground-Truth Annotation")
        save_btn.setProperty("class", "primary")
        save_btn.clicked.connect(self._save_annotation)
        act_row.addWidget(save_btn)

        layout.addLayout(act_row)

    def _tag_selected_text(self, label: str):
        cursor = self.text_edit.textCursor()
        selected_text = cursor.selectedText().strip()
        if not selected_text:
            QMessageBox.information(self, "No Selection", "Please highlight a word or phrase in the text area first.")
            return

        start = cursor.selectionStart()
        end = cursor.selectionEnd()

        ent = EntityAnnotation(
            label=label,
            text=selected_text,
            start_char=start,
            end_char=end
        )
        self.current_entities.append(ent)
        self.entity_list.addItem(f"[{label}] '{selected_text}' (chars {start}-{end})")

    def _clear_all(self):
        self.text_edit.clear()
        self.text_b_edit.clear()
        self.current_entities.clear()
        self.entity_list.clear()

    def _save_annotation(self):
        txt = self.text_edit.toPlainText().strip()
        if not txt:
            QMessageBox.warning(self, "Empty Text", "Please enter engineering text to annotate.")
            return

        doc_id = self.doc_id_input.text().strip() or "DOC_MANUAL"
        domain = self.domain_combo.currentText().lower()
        import uuid
        annot_id = f"ANN_{uuid.uuid4().hex[:8].upper()}"

        annot = DocumentAnnotation(
            annotation_id=annot_id,
            document_id=doc_id,
            domain=domain,
            page=1,
            text=txt,
            entities=list(self.current_entities),
            classification_label=self.class_combo.currentText(),
            logical_label=self.logical_combo.currentText(),
            statement_b=self.text_b_edit.text().strip() or None,
            annotated_by="engineer_manual"
        )

        file_path = self.manager.save_annotation(annot)
        QMessageBox.information(self, "Annotation Saved", f"Successfully saved training sample:\n{file_path}")
        self.annotation_saved.emit(annot_id)
        self._clear_all()
