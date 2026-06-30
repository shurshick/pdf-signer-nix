from __future__ import annotations

import json
import logging
from dataclasses import asdict
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QPlainTextEdit,
    QSpinBox,
    QDoubleSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from . import __version__
from .crypto import CryptoProError, list_certificates, verify_signature
from .diagnostics import run_diagnostics
from .models import Certificate, SigningJob, StampSettings
from .settings import default_settings, export_settings, import_settings, load_settings, save_settings
from .workflow import run_signing_job

LOG = logging.getLogger(__name__)


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


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.settings = load_settings()
        self.certificates: list[Certificate] = []
        self.worker: SigningThread | None = None
        self.setWindowTitle("PDF Signer Nix")
        self.resize(1080, 760)
        self._build_ui()
        self._load_settings_to_controls()
        self.refresh_certificates()

    def _build_ui(self) -> None:
        root = QWidget()
        layout = QVBoxLayout(root)
        self.setCentralWidget(root)

        self.pdf_list = QListWidget()
        self.pdf_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        layout.addWidget(QLabel("PDF-файлы"))
        layout.addWidget(self.pdf_list, stretch=4)

        pdf_buttons = QHBoxLayout()
        for text, handler in (
            ("Добавить PDF", self.add_pdfs),
            ("Убрать", self.remove_selected_pdfs),
            ("Очистить", self.pdf_list.clear),
        ):
            button = QPushButton(text)
            button.clicked.connect(handler)
            pdf_buttons.addWidget(button)
        layout.addLayout(pdf_buttons)

        self.cert_table = QTableWidget(0, 5)
        self.cert_table.setHorizontalHeaderLabels(["Владелец", "Организация", "Срок", "Ключ", "SHA1"])
        self.cert_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.cert_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        layout.addWidget(QLabel("Сертификаты"))
        layout.addWidget(self.cert_table, stretch=2)
        refresh = QPushButton("Обновить сертификаты")
        refresh.clicked.connect(self.refresh_certificates)
        layout.addWidget(refresh)

        form = QGridLayout()
        self.output_dir = QLineEdit()
        browse = QPushButton("Выбрать")
        browse.clicked.connect(self.choose_output_dir)
        form.addWidget(QLabel("Папка результата"), 0, 0)
        form.addWidget(self.output_dir, 0, 1)
        form.addWidget(browse, 0, 2)

        self.reason = QLineEdit()
        form.addWidget(QLabel("Назначение"), 1, 0)
        form.addWidget(self.reason, 1, 1, 1, 2)

        self.page_mode = combo([("all", "Все страницы"), ("first", "Первая"), ("last", "Последняя"), ("specific", "Указанная")])
        self.position = combo([
            ("bottom-right", "Снизу справа"),
            ("bottom-left", "Снизу слева"),
            ("top-right", "Сверху справа"),
            ("top-left", "Сверху слева"),
            ("custom", "Свое"),
        ])
        self.width_mm = spin(60, 220, 90)
        self.height_mm = spin(20, 120, 35)
        self.opacity = dspin(0.1, 1.0, 0.82, 0.05)
        self.logo_path = QLineEdit()
        logo = QPushButton("Логотип")
        logo.clicked.connect(self.choose_logo)

        form.addWidget(QLabel("Страницы"), 2, 0)
        form.addWidget(self.page_mode, 2, 1)
        form.addWidget(QLabel("Положение"), 2, 2)
        form.addWidget(self.position, 2, 3)
        form.addWidget(QLabel("Ширина, мм"), 3, 0)
        form.addWidget(self.width_mm, 3, 1)
        form.addWidget(QLabel("Высота, мм"), 3, 2)
        form.addWidget(self.height_mm, 3, 3)
        form.addWidget(QLabel("Прозрачность"), 4, 0)
        form.addWidget(self.opacity, 4, 1)
        form.addWidget(self.logo_path, 4, 2)
        form.addWidget(logo, 4, 3)
        layout.addLayout(form)

        checks = QGridLayout()
        self.auto_place = QCheckBox("Автоматически подобрать место штампа")
        self.create_detached = QCheckBox("Создать открепленную подпись .sig")
        self.detached_only = QCheckBox("Только .sig, без встроенной подписи PDF")
        self.verify_after = QCheckBox("Проверить подпись после создания")
        self.save_next = QCheckBox("Сохранять рядом с исходным PDF")
        for index, check in enumerate([self.auto_place, self.create_detached, self.detached_only, self.verify_after, self.save_next]):
            checks.addWidget(check, index // 2, index % 2)
        layout.addLayout(checks)

        self.progress = QProgressBar()
        self.progress.setFixedHeight(8)
        self.progress.setTextVisible(False)
        layout.addWidget(self.progress)

        actions = QHBoxLayout()
        for text, handler in (
            ("Подписать", self.sign),
            ("Проверка подписи", self.verify_dialog),
            ("Диагностика", self.show_diagnostics),
            ("Экспорт настроек", self.export_settings_dialog),
            ("Импорт настроек", self.import_settings_dialog),
            ("О приложении", self.about),
        ):
            button = QPushButton(text)
            button.clicked.connect(handler)
            actions.addWidget(button)
        layout.addLayout(actions)

        self.report = QPlainTextEdit()
        self.report.setReadOnly(True)
        layout.addWidget(self.report, stretch=2)

        copy_action = QAction("Копировать отчет", self)
        copy_action.triggered.connect(lambda: QApplication.clipboard().setText(self.report.toPlainText()))
        self.menuBar().addAction(copy_action)

    def _load_settings_to_controls(self) -> None:
        stamp = self.settings.get("stamp", {})
        self.output_dir.setText(self.settings.get("last_output_dir", ""))
        self.reason.setText(stamp.get("reason", "Подписано в PDF Signer Nix"))
        set_combo(self.page_mode, stamp.get("page_mode", "all"))
        set_combo(self.position, stamp.get("position", "bottom-right"))
        self.width_mm.setValue(int(stamp.get("width_mm", 90)))
        self.height_mm.setValue(int(stamp.get("height_mm", 35)))
        self.opacity.setValue(float(stamp.get("opacity", 0.82)))
        self.logo_path.setText(stamp.get("logo_path", ""))
        self.auto_place.setChecked(bool(stamp.get("auto_place", True)))
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
        settings["stamp"].update(
            {
                "reason": self.reason.text(),
                "page_mode": self.page_mode.currentData(),
                "position": self.position.currentData(),
                "width_mm": self.width_mm.value(),
                "height_mm": self.height_mm.value(),
                "opacity": self.opacity.value(),
                "auto_place": self.auto_place.isChecked(),
                "logo_path": self.logo_path.text(),
            }
        )
        return settings

    def add_pdfs(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, "Добавить PDF", "", "PDF (*.pdf)")
        for file in files:
            if not self.pdf_list.findItems(file, Qt.MatchFlag.MatchExactly):
                self.pdf_list.addItem(file)

    def remove_selected_pdfs(self) -> None:
        for item in self.pdf_list.selectedItems():
            self.pdf_list.takeItem(self.pdf_list.row(item))

    def choose_output_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Папка результата")
        if directory:
            self.output_dir.setText(directory)

    def choose_logo(self) -> None:
        file, _ = QFileDialog.getOpenFileName(self, "Логотип", "", "Images (*.png *.jpg *.jpeg)")
        if file:
            self.logo_path.setText(file)

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
            values = [cert.owner, cert.organization, cert.not_after, "Есть" if cert.has_private_key else "", cert.thumbprint]
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
        stamp = StampSettings(**{k: v for k, v in self.settings["stamp"].items() if k in StampSettings.__dataclass_fields__})
        job = SigningJob(
            pdf_paths=pdfs,
            output_dir=Path(self.output_dir.text() or Path.home()),
            certificate=cert,
            stamp=stamp,
            detached_only=self.detached_only.isChecked(),
            create_detached_sig=self.create_detached.isChecked(),
            save_next_to_source=self.save_next.isChecked(),
            verify_after_signing=self.verify_after.isChecked(),
        )
        self.progress.setValue(10)
        self.worker = SigningThread(job)
        self.worker.finished_ok.connect(self.signing_done)
        self.worker.failed.connect(self.signing_failed)
        self.worker.start()

    def signing_done(self, results: list) -> None:
        self.progress.setValue(100)
        self.report.setPlainText(json.dumps(results, ensure_ascii=False, indent=2, default=str))

    def signing_failed(self, message: str) -> None:
        self.progress.setValue(0)
        self.report.setPlainText(message)

    def verify_dialog(self) -> None:
        target, _ = QFileDialog.getOpenFileName(self, "Проверить подпись", "", "PDF/SIG/P7S (*.pdf *.sig *.p7s)")
        if not target:
            return
        ok, text = verify_signature(Path(target))
        self.report.setPlainText(("OK\n" if ok else "ERROR\n") + text)

    def show_diagnostics(self) -> None:
        self.report.setPlainText("\n".join(f"{i.status}: {i.title}: {i.message}" for i in run_diagnostics()))

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
        self._load_settings_to_controls()
        self.report.setPlainText("Настройки импортированы.")

    def about(self) -> None:
        QMessageBox.about(self, "О приложении", f"PDF Signer Nix\nВерсия: {__version__}\nCopyright (c) 2026 shurshick")


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
    widget.setSingleStep(step)
    widget.setValue(value)
    return widget


def run_gui() -> int:
    app = QApplication([])
    app.setApplicationName("PDF Signer Nix")
    window = MainWindow()
    window.show()
    return app.exec()
