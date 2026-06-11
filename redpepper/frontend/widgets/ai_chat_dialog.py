from __future__ import annotations

import base64
import html
from pathlib import Path
import re

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QDesktopServices, QTextDocument
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
)

from frontend.i18n.translator import tr
from frontend.services.chat_service import ChatService


class ChatWorker(QThread):
    completed = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(
        self,
        *,
        model: str,
        prompt: str,
        history: list[dict],
        attachments: list[dict] | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self._model = model
        self._prompt = prompt
        self._history = history
        self._attachments = attachments or []

    def run(self) -> None:
        try:
            svc = ChatService()
            result = svc.chat(
                model=self._model,
                prompt=self._prompt,
                messages=self._history,
                attachments=self._attachments,
            )
            self.completed.emit(result if isinstance(result, dict) else {})
        except Exception as exc:
            self.failed.emit(str(exc))


class AIChatDialog(QDialog):
    MODEL_ITEMS = [
        ("kimi-k2.6", "Kimi-k2.6"),
        ("deepseek-v4-flash", "DeepSeek-v4-Flash"),
        ("deepseek-v4-pro", "DeepSeek-v4-Pro"),
    ]
    TEXT_EXTENSIONS = {
        ".txt",
        ".md",
        ".csv",
        ".json",
        ".yaml",
        ".yml",
        ".log",
        ".py",
        ".sql",
        ".html",
        ".htm",
    }
    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("dashboard.ai_chat_title"))
        self.resize(900, 680)

        self._history: list[dict[str, str]] = []
        self._turns: list[dict[str, str]] = []
        self._pending_attachments: list[dict[str, str]] = []
        self._code_snippets: dict[str, str] = {}
        self._code_counter = 0
        self._worker: ChatWorker | None = None

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        top = QHBoxLayout()

        title = QLabel(tr("dashboard.ai_chat_title"))
        title.setObjectName("chatTitle")
        top.addWidget(title)
        top.addStretch()

        top.addWidget(QLabel(tr("dashboard.ai_chat_model")))

        self.model_combo = QComboBox()
        for value, label in self.MODEL_ITEMS:
            self.model_combo.addItem(label, userData=value)
        self.model_combo.currentIndexChanged.connect(self._on_model_changed)
        top.addWidget(self.model_combo)

        self.btn_clear = QPushButton(tr("dashboard.ai_chat_clear"))
        self.btn_clear.clicked.connect(self._on_clear)
        top.addWidget(self.btn_clear)

        layout.addLayout(top)

        self.hint_label = QLabel(tr("dashboard.ai_chat_kimi_hint"))
        self.hint_label.setWordWrap(True)
        layout.addWidget(self.hint_label)

        self.supported_label = QLabel("")
        self.supported_label.setWordWrap(True)
        layout.addWidget(self.supported_label)

        self.chat_log = QTextBrowser(self)
        self.chat_log.setOpenExternalLinks(False)
        self.chat_log.anchorClicked.connect(self._on_anchor_clicked)
        self.chat_log.setPlaceholderText(tr("dashboard.ai_chat_placeholder"))
        self.chat_log.setObjectName("chatLog")
        layout.addWidget(self.chat_log, 1)

        composer = QFrame(self)
        composer.setObjectName("composer")
        composer_layout = QVBoxLayout(composer)
        composer_layout.setContentsMargins(12, 12, 12, 12)
        composer_layout.setSpacing(8)

        self.attachment_label = QLabel(tr("dashboard.ai_chat_no_attachment"))
        self.attachment_label.setObjectName("attachmentInfo")
        self.attachment_label.setWordWrap(True)
        composer_layout.addWidget(self.attachment_label)

        self.input_edit = QTextEdit(composer)
        self.input_edit.setMinimumHeight(120)
        self.input_edit.setPlaceholderText(tr("dashboard.ai_chat_input_placeholder"))
        self.input_edit.setObjectName("inputBox")
        composer_layout.addWidget(self.input_edit)

        bottom = QHBoxLayout()

        self.btn_attach = QPushButton(tr("dashboard.ai_chat_upload_attachment"))
        self.btn_attach.clicked.connect(self._on_attach_files)
        bottom.addWidget(self.btn_attach)

        bottom.addStretch()

        self.btn_send = QPushButton(tr("dashboard.ai_chat_send"))
        self.btn_send.setObjectName("sendButton")
        self.btn_send.clicked.connect(self._on_send)
        bottom.addWidget(self.btn_send)

        composer_layout.addLayout(bottom)
        layout.addWidget(composer)

        self.setStyleSheet(
            """
            QDialog {
                background: #0D0D1A;
            }
            QLabel#chatTitle {
                font-size: 18px;
                font-weight: 700;
                color: #E8E8F0;
            }
            QTextBrowser#chatLog {
                background: #111125;
                border: 1px solid #338B5CF6;
                border-radius: 12px;
                color: #E8E8F0;
                padding: 12px;
            }
            QFrame#composer {
                background: #1A1A2E;
                border: 1px solid #338B5CF6;
                border-radius: 16px;
            }
            QTextEdit#inputBox {
                background: transparent;
                border: none;
                color: #E8E8F0;
                font-size: 13px;
            }
            QLabel#attachmentInfo {
                color: #B8B8D6;
                font-size: 12px;
            }
            QPushButton#sendButton {
                background: #F05C77;
                color: white;
                border: none;
                border-radius: 14px;
                padding: 8px 14px;
            }
            QPushButton#sendButton:hover {
                background: #F37A90;
            }
            QPushButton {
                color: #E8E8F0;
                background: #2A2A3E;
                border: 1px solid #338B5CF6;
                border-radius: 10px;
                padding: 6px 10px;
            }
            QComboBox {
                color: #E8E8F0;
                background: #2A2A3E;
                border: 1px solid #338B5CF6;
                border-radius: 10px;
                padding: 6px 8px;
            }
            """
        )

        self._on_model_changed()

    def _current_model(self) -> str:
        return str(self.model_combo.currentData() or "kimi-k2.6")

    def _is_kimi(self) -> bool:
        return self._current_model() == "kimi-k2.6"

    def _supported_extensions(self) -> set[str]:
        if self._is_kimi():
            return self.TEXT_EXTENSIONS | self.IMAGE_EXTENSIONS
        return set(self.TEXT_EXTENSIONS)

    def _supports_images(self) -> bool:
        return self._is_kimi()

    def _file_filter(self) -> str:
        supported = sorted(self._supported_extensions())
        filter_items = [f"*{ext}" for ext in supported]
        return f"Supported Files ({' '.join(filter_items)});;All Files (*.*)"

    def _capability_summary(self) -> str:
        text_types = ", ".join(sorted(ext.lstrip(".") for ext in self.TEXT_EXTENSIONS))
        if self._supports_images():
            image_types = ", ".join(sorted(ext.lstrip(".") for ext in self.IMAGE_EXTENSIONS))
            return tr("dashboard.ai_chat_support_kimi", text_types=text_types, image_types=image_types)
        return tr("dashboard.ai_chat_support_deepseek", text_types=text_types)

    def _on_model_changed(self) -> None:
        self.hint_label.setText(
            tr("dashboard.ai_chat_kimi_hint") if self._is_kimi() else tr("dashboard.ai_chat_non_kimi_hint")
        )
        self.supported_label.setText(self._capability_summary())
        self._pending_attachments.clear()
        self._refresh_attachment_label()

    def _guess_mime(self, ext: str) -> str:
        ext = ext.lower()
        if ext in {".jpg", ".jpeg"}:
            return "image/jpeg"
        if ext == ".png":
            return "image/png"
        if ext == ".webp":
            return "image/webp"
        if ext == ".gif":
            return "image/gif"
        if ext == ".bmp":
            return "image/bmp"
        if ext in {".md", ".txt", ".log", ".py", ".sql", ".yaml", ".yml"}:
            return "text/plain"
        if ext == ".csv":
            return "text/csv"
        if ext == ".json":
            return "application/json"
        if ext in {".html", ".htm"}:
            return "text/html"
        return "application/octet-stream"

    def _read_text_file(self, path: Path) -> str:
        for encoding in ("utf-8", "utf-8-sig", "gb18030"):
            try:
                return path.read_text(encoding=encoding)
            except Exception:
                continue
        return path.read_text(encoding="utf-8", errors="ignore")

    def _on_attach_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            tr("dashboard.ai_chat_upload_attachment"),
            "",
            self._file_filter(),
        )
        if not paths:
            return

        allowed = self._supported_extensions()
        skipped: list[str] = []
        added = 0

        for one_path in paths:
            path = Path(one_path)
            ext = path.suffix.lower()
            if ext not in allowed:
                skipped.append(path.name)
                continue

            try:
                if ext in self.IMAGE_EXTENSIONS:
                    payload = {
                        "name": path.name,
                        "kind": "image",
                        "mime": self._guess_mime(ext),
                        "content_base64": base64.b64encode(path.read_bytes()).decode("ascii"),
                        "text": "",
                    }
                else:
                    payload = {
                        "name": path.name,
                        "kind": "text",
                        "mime": self._guess_mime(ext),
                        "content_base64": "",
                        "text": self._read_text_file(path),
                    }
                self._pending_attachments.append(payload)
                added += 1
            except Exception:
                skipped.append(path.name)

        self._refresh_attachment_label()
        if skipped:
            QMessageBox.information(
                self,
                tr("common.info"),
                tr("dashboard.ai_chat_attachment_skipped", files=", ".join(skipped)),
            )
        if added <= 0:
            return

    def _refresh_attachment_label(self) -> None:
        if not self._pending_attachments:
            self.attachment_label.setText(tr("dashboard.ai_chat_no_attachment"))
            return
        names = ", ".join(str(a.get("name", "")) for a in self._pending_attachments[:6] if a.get("name"))
        more = len(self._pending_attachments) - 6
        if more > 0:
            names += tr("dashboard.ai_chat_attachment_more", count=more)
        self.attachment_label.setText(
            tr("dashboard.ai_chat_attachment_ready", count=len(self._pending_attachments), files=names)
        )

    def _markdown_fragment_to_html(self, text: str) -> str:
        doc = QTextDocument()
        doc.setMarkdown(text)
        html_text = doc.toHtml()
        match = re.search(r"<body[^>]*>(.*)</body>", html_text, flags=re.S | re.I)
        return match.group(1) if match else html.escape(text)

    def _register_code_snippets(self, html_fragment: str) -> str:
        pattern = re.compile(r"<pre[^>]*><code[^>]*>(.*?)</code></pre>", flags=re.S | re.I)

        def _replace(match: re.Match[str]) -> str:
            code_html = match.group(1)
            code_plain = re.sub(r"<br\s*/?>", "\n", code_html, flags=re.I)
            code_plain = re.sub(r"<[^>]+>", "", code_plain)
            code_plain = html.unescape(code_plain)
            self._code_counter += 1
            code_id = f"code-{self._code_counter}"
            self._code_snippets[code_id] = code_plain
            return (
                '<div class="code-card">'
                f'<a class="copy-link" href="copy://{code_id}">{tr("dashboard.ai_chat_copy_code")}</a>'
                f"<pre><code>{code_html}</code></pre>"
                "</div>"
            )

        return pattern.sub(_replace, html_fragment)

    def _on_anchor_clicked(self, url) -> None:
        if url.scheme() == "copy":
            code_id = (url.host() or url.path().lstrip("/")).strip()
            code = self._code_snippets.get(code_id, "")
            if code:
                QApplication.clipboard().setText(code)
            return
        QDesktopServices.openUrl(url)

    def _render_turns(self) -> None:
        if not self._turns:
            self.chat_log.clear()
            return

        self._code_snippets = {}
        self._code_counter = 0

        blocks: list[str] = [
            """
            <style>
                .chat-root { font-family: 'Microsoft YaHei UI', 'Segoe UI', sans-serif; color: #E8E8F0; }
                .row { display: flex; margin: 10px 0; }
                .row.user { justify-content: flex-end; }
                .row.assistant { justify-content: flex-start; }
                .bubble {
                    max-width: 78%;
                    padding: 12px 14px;
                    border-radius: 14px;
                    border: 1px solid #338B5CF6;
                    line-height: 1.55;
                    word-wrap: break-word;
                }
                .bubble.user {
                    background: #2A1A35;
                    border-color: #44F05C77;
                }
                .bubble.assistant {
                    background: #1A1A2E;
                }
                .role {
                    font-weight: 700;
                    margin-bottom: 6px;
                    color: #F59E0B;
                }
                .bubble.user .role {
                    color: #F05C77;
                }
                .bubble p { margin: 0 0 8px 0; }
                .bubble ul, .bubble ol { margin: 6px 0 8px 18px; }
                .bubble blockquote {
                    border-left: 3px solid #8B5CF6;
                    margin: 8px 0;
                    padding: 4px 10px;
                    color: #C9C9E3;
                    background: #141427;
                    border-radius: 6px;
                }
                .code-card {
                    background: #0F1020;
                    border: 1px solid #3A3A64;
                    border-radius: 10px;
                    margin: 8px 0;
                    overflow: hidden;
                }
                .copy-link {
                    display: inline-block;
                    margin: 8px 10px 0 10px;
                    padding: 4px 8px;
                    border-radius: 8px;
                    border: 1px solid #8B5CF6;
                    color: #F59E0B;
                    text-decoration: none;
                    font-size: 12px;
                }
                .copy-link:hover {
                    background: #2A2250;
                }
                .code-card pre {
                    margin: 8px 0 0 0;
                    padding: 10px;
                    background: transparent;
                    color: #E8E8F0;
                    white-space: pre-wrap;
                }
            </style>
            <div class="chat-root">
            """
        ]

        for turn in self._turns:
            role = str(turn.get("role", "assistant") or "assistant")
            content = str(turn.get("content", "") or "").strip()
            if not content:
                continue

            role_name = tr("dashboard.ai_chat_user") if role == "user" else tr("dashboard.ai_chat_assistant")
            content_html = self._markdown_fragment_to_html(content)
            content_html = self._register_code_snippets(content_html)
            role_class = "user" if role == "user" else "assistant"
            blocks.append(
                f'<div class="row {role_class}">'
                f'<div class="bubble {role_class}">'
                f'<div class="role">{html.escape(role_name)}</div>'
                f"{content_html}"
                "</div></div>"
            )

        blocks.append("</div>")
        self.chat_log.setHtml("\n".join(blocks))
        self.chat_log.verticalScrollBar().setValue(self.chat_log.verticalScrollBar().maximum())

    def _set_busy(self, busy: bool) -> None:
        self.btn_send.setEnabled(not busy)
        self.btn_attach.setEnabled(not busy)
        self.model_combo.setEnabled(not busy)

    def _on_send(self) -> None:
        prompt = self.input_edit.toPlainText().strip()
        if not prompt and not self._pending_attachments:
            return

        model = self._current_model()
        attachments = [dict(a) for a in self._pending_attachments]

        user_content = prompt or tr("dashboard.ai_chat_attachment_only_message")
        attachment_names = ", ".join(str(a.get("name", "")) for a in attachments if a.get("name"))
        if attachment_names:
            user_content = f"{user_content}\n\n> {tr('dashboard.ai_chat_with_attachment')}: {attachment_names}"

        history = list(self._history)
        self._turns.append(
            {
                "role": "user",
                "content": user_content,
                "image_name": attachment_names,
            }
        )
        self._render_turns()
        self.input_edit.clear()
        self._set_busy(True)

        self._worker = ChatWorker(
            model=model,
            prompt=prompt,
            history=history,
            attachments=attachments,
            parent=self,
        )
        self._worker.completed.connect(lambda result, p=prompt: self._on_completed(result, p))
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_completed(self, result: dict, prompt: str) -> None:
        self._set_busy(False)
        answer = str((result or {}).get("answer", "") or "").strip()
        if not answer:
            answer = tr("dashboard.ai_chat_empty_reply")

        self._history.append({"role": "user", "content": prompt or tr("dashboard.ai_chat_attachment_only_message")})
        self._history.append({"role": "assistant", "content": answer})
        self._turns.append({"role": "assistant", "content": answer, "image_name": ""})
        self._render_turns()

        self._pending_attachments.clear()
        self._refresh_attachment_label()

    def _on_failed(self, error_text: str) -> None:
        self._set_busy(False)
        QMessageBox.warning(self, tr("common.error"), f"{tr('dashboard.ai_chat_failed')}: {error_text}")

    def _on_clear(self) -> None:
        self._history.clear()
        self._turns.clear()
        self._pending_attachments.clear()
        self.chat_log.clear()
        self._refresh_attachment_label()
