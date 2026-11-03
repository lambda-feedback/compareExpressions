"""Generates the process graph images in `app/docs/process_graphs/` for the developer documentation.

Each example is run through `evaluation_function` while recording what happens, and drawn twice with graphviz:
- `<name>.svg`: the stages of the evaluation (from the `stage_start` events `_evaluate` logs), with the criteria graph
  the response went through and the path it took highlighted.
- `<name>_calls.svg`: the same stages, each with the `app` and `lambdafeedback` functions called during it (recorded
  with `sys.setprofile`), down to `CALL_DEPTH` calls below `_evaluate`.

Run from the repository root with `python -m scripts.generate_process_graphs`.
"""
from __future__ import annotations

import dis
import html
import inspect
import json
import logging
import re
import sys
from dataclasses import dataclass, field, is_dataclass
from pathlib import Path
from types import FrameType
from typing import Any

import pydot
import sympy
from lambdafeedback.criteria import CriteriaGraph

from app import evaluation
from app.context.base import Context
from app.result import EvaluationResult
from scripts.generate_criteria_graphs import _node_label, add_criteria_graph, new_drawing

OUTPUT_DIRECTORY = Path(__file__).resolve().parent.parent / "app" / "docs" / "process_graphs"

# (file name, response, answer, params)
EXAMPLES: list[tuple[str, str, str, dict[str, Any]]] = [
    ("process_symbolic", "1 + x", "x + 1", {}),
    ("process_physical_quantity", "100 cm", "1 m", {"physical_quantity": True}),
    ("process_symbolic_parse_error", "x +* 1", "x + 1", {}),
]

# How many calls below `_evaluate` the call graphs go.
CALL_DEPTH = 2

# The longest an argument or return value recorded for the process animation gets before it is cut short, and the
# longest the full value of a summarised dictionary gets.
VALUE_LENGTH = 200
FULL_VALUE_LENGTH = 1000

# The longest an exception's type and message recorded for the process animation get before they are cut short.
EXCEPTION_LENGTH = 160

REPOSITORY = Path(__file__).resolve().parent.parent

# Functions left out of the call graphs; the functions they call are shown under their caller instead.
HIDDEN_FUNCTIONS = {"log_event", "elapsed_ms", "_evaluate.<locals>.enter_stage"}
HIDDEN_FUNCTION_PARTS = ("<genexpr>", "<listcomp>", "<dictcomp>", "<setcomp>", "<lambda>", "__create_fn__")

# The stage `_evaluate` is in before its first `enter_stage` call.
FIRST_STAGE = "setup"

STAGE_STYLE = {"shape": "box", "style": "rounded,filled", "fillcolor": "#E8EAF6", "color": "#2F3C86"}
SKIPPED_STAGE_STYLE = {"shape": "box", "style": "rounded,dashed", "color": "#9E9E9E", "fontcolor": "#9E9E9E"}
RESULT_STYLE = {"shape": "hexagon", "style": "filled", "fillcolor": "#C5CAE9", "color": "#2F3C86"}
CALL_STYLE = {"shape": "box", "style": "filled", "fillcolor": "#FFFFFF", "color": "#212121"}
PIPELINE_EDGE_STYLE = {"penwidth": "2", "weight": "10"}


def all_stages() -> list[str]:
    """Every stage `_evaluate` can enter, in order, read from its `enter_stage` calls."""
    return [FIRST_STAGE] + re.findall(r'enter_stage\("(\w+)"\)', inspect.getsource(evaluation._evaluate))


@dataclass
class Call:
    """A function in the call graph: every call of it from the same caller in the same stage."""

    identifier: str
    module: str
    qualname: str
    stage: str
    parent: Call | None
    depth: int
    count: int = 1
    # The first paragraph of the function's docstring, and where it is defined (`path:line`); only set when values
    # are recorded.
    doc: str = ""
    source: str = ""

    @property
    def internal(self) -> bool:
        """Whether the function is a dunder method, such as `__init__` or `__getstate__`."""
        name = self.qualname.rsplit(".", 1)[-1]
        return name.startswith("__") and name.endswith("__")


