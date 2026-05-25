from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Callable

from .events import PermissionRequestHandler
from .permissions import PermissionBehavior, PermissionContext, decide_permission
from .tool_core import Tool


EmitEvent = Callable[..., None]


@dataclass
class ToolBatch:
    parallel: bool
    tool_uses: list[Any]


@dataclass
class ToolTurnExecutor:
    tools: dict[str, Tool]
    permission_context: PermissionContext
    emit: EmitEvent
    permission_handler: PermissionRequestHandler

    def execute(self, tool_uses: list[Any]) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for batch in self._partition_tool_uses(tool_uses):
            self._emit_batch_event("tool_batch_start", batch)
            if batch.parallel:
                with ThreadPoolExecutor(max_workers=min(4, len(batch.tool_uses))) as executor:
                    results.extend(executor.map(self._execute_one, batch.tool_uses))
            else:
                results.extend(self._execute_one(tool_use) for tool_use in batch.tool_uses)
            self._emit_batch_event("tool_batch_end", batch)
        return results

    def _emit_batch_event(self, event_type: str, batch: ToolBatch) -> None:
        self.emit(
            event_type,
            parallel=batch.parallel,
            tools=[tool_use.name for tool_use in batch.tool_uses],
            tool_use_ids=[tool_use.id for tool_use in batch.tool_uses],
        )

    def _partition_tool_uses(self, tool_uses: list[Any]) -> list[ToolBatch]:
        batches: list[ToolBatch] = []
        for tool_use in tool_uses:
            is_parallel_safe = self._is_parallel_safe(tool_use)
            if is_parallel_safe and batches and batches[-1].parallel:
                batches[-1].tool_uses.append(tool_use)
                continue
            batches.append(ToolBatch(parallel=is_parallel_safe, tool_uses=[tool_use]))
        return batches

    def _is_parallel_safe(self, tool_use: Any) -> bool:
        tool = self.tools.get(tool_use.name)
        if not tool:
            return False
        return tool.read_only(tool_use.input) and tool.concurrency_safe(tool_use.input)

    def _execute_one(self, tool_use: Any) -> dict[str, Any]:
        name = tool_use.name
        tool_input = tool_use.input
        tool = self.tools.get(name)
        if not tool:
            result = f"Unknown tool: {name}"
            return self._tool_error_result(tool_use.id, name=name, content=result, category="unknown_tool")

        self.emit("tool_start", name=name, input=tool_input)
        validation_error = tool.validation_error(tool_input)
        if validation_error:
            result = f"Invalid tool input: {validation_error}"
            return self._tool_error_result(tool_use.id, name=name, content=result, category="validation")

        decision = decide_permission(
            context=self.permission_context,
            tool_name=name,
            tool_input=tool_input,
            read_only=tool.read_only(tool_input),
            destructive=tool.destructive(tool_input),
        )
        if decision.behavior == PermissionBehavior.DENY:
            result = (
                f"Permission denied: {decision.reason}. "
                "Do not retry the same action with another tool; explain the permission boundary to the user."
            )
            return self._tool_error_result(tool_use.id, name=name, content=result, category="permission_denied")
        if decision.behavior == PermissionBehavior.ASK and not self._confirm_tool(name, tool_input, decision.reason):
            result = "Permission rejected by user"
            return self._tool_error_result(tool_use.id, name=name, content=result, category="permission_rejected")

        try:
            result = tool.run(tool_input)
            self.emit("tool_result", name=name, content=result, is_error=False)
            return self._tool_result(tool_use.id, result, False)
        except Exception as exc:
            result = f"{type(exc).__name__}: {exc}"
            return self._tool_error_result(
                tool_use.id,
                name=name,
                content=result,
                category="execution_exception",
                error_type=type(exc).__name__,
            )

    def _confirm_tool(self, name: str, tool_input: dict[str, Any], reason: str) -> bool:
        self.emit("permission_request", name=name, input=tool_input, reason=reason)
        return self.permission_handler(name, tool_input, reason)

    @staticmethod
    def _tool_result(tool_use_id: str, content: str, is_error: bool) -> dict[str, Any]:
        return {
            "type": "tool_result",
            "tool_use_id": tool_use_id,
            "content": content,
            "is_error": is_error,
        }

    def _tool_error_result(
        self,
        tool_use_id: str,
        *,
        name: str,
        content: str,
        category: str,
        error_type: str | None = None,
    ) -> dict[str, Any]:
        self.emit("tool_error", name=name, category=category, error_type=error_type, content=content)
        self.emit("tool_result", name=name, content=content, is_error=True)
        return self._tool_result(tool_use_id, content, True)
