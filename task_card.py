from __future__ import annotations

from datetime import date, timedelta

from PySide6.QtCore import QMimeData, Qt, Signal
from PySide6.QtGui import QColor, QDrag, QFontMetrics, QPainter, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
)

from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    CardWidget,
    FluentIcon,
    IconWidget,
    PushButton,
    StrongBodyLabel,
    ToolButton,
    isDarkTheme,
)

from models import Priority, Status, Task

TASK_MIME_TYPE = "application/x-task-id"


def status_colors(status: Status, dark: bool):
    if status == Status.TODO:
        return ("#E4E7EB", "#4B5563") if not dark else ("#2D3139", "#9CA3AF")
    if status == Status.IN_PROGRESS:
        return ("#DCE9F9", "#0078D4") if not dark else ("#1B3A5C", "#4FA3E3")
    return ("#DFF0DD", "#107C10") if not dark else ("#1E3A24", "#6CCB5F")


def overdue_colors(dark: bool):
    return ("#FDE7E9", "#D13438") if not dark else ("#4A1F24", "#F4877A")


def priority_colors(priority: Priority, dark: bool) -> str:
    if priority == Priority.LOW:
        return "#8A94A6" if not dark else "#9CA3AF"
    if priority == Priority.MEDIUM:
        return "#CA5010" if not dark else "#F6A94F"
    return "#D13438" if not dark else "#F4877A"


def text_color(dark: bool) -> str:
    return "#E6E6E6" if dark else "#2B2B2B"


def muted_color(dark: bool) -> str:
    return "#A0A0A0" if dark else "#6B6B6B"


def format_due(due: date) -> str:
    today = date.today()
    if due == today:
        return "Aujourd'hui"
    if due == today + timedelta(days=1):
        return "Demain"
    if due == today - timedelta(days=1):
        return "Hier"
    return due.strftime("%d/%m/%Y")


class PillLabel(QLabel):
    def __init__(self, text: str, bg: str, fg: str, parent=None):
        super().__init__(text, parent)
        self.setObjectName("pillLabel")
        self.setFixedHeight(20)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(
            f"#pillLabel {{ background-color: {bg}; color: {fg};"
            f" border-radius: 10px; padding: 0 10px; font-weight: 600; }}"
        )


class ElidedLabel(QLabel):
    """Label whose text is elided to a maximum number of lines."""

    def __init__(self, text: str = "", parent=None, max_lines: int = 2, color: str = ""):
        super().__init__(text, parent)
        self.max_lines = max_lines
        self._color = QColor(color) if color else QColor()
        self.setWordWrap(True)
        if color:
            self.setStyleSheet(f"color: {color};")
        metrics = QFontMetrics(self.font())
        self.setFixedHeight(metrics.lineSpacing() * max_lines)

    def setText(self, text: str):
        super().setText(text)
        self.setToolTip(text)

    def heightForWidth(self, width: int) -> int:
        return self.height()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        if self._color.isValid():
            painter.setPen(self._color)
        else:
            painter.setPen(self.palette().color(QPalette.ColorRole.WindowText))
        metrics = QFontMetrics(self.font())
        line_height = metrics.lineSpacing()
        width = max(self.width(), 1)
        remaining = self.text()
        y = metrics.ascent()
        for i in range(self.max_lines):
            if not remaining:
                break
            lo, hi = 0, len(remaining)
            while lo < hi:
                mid = (lo + hi + 1) // 2
                if metrics.horizontalAdvance(remaining[:mid]) <= width:
                    lo = mid
                else:
                    hi = mid - 1
            if lo == 0:
                break
            line = remaining[:lo]
            rest = remaining[lo:]
            if i < self.max_lines - 1:
                space = line.rfind(" ")
                if space > 0 and rest.strip():
                    rest = line[space + 1 :] + rest
                    line = line[:space]
                remaining = rest.lstrip()
            else:
                if rest.strip():
                    line = metrics.elidedText(
                        line + rest, Qt.TextElideMode.ElideRight, width
                    )
                remaining = ""
            painter.drawText(0, y, line)
            y += line_height
        painter.end()


