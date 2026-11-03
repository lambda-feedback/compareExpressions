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

# The longest an argument or return value recorded for the process animation gets before it is cut short.
VALUE_LENGTH = 200

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


@dataclass
class Recording:
    """What happened during one `evaluation_function` call.

    `events` is filled only when values are recorded (see `Recorder`): every stage entered, call made, value returned
    and criteria graph evaluation run, in order, as JSON-ready dictionaries.
    """

    stages: list[str] = field(default_factory=list)
    early_return: bool = False
    calls: dict[tuple[Any, ...], Call] = field(default_factory=dict)
    criteria_graphs: dict[str, CriteriaGraph] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)


def short_repr(value: Any) -> str:
    """`repr(value)` without memory addresses, cut short at `VALUE_LENGTH` characters."""
    try:
        text = repr(value)
    except (AttributeError, TypeError, ValueError, KeyError):
        # Objects whose `__init__` is still running can fail to give a repr.
        text = f"<{type(value).__name__}>"
    text = re.sub(r" at 0x[0-9a-f]+", "", text)
    if len(text) > VALUE_LENGTH:
        return text[:VALUE_LENGTH - 1] + "…"
    return text


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
    - the arguments and return value of each call, and whether it raised an exception instead of returning;
    - the evaluations each criteria graph runs, and the criteria each one reports;
    - each new form of the response (see `is_response_form`): the value returned by a call that was given the response,
      or an earlier form of it, as an argument.
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

    def emit(self, record: logging.LogRecord) -> None:
        event = json.loads(record.getMessage())
        if event["event"] == "stage_start":
            self.stage = event["stage"]
            self.recording.stages.append(self.stage)
            if self.record_values:
                self.recording.events.append({"kind": "stage", "stage": self.stage})
        elif event["event"] == "evaluation_end":
            self.recording.early_return = event["early_return"]

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
                shown_arguments.append((name, f"<{type(value).__name__}>"))
            else:
                shown_arguments.append((name, short_repr(value)))
        self.recording.events.append({
            "kind": "call", "stage": self.stage, "call": call.identifier, "arguments": shown_arguments
        })

    def _record_return(self, frame: FrameType, value: Any) -> None:
        call = self.call_frames.pop(frame, None)
        given_response = frame in self.response_frames
        self.response_frames.discard(frame)
        if call is not None:
            raised = not returned_normally(frame)
            self.recording.events.append({
                "kind": "return",
                "stage": self.stage,
                "call": call.identifier,
                "value": "" if raised else short_repr(value),
                "raised": raised,
            })
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
    sys.setprofile(recorder.profile)
    try:
        result = evaluation.evaluation_function(response, answer, dict(params), include_test_data=True)
    finally:
        sys.setprofile(None)
        logger.removeHandler(recorder)
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


def calls_to_dot(
    recording: Recording, params: dict[str, Any], result: dict[str, Any], depth: int = CALL_DEPTH
) -> pydot.Dot:
    """The stages of the evaluation down the left, each with the functions called during it to its right, down to
    `depth` calls below `_evaluate`.
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
        if call.depth > depth:
            continue
        label =call.qualname if call.count == 1 else f"{call.qualname} ×{call.count}"
        clusters[call.stage].add_node(pydot.Node(call.identifier, label=_node_label(label, call.module), **CALL_STYLE))
        caller = stages[call.stage] if call.parent is None else call.parent.identifier
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