@dataclass
class Recording:
    """What happened during one `evaluation_function` call.

    `events` is filled only when values are recorded (see `Recorder`): every stage entered, call made, value returned
    and criteria graph evaluation run, in order, as JSON-ready dictionaries.

    `stage_times` is the time from the start of the evaluation to the start of each stage, and `duration_ms` the time
    the whole evaluation took, in milliseconds, both from the evaluation's log events.
    """

    stages: list[str] = field(default_factory=list)
    early_return: bool = False
    calls: dict[tuple[Any, ...], Call] = field(default_factory=dict)
    criteria_graphs: dict[str, CriteriaGraph] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)
    stage_times: dict[str, float] = field(default_factory=dict)
    duration_ms: float | None = None


def _cut(text: str, length: int) -> str:
    if len(text) > length:
        return text[:length - 1] + "…"
    return text


def _plain_repr(value: Any) -> str:
    """`repr(value)` without memory addresses."""
    try:
        text = repr(value)
    except (AttributeError, TypeError, ValueError, KeyError):
        # Objects whose `__init__` is still running can fail to give a repr.
        text = f"<{type(value).__name__}>"
    return re.sub(r" at 0x[0-9a-f]+", "", text)


def short_repr(value: Any) -> str:
    """A short description of `value` for the process animation: `repr(value)` without memory addresses, cut short at
    `VALUE_LENGTH` characters.

    The values whose repr says little are summarised instead: a context by its name, an `EvaluationResult` by its
    correctness and tags, and a dictionary too long to show by its keys.
    """
    if isinstance(value, Context):
        name = value.feedback_procedure_generator.__module__.removeprefix("app.context.").split(".")[0]
        return f"{name} context"
    elif isinstance(value, EvaluationResult):
        try:
            return f"EvaluationResult(is_correct={value.is_correct}, tags={value.tags})"
        except AttributeError:
            # The result's `__init__` is still running
            return "EvaluationResult()"
    text = _plain_repr(value)
    if isinstance(value, dict) and len(text) > VALUE_LENGTH:
        keys = ", ".join(str(key) for key in value)
        return _cut(f"{{… {len(value)} keys: {keys} …}}", VALUE_LENGTH)
    return _cut(text, VALUE_LENGTH)


def full_repr(value: Any) -> str | None:
    """The repr of `value`, cut short at `FULL_VALUE_LENGTH` characters, when `short_repr` summarises it as a dictionary
    of keys; None otherwise.
    """
    if not isinstance(value, dict):
        return None
    text = _plain_repr(value)
    if len(text) <= VALUE_LENGTH:
        return None
    return _cut(text, FULL_VALUE_LENGTH)


def shown_value(name: str, value: Any) -> list[str]:
    """The name of an argument and its `short_repr`, followed by its `full_repr` when there is one."""
    full = full_repr(value)
    if full is None:
        return [name, short_repr(value)]
    return [name, short_repr(value), full]


def exception_text(exception: BaseException) -> str:
    """The type and message of `exception`, cut short at `EXCEPTION_LENGTH` characters."""
    try:
        message = str(exception)
    except (AttributeError, TypeError, ValueError):
        message = ""
    name = type(exception).__name__
    return _cut(f"{name}: {message}" if message else name, EXCEPTION_LENGTH)


def parse_tree_text(node: Any) -> str:
    """The criteria parse tree under `node` drawn with `├─` and `└─` connectors, one node per line as `label: content`,
    followed by the node's tags when it has any.
    """
    lines = [_parse_node_text(node)]
    _add_parse_children(node, "", lines)
    return "\n".join(lines)


def _parse_node_text(node: Any) -> str:
    label = node.label.strip()
    content = str(node.content).strip()
    text = label if content in ("", label) else f"{label}: {content}"
    if node.tags:
        text += f"  tags: {', '.join(sorted(str(tag) for tag in node.tags))}"
    return text


def _add_parse_children(node: Any, indent: str, lines: list[str]) -> None:
    for (index, child) in enumerate(node.children):
        last = index == len(node.children) - 1
        lines.append(indent + ("└─ " if last else "├─ ") + _parse_node_text(child))
        _add_parse_children(child, indent + ("   " if last else "│  "), lines)


