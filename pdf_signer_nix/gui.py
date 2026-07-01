from __future__ import annotations

import json
import logging
from dataclasses import asdict
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, QThread, Qt, QUrl, Signal
from PySide6.QtGui import QAction, QColor, QDesktopServices, QDragEnterEvent, QDropEvent, QIcon, QKeyEvent, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QProgressBar,
    QSlider,
    QSpinBox,
    QDoubleSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from . import __version__
from .crypto import CryptoProError, list_certificates
from .diagnostics import format_diagnostics_report, run_diagnostics
from .models import Certificate, SigningJob, StampSettings, VerificationReport, builtin_stamp_settings
from .paths import asset_path, installed_icon_path, log_dir
from .pdf_tools import Rect, stamp_lines, validate_stamp_layout
from .settings import (
    default_settings,
    export_settings,
    import_settings,
    load_settings,
    load_stamp_profile,
    save_settings,
    save_stamp_profile,
    stamp_from_payload,
    stamp_to_payload,
)
from .update_service import ReleaseInfo, get_current_version_text, get_latest_release, is_newer_than_current
from .verification import report_to_html, report_to_text, verify_file
from .workflow import run_signing_job

LOG = logging.getLogger(__name__)


PROFILE_ITEMS = [
    ("gost-minimal", "ГОСТ минимальный"),
    ("gost-standard", "ГОСТ стандартный"),
    ("gost-detailed", "ГОСТ подробный"),
    ("custom", "Custom"),
]


class PdfListWidget(QListWidget):
    verification_files_dropped = Signal(list)

    def __init__(self) -> None:
        super().__init__()
        self.setAcceptDrops(True)
        self.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Delete:
            for item in self.selectedItems():
                self.takeItem(self.row(item))
            return
        if event.key() == Qt.Key.Key_A and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.selectAll()
            return
        super().keyPressEvent(event)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        pdfs: list[str] = []
        verification_files: list[str] = []
        for url in event.mimeData().urls():
            local = Path(url.toLocalFile())
            if not local.exists():
                continue
            suffix = local.suffix.lower()
            if suffix == ".pdf":
                pdfs.append(str(local))
            elif suffix in {".sig", ".p7s"}:
                verification_files.append(str(local))
        for file in pdfs:
            if not self.findItems(file, Qt.MatchFlag.MatchExactly):
                self.addItem(file)
        if verification_files:
            self.verification_files_dropped.emit(verification_files)
        event.acceptProposedAction()


class SigningThread(QThread):
    finished_ok = Signal(list)
    failed = Signal(str)

    def __init__(self, job: SigningJob) -> None:
        super().__init__()
        self.job = job

    def run(self) -> None:
        try:
            self.finished_ok.emit([asdict(item) for item in run_signing_job(self.job)])
        except Exception as exc:
            LOG.exception("Signing failed")
            self.failed.emit(str(exc))


class VerificationThread(QThread):
    finished_ok = Signal(list)
    failed = Signal(str)

    def __init__(self, files: list[Path]) -> None:
        super().__init__()
        self.files = files

    def run(self) -> None:
        try:
            self.finished_ok.emit([verify_file(path) for path in self.files])
        except Exception as exc:
            LOG.exception("Verification failed")
            self.failed.emit(str(exc))


class UpdateCheckThread(QThread):
    finished_ok = Signal(object)
    failed = Signal(str)

    def run(self) -> None:
        try:
            self.finished_ok.emit(get_latest_release())
        except Exception as exc:
            LOG.exception("Update check failed")
            self.failed.emit(str(exc))


