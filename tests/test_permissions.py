from mini_agent.permissions import (
    PermissionBehavior,
    PermissionContext,
    PermissionMode,
    PermissionRule,
    decide_permission,
    parse_permission_rule,
)


def test_parse_permission_rule_with_pattern():
    rule = parse_permission_rule("run_shell(git status*)", PermissionBehavior.ALLOW)

    assert rule.tool_name == "run_shell"
    assert rule.content_pattern == "git status*"
    assert rule.behavior == PermissionBehavior.ALLOW


def test_deny_rule_wins_over_bypass_mode():
    context = PermissionContext(
        mode=PermissionMode.BYPASS,
        rules=[PermissionRule(PermissionBehavior.DENY, "run_shell", "rm*")],
    )

    decision = decide_permission(
        context=context,
        tool_name="run_shell",
        tool_input={"command": "rm file.txt"},
        read_only=False,
        destructive=True,
    )

    assert decision.behavior == PermissionBehavior.DENY


def test_plan_mode_allows_read_only_and_asks_for_write():
    context = PermissionContext(mode=PermissionMode.PLAN)

    read_decision = decide_permission(
        context=context,
        tool_name="read_file",
        tool_input={"path": "README.md"},
        read_only=True,
        destructive=False,
    )
    write_decision = decide_permission(
        context=context,
        tool_name="write_file",
        tool_input={"path": "x.txt"},
        read_only=False,
        destructive=False,
    )

    assert read_decision.behavior == PermissionBehavior.ALLOW
    assert write_decision.behavior == PermissionBehavior.ASK

