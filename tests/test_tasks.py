import pytest

from mini_agent.tasks import TaskState


def test_task_state_sets_and_renders_tasks():
    state = TaskState()

    rendered = state.set_tasks(["Inspect files", "Run tests"])

    assert "t1 [todo] Inspect files" in rendered
    assert "t2 [todo] Run tests" in rendered


def test_task_state_updates_status_and_note():
    state = TaskState()
    state.set_tasks(["Inspect files"])

    rendered = state.update_task("t1", "in_progress", "reading README")

    assert "t1 [in_progress] Inspect files - reading README" in rendered


def test_task_state_rejects_unknown_task():
    state = TaskState()
    state.set_tasks(["Inspect files"])

    with pytest.raises(ValueError):
        state.update_task("t9", "done")


def test_task_state_prompt_summary():
    state = TaskState()
    assert state.prompt_summary() == "Current tasks (live task state): none."

    state.set_tasks(["Inspect files"])

    assert "Current tasks (live task state):" in state.prompt_summary()