class StampPreviewWidget(QWidget):
    stamp_moved = Signal(float, float)

    def __init__(self) -> None:
        super().__init__()
        self.setMinimumSize(320, 440)
        self._stamp = StampSettings()
        self._certificate = Certificate(subject="CN=Иван Иванов, O=ООО Ромашка, T=Директор", issuer="Тестовый УЦ", serial="1234567890")
        self._dragging = False

    def set_stamp(self, stamp: StampSettings) -> None:
        self._stamp = stamp.clone().normalize()
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), QColor("#eef3f9"))

        page = self.page_rect()
        painter.setBrush(Qt.GlobalColor.white)
        painter.setPen(QPen(QColor("#d0dae7"), 1))
        painter.drawRoundedRect(page, 12, 12)

        stamp_rect = QRectF(self.stamp_rect(page)).adjusted(1.0, 1.0, -1.0, -1.0)
        painter.setPen(QPen(QColor("#004aad"), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(stamp_rect, 6, 6)

        layout = validate_stamp_layout(self._stamp, self._certificate, max_width=stamp_rect.width() - 16)
        font = painter.font()
        font.setPointSizeF(layout.font_size)
        painter.setFont(font)
        painter.setPen(QColor("#004aad"))
        text_rect = stamp_rect.adjusted(8, 8, -8, -8)
        painter.save()
        painter.setClipRect(text_rect)
        y = text_rect.top() + layout.font_size
        for line in layout.wrapped_lines[:10]:
            painter.drawText(QPointF(text_rect.left(), y), line)
            y += max(layout.font_size + 2, layout.font_size * 1.25)
        painter.restore()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.page_rect().contains(event.position().toPoint()):
            self._dragging = True
            self.move_stamp(event.position())

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._dragging:
            self.move_stamp(event.position())

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._dragging = False

    def page_rect(self):
        bounds = self.rect().adjusted(18, 18, -18, -18)
        page_ratio = 595 / 842
        if bounds.width() / max(bounds.height(), 1) > page_ratio:
            width = int(bounds.height() * page_ratio)
            left = bounds.left() + (bounds.width() - width) // 2
            return bounds.__class__(left, bounds.top(), width, bounds.height())
        height = int(bounds.width() / page_ratio)
        top = bounds.top() + (bounds.height() - height) // 2
        return bounds.__class__(bounds.left(), top, bounds.width(), height)

    def stamp_rect(self, page_rect):
        scale = min(page_rect.width() / 595.0, page_rect.height() / 842.0)
        width = self._stamp.width_points * scale
        height = self._stamp.height_points * scale
        preview_stamp = self._stamp.clone()
        preview_stamp.x *= scale
        preview_stamp.y *= scale
        preview_stamp.margin *= scale
        rect = rect_for_preview(preview_stamp, page_rect, width, height)
        return rect

    def move_stamp(self, position: QPointF) -> None:
        page = self.page_rect()
        scale = min(page.width() / 595.0, page.height() / 842.0)
        width = self._stamp.width_points * scale
        height = self._stamp.height_points * scale
        x = max(0.0, (position.x() - page.left() - width / 2) / scale)
        y = max(0.0, (page.bottom() - position.y() - height / 2) / scale)
        self.stamp_moved.emit(x, y)


class StampEditorDialog(QDialog):
    def __init__(self, stamp: StampSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Редактор штампа")
        self.resize(980, 720)
        self._loading = False
        self._stamp = stamp.clone().normalize()
        self.preview = StampPreviewWidget()
        self.preview.stamp_moved.connect(self.on_preview_stamp_moved)
        self._build_ui()
        self.load_stamp(self._stamp)

    @property
    def stamp(self) -> StampSettings:
        return self.collect_stamp()

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(self.preview)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        root.addWidget(splitter)

        top_buttons = QHBoxLayout()
        self.profile_combo = combo(PROFILE_ITEMS)
        self.profile_combo.currentIndexChanged.connect(self.apply_selected_profile)
        load_profile = QPushButton("Загрузить профиль")
        load_profile.clicked.connect(self.load_profile_dialog)
        save_profile = QPushButton("Сохранить профиль")
        save_profile.clicked.connect(self.save_profile_dialog)
        reset_position = QPushButton("Сбросить позицию")
        reset_position.clicked.connect(self.reset_position)
        top_buttons.addWidget(QLabel("Профиль"))
        top_buttons.addWidget(self.profile_combo)
        top_buttons.addWidget(load_profile)
        top_buttons.addWidget(save_profile)
        top_buttons.addWidget(reset_position)
        left_layout.addLayout(top_buttons)

        form = QGridLayout()
        self.page_mode = combo([("first", "Первая"), ("last", "Последняя"), ("all", "Все"), ("specific", "Указанная")])
        self.page_mode.currentIndexChanged.connect(self.refresh_preview)
        self.specific_page = spin(1, 999, 1)
        self.specific_page.valueChanged.connect(self.refresh_preview)
        self.position = combo(
            [
                ("top-left", "Сверху слева"),
                ("top-right", "Сверху справа"),
                ("bottom-left", "Снизу слева"),
                ("bottom-right", "Снизу справа"),
                ("custom", "Своя"),
            ]
        )
        self.position.currentIndexChanged.connect(self.refresh_preview)
        self.x = dspin(0, 2000, 36, 1)
        self.x.valueChanged.connect(self.refresh_preview)
        self.y = dspin(0, 2000, 36, 1)
        self.y.valueChanged.connect(self.refresh_preview)
        self.width_mm = spin(60, 200, 90)
        self.width_mm.valueChanged.connect(self.refresh_preview)
        self.height_mm = spin(20, 100, 35)
        self.height_mm.valueChanged.connect(self.refresh_preview)
        self.font_size = dspin(6, 16, 7, 0.5)
        self.font_size.valueChanged.connect(self.refresh_preview)
        self.min_font_size = dspin(6, 16, 7, 0.5)
        self.min_font_size.valueChanged.connect(self.refresh_preview)
        self.logo_scale = spin(10, 300, 100)
        self.logo_scale.valueChanged.connect(self.refresh_preview)
        self.opacity = QSlider(Qt.Orientation.Horizontal)
        self.opacity.setRange(0, 100)
        self.opacity.valueChanged.connect(self.refresh_preview)
        self.reason = QLineEdit()
        self.reason.textChanged.connect(self.refresh_preview)
        self.custom_text = QTextEdit()
        self.custom_text.setFixedHeight(72)
        self.custom_text.textChanged.connect(self.refresh_preview)
        self.logo_path = QLineEdit()
        self.logo_path.setReadOnly(True)

        add_form_row(form, 0, "Страницы", self.page_mode, "Конкретная", self.specific_page)
        add_form_row(form, 1, "Позиция", self.position, "X", self.x)
        add_form_row(form, 2, "Ширина, мм", self.width_mm, "Y", self.y)
        add_form_row(form, 3, "Высота, мм", self.height_mm, "Шрифт, pt", self.font_size)
        add_form_row(form, 4, "Мин. шрифт", self.min_font_size, "Логотип, %", self.logo_scale)
        form.addWidget(QLabel("Прозрачность"), 5, 0)
        form.addWidget(self.opacity, 5, 1, 1, 3)
        form.addWidget(QLabel("Причина"), 6, 0)
        form.addWidget(self.reason, 6, 1, 1, 3)
        logo_row = QHBoxLayout()
        choose_logo = QPushButton("Логотип")
        choose_logo.clicked.connect(self.choose_logo)
        clear_logo = QPushButton("Убрать")
        clear_logo.clicked.connect(self.clear_logo)
        logo_row.addWidget(self.logo_path)
        logo_row.addWidget(choose_logo)
        logo_row.addWidget(clear_logo)
        form.addWidget(QLabel("Файл логотипа"), 7, 0)
        logo_widget = QWidget()
        logo_widget.setLayout(logo_row)
        form.addWidget(logo_widget, 7, 1, 1, 3)
        form.addWidget(QLabel("Свой текст"), 8, 0)
        form.addWidget(self.custom_text, 8, 1, 1, 3)
        left_layout.addLayout(form)

        self.auto_place = QCheckBox("Автоматически подобрать место")
        self.include_owner = QCheckBox("Владелец")
        self.include_organization = QCheckBox("Организация")
        self.include_position = QCheckBox("Должность")
        self.include_inn = QCheckBox("ИНН")
        self.include_snils = QCheckBox("СНИЛС")
        self.include_issuer = QCheckBox("Издатель")
        self.include_serial = QCheckBox("Серийный номер")
        self.include_thumbprint = QCheckBox("Отпечаток")
        self.include_reason = QCheckBox("Причина")
        self.include_date = QCheckBox("Дата")
        self.include_time = QCheckBox("Время")
        self.include_signing_date_time = QCheckBox("Дата и время подписи")
        self.include_custom_text = QCheckBox("Включить свой текст")
        checks = [
            self.auto_place,
            self.include_owner,
            self.include_organization,
            self.include_position,
            self.include_inn,
            self.include_snils,
            self.include_issuer,
            self.include_serial,
            self.include_thumbprint,
            self.include_reason,
            self.include_date,
            self.include_time,
            self.include_signing_date_time,
            self.include_custom_text,
        ]
        checks_box = QGridLayout()
        for index, check in enumerate(checks):
            check.stateChanged.connect(self.refresh_preview)
            checks_box.addWidget(check, index // 2, index % 2)
        left_layout.addLayout(checks_box)

        self.warning = QLabel()
        self.warning.setWordWrap(True)
        left_layout.addWidget(self.warning)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        left_layout.addWidget(buttons)

    def load_stamp(self, stamp: StampSettings) -> None:
        self._loading = True
        try:
            set_combo(self.profile_combo, stamp.template_name)
            set_combo(self.page_mode, stamp.page_mode)
            set_combo(self.position, stamp.position)
            self.specific_page.setValue(stamp.specific_page)
            self.x.setValue(stamp.x)
            self.y.setValue(stamp.y)
            self.width_mm.setValue(int(stamp.width_mm))
            self.height_mm.setValue(int(stamp.height_mm))
            self.font_size.setValue(stamp.font_size)
            self.min_font_size.setValue(stamp.min_font_size)
            self.opacity.setValue(int(round(stamp.opacity * 100)))
            self.reason.setText(stamp.reason)
            self.logo_path.setText(stamp.logo_path)
            self.logo_scale.setValue(int(round(stamp.logo_scale * 100)))
            self.custom_text.setPlainText(stamp.custom_text)
            self.auto_place.setChecked(stamp.auto_place)
            self.include_owner.setChecked(stamp.include_owner)
            self.include_organization.setChecked(stamp.include_organization)
            self.include_position.setChecked(stamp.include_position)
            self.include_inn.setChecked(stamp.include_inn)
            self.include_snils.setChecked(stamp.include_snils)
            self.include_issuer.setChecked(stamp.include_issuer)
            self.include_serial.setChecked(stamp.include_serial)
            self.include_thumbprint.setChecked(stamp.include_thumbprint)
            self.include_reason.setChecked(stamp.include_reason)
            self.include_date.setChecked(stamp.include_date)
            self.include_time.setChecked(stamp.include_time)
            self.include_signing_date_time.setChecked(stamp.include_signing_date_time)
            self.include_custom_text.setChecked(stamp.include_custom_text)
        finally:
            self._loading = False
        self.refresh_preview()

    def collect_stamp(self) -> StampSettings:
        stamp = StampSettings(
            template_name=self.profile_combo.currentData(),
            size_mode="custom" if self.profile_combo.currentData() == "custom" else self.profile_combo.currentData().replace("gost-", ""),
            page_mode=self.page_mode.currentData(),
            specific_page=self.specific_page.value(),
            position=self.position.currentData(),
            auto_place=self.auto_place.isChecked(),
            x=self.x.value(),
            y=self.y.value(),
            width_mm=self.width_mm.value(),
            height_mm=self.height_mm.value(),
            opacity=self.opacity.value() / 100.0,
            font_size=self.font_size.value(),
            min_font_size=self.min_font_size.value(),
            reason=self.reason.text().strip() or StampSettings().reason,
            include_owner=self.include_owner.isChecked(),
            include_organization=self.include_organization.isChecked(),
            include_position=self.include_position.isChecked(),
            include_inn=self.include_inn.isChecked(),
            include_snils=self.include_snils.isChecked(),
            include_issuer=self.include_issuer.isChecked(),
            include_serial=self.include_serial.isChecked(),
            include_thumbprint=self.include_thumbprint.isChecked(),
            include_reason=self.include_reason.isChecked(),
            include_date=self.include_date.isChecked(),
            include_time=self.include_time.isChecked(),
            include_signing_date_time=self.include_signing_date_time.isChecked(),
            include_custom_text=self.include_custom_text.isChecked(),
            custom_text=self.custom_text.toPlainText(),
            logo_path=self.logo_path.text(),
            logo_scale=self.logo_scale.value() / 100.0,
        )
        stamp.name = dict(PROFILE_ITEMS).get(stamp.template_name, "Custom")
        return stamp.normalize()

    def refresh_preview(self) -> None:
        if self._loading:
            return
        stamp = self.collect_stamp()
        layout = validate_stamp_layout(stamp)
        self.warning.setText("\n".join(layout.errors + layout.warnings))
        self.preview.set_stamp(stamp)

    def apply_selected_profile(self) -> None:
        if self._loading:
            return
        profile_id = self.profile_combo.currentData()
        if profile_id == "custom":
            custom = self.collect_stamp()
            custom.template_name = "custom"
            custom.size_mode = "custom"
            self.load_stamp(custom.normalize())
            return
        preset = builtin_stamp_settings()[profile_id].clone()
        preset.reason = self.reason.text().strip() or preset.reason
        self.load_stamp(preset)

    def reset_position(self) -> None:
        self.position.setCurrentIndex(self.position.findData("bottom-right"))
        self.x.setValue(36)
        self.y.setValue(36)
        self.refresh_preview()

    def choose_logo(self) -> None:
        file, _ = QFileDialog.getOpenFileName(self, "Логотип", "", "Images (*.png *.jpg *.jpeg)")
        if file:
            self.logo_path.setText(file)
            self.refresh_preview()

    def clear_logo(self) -> None:
        self.logo_path.clear()
        self.refresh_preview()

    def load_profile_dialog(self) -> None:
        file, _ = QFileDialog.getOpenFileName(self, "Профиль штампа", "", "JSON (*.json)")
        if not file:
            return
        self.load_stamp(load_stamp_profile(Path(file)))

    def save_profile_dialog(self) -> None:
        file, _ = QFileDialog.getSaveFileName(self, "Сохранить профиль", "stamp-profile.json", "JSON (*.json)")
        if not file:
            return
        save_stamp_profile(Path(file), self.collect_stamp())

    def on_preview_stamp_moved(self, x: float, y: float) -> None:
        self.position.setCurrentIndex(self.position.findData("custom"))
        self.x.setValue(x)
        self.y.setValue(y)
        self.refresh_preview()


class VerificationDialog(QDialog):
    def __init__(self, files: list[str] | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Проверка подписи")
        self.resize(900, 620)
        self.worker: VerificationThread | None = None
        self.reports: list[VerificationReport] = []
        self._build_ui()
        for file in files or []:
            self.add_file(file)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.file_list.setAcceptDrops(True)
        layout.addWidget(self.file_list, stretch=2)

        buttons = QHBoxLayout()
        for text, handler in (
            ("Добавить", self.select_files),
            ("Убрать", self.remove_selected),
            ("Очистить", self.clear_files),
            ("Проверить", self.verify_files),
            ("Копировать отчет", self.copy_report),
            ("Экспорт TXT", lambda: self.save_report("txt")),
            ("Экспорт HTML", lambda: self.save_report("html")),
        ):
            button = QPushButton(text)
            button.clicked.connect(handler)
            buttons.addWidget(button)
        layout.addLayout(buttons)

        self.report = QPlainTextEdit()
        self.report.setReadOnly(True)
        layout.addWidget(self.report, stretch=4)

    def select_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, "Проверить подпись", "", "PDF/SIG/P7S (*.pdf *.sig *.p7s)")
        for file in files:
            self.add_file(file)

    def add_file(self, file: str) -> None:
        if not file.lower().endswith((".pdf", ".sig", ".p7s")):
            return
        if not self.file_list.findItems(file, Qt.MatchFlag.MatchExactly):
            self.file_list.addItem(file)

    def remove_selected(self) -> None:
        for item in self.file_list.selectedItems():
            self.file_list.takeItem(self.file_list.row(item))

    def clear_files(self) -> None:
        self.file_list.clear()
        self.report.clear()
        self.reports = []

    def verify_files(self) -> None:
        files = [Path(self.file_list.item(i).text()) for i in range(self.file_list.count())]
        if not files:
            QMessageBox.information(self, "PDF Signer Nix", "Добавьте файлы для проверки.")
            return
        self.worker = VerificationThread(files)
        self.worker.finished_ok.connect(self.verification_done)
        self.worker.failed.connect(self.verification_failed)
        self.worker.start()

    def verification_done(self, reports: list[VerificationReport]) -> None:
        self.reports = reports
        blocks = [report_to_text(report) for report in reports]
        self.report.setPlainText(("\n" + "-" * 72 + "\n").join(blocks))

    def verification_failed(self, message: str) -> None:
        self.report.setPlainText(message)

    def copy_report(self) -> None:
        if self.report.toPlainText().strip():
            QApplication.clipboard().setText(self.report.toPlainText())

    def save_report(self, fmt: str) -> None:
        if not self.reports:
            return
        file, _ = QFileDialog.getSaveFileName(
            self,
            "Экспорт отчета",
            f"verification-report.{fmt}",
            "HTML (*.html)" if fmt == "html" else "Text (*.txt)",
        )
        if not file:
            return
        target = Path(file)
        if fmt == "html":
            html_body = "\n<hr>\n".join(report_to_html(report) for report in self.reports)
            target.write_text(html_body, encoding="utf-8")
        else:
            text_body = ("\n" + "-" * 72 + "\n").join(report_to_text(report) for report in self.reports)
            target.write_text(text_body, encoding="utf-8")


class DiagnosticsDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Диагностика")
        self.resize(820, 560)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        buttons = QHBoxLayout()
        for text, handler in (
            ("Обновить", self.run_diagnostics),
            ("Копировать", self.copy_report),
            ("Сохранить", self.save_report),
            ("Открыть логи", self.open_logs_dir),
        ):
            button = QPushButton(text)
            button.clicked.connect(handler)
            buttons.addWidget(button)
        layout.addLayout(buttons)

        self.report = QPlainTextEdit()
        self.report.setReadOnly(True)
        layout.addWidget(self.report, stretch=1)
        self.run_diagnostics()

    def run_diagnostics(self) -> None:
        self.report.setPlainText(format_diagnostics_report())

    def copy_report(self) -> None:
        QApplication.clipboard().setText(self.report.toPlainText())

    def save_report(self) -> None:
        file, _ = QFileDialog.getSaveFileName(self, "Сохранить отчет", "pdf-signer-nix-diagnostics.txt", "Text (*.txt)")
        if file:
            Path(file).write_text(self.report.toPlainText(), encoding="utf-8")

    def open_logs_dir(self) -> None:
        directory = log_dir()
        directory.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(directory)))


class AboutDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("О приложении")
        self.setFixedSize(460, 250)
        self.worker: UpdateCheckThread | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        title = QLabel("PDF Signer Nix")
        title_font = title.font()
        title_font.setBold(True)
        title_font.setPointSize(title_font.pointSize() + 2)
        title.setFont(title_font)
        layout.addWidget(title)
        layout.addWidget(QLabel(f"Версия: {get_current_version_text()}"))
        layout.addWidget(QLabel("Copyright (c) 2026 shurshick"))

        project_link = QLabel('<a href="https://github.com/shurshick/pdf-signer-nix">https://github.com/shurshick/pdf-signer-nix</a>')
        project_link.setOpenExternalLinks(True)
        layout.addWidget(project_link)

        self.update_button = QPushButton("Проверить обновления")
        self.update_button.clicked.connect(self.check_updates)
        layout.addWidget(self.update_button)

        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status, stretch=1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    def check_updates(self) -> None:
        self.update_button.setEnabled(False)
        self.status.setText("Проверяю релизы на GitHub...")
        self.worker = UpdateCheckThread()
        self.worker.finished_ok.connect(self.update_check_done)
        self.worker.failed.connect(self.update_check_failed)
        self.worker.start()

    def update_check_done(self, release: ReleaseInfo) -> None:
        self.update_button.setEnabled(True)
        if is_newer_than_current(release.tag_name):
            self.status.setText(f"Доступно обновление: {release.tag_name}")
            answer = QMessageBox.question(
                self,
                "Обновление",
                f"Найден новый релиз {release.tag_name}. Открыть страницу релиза?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if answer == QMessageBox.StandardButton.Yes:
                QDesktopServices.openUrl(QUrl(release.url))
        else:
            self.status.setText("Новых релизов нет.")

    def update_check_failed(self, message: str) -> None:
        self.update_button.setEnabled(True)
        self.status.setText(f"Не удалось проверить обновления: {message}")


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.settings = load_settings()
        self.stamp_settings = stamp_from_payload(self.settings.get("stamp", {}))
        self.certificates: list[Certificate] = []
        self.worker: SigningThread | None = None
        self.setWindowTitle("PDF Signer Nix")
        self.apply_window_icon()
        self.resize(1120, 820)
        self._build_ui()
        self._load_settings_to_controls()
        self.refresh_certificates()

    def apply_window_icon(self) -> None:
        for path in (asset_path("pdf-signer-nix.png"), installed_icon_path()):
            if path.exists():
                self.setWindowIcon(QIcon(str(path)))
                return

    def _build_ui(self) -> None:
        root = QWidget()
        layout = QVBoxLayout(root)
        self.setCentralWidget(root)

        layout.addWidget(QLabel("PDF-файлы"))
        self.pdf_list = PdfListWidget()
        self.pdf_list.itemSelectionChanged.connect(self.update_file_summary)
        self.pdf_list.verification_files_dropped.connect(self.open_verification_dialog)
        layout.addWidget(self.pdf_list, stretch=4)
        self.file_summary = QLabel()
        layout.addWidget(self.file_summary)

        file_buttons = QHBoxLayout()
        for text, handler in (
            ("Добавить PDF", self.add_pdfs),
            ("Убрать", self.remove_selected_pdfs),
            ("Очистить", self.clear_pdfs),
            ("Редактор штампа", self.open_stamp_editor),
        ):
            button = QPushButton(text)
            button.clicked.connect(handler)
            file_buttons.addWidget(button)
        layout.addLayout(file_buttons)

        layout.addWidget(QLabel("Сертификаты"))
        self.cert_table = QTableWidget(0, 6)
        self.cert_table.setHorizontalHeaderLabels(["Владелец", "Организация", "Срок", "Ключ", "Статус", "SHA1"])
        self.cert_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.cert_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.cert_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.cert_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.cert_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.cert_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.cert_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.cert_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.cert_table, stretch=2)
        refresh = QPushButton("Обновить сертификаты")
        refresh.clicked.connect(self.refresh_certificates)
        layout.addWidget(refresh)

        options = QGridLayout()
        self.output_dir = QLineEdit()
        browse = QPushButton("Выбрать")
        browse.clicked.connect(self.choose_output_dir)
        self.reason = QLineEdit()
        self.reason.textChanged.connect(self.update_reason)
        self.create_detached = QCheckBox("Создать открепленную подпись .sig")
        self.detached_only = QCheckBox("Только .sig, без встроенной подписи PDF")
        self.verify_after = QCheckBox("Проверить подпись после создания")
        self.save_next = QCheckBox("Сохранять рядом с исходным PDF")

        options.addWidget(QLabel("Папка результата"), 0, 0)
        options.addWidget(self.output_dir, 0, 1)
        options.addWidget(browse, 0, 2)
        options.addWidget(QLabel("Причина"), 1, 0)
        options.addWidget(self.reason, 1, 1, 1, 2)
        options.addWidget(self.create_detached, 2, 1, 1, 2)
        options.addWidget(self.detached_only, 3, 1, 1, 2)
        options.addWidget(self.verify_after, 4, 1, 1, 2)
        options.addWidget(self.save_next, 5, 1, 1, 2)
        layout.addLayout(options)

        self.progress = QProgressBar()
        self.progress.setFixedHeight(8)
        self.progress.setTextVisible(False)
        layout.addWidget(self.progress)

        action_buttons = QHBoxLayout()
        for text, handler in (
            ("Подписать", self.sign),
            ("Проверка подписи", lambda: self.open_verification_dialog()),
            ("Диагностика", self.show_diagnostics),
            ("Экспорт настроек", self.export_settings_dialog),
            ("Импорт настроек", self.import_settings_dialog),
            ("О приложении", self.about),
        ):
            button = QPushButton(text)
            button.clicked.connect(handler)
            action_buttons.addWidget(button)
        layout.addLayout(action_buttons)

        self.report = QPlainTextEdit()
        self.report.setReadOnly(True)
        layout.addWidget(self.report, stretch=3)

        copy_action = QAction("Копировать отчет", self)
        copy_action.triggered.connect(lambda: QApplication.clipboard().setText(self.report.toPlainText()))
        self.menuBar().addAction(copy_action)
        self.update_file_summary()

    def _load_settings_to_controls(self) -> None:
        self.output_dir.setText(self.settings.get("last_output_dir", ""))
        self.reason.setText(self.stamp_settings.reason)
        self.create_detached.setChecked(bool(self.settings.get("create_detached_sig", False)))
        self.detached_only.setChecked(bool(self.settings.get("detached_only", False)))
        self.verify_after.setChecked(bool(self.settings.get("verify_after_signing", False)))
        self.save_next.setChecked(bool(self.settings.get("save_next_to_source", True)))

    def collect_settings(self) -> dict:
        settings = default_settings()
        settings["last_output_dir"] = self.output_dir.text()
        settings["save_next_to_source"] = self.save_next.isChecked()
        settings["create_detached_sig"] = self.create_detached.isChecked()
        settings["detached_only"] = self.detached_only.isChecked()
        settings["verify_after_signing"] = self.verify_after.isChecked()
        self.stamp_settings.reason = self.reason.text().strip() or self.stamp_settings.reason
        settings["stamp"] = stamp_to_payload(self.stamp_settings)
        return settings

    def add_pdfs(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, "Добавить PDF", "", "PDF (*.pdf)")
        for file in files:
            if not self.pdf_list.findItems(file, Qt.MatchFlag.MatchExactly):
                self.pdf_list.addItem(file)
        self.update_file_summary()

    def remove_selected_pdfs(self) -> None:
        for item in self.pdf_list.selectedItems():
            self.pdf_list.takeItem(self.pdf_list.row(item))
        self.update_file_summary()

    def clear_pdfs(self) -> None:
        self.pdf_list.clear()
        self.update_file_summary()

    def update_file_summary(self) -> None:
        total = 0
        for index in range(self.pdf_list.count()):
            file = Path(self.pdf_list.item(index).text())
            if file.exists():
                total += file.stat().st_size
        self.file_summary.setText(f"Файлов: {self.pdf_list.count()} | Размер: {format_bytes(total)}")

    def choose_output_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Папка результата")
        if directory:
            self.output_dir.setText(directory)

    def update_reason(self) -> None:
        self.stamp_settings.reason = self.reason.text().strip() or self.stamp_settings.reason

    def open_stamp_editor(self) -> None:
        dialog = StampEditorDialog(self.stamp_settings, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.stamp_settings = dialog.stamp
            self.reason.setText(self.stamp_settings.reason)
            self.settings = self.collect_settings()
            save_settings(self.settings)

    def refresh_certificates(self) -> None:
        self.cert_table.setRowCount(0)
        try:
            self.certificates = list_certificates()
        except CryptoProError as exc:
            self.report.setPlainText(str(exc))
            self.certificates = []
            return
        for cert in self.certificates:
            row = self.cert_table.rowCount()
            self.cert_table.insertRow(row)
            values = [
                cert.owner,
                cert.organization,
                cert.not_after,
                "Есть" if cert.has_private_key else "Нет",
                certificate_status(cert),
                cert.thumbprint,
            ]
            for col, value in enumerate(values):
                self.cert_table.setItem(row, col, QTableWidgetItem(value))

    def selected_certificate(self) -> Certificate | None:
        row = self.cert_table.currentRow()
        if row < 0 or row >= len(self.certificates):
            return None
        return self.certificates[row]

    def sign(self) -> None:
        cert = self.selected_certificate()
        if cert is None:
            QMessageBox.information(self, "PDF Signer Nix", "Выберите сертификат.")
            return
        pdfs = [Path(self.pdf_list.item(i).text()) for i in range(self.pdf_list.count())]
        if not pdfs:
            QMessageBox.information(self, "PDF Signer Nix", "Добавьте PDF.")
            return
        self.settings = self.collect_settings()
        save_settings(self.settings)
        self.stamp_settings = stamp_from_payload(self.settings["stamp"])
        layout = validate_stamp_layout(self.stamp_settings, cert)
        if not layout.is_valid:
            QMessageBox.warning(self, "Штамп", "\n".join(layout.errors))
            return
        if layout.warnings:
            proceed = QMessageBox.question(
                self,
                "Штамп",
                "\n".join(layout.warnings) + "\n\nПродолжить?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if proceed != QMessageBox.StandardButton.Yes:
                return
        job = SigningJob(
            pdf_paths=pdfs,
            output_dir=Path(self.output_dir.text() or Path.home()),
            certificate=cert,
            stamp=self.stamp_settings.clone(),
            detached_only=self.detached_only.isChecked(),
            create_detached_sig=self.create_detached.isChecked(),
            save_next_to_source=self.save_next.isChecked(),
            verify_after_signing=self.verify_after.isChecked(),
        )
        self.progress.setRange(0, 0)
        self.worker = SigningThread(job)
        self.worker.finished_ok.connect(self.signing_done)
        self.worker.failed.connect(self.signing_failed)
        self.worker.start()

    def signing_done(self, results: list) -> None:
        self.progress.setRange(0, 100)
        self.progress.setValue(100)
        lines: list[str] = []
        for result in results:
            lines.append(f"Источник: {result['source_pdf']}")
            lines.append(f"PDF: {result['output_pdf']}")
            if result.get("signature_path"):
                lines.append(f"SIG: {result['signature_path']}")
            if result.get("verified") is not None:
                lines.append(f"Проверка: {'OK' if result['verified'] else 'Ошибка'}")
            if result.get("message"):
                lines.append(f"Сообщение: {result['message']}")
            lines.append("")
        self.report.setPlainText("\n".join(lines).strip())

    def signing_failed(self, message: str) -> None:
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.report.setPlainText(message)

    def open_verification_dialog(self, files: list[str] | None = None) -> None:
        dialog = VerificationDialog(files, self)
        dialog.exec()

    def show_diagnostics(self) -> None:
        dialog = DiagnosticsDialog(self)
        dialog.exec()

    def export_settings_dialog(self) -> None:
        file, _ = QFileDialog.getSaveFileName(self, "Экспорт настроек", "pdf-signer-nix-settings.json", "JSON (*.json)")
        if not file:
            return
        self.settings = self.collect_settings()
        export_settings(Path(file), self.settings)
        self.report.setPlainText(f"Настройки экспортированы: {file}")

    def import_settings_dialog(self) -> None:
        file, _ = QFileDialog.getOpenFileName(self, "Импорт настроек", "", "JSON (*.json)")
        if not file:
            return
        try:
            self.settings = import_settings(Path(file), self.collect_settings())
        except Exception as exc:
            QMessageBox.warning(self, "Ошибка", f"Не удалось импортировать настройки.\n{exc}")
            return
        save_settings(self.settings)
        self.stamp_settings = stamp_from_payload(self.settings.get("stamp", {}))
        self._load_settings_to_controls()
        self.report.setPlainText("Настройки импортированы.")

    def about(self) -> None:
        dialog = AboutDialog(self)
        dialog.exec()


def combo(items: list[tuple[str, str]]) -> QComboBox:
    box = QComboBox()
    for value, text in items:
        box.addItem(text, value)
    return box


def set_combo(box: QComboBox, value: str) -> None:
    index = box.findData(value)
    if index >= 0:
        box.setCurrentIndex(index)


def spin(minimum: int, maximum: int, value: int) -> QSpinBox:
    widget = QSpinBox()
    widget.setRange(minimum, maximum)
    widget.setValue(value)
    return widget


def dspin(minimum: float, maximum: float, value: float, step: float) -> QDoubleSpinBox:
    widget = QDoubleSpinBox()
    widget.setRange(minimum, maximum)
    widget.setDecimals(1)
    widget.setSingleStep(step)
    widget.setValue(value)
    return widget


def add_form_row(layout: QGridLayout, row: int, left_label: str, left_widget: QWidget, right_label: str, right_widget: QWidget) -> None:
    layout.addWidget(QLabel(left_label), row, 0)
    layout.addWidget(left_widget, row, 1)
    layout.addWidget(QLabel(right_label), row, 2)
    layout.addWidget(right_widget, row, 3)


def rect_for_preview(stamp: StampSettings, page_rect, width: float, height: float):
    margin = stamp.margin
    page_right = page_rect.x() + page_rect.width()
    page_bottom = page_rect.y() + page_rect.height()
    if stamp.position == "top-left":
        x = page_rect.left() + margin
        y = page_rect.top() + margin
    elif stamp.position == "top-right":
        x = page_right - width - margin
        y = page_rect.top() + margin
    elif stamp.position == "bottom-left":
        x = page_rect.left() + margin
        y = page_bottom - height - margin
    elif stamp.position == "custom":
        x = page_rect.left() + stamp.x
        y = page_bottom - height - stamp.y
    else:
        x = page_right - width - margin
        y = page_bottom - height - margin
    return page_rect.__class__(int(x), int(y), int(width), int(height))


def certificate_status(cert: Certificate) -> str:
    if cert.has_private_key is False:
        return "Нет закрытого ключа"
    return "Готов"


def format_bytes(value: int) -> str:
    if value >= 1024**3:
        return f"{value / 1024**3:.2f} ГБ"
    if value >= 1024**2:
        return f"{value / 1024**2:.2f} МБ"
    if value >= 1024:
        return f"{value / 1024:.2f} КБ"
    return f"{value} Б"


def run_gui() -> int:
    app = QApplication([])
    app.setApplicationName("PDF Signer Nix")
    for path in (asset_path("pdf-signer-nix.png"), installed_icon_path()):
        if path.exists():
            app.setWindowIcon(QIcon(str(path)))
            break
    window = MainWindow()
    window.show()
    return app.exec()
