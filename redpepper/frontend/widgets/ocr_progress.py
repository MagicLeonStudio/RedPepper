from __future__ import annotations

import base64
import inspect
import time
from collections.abc import Callable

from PyQt6.QtCore import QThread, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import QDialog, QHBoxLayout, QLabel, QProgressBar, QTextEdit, QVBoxLayout

from frontend.ai_runtime import get_ocr_runtime_target
from frontend.app_meta import logo_icon_path
from frontend.i18n.translator import tr


class OCRImportWorker(QThread):
    stage_changed = pyqtSignal(str)
    progress_changed = pyqtSignal(object)
    completed = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, task: Callable[[str], object], file_path: str, parent=None, *, text_mode: bool = False):
        super().__init__(parent)
        self._task = task
        self._file_path = file_path
        self._text_mode = text_mode

    def _emit_progress(self, payload: dict) -> None:
        self.progress_changed.emit(payload)

    def run(self) -> None:
        try:
            if self._text_mode:
                self.stage_changed.emit(tr("ocr_progress.text_preparing"))
            else:
                self.stage_changed.emit(tr("ocr_progress.preparing_image"))
                self.stage_changed.emit(tr("ocr_progress.uploading_image"))
                provider_name, model_name = get_ocr_runtime_target()
                self.stage_changed.emit(
                    tr("ocr_progress.waiting_model", provider=provider_name, model=model_name)
                )
            signature = inspect.signature(self._task)
            if len(signature.parameters) >= 2:
                result = self._task(self._file_path, self._emit_progress)
            else:
                result = self._task(self._file_path)
            self.completed.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))


