from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from PySide6.QtCore import QDate
from PySide6.QtWidgets import QCheckBox, QComboBox, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from qfluentwidgets import (
    BodyLabel,
    ComboBox,
    DateEdit,
    Dialog,
    LineEdit,
    PrimaryPushButton,
    TextEdit,
)

from models import Priority, Status, Task


class TaskForm(QWidget):
    def __init__(self, task: Optional[Task] = None, parent=None):
        super().__init__(parent)
        self.task = task
        self._init_ui()
        self._load_task()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        self.titleEdit = LineEdit(self)
        self.titleEdit.setPlaceholderText("Titre de la tâche")
        self.titleEdit.setClearButtonEnabled(True)

        self.descriptionEdit = TextEdit(self)
        self.descriptionEdit.setPlaceholderText("Description (optionnelle)")
        self.descriptionEdit.setMinimumHeight(110)

        self.statusCombo = ComboBox(self)
        for status in Status:
            self.statusCombo.addItem(status.label, userData=status)

        self.priorityCombo = ComboBox(self)
        for priority in Priority:
            self.priorityCombo.addItem(priority.label, userData=priority)

        self.noDueCheck = QCheckBox("Sans échéance", self)
        self.dueEdit = DateEdit(self)
        self.dueEdit.setDisplayFormat("dd/MM/yyyy")
        self.dueEdit.setCalendarPopup(True)
        self.dueEdit.setDate(QDate.currentDate())
        self.noDueCheck.toggled.connect(
            lambda checked: self.dueEdit.setEnabled(not checked)
        )

        dueRow = QHBoxLayout()
        dueRow.addWidget(self.noDueCheck)
        dueRow.addWidget(self.dueEdit, 1)

        self.errorLabel = BodyLabel(self)
        self.errorLabel.setStyleSheet("color: #D13438;")
        self.errorLabel.setVisible(False)

        form = QVBoxLayout()
        form.setSpacing(6)
        form.addWidget(BodyLabel("Titre *"))
        form.addWidget(self.titleEdit)
        form.addWidget(BodyLabel("Description"))
        form.addWidget(self.descriptionEdit)

        row = QHBoxLayout()
        statusCol = QVBoxLayout()
        statusCol.addWidget(BodyLabel("Statut"))
        statusCol.addWidget(self.statusCombo)
        priorityCol = QVBoxLayout()
        priorityCol.addWidget(BodyLabel("Priorité"))
        priorityCol.addWidget(self.priorityCombo)
        row.addLayout(statusCol, 1)
        row.addLayout(priorityCol, 1)
        form.addLayout(row)

        form.addWidget(BodyLabel("Échéance"))
        form.addLayout(dueRow)
        form.addWidget(self.errorLabel)

        layout.addLayout(form)
        layout.addStretch(1)

        self.titleEdit.textChanged.connect(self._clear_error)

    def _load_task(self):
        if self.task is None:
            self.noDueCheck.setChecked(False)
            return
        self.titleEdit.setText(self.task.title)
        self.descriptionEdit.setPlainText(self.task.description)
        self._set_current_data(self.statusCombo, self.task.status)
        self._set_current_data(self.priorityCombo, self.task.priority)
        due = self.task.due_date_obj
        if due is None:
            self.noDueCheck.setChecked(True)
        else:
            self.noDueCheck.setChecked(False)
            self.dueEdit.setDate(QDate(due.year, due.month, due.day))

    @staticmethod
    def _set_current_data(combo: ComboBox, data):
        for index in range(combo.count()):
            if combo.itemData(index) == data:
                combo.setCurrentIndex(index)
                return

    def _clear_error(self):
        self.errorLabel.setVisible(False)

    def validate(self) -> bool:
        if not self.titleEdit.text().strip():
            self.errorLabel.setText("Le titre est obligatoire.")
            self.errorLabel.setVisible(True)
            self.titleEdit.setFocus()
            return False
        return True

    def build_task(self) -> Task:
        if self.task is not None:
            task = self.task
        else:
            task = Task()
        task.title = self.titleEdit.text().strip()
        task.description = self.descriptionEdit.toPlainText().strip()
        task.status = self.statusCombo.currentData()
        task.priority = self.priorityCombo.currentData()
        if self.noDueCheck.isChecked():
            task.due_date = ""
        else:
            d = self.dueEdit.date()
            task.due_date = d.toString("yyyy-MM-dd")
        return task


class TaskDialog(Dialog):
    def __init__(self, task: Optional[Task] = None, parent=None):
        super().__init__(
            "Modifier la tâche" if task is not None else "Nouvelle tâche",
            "",
            parent,
        )
        self.textLayout.removeWidget(self.contentLabel)
        self.contentLabel.deleteLater()

        self.form = TaskForm(task, self)
        self.textLayout.addWidget(self.form, 1)

        self.yesButton.setText("Enregistrer")
        self.cancelButton.setText("Annuler")
        self.setFixedSize(560, 620)

        self.yesButton.clicked.disconnect()
        self.yesButton.clicked.connect(self._on_save)

    def _on_save(self):
        if not self.form.validate():
            return
        self.accept()

    def get_task(self) -> Task:
        return self.form.build_task()