def source_location(frame: FrameType) -> str:
    """Where the function running in `frame` is defined, as `path:line`, with the path relative to the repository or,
    for an installed package, to `site-packages`.
    """
    path = Path(frame.f_code.co_filename)
    if path.is_relative_to(REPOSITORY) and "site-packages" not in path.parts:
        shown = str(path.relative_to(REPOSITORY))
    elif "site-packages" in path.parts:
        shown = "/".join(path.parts[path.parts.index("site-packages") + 1:])
    else:
        shown = path.name
    return f"{shown}:{frame.f_code.co_firstlineno}"


def first_doc_paragraph(frame: FrameType) -> str:
    """The first paragraph of the docstring of the function running in `frame`, on one line, found from its module by
    its qualified name; empty when it has none of its own, or is defined inside another function.
    """
    qualname = frame.f_code.co_qualname
    if "<locals>" in qualname:
        return ""
    function: Any = None
    for (index, part) in enumerate(qualname.split(".")):
        if index == 0:
            function = frame.f_globals.get(part)
        else:
            function = inspect.getattr_static(function, part, None)
        if function is None:
            return ""
    if isinstance(function, (staticmethod, classmethod)):
        function = function.__func__
    elif isinstance(function, property):
        function = function.fget
    # `__doc__` rather than `inspect.getdoc`, which falls back to the docstring of the method a class inherits from,
    # e.g. `object.__init__`'s "Initialize self."
    doc = getattr(function, "__doc__", None)
    if not isinstance(doc, str):
        return ""
    paragraph = inspect.cleandoc(doc).split("\n\n")[0]
    return _cut(" ".join(paragraph.split()), VALUE_LENGTH)


def frame_argument_values(frame: FrameType) -> list[tuple[str, Any]]:
    """The name and value of each argument of the function running in `frame`."""
    arguments = inspect.getargvalues(frame)
    names = list(arguments.args)
    if arguments.varargs is not None:
        names.append(arguments.varargs)
    if arguments.keywords is not None:
        names.append(arguments.keywords)
    return [(name, arguments.locals.get(name)) for name in names]


def is_response_form(value: Any) -> bool:
    """Whether `value` is the kind of value the response is turned into: a string, a SymPy expression, an `app` or
    `lambdafeedback` dataclass such as a parsed quantity or a token, or a list or tuple of these.
    """
    if isinstance(value, (str, sympy.Basic)):
        return True
    elif isinstance(value, (list, tuple)):
        return len(value) > 0 and all(is_response_form(item) for item in value)
    elif type(value).__module__.startswith("lambdafeedback."):
        return True
    return type(value).__module__.startswith("app.") and is_dataclass(value)


def returned_normally(frame: FrameType) -> bool:
    """Whether `frame` is returning (or yielding) a value, rather than stopping because of an exception."""
    instruction = dis.opname[frame.f_code.co_code[frame.f_lasti]]
    return instruction in ("RETURN_VALUE", "RETURN_CONST", "YIELD_VALUE")


