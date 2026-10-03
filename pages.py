from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    ComboBox,
    FluentIcon,
    IconWidget,
    MessageBox,
    PrimaryPushButton,
    ProgressBar,
    SearchLineEdit,
    SimpleCardWidget,
    SmoothScrollArea,
    StrongBodyLabel,
    SubtitleLabel,
    TitleLabel,
    isDarkTheme,
)

from models import Priority, Status, Task, TaskStore
from task_card import (
    TASK_MIME_TYPE,
    TaskCard,
    format_due,
    muted_color,
    overdue_colors,
    status_colors,
)
from task_dialog import TaskDialog


class TaskDropContainer(QWidget):
    """ Container that accepts task drag-and-drop to reorder tasks. """

    dropOccurred = Signal(str, int)
    INDICATOR_HEIGHT = 3

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._indicator = QWidget(self)
        self._indicator.setObjectName("dropIndicator")
        self._indicator.setFixedHeight(self.INDICATOR_HEIGHT)
        self._indicator.setStyleSheet(
            "#dropIndicator { background-color: #0078D4; border-radius: 2px; }"
        )
        self._indicator.hide()

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(TASK_MIME_TYPE):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(TASK_MIME_TYPE):
            self._show_indicator(self._index_at(event.position().y()))
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self._hide_indicator()
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        self._hide_indicator()
        if not event.mimeData().hasFormat(TASK_MIME_TYPE):
            return
        data = event.mimeData().data(TASK_MIME_TYPE)
        task_id = bytes(data).decode("utf-8")
        index = self._index_at(event.position().y())
        self.dropOccurred.emit(task_id, index)
        event.acceptProposedAction()

    def _index_at(self, y: float) -> int:
        layout = self.layout()
        if layout is None:
            return 0
        index = 0
        for i in range(layout.count()):
            item = layout.itemAt(i)
            widget = item.widget()
            if widget is None:
                continue
            if y < widget.geometry().center().y():
                return index
            index += 1
        return index

    def _cards(self):
        layout = self.layout()
        if layout is None:
            return []
        cards = []
        for i in range(layout.count()):
            widget = layout.itemAt(i).widget()
            if widget is not None:
                cards.append(widget)
        return cards

    def _indicator_y(self, index: int) -> int:
        cards = self._cards()
        if not cards:
            return 0
        if index <= 0:
            return max(0, cards[0].geometry().top() - self.INDICATOR_HEIGHT)
        if index >= len(cards):
            return cards[-1].geometry().bottom()
        prev_bottom = cards[index - 1].geometry().bottom()
        next_top = cards[index].geometry().top()
        return (prev_bottom + next_top) // 2

    def _show_indicator(self, index: int):
        y = self._indicator_y(index)
        indicator = self._indicator
        if indicator.isVisible() and indicator.y() == y:
            return
        indicator.setGeometry(0, y, self.width(), indicator.height())
        indicator.show()
        indicator.raise_()

    def _hide_indicator(self):
        self._indicator.hide()


class UpcomingRow(SimpleCardWidget):
    clicked = Signal(Task)

    def __init__(self, task: Task, parent=None):
        super().__init__(parent)
        self.task = task
        dark = isDarkTheme()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(12)

        icon = IconWidget(self)
        icon.setFixedSize(20, 20)
        icon.setIcon(FluentIcon.CALENDAR.icon())

        title = QLabel(task.title)
        title.setWordWrap(True)

        bg, fg = status_colors(task.status, dark)
        statusPill = QLabel(task.status.label)
        statusPill.setObjectName("pillLabel")
        statusPill.setFixedHeight(20)
        statusPill.setStyleSheet(
            f"#pillLabel {{ background-color: {bg}; color: {fg};"
            f" border-radius: 10px; padding: 0 10px; font-weight: 600; }}"
        )

        due = CaptionLabel(format_due(task.due_date_obj))
        dueColor = overdue_colors(dark)[1] if task.is_overdue else muted_color(dark)
        due.setStyleSheet(f"color: {dueColor}; font-weight: 600;")

        layout.addWidget(icon)
        layout.addWidget(title, 1)
        layout.addWidget(statusPill)
        layout.addWidget(due)

    def mouseReleaseEvent(self, event):
        self.clicked.emit(self.task)
        super().mouseReleaseEvent(event)


