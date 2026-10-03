from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import QObject, Signal

DATA_FILE = Path(__file__).resolve().parent / "tasks.json"


class Status(Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"

    @property
    def label(self) -> str:
        return {
            Status.TODO: "À faire",
            Status.IN_PROGRESS: "En cours",
            Status.DONE: "Terminée",
        }[self]


class Priority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

    @property
    def label(self) -> str:
        return {
            Priority.LOW: "Basse",
            Priority.MEDIUM: "Moyenne",
            Priority.HIGH: "Haute",
        }[self]

    @property
    def weight(self) -> int:
        return {Priority.LOW: 0, Priority.MEDIUM: 1, Priority.HIGH: 2}[self]


@dataclass
class Task:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    title: str = ""
    description: str = ""
    status: Status = Status.TODO
    priority: Priority = Priority.MEDIUM
    due_date: str = ""
    created_at: str = field(
        default_factory=lambda: datetime.now().isoformat(timespec="seconds")
    )
    completed_at: str = ""

    @property
    def due_date_obj(self) -> Optional[date]:
        try:
            return date.fromisoformat(self.due_date) if self.due_date else None
        except ValueError:
            return None

    @property
    def is_overdue(self) -> bool:
        due = self.due_date_obj
        return due is not None and due < date.today() and self.status != Status.DONE

    def to_dict(self) -> dict:
        data = asdict(self)
        data["status"] = self.status.value
        data["priority"] = self.priority.value
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        try:
            status = Status(data.get("status", Status.TODO.value))
        except ValueError:
            status = Status.TODO
        try:
            priority = Priority(data.get("priority", Priority.MEDIUM.value))
        except ValueError:
            priority = Priority.MEDIUM
        return cls(
            id=data.get("id") or uuid.uuid4().hex,
            title=data.get("title", ""),
            description=data.get("description", ""),
            status=status,
            priority=priority,
            due_date=data.get("due_date", ""),
            created_at=data.get("created_at", ""),
            completed_at=data.get("completed_at", ""),
        )


class TaskStore(QObject):
    changed = Signal()

    def __init__(self, path: Path = DATA_FILE, parent=None):
        super().__init__(parent)
        self.path = path
        self.tasks: List[Task] = []
        self.load()

    def load(self) -> None:
        self.tasks = []
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                self.tasks = [Task.from_dict(item) for item in data]
            except (json.JSONDecodeError, OSError):
                self.tasks = []

    def save(self) -> None:
        try:
            self.path.write_text(
                json.dumps(
                    [task.to_dict() for task in self.tasks],
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
        except OSError:
            pass
        self.changed.emit()

    def add(self, task: Task) -> None:
        self.tasks.append(task)
        self.save()

    def remove(self, task_id: str) -> None:
        self.tasks = [task for task in self.tasks if task.id != task_id]
        self.save()

    def move(self, task_id: str, target_id: Optional[str]) -> None:
        """ Move `task_id` just before `target_id` (or at the end if target_id is None). """
        tasks = self.tasks
        from_idx = next((i for i, t in enumerate(tasks) if t.id == task_id), None)
        if from_idx is None:
            return
        dragged = tasks.pop(from_idx)
        if target_id is None:
            tasks.append(dragged)
        else:
            to_idx = next((i for i, t in enumerate(tasks) if t.id == target_id), None)
            if to_idx is None:
                tasks.append(dragged)
            else:
                tasks.insert(to_idx, dragged)
        self.save()

    def get(self, task_id: str) -> Optional[Task]:
        return next((task for task in self.tasks if task.id == task_id), None)
