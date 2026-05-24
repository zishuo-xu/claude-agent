from mini_agent.llm import ReasoningBlock, TextBlock
from mini_agent.pseudo_tools import contains_pseudo_tool_call, normalize_pseudo_tool_call


def test_normalizes_xml_invoke_pseudo_tool_call():
    content = normalize_pseudo_tool_call(
        [TextBlock('<tool_call><invoke name="explore_agent"><query>inspect runtime</query></invoke></tool_call>')],
        available_tool_names={"explore_agent"},
        tool_use_id="pseudo_tool_1",
    )

    assert len(content) == 1
    assert content[0].type == "tool_use"
    assert content[0].id == "pseudo_tool_1"
    assert content[0].name == "explore_agent"
    assert content[0].input == {"prompt": "inspect runtime"}


def test_preserves_reasoning_when_normalizing_json_pseudo_tool_call():
    content = normalize_pseudo_tool_call(
        [
            ReasoningBlock("thinking state"),
            TextBlock('<tool_call>{"name": "explore_agent", "arguments": {"query": "inspect runtime"}}</tool_call>'),
        ],
        available_tool_names={"explore_agent"},
        tool_use_id="pseudo_tool_2",
    )

    assert len(content) == 2
    assert content[0].type == "reasoning"
    assert content[1].type == "tool_use"
    assert content[1].input == {"prompt": "inspect runtime"}


def test_normalizes_function_parameter_pseudo_tool_call():
    content = normalize_pseudo_tool_call(
        [TextBlock("<tool_call><function=read_file><parameter=file_path>README.md</parameter></function></tool_call>")],
        available_tool_names={"read_file"},
        tool_use_id="pseudo_tool_3",
    )

    assert len(content) == 1
    assert content[0].type == "tool_use"
    assert content[0].name == "read_file"
    assert content[0].input == {"path": "README.md"}


def test_does_not_normalize_unavailable_pseudo_tool_call():
    original = [TextBlock('<tool_call>{"name": "list_files", "arguments": {"path": "."}}</tool_call>')]

    content = normalize_pseudo_tool_call(
        original,
        available_tool_names={"read_file"},
        tool_use_id="pseudo_tool_4",
    )

    assert content == original


def test_detects_pseudo_tool_call_markup():
    assert contains_pseudo_tool_call("<tool_call>{}</tool_call>")
    assert contains_pseudo_tool_call("<invoke name='x'></invoke>")
    assert not contains_pseudo_tool_call("plain answer")