class Recorder(logging.Handler):
    """Records the stages from the evaluation's log events, and the function calls with `sys.setprofile`.

    Calls are followed down to `depth` calls below `_evaluate`. With `record_values`, these are kept in order in
    `Recording.events`:
    - the arguments and return value of each call, or the exception it raised instead of returning (see `unwind`);
    - the evaluations each criteria graph runs, and the criteria each one reports;
    - each new form of the response (see `is_response_form`): the value returned by a call that was given the response,
      or an earlier form of it, as an argument;
    - the criteria `create_criteria_dict` parses, and the template that builds each one's criteria graph;
    - the parameters `_build_parameters` completes, and the feedback each criteria graph exports for its reached
      criteria.
    The docstring and source location of each function called are kept on its `Call` too.
    """

    def __init__(self, depth: int = CALL_DEPTH, record_values: bool = False, response: str = "") -> None:
        super().__init__()
        self.recording = Recording()
        self.stage = FIRST_STAGE
        self.depth = depth
        self.record_values = record_values
        # Each frame being followed: (the Call it belongs to, or None for `_evaluate`, its depth below `_evaluate`).
        self.frames: dict[FrameType, tuple[Call | None, int]] = {}
        # The frames whose return is recorded: each frame's Call, or the criterion and evaluation node it runs.
        self.call_frames: dict[FrameType, Call] = {}
        self.evaluation_frames: dict[FrameType, tuple[str, str]] = {}
        # The reprs of the forms the response has taken so far, and the frames given one of them as an argument.
        self.response_forms = {repr(response)}
        self.response_frames: set[FrameType] = set()
        # The code of the last call recorded as raising an exception, and its return event, until `unwind` fills in
        # the exception.
        self.raised: tuple[Any, dict[str, Any]] | None = None

    def emit(self, record: logging.LogRecord) -> None:
        event = json.loads(record.getMessage())
        if event["event"] == "stage_start":
            self.stage = event["stage"]
            self.recording.stages.append(self.stage)
            self.recording.stage_times[self.stage] = event["elapsed_ms"]
            if self.record_values:
                self.recording.events.append({"kind": "stage", "stage": self.stage})
        elif event["event"] == "evaluation_end":
            self.recording.early_return = event["early_return"]
            self.recording.duration_ms = event["duration_ms"]

    def unwind(self, code: Any, offset: int, exception: BaseException) -> None:
        """The `sys.monitoring` `PY_UNWIND` callback: a frame of `code` is stopping because of `exception`.

        It runs just after the profile function's `return` event for the same frame, which cannot see the exception,
        so the exception is added to the return event recorded there.
        """
        if self.raised is not None and self.raised[0] is code:
            self.raised[1]["exception"] = exception_text(exception)
        self.raised = None

    def _record_evaluation(self, frame: FrameType) -> None:
        """Records the start of a criteria graph evaluation, when `frame` is the `evaluate` function of one."""
        runner = frame.f_back
        if runner is None or runner.f_code.co_qualname != "CriteriaGraph.generate_feedback":
            return
        evaluate = runner.f_locals.get("evaluate")
        # `evaluate` can be a `functools.partial` of the function that runs
        function = getattr(evaluate, "func", evaluate)
        if getattr(function, "__code__", None) is not frame.f_code:
            return
        criterion = runner.f_locals["main_criterion"].removesuffix("_TRUE")
        node = runner.f_locals["label"]
        self.evaluation_frames[frame] = (criterion, node)
        self.recording.events.append({"kind": "evaluate", "stage": self.stage, "criterion": criterion, "node": node})

    def _record_call(self, frame: FrameType, call: Call) -> None:
        self.call_frames[frame] = call
        arguments = frame_argument_values(frame)
        for (name, value) in arguments:
            if name != "self" and is_response_form(value) and repr(value) in self.response_forms:
                self.response_frames.add(frame)
                break
        shown_arguments = []
        for (name, value) in arguments:
            if name == "self":
                shown_arguments.append([name, f"<{type(value).__name__}>"])
            else:
                shown_arguments.append(shown_value(name, value))
        self.recording.events.append({
            "kind": "call", "stage": self.stage, "call": call.identifier, "arguments": shown_arguments
        })

    def _record_criteria(self, frame: FrameType, value: Any) -> None:
        """Records the criteria when `frame` is `create_criteria_dict` returning them: the criteria string before and
        after preprocessing, and each criterion with the label and tree its parse gave.
        """
        if frame.f_code.co_qualname != "create_criteria_dict" or not isinstance(value, dict):
            return
        self.recording.events.append({
            "kind": "criteria",
            "stage": self.stage,
            "original": frame.f_locals.get("original_criteria_string", ""),
            "preprocessed": frame.f_locals.get("criteria_string", ""),
            "criteria": [
                {"identifier": identifier, "label": node.label.strip(), "tree": parse_tree_text(node)}
                for (identifier, node) in value.items()
            ],
        })

    def _record_parameters(self, frame: FrameType, value: Any) -> None:
        """Records the parameters when `frame` is `_build_parameters` returning them: the parameters it was given, and
        the ones it added.
        """
        if frame.f_code.co_qualname != "_build_parameters" or not isinstance(value, dict):
            return
        given = frame.f_locals.get("params", {})
        self.recording.events.append({
            "kind": "parameters",
            "stage": self.stage,
            "given": [shown_value(str(key), item) for (key, item) in value.items() if key in given],
            "added": [shown_value(str(key), item) for (key, item) in value.items() if key not in given],
        })

    def _record_feedback(self, frame: FrameType, value: Any) -> None:
        """Records the feedback text of each reached criterion, when `frame` is `CriteriaGraph.resolve_feedback`
        returning it for `CriteriaGraph.export_feedback`.
        """
        exporter = frame.f_back
        if frame.f_code.co_qualname != "CriteriaGraph.resolve_feedback" or exporter is None:
            return
        if exporter.f_code.co_qualname != "CriteriaGraph.export_feedback":
            return
        graph = frame.f_locals.get("self")
        criterion = next((key for (key, item) in self.recording.criteria_graphs.items() if item is graph), None)
        self.recording.events.append({
            "kind": "feedback",
            "stage": self.stage,
            "criterion": criterion,
            "feedback": [[str(tag), str(text)] for (tag, text) in value],
        })

    def _record_template(self, frame: FrameType, value: Any, call: Call | None) -> None:
        """Records which template built which criteria graph, when `frame` is a template `feedback_procedure_generator`
        called to build the graph of one criterion.
        """
        generator = frame.f_back
        if generator is None or generator.f_code.co_qualname != "feedback_procedure_generator":
            return
        if not isinstance(value, CriteriaGraph):
            return
        # The key of `graph_templates` that chose this template, or None when the template is the context's default
        label = None
        for (key, template) in generator.f_globals.get("graph_templates", {}).items():
            if getattr(template, "__code__", None) is frame.f_code:
                label = key.strip()
        self.recording.events.append({
            "kind": "template",
            "stage": self.stage,
            "call": None if call is None else call.identifier,
            "criterion": generator.f_locals["label"],
            "template": frame.f_code.co_qualname,
            "label": label,
            "evaluations": len(value.evaluations),
        })

    def _record_return(self, frame: FrameType, value: Any) -> None:
        call = self.call_frames.pop(frame, None)
        given_response = frame in self.response_frames
        self.response_frames.discard(frame)
        if returned_normally(frame):
            self._record_criteria(frame, value)
            self._record_template(frame, value, call)
            self._record_parameters(frame, value)
            self._record_feedback(frame, value)
        if call is not None:
            raised = not returned_normally(frame)
            event = {
                "kind": "return",
                "stage": self.stage,
                "call": call.identifier,
                "value": "" if raised else short_repr(value),
                "raised": raised,
            }
            full = None if raised else full_repr(value)
            if full is not None:
                event["full"] = full
            self.recording.events.append(event)
            if raised:
                self.raised = (frame.f_code, event)
            if given_response and not raised and is_response_form(value) and repr(value) not in self.response_forms:
                self.response_forms.add(repr(value))
                self.recording.events.append({
                    "kind": "form",
                    "stage": self.stage,
                    "call": call.identifier,
                    "value": short_repr(value),
                    "type": type(value).__name__,
                })
        evaluation = self.evaluation_frames.pop(frame, None)
        if evaluation is not None:
            (criterion, node) = evaluation
            reached = list(value) if isinstance(value, dict) else []
            self.recording.events.append({
                "kind": "evaluated", "stage": self.stage, "criterion": criterion, "node": node, "reached": reached
            })

    def _caller(self, frame: FrameType) -> tuple[Call | None, int] | None:
        caller = frame.f_back
        while caller is not None and caller not in self.frames:
            caller = caller.f_back
        if caller is None:
            return None
        return self.frames[caller]

    def profile(self, frame: FrameType, event: str, arg: Any) -> None:
        module = frame.f_globals.get("__name__", "")
        qualname = frame.f_code.co_qualname
        if event == "return":
            if qualname == "feedback_procedure_generator" and module.startswith("app.context."):
                self.recording.criteria_graphs.update(arg)
            if self.record_values:
                self._record_return(frame, arg)
            self.frames.pop(frame, None)
            return
        if event != "call":
            return
        if module == "app.evaluation" and qualname == "_evaluate":
            self.frames[frame] = (None, 0)
            return
        if self.record_values:
            self._record_evaluation(frame)
        if not module.startswith(("app.", "lambdafeedback.")):
            return
        caller = self._caller(frame)
        if caller is None:
            return
        (parent, depth) = caller
        if qualname in HIDDEN_FUNCTIONS or any(part in qualname for part in HIDDEN_FUNCTION_PARTS):
            self.frames[frame] = caller
            return
        if depth >= self.depth:
            self.frames[frame] = (parent, depth + 1)
            return
        key = (self.stage if parent is None else parent.identifier, module, qualname)
        call = self.recording.calls.get(key)
        if call is None:
            call = Call(f"call_{len(self.recording.calls)}", module, qualname, self.stage, parent, depth + 1)
            if self.record_values:
                call.doc = first_doc_paragraph(frame)
                call.source = source_location(frame)
            self.recording.calls[key] = call
        else:
            call.count += 1
        self.frames[frame] = (call, depth + 1)
        if self.record_values:
            self._record_call(frame, call)