class DashboardPage(QWidget):
    def __init__(self, store: TaskStore, parent=None):
        super().__init__(parent)
        self.store = store
        self.store.changed.connect(self.refresh)
        self._init_ui()
        self.refresh()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 20, 28, 20)
        layout.setSpacing(16)

        layout.addWidget(TitleLabel("Tableau de bord"))
        layout.addWidget(SubtitleLabel("Aperçu général de vos tâches"))

        statsRow = QHBoxLayout()
        statsRow.setSpacing(12)
        statsRow.addWidget(self._stat_card(FluentIcon.DOCUMENT, "total", "Total", "#0078D4"))
        statsRow.addWidget(self._stat_card(FluentIcon.PLAY, "inProgress", "En cours", "#CA5010"))
        statsRow.addWidget(self._stat_card(FluentIcon.STOP_WATCH, "overdue", "En retard", "#D13438"))
        statsRow.addWidget(self._stat_card(FluentIcon.COMPLETED, "done", "Terminées", "#107C10"))
        layout.addLayout(statsRow)

        progressCard = SimpleCardWidget(self)
        progressLayout = QHBoxLayout(progressCard)
        progressLayout.setContentsMargins(20, 16, 20, 16)
        progressLayout.setSpacing(16)
        progressLayout.addWidget(BodyLabel("Taux d'achèvement"))
        self.progressBar = ProgressBar(progressCard)
        self.progressBar.setRange(0, 100)
        self.progressValue = BodyLabel("0%")
        progressLayout.addWidget(self.progressBar, 1)
        progressLayout.addWidget(self.progressValue)
        layout.addWidget(progressCard)

        layout.addWidget(StrongBodyLabel("Prochaines échéances"))
        self.upcomingLayout = QVBoxLayout()
        self.upcomingLayout.setSpacing(8)
        layout.addLayout(self.upcomingLayout)
        layout.addStretch(1)

    def _stat_card(self, icon, attr: str, label: str, color: str) -> SimpleCardWidget:
        card = SimpleCardWidget(self)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)
        iconWidget = IconWidget(card)
        iconWidget.setFixedSize(40, 40)
        iconWidget.setIcon(icon.icon(color=QColor(color)))
        valueLabel = TitleLabel("0")
        valueLabel.setObjectName(f"{attr}Value")
        nameLabel = BodyLabel(label)
        column = QVBoxLayout()
        column.addWidget(valueLabel)
        column.addWidget(nameLabel)
        layout.addWidget(iconWidget)
        layout.addLayout(column, 1)
        setattr(self, f"{attr}Value", valueLabel)
        return card

    def refresh(self):
        tasks = self.store.tasks
        total = len(tasks)
        inProgress = sum(1 for t in tasks if t.status == Status.IN_PROGRESS)
        overdue = sum(1 for t in tasks if t.is_overdue)
        done = sum(1 for t in tasks if t.status == Status.DONE)

        self.totalValue.setText(str(total))
        self.inProgressValue.setText(str(inProgress))
        self.overdueValue.setText(str(overdue))
        self.doneValue.setText(str(done))

        rate = int(done / total * 100) if total else 0
        self.progressBar.setValue(rate)
        self.progressValue.setText(f"{rate} %")

        self._clear_layout(self.upcomingLayout)
        upcoming = [t for t in tasks if t.status != Status.DONE and t.due_date_obj]
        upcoming.sort(key=lambda t: (t.due_date, -t.priority.weight))
        for task in upcoming[:5]:
            row = UpcomingRow(task, self)
            row.clicked.connect(self._edit_task)
            self.upcomingLayout.addWidget(row)
        if not upcoming:
            hint = BodyLabel("Aucune échéance à venir.")
            self.upcomingLayout.addWidget(hint)

    def _clear_layout(self, layout: QVBoxLayout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                ani = getattr(widget, "backgroundColorAni", None)
                if ani is not None:
                    ani.stop()
                widget.deleteLater()
            elif item.layout() is not None:
                self._clear_layout(item.layout())

    def _edit_task(self, task: Task):
        dialog = TaskDialog(task, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.store.save()


class TaskListPage(QWidget):
    def __init__(
        self,
        store: TaskStore,
        title: str,
        subtitle: str,
        status_filter: Status | None = None,
        overdue_only: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self.store = store
        self.status_filter = status_filter
        self.overdue_only = overdue_only
        self.search_text = ""
        self.store.changed.connect(self.refresh)
        self._init_ui(title, subtitle)
        self.refresh()

    def _init_ui(self, title: str, subtitle: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 20, 28, 20)
        layout.setSpacing(14)

        layout.addWidget(TitleLabel(title))
        layout.addWidget(SubtitleLabel(subtitle))

        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)
        self.searchEdit = SearchLineEdit(self)
        self.searchEdit.setPlaceholderText("Rechercher une tâche...")
        self.searchEdit.setFixedWidth(300)
        self.searchEdit.textChanged.connect(self._on_search)

        self.sortCombo = ComboBox(self)
        self.sortCombo.addItem("Manuel", userData="manual")
        self.sortCombo.addItem("Échéance", userData="due")
        self.sortCombo.addItem("Priorité", userData="priority")
        self.sortCombo.addItem("Date de création", userData="created")
        self.sortCombo.currentIndexChanged.connect(lambda _: self.refresh())

        self.addButton = PrimaryPushButton("Nouvelle tâche", self)
        self.addButton.setIcon(FluentIcon.ADD)
        self.addButton.clicked.connect(self._add_task)

        toolbar.addWidget(self.searchEdit)
        toolbar.addWidget(self.sortCombo)
        toolbar.addStretch(1)
        toolbar.addWidget(self.addButton)
        layout.addLayout(toolbar)

        self.scrollArea = SmoothScrollArea(self)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.cardsContainer = TaskDropContainer()
        self.cardsLayout = QVBoxLayout(self.cardsContainer)
        self.cardsLayout.setContentsMargins(2, 2, 2, 2)
        self.cardsLayout.setSpacing(10)
        self.cardsLayout.addStretch(1)
        self.cardsContainer.dropOccurred.connect(self._on_drop_task)
        self.scrollArea.setWidget(self.cardsContainer)
        self.scrollArea.setStyleSheet(
            "QScrollArea{border: none; background: transparent}"
            "QScrollArea > QWidget > QWidget{background: transparent}"
        )
        self.scrollArea.viewport().setAutoFillBackground(False)
        self.scrollArea.viewport().setStyleSheet("background: transparent")
        self.cardsContainer.setAutoFillBackground(False)
        self.cardsContainer.setStyleSheet("background: transparent")
        layout.addWidget(self.scrollArea, 1)

        self.emptyWidget = QWidget(self)
        emptyLayout = QVBoxLayout(self.emptyWidget)
        emptyIcon = IconWidget(self.emptyWidget)
        emptyIcon.setFixedSize(72, 72)
        emptyIcon.setIcon(FluentIcon.DOCUMENT.icon())
        emptyText = SubtitleLabel("Aucune tâche à afficher")
        emptyLayout.addStretch(1)
        emptyLayout.addWidget(emptyIcon, 0, Qt.AlignmentFlag.AlignHCenter)
        emptyLayout.addWidget(emptyText, 0, Qt.AlignmentFlag.AlignHCenter)
        emptyLayout.addStretch(1)
        layout.addWidget(self.emptyWidget, 1)

    def _on_search(self, text: str):
        self.search_text = text.strip().lower()
        self.refresh()

    def _on_drop_task(self, task_id: str, index: int):
        visible = self._visible_tasks()
        target = visible[index] if index < len(visible) else None
        target_id = target.id if target is not None else None
        # switch to manual order so the new position becomes visible
        idx = self.sortCombo.findData("manual")
        if idx >= 0:
            self.sortCombo.blockSignals(True)
            self.sortCombo.setCurrentIndex(idx)
            self.sortCombo.blockSignals(False)
        self.store.move(task_id, target_id)

    def refresh(self):
        self._clear_layout(self.cardsLayout)
        tasks = self._visible_tasks()
        for task in tasks:
            card = TaskCard(task, self)
            card.edited.connect(self._edit_task)
            card.deleted.connect(self._delete_task)
            card.statusChanged.connect(self._change_status)
            self.cardsLayout.addWidget(card)
        self.cardsLayout.addStretch(1)
        has_tasks = bool(tasks)
        self.scrollArea.setVisible(has_tasks)
        self.emptyWidget.setVisible(not has_tasks)

    def _visible_tasks(self):
        tasks = [task for task in self.store.tasks if self._match(task)]
        return self._sort(tasks)

    def _match(self, task: Task) -> bool:
        if self.overdue_only:
            if not task.is_overdue:
                return False
        elif self.status_filter is not None and task.status != self.status_filter:
            return False
        if self.search_text:
            haystack = f"{task.title} {task.description}".lower()
            if self.search_text not in haystack:
                return False
        return True

    def _sort(self, tasks):
        key = self.sortCombo.currentData()
        if key == "manual":
            return list(tasks)
        if key == "due":
            return sorted(
                tasks,
                key=lambda t: (t.due_date == "", t.due_date, -t.priority.weight),
            )
        if key == "priority":
            return sorted(
                tasks,
                key=lambda t: (-t.priority.weight, t.due_date == "", t.due_date),
            )
        return sorted(tasks, key=lambda t: t.created_at, reverse=True)

    def _add_task(self):
        dialog = TaskDialog(None, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.store.add(dialog.get_task())

    def _edit_task(self, task: Task):
        dialog = TaskDialog(task, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.store.save()

    def _delete_task(self, task_id: str):
        task = self.store.get(task_id)
        if task is None:
            return
        box = MessageBox(
            "Supprimer la tâche",
            f"Voulez-vous vraiment supprimer « {task.title} » ?",
            self,
        )
        box.yesButton.setText("Supprimer")
        box.cancelButton.setText("Annuler")
        if box.exec() == QDialog.DialogCode.Accepted:
            # defer the removal so it runs after the 'deleted' signal
            # emission and the confirmation dialog are fully done
            QTimer.singleShot(0, lambda: self.store.remove(task_id))

    def _change_status(self, task: Task, new_status: Status):
        task.status = new_status
        task.completed_at = (
            datetime.now().isoformat(timespec="seconds")
            if new_status == Status.DONE
            else ""
        )
        self.store.save()

    def _clear_layout(self, layout: QVBoxLayout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                ani = getattr(widget, "backgroundColorAni", None)
                if ani is not None:
                    ani.stop()
                widget.deleteLater()
            elif item.layout() is not None:
                self._clear_layout(item.layout())