class OCRProgressDialog(QDialog):
    def __init__(self, title: str, parent=None, *, text_mode: bool = False):
        super().__init__(parent)
        self._started_at = time.monotonic()
        self._text_mode = text_mode
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_elapsed)

        provider_name, model_name = get_ocr_runtime_target()
        self._provider_name = provider_name
        self._model_name = model_name

        self.setWindowTitle(title)
        self.setModal(True)
        self.setFixedWidth(460)
        icon_path = logo_icon_path()
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        logo = QLabel()
        logo.setObjectName("progressLogo")
        logo.setMinimumHeight(72)
        if icon_path.exists():
            logo.setPixmap(QPixmap(str(icon_path)).scaledToHeight(64))
        layout.addWidget(logo)

        self.title_label = QLabel(
            tr("ocr_progress.text_title") if self._text_mode else tr("ocr_progress.title")
        )
        self.title_label.setObjectName("progressTitle")
        layout.addWidget(self.title_label)

        self.model_label = QLabel(
            tr("ocr_progress.using_model", provider=self._provider_name, model=self._model_name)
        )
        self.model_label.setWordWrap(True)
        layout.addWidget(self.model_label)

        self.stage_label = QLabel(
            tr("ocr_progress.text_preparing") if self._text_mode else tr("ocr_progress.preparing_image")
        )
        self.stage_label.setWordWrap(True)
        layout.addWidget(self.stage_label)

        self.elapsed_label = QLabel(tr("ocr_progress.elapsed", seconds=0))
        layout.addWidget(self.elapsed_label)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        layout.addWidget(self.progress)

        preview_layout = QHBoxLayout()
        preview_layout.setSpacing(12)

        self.original_preview = QLabel(tr("ocr_progress.preparing_image"))
        self.original_preview.setObjectName("previewFrame")
        self.original_preview.setMinimumSize(180, 220)
        self.original_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.original_preview.setWordWrap(True)
        preview_layout.addWidget(self.original_preview)

        self.segment_preview = QLabel(tr("ocr_progress.uploading_image"))
        self.segment_preview.setObjectName("previewFrame")
        self.segment_preview.setMinimumSize(180, 220)
        self.segment_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.segment_preview.setWordWrap(True)
        preview_layout.addWidget(self.segment_preview)

        layout.addLayout(preview_layout)

        self.segment_counter = QLabel("")
        self.segment_counter.setWordWrap(True)
        layout.addWidget(self.segment_counter)

        if self._text_mode:
            self.original_preview.hide()
            self.segment_preview.hide()
            self.model_label.hide()

        self.csv_title = QLabel("CSV Preview")
        layout.addWidget(self.csv_title)

        self.csv_output = QTextEdit(self)
        self.csv_output.setReadOnly(True)
        self.csv_output.setMinimumHeight(180)
        layout.addWidget(self.csv_output)

        self.setStyleSheet(
            """
            QDialog {
                background-color: #0D0D1A;
            }
            QLabel {
                color: #E8E8F0;
                font-size: 13px;
            }
            QLabel#progressTitle {
                color: #FFFFFF;
                font-size: 16px;
                font-weight: 700;
            }
            QProgressBar {
                background-color: #1A1A2E;
                border: 1px solid #338B5CF6;
                border-radius: 8px;
                min-height: 14px;
            }
            QProgressBar::chunk {
                background-color: #F05C77;
                border-radius: 8px;
            }
            QLabel#previewFrame {
                border: 1px solid #338B5CF6;
                border-radius: 8px;
                background-color: #1A1A2E;
                padding: 6px;
            }
            QTextEdit {
                background-color: #111125;
                color: #DCDCF4;
                border: 1px solid #338B5CF6;
                border-radius: 8px;
                padding: 8px;
                font-family: Consolas, 'Courier New', monospace;
                font-size: 12px;
            }
            """
        )

    def start(self) -> None:
        self._timer.start(500)
        self._update_elapsed()

    def stop(self) -> None:
        self._timer.stop()

    def set_stage(self, text: str) -> None:
        self.stage_label.setText(text)

    def update_progress(self, payload: object) -> None:
        if not isinstance(payload, dict):
            return

        message = str(payload.get("message", "") or "").strip()
        if message:
            self.stage_label.setText(message)

        current = int(payload.get("current", 0) or 0)
        total = int(payload.get("total", 0) or 0)
        if total > 0:
            self.progress.setRange(0, total)
            self.progress.setValue(min(max(current, 0), total))
            self.progress.setTextVisible(True)

        segment_current = int(payload.get("segment_current", 0) or 0)
        segment_total = int(payload.get("segment_total", 0) or 0)
        if segment_total > 0:
            if segment_total <= 1:
                self.segment_counter.setText("Fragments: 1/1 (no split)")
            else:
                self.segment_counter.setText(f"Fragments: {segment_current}/{segment_total}")
        elif total > 0:
            self.segment_counter.setText(f"Progress: {current}/{total}")
        else:
            self.segment_counter.setText("")

        original_b64 = str(payload.get("original_image_base64", "") or "")
        if original_b64:
            self._set_preview(self.original_preview, original_b64)
            self.original_preview.setToolTip("Original screenshot")

        segment_b64 = str(payload.get("segment_image_base64", "") or "")
        if segment_b64:
            self._set_preview(self.segment_preview, segment_b64)
            self.segment_preview.setToolTip("Current OCR fragment")

        csv_text = payload.get("csv_text")
        if isinstance(csv_text, str) and csv_text.strip():
            self.csv_output.setPlainText(csv_text)
            self.csv_output.verticalScrollBar().setValue(self.csv_output.verticalScrollBar().maximum())

    def _set_preview(self, label: QLabel, image_base64: str) -> None:
        try:
            image_bytes = base64.b64decode(image_base64, validate=False)
        except Exception:
            return

        pixmap = QPixmap()
        if not pixmap.loadFromData(image_bytes):
            return

        scaled = pixmap.scaled(
            label.width() - 12,
            label.height() - 12,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        label.setPixmap(scaled)

    def _update_elapsed(self) -> None:
        elapsed_seconds = int(time.monotonic() - self._started_at)
        self.elapsed_label.setText(tr("ocr_progress.elapsed", seconds=elapsed_seconds))


def run_ocr_import(parent, title: str, task: Callable[[str], object], file_path: str, *, text_mode: bool = False):
    dialog = OCRProgressDialog(title, parent, text_mode=text_mode)
    worker = OCRImportWorker(task, file_path, parent=dialog, text_mode=text_mode)
    result_holder: dict[str, object] = {}

    worker.stage_changed.connect(dialog.set_stage)
    worker.progress_changed.connect(dialog.update_progress)

    def _completed(result: object) -> None:
        result_holder["result"] = result
        dialog.stop()
        dialog.accept()

    def _failed(error_text: str) -> None:
        result_holder["error"] = error_text
        dialog.stop()
        dialog.reject()

    worker.completed.connect(_completed)
    worker.failed.connect(_failed)

    worker.start()
    dialog.start()
    dialog.exec()
    worker.wait()

    if "error" in result_holder:
        raise RuntimeError(str(result_holder["error"]))
    return result_holder.get("result")