def record(
    response: str, answer: str, params: dict[str, Any], depth: int = CALL_DEPTH, record_values: bool = False
) -> tuple[Recording, dict[str, Any]]:
    """Runs `evaluation_function` on the example and returns what happened, and the result.

    See `Recorder` for `depth` and `record_values`.
    """
    recorder = Recorder(depth, record_values, response)
    logger = logging.getLogger(evaluation.__name__)
    logger.addHandler(recorder)
    monitoring = sys.monitoring
    unwind = monitoring.events.PY_UNWIND
    if record_values:
        monitoring.use_tool_id(monitoring.PROFILER_ID, "generate_process_graphs")
        monitoring.register_callback(monitoring.PROFILER_ID, unwind, recorder.unwind)
        monitoring.set_events(monitoring.PROFILER_ID, unwind)
    sys.setprofile(recorder.profile)
    try:
        result = evaluation.evaluation_function(response, answer, dict(params), include_test_data=True)
    finally:
        sys.setprofile(None)
        logger.removeHandler(recorder)
        if record_values:
            monitoring.set_events(monitoring.PROFILER_ID, monitoring.events.NO_EVENTS)
            monitoring.register_callback(monitoring.PROFILER_ID, unwind, None)
            monitoring.free_tool_id(monitoring.PROFILER_ID)
    return (recorder.recording, result)