class TaskCard(CardWidget):
    edited = Signal(Task)
    deleted = Signal(str)
    statusChanged = Signal(Task, Status)

    def __init__(self, task: Task, parent=None):
        super().__init__(parent)
        self.task = task
        self._drag_start = None
        self._init_ui()
        self._update_content()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (
            event.buttons() & Qt.MouseButton.LeftButton
            and self._drag_start is not None
            and (event.position().toPoint() - self._drag_start).manhattanLength()
            >= QApplication.startDragDistance()
        ):
            self._start_drag()
            return
        super().mouseMoveEvent(event)

    def _start_drag(self):
        start = self._drag_start
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(TASK_MIME_TYPE, self.task.id.encode("utf-8"))
        drag.setMimeData(mime)
        drag.setPixmap(self.grab())
        if start is not None:
            drag.setHotSpot(start)
        drag.exec(Qt.DropAction.MoveAction)
        self._drag_start = None

    def _init_ui(self):
        dark = isDarkTheme()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        header = QHBoxLayout()
        self.pill = PillLabel("", "#000000", "#FFFFFF")
        self.titleLabel = StrongBodyLabel(self.task.title)
        self.titleLabel.setWordWrap(True)
        self.priorityIcon = IconWidget(self)
        self.priorityIcon.setFixedSize(16, 16)
        self.priorityLabel = CaptionLabel()
        header.addWidget(self.pill)
        header.addWidget(self.titleLabel, 1)
        header.addWidget(self.priorityIcon)
        header.addWidget(self.priorityLabel)

        self.descLabel = ElidedLabel(
            self.task.description, max_lines=2, color=muted_color(dark)
        )
        self.descLabel.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )

        footer = QHBoxLayout()
        self.dueIcon = IconWidget(self)
        self.dueIcon.setFixedSize(14, 14)
        self.dueLabel = CaptionLabel()
        self.dueLabel.setStyleSheet(f"color: {muted_color(dark)};")
        self.overduePill = PillLabel("En retard", *overdue_colors(dark))
        self.overduePill.setVisible(False)
        footer.addWidget(self.dueIcon)
        footer.addWidget(self.dueLabel)
        footer.addWidget(self.overduePill)
        footer.addStretch(1)

        self.actionButton = PushButton(self)
        self.actionButton.setFixedHeight(30)
        self.editButton = ToolButton(self)
        self.editButton.setIcon(FluentIcon.EDIT)
        self.editButton.setToolTip("Modifier")
        self.deleteButton = ToolButton(self)
        self.deleteButton.setIcon(FluentIcon.DELETE)
        self.deleteButton.setToolTip("Supprimer")
        footer.addWidget(self.actionButton)
        footer.addWidget(self.editButton)
        footer.addWidget(self.deleteButton)

        layout.addLayout(header)
        layout.addWidget(self.descLabel)
        layout.addLayout(footer)

        self.actionButton.clicked.connect(self._on_action_clicked)
        self.editButton.clicked.connect(lambda: self.edited.emit(self.task))
        self.deleteButton.clicked.connect(lambda: self.deleted.emit(self.task.id))

    def _update_content(self):
        dark = isDarkTheme()
        task = self.task
        self.titleLabel.setText(task.title)
        self.descLabel.setText(task.description)
        self.descLabel.setVisible(bool(task.description.strip()))

        bg, fg = status_colors(task.status, dark)
        self.pill.setText(task.status.label)
        self.pill.setStyleSheet(
            f"#pillLabel {{ background-color: {bg}; color: {fg};"
            f" border-radius: 10px; padding: 0 10px; font-weight: 600; }}"
        )

        priority_color = priority_colors(task.priority, dark)
        self.priorityIcon.setIcon(
            FluentIcon.FLAG.icon(color=QColor(priority_color))
        )
        self.priorityLabel.setText(task.priority.label)
        self.priorityLabel.setStyleSheet(
            f"color: {priority_color}; font-weight: 600;"
        )

        due = task.due_date_obj
        self.dueIcon.setIcon(FluentIcon.CALENDAR.icon())
        if due is None:
            self.dueLabel.setText("Sans échéance")
        else:
            self.dueLabel.setText(f"Échéance : {format_due(due)}")

        self.overduePill.setVisible(task.is_overdue)

        if task.status == Status.TODO:
            self.actionButton.setText("Commencer")
            self.actionButton.setIcon(FluentIcon.PLAY)
            self.actionButton.setToolTip("Passer en cours")
        elif task.status == Status.IN_PROGRESS:
            self.actionButton.setText("Terminer")
            self.actionButton.setIcon(FluentIcon.COMPLETED)
            self.actionButton.setToolTip("Marquer comme terminée")
        else:
            self.actionButton.setText("Réactiver")
            self.actionButton.setIcon(FluentIcon.SYNC)
            self.actionButton.setToolTip("Remettre à faire")

    def _on_action_clicked(self):
        task = self.task
        if task.status == Status.TODO:
            new_status = Status.IN_PROGRESS
        elif task.status == Status.IN_PROGRESS:
            new_status = Status.DONE
        else:
            new_status = Status.TODO
        self.statusChanged.emit(task, new_status)
