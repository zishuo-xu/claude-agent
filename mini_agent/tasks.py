from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BLOCKED = "blocked"


@dataclass
class TaskItem:
    id: str
    title: str
    status: TaskStatus = TaskStatus.TODO
    note: str = ""


@dataclass
class TaskState:
    items: list[TaskItem] = field(default_factory=list)

    def set_tasks(self, titles: list[str]) -> str:
        cleaned = [title.strip() for title in titles if title.strip()]
        if not cleaned:
            raise ValueError("tasks must contain at least one non-empty title")
        self.items = [TaskItem(id=f"t{index + 1}", title=title) for index, title in enumerate(cleaned)]
        return self.render()

    def update_task(self, task_id: str, status: str, note: str = "") -> str:
        item = self.get(task_id)
        item.status = TaskStatus(status)
        item.note = note.strip()
        return self.render()

    def get(self, task_id: str) -> TaskItem:
        for item in self.items:
            if item.id == task_id:
                return item
        raise ValueError(f"unknown task id: {task_id}")

    def render(self) -> str:
        if not self.items:
            return "(no tasks)"
        rows = []
        for item in self.items:
            note = f" - {item.note}" if item.note else ""
            rows.append(f"{item.id} [{item.status.value}] {item.title}{note}")
        return "\n".join(rows)

    def prompt_summary(self) -> str:
        if not self.items:
            return "Current tasks (live task state): none."
        return "Current tasks (live task state):\n" + self.render()