def stage_description(stage: str, recording: Recording, params: dict[str, Any], result: dict[str, Any]) -> str:
    """What `stage` did for the example, or why it didn't run."""
    ran = stage in recording.stages or stage == FIRST_STAGE
    if stage == "parse_latex" and not ran:
        return "Not run: is_latex is not set."
    elif not ran and recording.early_return:
        return "Not run: the response could not be parsed."
    elif stage == FIRST_STAGE:
        return "Copies the tolerance aliases to rtol and atol and creates the EvaluationResult."
    elif stage == "determine_context":
        context = "physical_quantity" if params.get("physical_quantity", False) is True else "symbolic"
        return f"Chooses the {context} context and adds its default parameters and criteria."
    elif stage == "parse_latex":
        return "Reads the LaTeX response as SymPy syntax."
    elif stage == "parse_reserved_expressions":
        if recording.early_return:
            return "Preprocesses and parses the response and answer. The response could not be parsed, so the " \
                "result is returned with its feedback."
        return "Preprocesses and parses the response and answer."
    elif stage == "preview":
        return "Sets the LaTeX and simplified forms of the response."
    elif stage == "parse_criteria":
        return "Parses the criteria: " + ", ".join(f"`{criterion}`" for criterion in recording.criteria_graphs) + "."
    elif stage == "generate_feedback_procedures":
        return "Builds the criteria graph for each criterion."
    elif stage == "generate_feedback":
        return "Runs each criteria graph on the response; the path it took is highlighted."
    elif stage == "serialise":
        return "Serialises the result."
    return ""


def result_label(result: dict[str, Any]) -> str:
    tags = ", ".join(result["tags"])
    return _node_label("Result", f"is_correct: {result['is_correct']}; tags: {tags}")


def add_stage_nodes(dot: pydot.Graph, recording: Recording, params: dict[str, Any], result: dict[str, Any]) -> dict[str, str]:
    """Adds a node for each stage, in order, then the result, and returns each stage's node identifier."""
    identifiers = {}
    previous = None
    for (index, stage) in enumerate(all_stages()):
        identifier = f"stage_{index}"
        identifiers[stage] = identifier
        ran = stage in recording.stages or stage == FIRST_STAGE
        style = STAGE_STYLE if ran else SKIPPED_STAGE_STYLE
        label = _node_label(stage, stage_description(stage, recording, params, result))
        dot.add_node(pydot.Node(identifier, label=label, **style))
        if previous is not None:
            dot.add_edge(pydot.Edge(previous, identifier, **PIPELINE_EDGE_STYLE))
        previous = identifier
    dot.add_node(pydot.Node("result", label=result_label(result), **RESULT_STYLE))
    dot.add_edge(pydot.Edge(previous, "result", **PIPELINE_EDGE_STYLE))
    return identifiers


def process_to_dot(recording: Recording, params: dict[str, Any], result: dict[str, Any]) -> pydot.Dot:
    """The stages of the evaluation, with the criteria graphs it ran and the path the response took through them."""
    dot = new_drawing()
    dot.set("compound", "true")
    stages = add_stage_nodes(dot, recording, params, result)
    for (index, (criterion, graph)) in enumerate(recording.criteria_graphs.items()):
        cluster = pydot.Cluster(f"criteria_{index}", label=f"Criteria graph: {html.escape(criterion)}", color="#9E9E9E")
        identifiers = add_criteria_graph(cluster, graph, prefix=f"criteria_{index}_", reached_criteria=result["tags"])
        dot.add_subgraph(cluster)
        for start in graph.starting_evaluations(criterion + "_TRUE"):
            dot.add_edge(pydot.Edge(stages["generate_feedback"], identifiers[start], style="dashed", lhead=cluster.get_name()))
    return dot


def shown_parent(call: Call, hide_internals: bool) -> Call | None:
    """The caller drawn for `call`: its parent, or with `hide_internals` its nearest caller that is not internal (see
    `Call.internal`); None for a call made by `_evaluate`.
    """
    parent = call.parent
    while hide_internals and parent is not None and parent.internal:
        parent = parent.parent
    return parent


def calls_to_dot(
    recording: Recording,
    params: dict[str, Any],
    result: dict[str, Any],
    depth: int = CALL_DEPTH,
    hide_internals: bool = False,
) -> pydot.Dot:
    """The stages of the evaluation down the left, each with the functions called during it to its right, down to
    `depth` calls below `_evaluate`.

    With `hide_internals`, dunder methods are left out, and the calls they made are drawn under their caller.
    """
    dot = new_drawing()
    dot.set("rankdir", "LR")
    pipeline = pydot.Subgraph("pipeline", rank="same")
    dot.add_subgraph(pipeline)
    stages = add_stage_nodes(pipeline, recording, params, result)
    clusters = {}
    for (index, stage) in enumerate(all_stages()):
        cluster = pydot.Cluster(f"stage_cluster_{index}", label="", color="#9E9E9E")
        clusters[stage] = cluster
        dot.add_subgraph(cluster)
    for call in recording.calls.values():
        if call.depth > depth or (hide_internals and call.internal):
            continue
        label = call.qualname if call.count == 1 else f"{call.qualname} ×{call.count}"
        clusters[call.stage].add_node(pydot.Node(call.identifier, label=_node_label(label, call.module), **CALL_STYLE))
        parent = shown_parent(call, hide_internals)
        caller = stages[call.stage] if parent is None else parent.identifier
        dot.add_edge(pydot.Edge(caller, call.identifier))
    return dot


def main() -> None:
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    for (name, response, answer, params) in EXAMPLES:
        (recording, result) = record(response, answer, params)
        process_to_dot(recording, params, result).write_svg(str(OUTPUT_DIRECTORY / f"{name}.svg"))
        calls_to_dot(recording, params, result).write_svg(str(OUTPUT_DIRECTORY / f"{name}_calls.svg"))
        print(f"Generated {name}: stages {', '.join(recording.stages)}; tags {', '.join(result['tags'])}")


if __name__ == "__main__":
    main()
