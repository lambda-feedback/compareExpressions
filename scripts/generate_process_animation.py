"""Generates `build/process_animation.html`: an interactive page that animates the process graphs of
`scripts/generate_process_graphs.py`.

Each example (those of the static figures, and `EXTRA_EXAMPLES`) is run through `evaluation_function` while recording
every call down to `MAX_DEPTH` calls below `_evaluate`, with its arguments and return value or exception, the forms the
response takes, the parameters, the criteria and the evaluations each criteria graph runs. The calls graph is laid out
with graphviz once for each depth, with and without the criteria graphs and the internal (dunder) calls, and the page
grows it in the order the functions were called. A side panel shows each step's details, and these can be switched on
and off on the page.

The page is a build output and is not committed. Run from the repository root with
`python -m scripts.generate_process_animation` (it needs graphviz, i.e. `dot`), then open the page in a browser.
"""
from __future__ import annotations

import base64
import gzip
import html
import json
import re
from pathlib import Path
from typing import Any

import pydot

from scripts.generate_criteria_graphs import _node_label, add_criteria_graph
from scripts.generate_process_graphs import (
    EXAMPLES,
    FIRST_STAGE,
    Recording,
    all_stages,
    calls_to_dot,
    record,
    shown_parent,
    stage_description,
)

OUTPUT_FILE = Path(__file__).resolve().parent.parent / "build" / "process_animation.html"

# Examples shown only in the animation, for the parts of the criteria chain the static figures' examples don't reach:
# a response that is not correct, more than one criterion, and a criterion without a template of its own.
EXTRA_EXAMPLES: list[tuple[str, str, str, dict[str, Any]]] = [
    ("process_symbolic_incorrect", "x + 2", "x + 1", {}),
    ("process_symbolic_syntactical_comparison", "1 + x", "x + 1", {"syntactical_comparison": True}),
    ("process_symbolic_default_template", "2*x + 1", "x + 1", {"criteria": "response contains x"}),
]

# The deepest calls below `_evaluate` recorded, and the deepest the page can show.
MAX_DEPTH = 5

# The depth the page starts at: the depth of the static calls figures.
START_DEPTH = 2

# How many calls of each function keep their arguments and return value, for the details of a clicked node.
INVOCATION_VALUES = 20

CRITERION_STYLE = {"shape": "note", "style": "filled", "fillcolor": "#FFF8E1", "color": "#8D6E63"}
CRITERION_EDGE_STYLE = {"color": "#8D6E63", "fontcolor": "#5D4037", "fontname": "Helvetica", "fontsize": "10"}


def example_title(name: str) -> str:
    """The name shown on the page for the example `name`, e.g. "Physical quantity" for `process_physical_quantity`."""
    return name.removeprefix("process_").replace("_", " ").capitalize()


def stage_identifier(stage: str) -> str:
    """The graphviz identifier `add_stage_nodes` gives the node of `stage`."""
    return f"stage_{all_stages().index(stage)}"


def build_steps(recording: Recording) -> tuple[list[dict[str, Any]], dict[str, dict[str, list[Any]]], list[dict[str, Any]]]:
    """The steps of the animation, the index of the event of each call of each function, and the forms the response
    took, from the events in `recording`.

    Each step is a stage being entered, a function called for the first time from its caller (a node of the calls
    graph appearing), the criteria being parsed, a template building a criteria graph, a criteria graph evaluation, or
    the result. Later calls of the same function only raise its count, so they are not steps of their own.

    The invocations of each call are the index of the event of each, and the values of the first `INVOCATION_VALUES`.
    """
    steps: list[dict[str, Any]] = [{"kind": "stage", "stage": FIRST_STAGE, "event": -1, "depth": 0}]
    invocations: dict[str, dict[str, list[Any]]] = {}
    forms: list[dict[str, Any]] = []
    calls = {call.identifier: call for call in recording.calls.values()}
    # The values of each call still running, and its step, or None for a call that is not the first of its function.
    running: list[tuple[dict[str, Any], dict[str, Any] | None]] = []
    evaluation_step: dict[str, Any] = {}
    for (index, event) in enumerate(recording.events):
        kind = event["kind"]
        if kind == "stage":
            steps.append({"kind": "stage", "stage": event["stage"], "event": index, "depth": 0})
        elif kind == "call":
            call_invocations = invocations.setdefault(event["call"], {"events": [], "values": []})
            call_invocations["events"].append(index)
            values = {"event": index, "arguments": event["arguments"], "returned": "", "raised": False}
            # Only the first calls keep their values, as some functions are called over a thousand times
            if len(call_invocations["values"]) < INVOCATION_VALUES:
                call_invocations["values"].append(values)
            if len(call_invocations["events"]) == 1:
                step = {
                    "kind": "call",
                    "call": event["call"],
                    "stage": event["stage"],
                    "depth": calls[event["call"]].depth,
                    "event": index,
                    "arguments": event["arguments"],
                    "returned": "",
                    "raised": False,
                }
                steps.append(step)
                running.append((values, step))
            else:
                running.append((values, None))
        elif kind == "return":
            (values, step) = running.pop()
            outcome = {"returned": event["value"], "raised": event["raised"]}
            if "full" in event:
                outcome["returnedFull"] = event["full"]
            if "exception" in event:
                outcome["exception"] = event["exception"]
            values.update(outcome)
            if step is not None:
                step.update(outcome)
        elif kind == "criteria":
            steps.append({
                "kind": "criteria",
                "depth": 0,
                "event": index,
                "criteria": [criterion["identifier"] for criterion in event["criteria"]],
            })
        elif kind == "template":
            steps.append({"kind": "template", "depth": 0, "event": index, "criterion": event["criterion"]})
        elif kind == "evaluate":
            evaluation_step = {
                "kind": "evaluate",
                "criterion": event["criterion"],
                "node": event["node"],
                "depth": 0,
                "event": index,
                "reached": [],
            }
            steps.append(evaluation_step)
        elif kind == "evaluated":
            evaluation_step["reached"] = event["reached"]
        elif kind == "form":
            forms.append({"event": index, "call": event["call"], "value": event["value"], "type": event["type"]})
        elif kind == "parameters" or kind == "feedback":
            # Shown in the panel rather than as steps (see `parameters_data` and `feedback_data`)
            continue
        else:
            raise ValueError(f"Unknown event kind {kind!r}.")
    steps.append({"kind": "result", "event": len(recording.events), "depth": 0})
    for (index, step) in enumerate(steps):
        step["index"] = index
    return (steps, invocations, forms)


def criteria_chain(recording: Recording, params: dict[str, Any]) -> dict[str, Any]:
    """How the example's criteria graphs came about: where the criteria string came from, the string before and after
    preprocessing, and for each criterion (by its identifier) its parse, the template that built its graph and the
    index of its graph's cluster.

    Empty when the evaluation stopped before parsing the criteria.
    """
    criteria_event = next((event for event in recording.events if event["kind"] == "criteria"), None)
    if criteria_event is None:
        return {}
    if "criteria" in params:
        source = 'Given in params["criteria"].'
    else:
        context = "physical_quantity" if params.get("physical_quantity", False) is True else "symbolic"
        source = f"Not given in params, so the default criteria of the {context} context."
    if params.get("syntactical_comparison", False) is True:
        source += ' syntactical_comparison adds "response written as answer".'
    indices = {criterion: index for (index, criterion) in enumerate(recording.criteria_graphs)}
    criteria = {}
    for criterion in criteria_event["criteria"]:
        criteria[criterion["identifier"]] = {
            "index": indices.get(criterion["identifier"]),
            "label": criterion["label"],
            "tree": criterion["tree"],
        }
    for event in recording.events:
        if event["kind"] == "template":
            criteria[event["criterion"]].update({
                "template": event["template"],
                "templateLabel": event["label"],
                "call": event["call"],
                "evaluations": event["evaluations"],
            })
    return {
        "source": source,
        "original": criteria_event["original"],
        "preprocessed": criteria_event["preprocessed"],
        "criteria": criteria,
    }


def visible_call(recording: Recording, identifier: str, depth: int, hide_internals: bool) -> str:
    """The identifier of the call `identifier`, or of its nearest caller, that is drawn down to `depth`, with or
    without the internal calls.
    """
    calls = {call.identifier: call for call in recording.calls.values()}
    call = calls[identifier]
    while call.parent is not None and (call.depth > depth or (hide_internals and call.internal)):
        call = call.parent
    return call.identifier


def calls_layout(
    recording: Recording,
    params: dict[str, Any],
    result: dict[str, Any],
    chain: dict[str, Any],
    depth: int,
    with_criteria: bool,
    hide_internals: bool,
) -> tuple[pydot.Dot, dict[str, dict[str, str]]]:
    """The calls graph down to `depth`, with the graphviz identifier of each criteria graph node by criterion and node
    label.

    With `with_criteria`, each criterion gets a node in the `parse_criteria` stage, with an edge to the template call
    its parse label chose, and each criteria graph is drawn with an edge from that template call, which built it, and
    from the `generate_feedback` stage, which ran it. Only the edge from the stage places the graph, so it is drawn
    next to the stage rather than past the template call.

    With `hide_internals`, the internal calls are left out (see `calls_to_dot`).
    """
    dot = calls_to_dot(recording, params, result, depth, hide_internals)
    identifiers: dict[str, dict[str, str]] = {}
    # Without criteria, i.e. when the evaluation stopped before parsing them, there is nothing to add
    if not with_criteria or not chain:
        return (dot, identifiers)
    dot.set("compound", "true")
    stages = all_stages()
    parse_cluster = dot.get_subgraph(f"cluster_stage_cluster_{stages.index('parse_criteria')}")[0]
    parser_call = next(call.identifier for call in recording.calls.values() if call.qualname == "create_criteria_dict")
    for (index, (criterion, graph)) in enumerate(recording.criteria_graphs.items()):
        details = chain["criteria"][criterion]
        template_call = visible_call(recording, details["call"], depth, hide_internals)
        criterion_node = f"criterion_{index}"
        parse_cluster.add_node(pydot.Node(
            criterion_node, label=_node_label(criterion, f"parse label: {details['label']}"), **CRITERION_STYLE
        ))
        dot.add_edge(pydot.Edge(parser_call, criterion_node, **CRITERION_EDGE_STYLE))
        choice = details["label"] if details["templateLabel"] is not None else "default"
        dot.add_edge(pydot.Edge(criterion_node, template_call, label=html.escape(choice), **CRITERION_EDGE_STYLE))
        title = f"Criteria graph: {criterion} (built by {details['template']})"
        cluster = pydot.Cluster(f"criteria_{index}", label=html.escape(title), color="#9E9E9E")
        identifiers[criterion] = add_criteria_graph(cluster, graph, prefix=f"criteria_{index}_")
        dot.add_subgraph(cluster)
        for start in graph.starting_evaluations(criterion + "_TRUE"):
            dot.add_edge(pydot.Edge(
                template_call,
                identifiers[criterion][start],
                label="builds",
                style="dashed",
                lhead=cluster.get_name(),
                constraint="false",
                **CRITERION_EDGE_STYLE,
            ))
            dot.add_edge(pydot.Edge(
                stage_identifier("generate_feedback"),
                identifiers[criterion][start],
                label="runs",
                style="dashed",
                lhead=cluster.get_name(),
                fontname="Helvetica",
                fontsize="10",
            ))
    return (dot, identifiers)


def svg_markup(dot: pydot.Dot) -> str:
    """`dot` drawn as an SVG element, gzipped and base64 encoded (the page unpacks it).

    The SVG is left without the XML declaration and doctype in front of it, or the comments graphviz writes before each
    node and edge (their titles hold the same names). The 20 layouts of an example are mostly the same markup, so
    gzipping them makes the page about a tenth of the size.
    """
    svg = dot.create(format="svg").decode("utf-8")
    svg = re.sub(r"<!--.*?-->\n?", "", svg[svg.index("<svg"):], flags=re.DOTALL)
    return base64.b64encode(gzip.compress(svg.encode("utf-8"), mtime=0)).decode("ascii")


def criteria_data(recording: Recording, identifiers: dict[str, dict[str, str]]) -> dict[str, Any]:
    """The graphviz identifier, kind and details of each node of each criteria graph, by criterion and node label."""
    data: dict[str, Any] = {}
    for (criterion, graph) in recording.criteria_graphs.items():
        nodes = {}
        groups = [("evaluation", graph.evaluations), ("criterion", graph.criteria), ("output", graph.outputs)]
        for (kind, group) in groups:
            for (label, node) in group.items():
                nodes[label] = {
                    "id": identifiers[criterion][label], "kind": kind, "summary": node.summary, "details": node.details
                }
        data[criterion] = nodes
    return data


def parameters_data(recording: Recording) -> dict[str, Any]:
    """The parameters `_build_parameters` completed: the index of its event, the ones it was given and the ones it
    added. Empty when it wasn't called.
    """
    for (index, event) in enumerate(recording.events):
        if event["kind"] == "parameters":
            return {"event": index, "given": event["given"], "added": event["added"]}
    return {}


def feedback_data(recording: Recording, identifiers: dict[str, dict[str, str]]) -> dict[str, dict[str, Any]]:
    """For each tag a criteria graph exported, the criterion whose graph exported it first, its feedback text and the
    graphviz identifier of its criteria node.
    """
    feedback: dict[str, dict[str, Any]] = {}
    for event in recording.events:
        if event["kind"] != "feedback" or event["criterion"] is None:
            continue
        for (tag, text) in event["feedback"]:
            if tag not in feedback:
                feedback[tag] = {
                    "criterion": event["criterion"],
                    "text": text,
                    "node": identifiers.get(event["criterion"], {}).get(tag),
                }
    return feedback


def stage_durations(recording: Recording) -> dict[str, float]:
    """How long each stage that ran took, in milliseconds: from its start to the next stage's, or to the end of the
    evaluation for the last one.
    """
    starts = [(FIRST_STAGE, 0.0)] + list(recording.stage_times.items())
    durations = {}
    for (position, (stage, start)) in enumerate(starts):
        if position + 1 < len(starts):
            durations[stage] = round(starts[position + 1][1] - start, 1)
        elif recording.duration_ms is not None:
            durations[stage] = round(recording.duration_ms - start, 1)
    return durations


def example_data(name: str, response: str, answer: str, params: dict[str, Any]) -> dict[str, Any]:
    """Everything the page needs to animate one example."""
    (recording, result) = record(response, answer, params, depth=MAX_DEPTH, record_values=True)
    (steps, invocations, forms) = build_steps(recording)
    chain = criteria_chain(recording, params)
    layouts = {}
    criteria_identifiers: dict[str, dict[str, str]] = {}
    for depth in range(1, MAX_DEPTH + 1):
        for with_criteria in (False, True):
            for hide_internals in (False, True):
                (dot, identifiers) = calls_layout(
                    recording, params, result, chain, depth, with_criteria, hide_internals
                )
                key = f"{depth}{'c' if with_criteria else ''}{'h' if hide_internals else ''}"
                layouts[key] = svg_markup(dot)
                if with_criteria:
                    criteria_identifiers = identifiers
    calls = {}
    for call in recording.calls.values():
        parent = shown_parent(call, hide_internals=True)
        calls[call.identifier] = {
            "qualname": call.qualname,
            "module": call.module,
            "depth": call.depth,
            "stage": call.stage,
            "parent": None if call.parent is None else call.parent.identifier,
            # The caller drawn when the internal calls are hidden
            "shownParent": None if parent is None else parent.identifier,
            "internal": call.internal,
            "doc": call.doc,
            "source": call.source,
        }
    durations = stage_durations(recording)
    return {
        "name": name,
        "title": example_title(name),
        "response": response,
        "answer": answer,
        "params": params,
        "stages": [
            {
                "name": stage,
                "id": stage_identifier(stage),
                "description": stage_description(stage, recording, params, result),
                "duration": durations.get(stage),
            }
            for stage in all_stages()
        ],
        "duration": recording.duration_ms,
        "calls": calls,
        "steps": steps,
        "invocations": invocations,
        "forms": forms,
        "criteria": criteria_data(recording, criteria_identifiers),
        "chain": chain,
        "parameters": parameters_data(recording),
        "feedback": feedback_data(recording, criteria_identifiers),
        "layouts": layouts,
        "result": {
            "is_correct": result["is_correct"],
            "tags": result["tags"],
            "feedback": result["feedback"],
            "response_latex": result.get("response_latex", ""),
            "response_simplified": result.get("response_simplified", ""),
        },
    }


def main() -> None:
    examples = []
    for (name, response, answer, params) in EXAMPLES + EXTRA_EXAMPLES:
        examples.append(example_data(name, response, answer, params))
        print(f"Recorded {name}: {len(examples[-1]['steps'])} steps")
    data = json.dumps({"examples": examples, "maxDepth": MAX_DEPTH, "startDepth": START_DEPTH})
    # Keeps the data from closing the script element it is in.
    data = data.replace("</", "<\\/")
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(PAGE.replace("__DATA__", data), encoding="utf-8")
    print(f"Generated {OUTPUT_FILE}")


PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Evaluation process animation</title>
<style>
:root {
  --bg: #f5f6fa;
  --surface: #ffffff;
  --text: #1c1f2e;
  --muted: #5d6275;
  --border: #d8dbe6;
  --accent: #2f3c86;
  --accent-soft: #e8eaf6;
  --highlight: #e65100;
  --highlight-soft: #fff3e0;
  --evaluation: #00b8d4;
  --code-bg: #f0f1f6;
  --good: #2e7d32;
  --bad: #c62828;
  --graph-filter: none;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #14161f;
    --surface: #1d2030;
    --text: #e6e8f2;
    --muted: #9ba1b8;
    --border: #33384d;
    --accent: #9fa8f0;
    --accent-soft: #272c48;
    --highlight: #ffa25c;
    --highlight-soft: #3a2a1c;
    --code-bg: #262a3c;
    --good: #81c784;
    --bad: #ef9a9a;
    --graph-filter: invert(0.92) hue-rotate(180deg);
  }
}
:root[data-theme="dark"] {
  --bg: #14161f;
  --surface: #1d2030;
  --text: #e6e8f2;
  --muted: #9ba1b8;
  --border: #33384d;
  --accent: #9fa8f0;
  --accent-soft: #272c48;
  --highlight: #ffa25c;
  --highlight-soft: #3a2a1c;
  --code-bg: #262a3c;
  --good: #81c784;
  --bad: #ef9a9a;
  --graph-filter: invert(0.92) hue-rotate(180deg);
}
* { box-sizing: border-box; }
html, body { height: 100%; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font: 14px/1.45 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  display: flex;
  flex-direction: column;
}
code, .mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 12.5px; }
header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 20px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border);
  background: var(--surface);
}
header h1 { font-size: 16px; margin: 0; }
.inputs { display: flex; flex-wrap: wrap; gap: 6px 16px; color: var(--muted); }
.inputs code { color: var(--text); background: var(--code-bg); padding: 1px 6px; border-radius: 4px; }
select, button {
  font: inherit;
  color: var(--text);
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 4px 10px;
  min-height: 32px;
}
button { cursor: pointer; }
button:hover, select:hover { border-color: var(--accent); }
button:focus-visible, select:focus-visible, input:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }
main {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 400px;
}
#graph-wrap { position: relative; min-height: 0; border-right: 1px solid var(--border); }
#graph {
  position: absolute;
  inset: 0;
  overflow: auto;
  background: white;
  filter: var(--graph-filter);
}
#graph svg { display: block; height: auto; }
.zoom { display: flex; gap: 4px; }
.zoom button { min-width: 32px; padding: 4px 8px; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.15); }
aside {
  min-height: 0;
  overflow-y: auto;
  background: var(--surface);
  padding: 14px 16px 24px;
}
aside section { margin-bottom: 18px; }
aside h2 {
  font-size: 11px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--muted);
  margin: 0 0 6px;
}
.chip {
  display: inline-block;
  padding: 1px 8px;
  border-radius: 999px;
  background: var(--accent-soft);
  color: var(--accent);
  font-weight: 600;
  font-size: 12px;
}
.chip.evaluation { background: transparent; border: 1px solid var(--evaluation); color: var(--text); }
.muted { color: var(--muted); }
.call-name { font-size: 15px; font-weight: 600; word-break: break-all; }
.stack { display: flex; flex-wrap: wrap; gap: 2px 4px; color: var(--muted); font-size: 12px; margin-top: 4px; }
.stack span::after { content: "›"; margin-left: 4px; }
.stack span:last-child::after { content: ""; }
.values { display: grid; grid-template-columns: max-content minmax(0, 1fr); gap: 4px 10px; margin-top: 8px; }
.values dt { color: var(--muted); font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 12.5px; }
.values dd {
  margin: 0;
  background: var(--code-bg);
  padding: 2px 6px;
  border-radius: 4px;
  word-break: break-all;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12.5px;
}
.returned { margin-top: 8px; padding: 6px 8px; border-left: 3px solid var(--accent); background: var(--code-bg); word-break: break-all; }
.returned.raised { border-left-color: var(--bad); color: var(--bad); }
.forms { list-style: none; margin: 0; padding: 0; }
.forms li { padding: 5px 0 5px 12px; border-left: 2px solid var(--border); position: relative; }
.forms li::before {
  content: "";
  position: absolute;
  left: -5px;
  top: 11px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--border);
}
.forms li.latest { border-left-color: var(--highlight); }
.forms li.latest::before { background: var(--highlight); }
.forms .value { background: var(--code-bg); padding: 1px 6px; border-radius: 4px; word-break: break-all; }
.forms .via { font-size: 12px; color: var(--muted); }
.new-badge { font-size: 10px; font-weight: 700; color: var(--highlight); margin-left: 4px; text-transform: uppercase; }
.reached-list { margin: 6px 0 0; padding-left: 18px; }
.result-box { border: 1px solid var(--border); border-radius: 8px; padding: 10px 12px; }
.result-box .verdict { font-weight: 700; font-size: 15px; }
.verdict.correct { color: var(--good); }
.verdict.incorrect { color: var(--bad); }
footer {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 16px;
  padding: 10px 16px;
  border-top: 1px solid var(--border);
  background: var(--surface);
}
.transport { display: flex; align-items: center; gap: 6px; flex: 1 1 360px; min-width: 0; }
.transport input[type="range"] { flex: 1; min-width: 80px; accent-color: var(--highlight); }
#counter { min-width: 92px; text-align: right; color: var(--muted); font-variant-numeric: tabular-nums; }
.toggles { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 14px; }
.toggles label { display: inline-flex; align-items: center; gap: 5px; cursor: pointer; }
.toggles input[type="checkbox"] { accent-color: var(--accent); width: 16px; height: 16px; }

/* States of the graphviz nodes and edges */
#graph g.is-hidden { visibility: hidden; }
#graph g.is-waiting { opacity: 0.28; }
#graph g.appear { animation: appear 0.5s ease-out; }
@keyframes appear { from { opacity: 0; } to { opacity: 1; } }
#graph g.draw > path { stroke-dasharray: 1; stroke-dashoffset: 1; animation: draw 0.45s ease-out forwards; }
#graph g.draw > polygon { opacity: 0; animation: appear 0.2s 0.4s ease-out forwards; }
@keyframes draw { to { stroke-dashoffset: 0; } }
#graph g.is-current > :is(polygon, path, ellipse):first-of-type {
  stroke: #e65100;
  stroke-width: 4px;
  filter: drop-shadow(0 0 5px rgba(230, 81, 0, 0.55));
}
#graph g.is-stack > :is(polygon, path, ellipse):first-of-type { stroke: #fb8c00; stroke-width: 2.5px; stroke-dasharray: 5 3; }
#graph g.is-visited > :is(polygon, path, ellipse):first-of-type { stroke: #00b8d4; stroke-width: 4px; }
#graph g.is-reached > :is(polygon, path, ellipse):first-of-type { stroke: #e65100; stroke-width: 3px; }
#graph g.edge.is-reached > path { stroke: #e65100; stroke-width: 2.5px; }
#graph g.edge.is-reached > polygon { stroke: #e65100; fill: #e65100; }
#graph g.node:not(.is-hidden) { cursor: pointer; }
#graph g.node:not(.is-hidden):hover > :is(polygon, path, ellipse):first-of-type { stroke-width: 2.5px; }
#graph g.is-pinned > :is(polygon, path, ellipse):first-of-type { stroke: #7b1fa2; stroke-width: 4px; stroke-dasharray: none; }

.pinned { border: 1px solid var(--border); border-left: 3px solid #ab47bc; border-radius: 8px; padding: 10px 12px; }
.pinned-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 8px; }
.pinned-head button { min-height: 26px; padding: 0 8px; }
.link { color: var(--accent); background: none; border: none; padding: 0; min-height: 0; text-decoration: underline; cursor: pointer; }
.invocations { list-style: none; margin: 8px 0 0; padding: 0; display: grid; gap: 8px; }
.invocations li { border-top: 1px solid var(--border); padding-top: 6px; }
.chain { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }
.chain > li { padding-left: 12px; border-left: 2px solid var(--border); }
.chain > li.is-focus { border-left-color: var(--highlight); }
.chain .step-label { font-size: 12px; color: var(--muted); }
.chain code { background: var(--code-bg); padding: 1px 6px; border-radius: 4px; word-break: break-word; }
.tree {
  margin: 4px 0 0;
  padding: 6px 8px;
  background: var(--code-bg);
  border-radius: 4px;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-word;
}
.status-good { color: var(--good); font-weight: 600; }
.status-bad { color: var(--bad); font-weight: 600; }
.doc { margin: 6px 0 0; }
.source { font-size: 12px; color: var(--muted); }
details.section { margin-bottom: 18px; }
details.section > summary { cursor: pointer; list-style: none; display: flex; align-items: center; gap: 6px; margin-bottom: 6px; }
details.section > summary::-webkit-details-marker { display: none; }
details.section > summary::before { content: "▸"; color: var(--muted); font-size: 11px; transition: transform 0.15s; }
details.section[open] > summary::before { transform: rotate(90deg); }
details.section > summary h2 { margin: 0; }
details.more > summary { cursor: pointer; color: var(--accent); font-family: system-ui, sans-serif; font-size: 12px; }
details.more pre { margin: 4px 0 0; white-space: pre-wrap; word-break: break-all; }
.group-label { font-size: 12px; color: var(--muted); margin-top: 8px; }
.feedback-list { list-style: none; margin: 6px 0 0; padding: 0; display: grid; gap: 8px; }
.feedback-list li { padding-left: 10px; border-left: 2px solid var(--border); }
.feedback-text { margin-top: 2px; }

.graph-tools {
  position: absolute;
  right: 12px;
  top: 12px;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
  z-index: 1;
  max-height: calc(100% - 24px);
}
.legend {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 6px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.15);
  font-size: 12px;
  overflow-y: auto;
  min-height: 0;
}
.legend > summary { cursor: pointer; padding: 5px 10px; font-weight: 600; }
.legend-body { padding: 4px 10px 8px; display: grid; gap: 2px; }
.legend-body .group-label { margin-top: 4px; font-weight: 600; }
.legend-row { display: flex; align-items: center; gap: 8px; }
/* The swatches are drawn in the graph's colours, and recoloured with it in dark mode */
.legend-row svg { flex: none; background: white; filter: var(--graph-filter); border-radius: 2px; }

@media (max-width: 900px) {
  main { grid-template-columns: 1fr; grid-template-rows: minmax(320px, 55vh) auto; overflow-y: auto; }
  #graph-wrap { border-right: none; border-bottom: 1px solid var(--border); }
  aside { overflow: visible; }
}
@media (prefers-reduced-motion: reduce) {
  #graph g.appear, #graph g.draw > path, #graph g.draw > polygon { animation: none; stroke-dashoffset: 0; opacity: 1; }
}
</style>
</head>
<body>
<header>
  <h1>Evaluation process</h1>
  <label>Example <select id="example"></select></label>
  <div class="inputs" id="inputs"></div>
</header>
<main>
  <div id="graph-wrap">
    <div class="graph-tools">
      <div class="zoom">
        <button id="zoom-out" title="Zoom out" aria-label="Zoom out">−</button>
        <button id="zoom-fit" title="Fit to width">Fit</button>
        <button id="zoom-in" title="Zoom in" aria-label="Zoom in">+</button>
      </div>
      <details class="legend" id="legend">
        <summary>Key</summary>
        <div class="legend-body">
          <div class="group-label">Nodes</div>
          <div class="legend-row"><svg width="28" height="18"><rect x="2" y="3" width="24" height="12" rx="4" fill="#E8EAF6" stroke="#2F3C86"/></svg>stage of <code>_evaluate</code></div>
          <div class="legend-row"><svg width="28" height="18"><rect x="2" y="3" width="24" height="12" fill="#FFFFFF" stroke="#212121"/></svg>function call (×N: calls from that caller)</div>
          <div class="legend-row"><svg width="28" height="18"><path d="M2 3h19l5 5v7H2z" fill="#FFF8E1" stroke="#8D6E63"/></svg>criterion parsed from the criteria</div>
          <div class="legend-row"><svg width="28" height="18"><rect x="2" y="3" width="24" height="12" rx="4" fill="#E5F8FB" stroke="#00B8D4"/></svg>criteria graph evaluation</div>
          <div class="legend-row"><svg width="28" height="18"><rect x="2" y="3" width="24" height="12" fill="#FFFFFF" stroke="#212121"/></svg>criteria graph criterion (a tag)</div>
          <div class="legend-row"><svg width="28" height="18"><path d="M2 9l5-6h14l5 6-5 6H7z" fill="#C5CAE9" stroke="#2F3C86"/></svg>output, or the result</div>
          <div class="group-label">States</div>
          <div class="legend-row"><svg width="28" height="18"><rect x="3" y="4" width="22" height="10" fill="#FFFFFF" stroke="#e65100" stroke-width="3" style="filter: drop-shadow(0 0 2px rgba(230, 81, 0, 0.8))"/></svg>the current step</div>
          <div class="legend-row"><svg width="28" height="18"><rect x="3" y="4" width="22" height="10" fill="#FFFFFF" stroke="#fb8c00" stroke-width="2" stroke-dasharray="4 2"/></svg>its callers (the call stack)</div>
          <div class="legend-row"><svg width="28" height="18"><rect x="3" y="4" width="22" height="10" rx="3" fill="#E5F8FB" stroke="#00b8d4" stroke-width="3"/></svg>evaluation run</div>
          <div class="legend-row"><svg width="28" height="18"><rect x="3" y="4" width="22" height="10" fill="#FFFFFF" stroke="#e65100" stroke-width="2.5"/></svg>criterion reached, and its path</div>
          <div class="legend-row"><svg width="28" height="18"><rect x="3" y="4" width="22" height="10" fill="#FFFFFF" stroke="#7b1fa2" stroke-width="3"/></svg>pinned in the panel</div>
          <div class="legend-row"><svg width="28" height="18"><rect x="3" y="4" width="22" height="10" fill="#FFFFFF" stroke="#212121" opacity="0.28"/></svg>not reached yet</div>
          <div class="group-label">Edges</div>
          <div class="legend-row"><svg width="28" height="18"><path d="M2 9h20" stroke="#212121"/><path d="M21 6l5 3-5 3z" fill="#212121"/></svg>calls</div>
          <div class="legend-row"><svg width="28" height="18"><path d="M2 9h20" stroke="#8D6E63"/><path d="M21 6l5 3-5 3z" fill="#8D6E63"/></svg>criterion chooses its template</div>
          <div class="legend-row"><svg width="28" height="18"><path d="M2 9h20" stroke="#8D6E63" stroke-dasharray="4 2"/><path d="M21 6l5 3-5 3z" fill="#8D6E63"/></svg>template builds the graph</div>
          <div class="legend-row"><svg width="28" height="18"><path d="M2 9h20" stroke="#212121" stroke-dasharray="4 2"/><path d="M21 6l5 3-5 3z" fill="#212121"/></svg><code>generate_feedback</code> runs the graph</div>
          <div class="legend-row"><svg width="28" height="18"><path d="M2 9h20" stroke="#212121" stroke-dasharray="1 2"/><path d="M21 6l5 3-5 3z" fill="#212121"/></svg>sufficiency in a criteria graph</div>
        </div>
      </details>
    </div>
    <div id="graph"></div>
  </div>
  <aside id="panel" aria-live="polite"></aside>
</main>
<footer>
  <div class="transport">
    <button id="restart" title="Back to the start" aria-label="Back to the start">⏮</button>
    <button id="back" title="Step back (←)" aria-label="Step back">◀</button>
    <button id="play" title="Play or pause (space)" aria-label="Play">▶ Play</button>
    <button id="forward" title="Step forward (→)" aria-label="Step forward">▶|</button>
    <input type="range" id="scrubber" min="0" value="0" aria-label="Step">
    <span id="counter"></span>
  </div>
  <div class="toggles">
    <label>Speed
      <select id="speed">
        <option value="0.5">0.5×</option>
        <option value="1" selected>1×</option>
        <option value="2">2×</option>
        <option value="4">4×</option>
        <option value="10">10×</option>
      </select>
    </label>
    <label>Call depth <select id="depth"></select></label>
    <label><input type="checkbox" id="show-forms" checked> Response forms</label>
    <label><input type="checkbox" id="show-values" checked> Arguments and returns</label>
    <label><input type="checkbox" id="show-criteria" checked> Criteria graph</label>
    <label title="Leaves out dunder methods such as __init__; the calls they make are drawn under their caller">
      <input type="checkbox" id="hide-internals" checked> Hide internals</label>
  </div>
</footer>
<script type="application/json" id="data">__DATA__</script>
<script>
"use strict";

const DATA = JSON.parse(document.getElementById("data").textContent);
const STORAGE_KEY = "process-animation-settings";

const state = {
  example: 0,
  depth: DATA.startDepth,
  forms: true,
  values: true,
  criteria: true,
  // Whether the internal (dunder) calls are left out of the graph.
  internals: true,
  speed: 1,
  zoom: 0.9,
  // Whether each collapsible panel section is open, by its key, when it differs from `SECTION_DEFAULTS`.
  sections: {},
  // The index in the example's steps of the step shown.
  step: 0,
  // The graphviz title of the node whose details are pinned in the panel, or null.
  pinned: null,
  playing: false,
  timer: null,
  layout: null,
};

// The node and edge groups of the drawn SVG, by their graphviz title.
let nodes = new Map();
let edges = new Map();
let clusters = new Map();

// The SVG markup of each layout of the example `layoutsExample`, by its key, unpacked by `unpackLayouts`.
let layouts = new Map();
let layoutsExample = -1;

// The layouts of the example `index`, which are gzipped and base64 encoded in the data.
async function unpackLayouts(index) {
  const unpacked = new Map();
  for (const [key, packed] of Object.entries(DATA.examples[index].layouts)) {
    const bytes = Uint8Array.from(atob(packed), (character) => character.charCodeAt(0));
    const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream("gzip"));
    unpacked.set(key, await new Response(stream).text());
  }
  return unpacked;
}

function loadSettings() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
    for (const key of ["depth", "forms", "values", "criteria", "internals", "speed", "zoom", "sections"]) {
      if (key in saved) {
        state[key] = saved[key];
      }
    }
  } catch (error) {
    // Storage can be unavailable, e.g. in a private window; the defaults are used.
  }
}

function saveSettings() {
  try {
    const { depth, forms, values, criteria, internals, speed, zoom, sections } = state;
    localStorage.setItem(
      STORAGE_KEY, JSON.stringify({ depth, forms, values, criteria, internals, speed, zoom, sections })
    );
  } catch (error) {
    // The settings are only a convenience, so they are not saved when storage is unavailable.
  }
}

function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function example() {
  return DATA.examples[state.example];
}

function stageOf(stageName) {
  return example().stages.find((stage) => stage.name === stageName);
}

function isShown(step) {
  if (step.kind === "evaluate" || step.kind === "criteria" || step.kind === "template") {
    return state.criteria;
  } else if (step.kind === "call" && state.internals && example().calls[step.call].internal) {
    return false;
  }
  return step.depth <= state.depth;
}

// The caller drawn for the call `callId`: its parent, or its nearest caller that is not internal when the internal
// calls are hidden; null for a call made by `_evaluate`.
function parentOf(callId) {
  const call = example().calls[callId];
  return state.internals ? call.shownParent : call.parent;
}

function shownSteps() {
  return example().steps.filter(isShown);
}

// The shown step at or before the step with index `index`, so that changing a setting keeps the place.
function nearestShownStep(index) {
  const shown = shownSteps();
  let nearest = shown[0];
  for (const step of shown) {
    if (step.index <= index) {
      nearest = step;
    }
  }
  return nearest.index;
}

function callerOf(callId) {
  const parent = parentOf(callId);
  if (parent === null) {
    return stageOf(example().calls[callId].stage).id;
  }
  return parent;
}

function invocationsUpTo(callId, event) {
  let count = 0;
  for (const index of invocationEvents(callId)) {
    if (index <= event) {
      count += 1;
    }
  }
  return count;
}

function invocationEvents(callId) {
  const invocations = example().invocations[callId];
  return invocations === undefined ? [] : invocations.events;
}

// The chain of the criterion `identifier`: its parse, template and graph cluster index.
function chainOf(identifier) {
  return example().chain.criteria[identifier];
}

function firstStepOf(kind) {
  return example().steps.find((step) => step.kind === kind);
}

// Drawing

function drawLayout() {
  const key = String(state.depth) + (state.criteria ? "c" : "") + (state.internals ? "h" : "");
  const layoutId = state.example + ":" + key;
  if (state.layout === layoutId) {
    return;
  }
  state.layout = layoutId;
  const graph = document.getElementById("graph");
  graph.innerHTML = layouts.get(key);
  nodes = new Map();
  edges = new Map();
  clusters = new Map();
  for (const group of graph.querySelectorAll("g.node, g.edge, g.cluster")) {
    const title = group.querySelector(":scope > title");
    if (title === null) {
      continue;
    }
    const name = title.textContent;
    if (group.classList.contains("node")) {
      nodes.set(name, group);
    } else if (group.classList.contains("edge")) {
      edges.set(name, group);
      const path = group.querySelector(":scope > path");
      if (path !== null) {
        path.setAttribute("pathLength", "1");
      }
    } else {
      clusters.set(name, group);
    }
  }
  applyZoom();
}

function applyZoom() {
  const svg = document.querySelector("#graph svg");
  if (svg === null) {
    return;
  }
  const box = svg.viewBox.baseVal;
  svg.style.width = Math.round(box.width * state.zoom) + "px";
}

function fitZoom() {
  const svg = document.querySelector("#graph svg");
  const graph = document.getElementById("graph");
  if (svg === null) {
    return;
  }
  state.zoom = Math.max(0.1, (graph.clientWidth - 16) / svg.viewBox.baseVal.width);
  applyZoom();
  saveSettings();
}

const STATE_CLASSES = [
  "is-hidden", "is-waiting", "is-current", "is-stack", "is-visited", "is-reached", "is-pinned", "appear", "draw",
];

// Whether the node `name` is only drawn once a step reveals it: calls, criteria and criteria graph nodes.
function isRevealedNode(name) {
  return name.startsWith("call_") || name.startsWith("criteria_") || name.startsWith("criterion_");
}

function resetGraph() {
  for (const group of [...nodes.values(), ...edges.values(), ...clusters.values()]) {
    group.classList.remove(...STATE_CLASSES);
  }
  for (const [name, group] of nodes) {
    if (isRevealedNode(name)) {
      group.classList.add("is-hidden");
    } else {
      group.classList.add("is-waiting");
    }
  }
  for (const [name, group] of edges) {
    const [source, target] = name.split("->");
    if (isRevealedNode(target) || source.startsWith("criterion_")) {
      group.classList.add("is-hidden");
    }
  }
  // The criteria graphs, and the box around each stage's calls, appear once the stage is entered
  for (const group of clusters.values()) {
    group.classList.add("is-hidden");
  }
}

function stageCluster(stageId) {
  return clusters.get("cluster_" + stageId.replace("stage_", "stage_cluster_"));
}

function reveal(group, isCurrent, animation) {
  if (group === undefined) {
    return;
  }
  group.classList.remove("is-hidden", "is-waiting");
  if (isCurrent) {
    group.classList.add(animation);
  }
}

// The criteria parsed: each criterion's node, and the edge to it from the call that parsed it.
function applyCriteria(step, isCurrent) {
  for (const identifier of step.criteria) {
    const node = "criterion_" + chainOf(identifier).index;
    reveal(nodes.get(node), isCurrent, "appear");
    for (const [name, group] of edges) {
      if (name.split("->")[1] === node) {
        reveal(group, isCurrent, "draw");
      }
    }
    if (isCurrent) {
      nodes.get(node)?.classList.add("is-current");
    }
  }
}

// A template building a criteria graph: the edge from the criterion to the template its label chose, and the graph,
// dimmed until `generate_feedback` runs it.
function applyTemplate(step, isCurrent) {
  const index = chainOf(step.criterion).index;
  const node = "criterion_" + index;
  const prefix = "criteria_" + index + "_";
  reveal(clusters.get("cluster_criteria_" + index), isCurrent, "appear");
  for (const [name, group] of nodes) {
    if (name.startsWith(prefix)) {
      reveal(group, isCurrent, "appear");
      group.classList.add("is-waiting");
    }
  }
  for (const [name, group] of edges) {
    const [source, target] = name.split("->");
    if (source === node) {
      reveal(group, isCurrent, "draw");
    } else if (source.startsWith(prefix)) {
      reveal(group, isCurrent, "appear");
      group.classList.add("is-waiting");
    } else if (target.startsWith(prefix) && source.startsWith("call_")) {
      // The template call building the graph
      reveal(group, isCurrent, "draw");
    }
  }
  if (isCurrent) {
    nodes.get(node)?.classList.add("is-current");
  }
}

// `generate_feedback` starting: the criteria graphs are no longer dimmed, and the edges to them from the stage show.
function runCriteriaGraphs(stageId, isCurrent) {
  for (const [name, group] of nodes) {
    if (name.startsWith("criteria_")) {
      group.classList.remove("is-waiting");
    }
  }
  for (const [name, group] of edges) {
    const [source, target] = name.split("->");
    if (target.startsWith("criteria_")) {
      group.classList.remove("is-waiting");
      if (source === stageId) {
        reveal(group, isCurrent, "draw");
      }
    }
  }
}

function applyEvaluation(step, isCurrent) {
  const criterionNodes = example().criteria[step.criterion];
  const evaluation = criterionNodes[step.node];
  if (evaluation === undefined) {
    return;
  }
  const evaluationGroup = nodes.get(evaluation.id);
  if (evaluationGroup !== undefined) {
    evaluationGroup.classList.add("is-visited");
  }
  // The edges from criteria already reached that lead to this evaluation
  for (const [name, group] of edges) {
    const [source, target] = name.split("->");
    const sourceGroup = nodes.get(source);
    if (target === evaluation.id && sourceGroup !== undefined && sourceGroup.classList.contains("is-reached")) {
      group.classList.add("is-reached");
    }
  }
  for (const criterion of step.reached) {
    const reached = criterionNodes[criterion];
    if (reached === undefined) {
      continue;
    }
    nodes.get(reached.id)?.classList.add("is-reached");
    edges.get(evaluation.id + "->" + reached.id)?.classList.add("is-reached");
    // The outputs the reached criterion leads to
    for (const [name, group] of edges) {
      const [source, target] = name.split("->");
      if (source === reached.id && target.includes("_output_")) {
        group.classList.add("is-reached");
        nodes.get(target)?.classList.add("is-reached");
      }
    }
  }
  if (isCurrent && evaluationGroup !== undefined) {
    evaluationGroup.classList.add("is-current");
  }
}

function applyStep(step, isCurrent) {
  if (step.kind === "stage") {
    const stageGroup = nodes.get(stageOf(step.stage).id);
    reveal(stageGroup, false, "appear");
    reveal(stageCluster(stageOf(step.stage).id), isCurrent, "appear");
    if (step.stage === "generate_feedback") {
      runCriteriaGraphs(stageOf(step.stage).id, isCurrent);
    }
    if (isCurrent && stageGroup !== undefined) {
      stageGroup.classList.add("is-current");
    }
  } else if (step.kind === "call") {
    const callGroup = nodes.get(step.call);
    reveal(callGroup, isCurrent, "appear");
    reveal(edges.get(callerOf(step.call) + "->" + step.call), isCurrent, "draw");
    if (isCurrent && callGroup !== undefined) {
      callGroup.classList.add("is-current");
      markCallStack(step.call);
    }
  } else if (step.kind === "criteria") {
    applyCriteria(step, isCurrent);
  } else if (step.kind === "template") {
    applyTemplate(step, isCurrent);
  } else if (step.kind === "evaluate") {
    applyEvaluation(step, isCurrent);
  } else if (step.kind === "result") {
    const resultGroup = nodes.get("result");
    reveal(resultGroup, false, "appear");
    // Shows the boxes of the stages that did not run too, as the static calls figure does
    for (const stage of example().stages) {
      reveal(stageCluster(stage.id), false, "appear");
    }
    if (isCurrent && resultGroup !== undefined) {
      resultGroup.classList.add("is-current");
    }
  }
}

function callStack(callId) {
  const stack = [];
  let current = parentOf(callId);
  while (current !== null) {
    stack.unshift(current);
    current = parentOf(current);
  }
  return stack;
}

function markCallStack(callId) {
  const call = example().calls[callId];
  nodes.get(stageOf(call.stage).id)?.classList.add("is-stack");
  for (const ancestor of callStack(callId)) {
    nodes.get(ancestor)?.classList.add("is-stack");
  }
}

function updateCounts(event) {
  for (const [callId, call] of Object.entries(example().calls)) {
    const group = nodes.get(callId);
    if (group === undefined) {
      continue;
    }
    const label = group.querySelector("text");
    if (label === null) {
      continue;
    }
    const count = invocationsUpTo(callId, event);
    label.textContent = count > 1 ? call.qualname + " ×" + count : call.qualname;
  }
}

function followCurrent() {
  const graph = document.getElementById("graph");
  const current = graph.querySelector("g.is-current");
  if (current === null) {
    return;
  }
  const box = current.getBoundingClientRect();
  const view = graph.getBoundingClientRect();
  const margin = 40;
  const outside = box.left < view.left + margin || box.right > view.right - margin
    || box.top < view.top + margin || box.bottom > view.bottom - margin;
  if (!outside) {
    return;
  }
  const left = graph.scrollLeft + box.left - view.left - (view.width - box.width) / 2;
  const top = graph.scrollTop + box.top - view.top - (view.height - box.height) / 2;
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  graph.scrollTo({ left: left, top: top, behavior: reduceMotion ? "auto" : "smooth" });
}

// Side panel

function stepStage(step) {
  const steps = example().steps;
  for (let index = step.index; index >= 0; index -= 1) {
    if (steps[index].kind === "stage") {
      return steps[index].stage;
    }
  }
  return steps[0].stage;
}

// Whether each collapsible section is open until it is opened or closed on the page.
const SECTION_DEFAULTS = { stage: true, parameters: false, criteria: true, forms: true };

function sectionOpen(key) {
  return key in state.sections ? state.sections[key] : SECTION_DEFAULTS[key];
}

// A panel section that can be collapsed, and stays open or closed from step to step.
function collapsible(key, title, body) {
  return `<details class="section" data-section="${key}"${sectionOpen(key) ? " open" : ""}>
    <summary><h2>${escapeHtml(title)}</h2></summary>${body}</details>`;
}

// A recorded value; with `withFull`, a summarised value has its full value behind "show more".
function valueHtml(value, full, withFull) {
  if (!withFull || full === undefined) {
    return escapeHtml(value);
  }
  return `${escapeHtml(value)}<details class="more"><summary>show more</summary><pre>${escapeHtml(full)}</pre></details>`;
}

// `[name, value, full?]` pairs as a list of names and values.
function namedValues(pairs, withFull) {
  return `<dl class="values">${pairs.map(([name, value, full]) =>
    `<dt>${escapeHtml(name)}</dt><dd>${valueHtml(value, full, withFull)}</dd>`).join("")}</dl>`;
}

function argumentsHtml(argumentList, withFull) {
  return argumentList.length === 0 ? `<p class="muted">No arguments.</p>` : namedValues(argumentList, withFull);
}

// What a call returned, or the exception it raised.
function outcomeHtml(values, withFull) {
  if (values.raised) {
    const exception = values.exception === undefined ? "an exception" : values.exception;
    return `<div class="returned raised mono">raised ${escapeHtml(exception)}</div>`;
  }
  return `<div class="returned mono">↩ ${valueHtml(values.returned, values.returnedFull, withFull)}</div>`;
}

function durationText(stage) {
  return stage.duration === null || stage.duration === undefined ? "" : `took ${stage.duration} ms`;
}

const TIMING_NOTE = "Times are measured while every call is recorded, so they are far longer than a normal evaluation's.";

function stageSection(step) {
  const stage = stageOf(stepStage(step));
  const duration = durationText(stage);
  return collapsible("stage", "Stage", `<span class="chip">${escapeHtml(stage.name)}</span>
    ${duration === "" ? "" : `<span class="muted" title="${escapeHtml(TIMING_NOTE)}">${duration}</span>`}
    <p class="muted">${escapeHtml(stage.description)}</p>`);
}

function callSection(step) {
  const call = example().calls[step.call];
  const stack = [stepStage(step), ...callStack(step.call).map((id) => example().calls[id].qualname), call.qualname];
  const total = invocationEvents(step.call).length;
  let body = `<div class="call-name mono">${escapeHtml(call.qualname)}</div>
    <div class="muted mono">${escapeHtml(call.module)} · depth ${call.depth}</div>
    <div class="stack">${stack.map((name) => `<span class="mono">${escapeHtml(name)}</span>`).join("")}</div>
    ${call.doc === "" ? "" : `<p class="doc">${escapeHtml(call.doc)}</p>`}`;
  if (total > 1) {
    body += `<p class="muted">First of ${total} calls from this caller; the rest raise the count on its node.</p>`;
  }
  if (state.values) {
    body += argumentsHtml(step.arguments, false) + outcomeHtml(step, false);
  }
  return `<section><h2>Call</h2>${body}</section>`;
}

// The parameters `_build_parameters` completed, once it has returned.
function parametersSection(step) {
  const parameters = example().parameters;
  if (parameters.event === undefined || step.event < parameters.event) {
    return "";
  }
  const group = (pairs) => pairs.length === 0 ? `<p class="muted">None.</p>` : namedValues(pairs, true);
  return collapsible("parameters", "Parameters", `
    <div class="group-label">Given in params</div>${group(parameters.given)}
    <div class="group-label">Added by <code>_build_parameters</code>: the context's defaults and the parsing set-up</div>
    ${group(parameters.added)}`);
}

function evaluationSection(step) {
  const criterionNodes = example().criteria[step.criterion];
  const evaluation = criterionNodes[step.node];
  const reached = step.reached.map((label) => {
    const details = criterionNodes[label] === undefined ? "" : criterionNodes[label].details;
    return `<li><span class="mono">${escapeHtml(label)}</span><br><span class="muted">${escapeHtml(details)}</span></li>`;
  });
  return `<section>
    <h2>Criteria graph evaluation</h2>
    <div class="muted">Criterion <span class="mono">${escapeHtml(step.criterion)}</span></div>
    <div class="call-name"><span class="chip evaluation">evaluation</span> ${escapeHtml(step.node)}</div>
    <p class="muted">${escapeHtml(evaluation === undefined ? "" : evaluation.details)}</p>
    ${reached.length > 0 ? `<div>Reports:</div><ul class="reached-list">${reached.join("")}</ul>`
      : `<p class="muted">Reports no criteria.</p>`}
  </section>`;
}

function formsSection(step) {
  const previousShown = shownSteps().filter((shown) => shown.index < step.index).pop();
  const previousEvent = previousShown === undefined ? -Infinity : previousShown.event;
  const forms = example().forms.filter((form) => form.event <= step.event);
  const items = [`<li class="${forms.length === 0 ? "latest" : ""}">
    <div class="via">the response as entered</div>
    <span class="value mono">${escapeHtml(JSON.stringify(example().response))}</span></li>`];
  forms.forEach((form, position) => {
    const call = example().calls[form.call];
    const isNew = form.event > previousEvent;
    const latest = position === forms.length - 1 ? "latest" : "";
    items.push(`<li class="${latest}">
      <div class="via">↓ <span class="mono">${escapeHtml(call.qualname)}</span> · ${escapeHtml(form.type)}
        ${isNew ? '<span class="new-badge">new</span>' : ""}</div>
      <span class="value mono">${escapeHtml(form.value)}</span></li>`);
  });
  return collapsible("forms", "Response forms", `<ul class="forms">${items.join("")}</ul>`);
}

// A tag of the result: the criteria graph criterion it came from (a link that pins it) and its feedback text.
function tagItem(tag) {
  const source = example().feedback[tag];
  if (source === undefined) {
    return `<li><span class="mono">${escapeHtml(tag)}</span>
      <div class="muted">Added by the evaluation itself, not by a criteria graph.</div></li>`;
  }
  const name = source.node === null ? `<span class="mono">${escapeHtml(tag)}</span>`
    : `<button class="link mono" data-pin="${escapeHtml(source.node)}">${escapeHtml(tag)}</button>`;
  const text = source.text === "" ? `<span class="muted">No feedback text.</span>`
    : `“${escapeHtml(source.text)}”`;
  return `<li>${name}
    <div class="muted">Reached in the criteria graph of <code>${escapeHtml(source.criterion)}</code></div>
    <div class="feedback-text">${text}</div></li>`;
}

function resultSection() {
  const result = example().result;
  const verdict = result.is_correct ? "correct" : "incorrect";
  let preview = "";
  if (result.response_latex !== "") {
    preview = `<div class="muted">Preview LaTeX: <span class="mono">${escapeHtml(result.response_latex)}</span></div>
      <div class="muted">Simplified: <span class="mono">${escapeHtml(result.response_simplified)}</span></div>`;
  }
  const duration = example().duration === null ? ""
    : `<div class="muted" title="${escapeHtml(TIMING_NOTE)}">The evaluation took ${example().duration} ms while recording.</div>`;
  return `<section>
    <h2>Result</h2>
    <div class="result-box">
      <div class="verdict ${verdict}">is_correct: ${result.is_correct}</div>
      ${result.feedback === "" ? `<p class="muted">No feedback text.</p>` : `<p>${escapeHtml(result.feedback)}</p>`}
      <div class="muted">Tags, and where each came from</div>
      <ul class="feedback-list">${result.tags.map(tagItem).join("")}</ul>
      ${preview}
      ${duration}
    </div>
  </section>`;
}

// The template that built the graph of the criterion `identifier`, and why that one.
function templateChoice(details) {
  if (details.templateLabel !== null) {
    return `Its parse label <code>${escapeHtml(details.label)}</code> is in <code>graph_templates</code>, which maps it
      to <code>${escapeHtml(details.template)}</code>.`;
  }
  return `Its parse label <code>${escapeHtml(details.label)}</code> is not in <code>graph_templates</code>, so the
    context's default template <code>${escapeHtml(details.template)}</code> is used.`;
}

// Whether the criteria graph of `identifier` reached its main criterion by `step`: "reached", "missed" once
// `generate_feedback` has finished without reaching it, "running", "built" or "" before the graph is built.
function mainCriterionStatus(identifier, step) {
  const main = identifier + "_TRUE";
  const evaluations = example().steps.filter(
    (candidate) => candidate.kind === "evaluate" && candidate.criterion === identifier && candidate.event <= step.event
  );
  if (evaluations.some((evaluation) => evaluation.reached.includes(main))) {
    return "reached";
  }
  const serialise = example().steps.find((candidate) => candidate.kind === "stage" && candidate.stage === "serialise");
  if (serialise !== undefined && step.event >= serialise.event) {
    return "missed";
  }
  if (evaluations.length > 0) {
    return "running";
  }
  const built = example().steps.some(
    (candidate) => candidate.kind === "template" && candidate.criterion === identifier && candidate.event <= step.event
  );
  return built ? "built" : "";
}

function criterionChainItems(identifier, step) {
  const details = chainOf(identifier);
  const items = [`<li>
    <div class="step-label">Parsed by the criteria parser into</div>
    <pre class="tree mono">${escapeHtml(details.tree)}</pre>
    <div class="muted">Parse label <code>${escapeHtml(details.label)}</code></div></li>`];
  const template = firstStepOf("template") === undefined ? undefined : example().steps.find(
    (candidate) => candidate.kind === "template" && candidate.criterion === identifier
  );
  if (template !== undefined && template.event <= step.event) {
    items.push(`<li><div class="step-label">feedback_procedure_generator chooses its template</div>
      <div>${templateChoice(details)}</div>
      <div class="muted">It builds a criteria graph with ${details.evaluations} evaluation
        node${details.evaluations === 1 ? "" : "s"}.</div></li>`);
  }
  const status = mainCriterionStatus(identifier, step);
  const main = `<code>${escapeHtml(identifier + "_TRUE")}</code>`;
  if (status === "reached") {
    items.push(`<li><div class="step-label">generate_feedback runs the graph</div>
      <span class="status-good">✓ reached ${main}</span></li>`);
  } else if (status === "missed") {
    items.push(`<li><div class="step-label">generate_feedback runs the graph</div>
      <span class="status-bad">✗ did not reach ${main}</span></li>`);
  } else if (status === "running") {
    items.push(`<li><div class="step-label">generate_feedback runs the graph</div>
      <span class="muted">Running; the main criterion is ${main}.</span></li>`);
  } else if (status === "built") {
    items.push(`<li><div class="step-label">Waiting for generate_feedback</div>
      <span class="muted">The response is correct for this criterion if the graph reaches ${main}.</span></li>`);
  }
  return items;
}

// How the criteria graphs came about, up to `step`, from the criteria string to whether each reached its main
// criterion; empty before the criteria are parsed.
function criteriaSection(step) {
  const chain = example().chain;
  const criteriaStep = firstStepOf("criteria");
  if (chain.criteria === undefined || criteriaStep === undefined || step.event < criteriaStep.event) {
    return "";
  }
  const focus = step.kind === "template" ? step.criterion : null;
  const identifiers = Object.keys(chain.criteria);
  const items = [`<li>
      <div class="step-label">The criteria string</div>
      <code>${escapeHtml(chain.original)}</code>
      <div class="muted">${escapeHtml(chain.source)}</div></li>`,
    `<li><div class="step-label">${chain.preprocessed === chain.original ? "Preprocessing leaves it unchanged; "
      : `Preprocessed to <code>${escapeHtml(chain.preprocessed)}</code>, then `}split at the top-level commas into
      ${identifiers.length} criteri${identifiers.length === 1 ? "on" : "a"}, one criteria graph each</div>
      ${identifiers.map((identifier) => `<code>${escapeHtml(identifier)}</code>`).join(" ")}</li>`];
  for (const identifier of identifiers) {
    items.push(`<li class="${identifier === focus ? "is-focus" : ""}">
      <div><button class="link mono" data-pin="criterion_${chainOf(identifier).index}">${escapeHtml(identifier)}</button></div>
      <ul class="chain">${criterionChainItems(identifier, step).join("")}</ul></li>`);
  }
  const statuses = identifiers.map((identifier) => mainCriterionStatus(identifier, step));
  if (statuses.every((status) => status === "reached" || status === "missed")) {
    const correct = statuses.every((status) => status === "reached");
    items.push(`<li><div class="step-label">is_correct</div>
      <span class="${correct ? "status-good" : "status-bad"}">${correct}</span>:
      true only if every criteria graph reached its main criterion.</li>`);
  }
  return collapsible("criteria", "Criteria", `<ul class="chain">${items.join("")}</ul>`);
}

// Pinned details

function pinnedCall(callId, step) {
  const call = example().calls[callId];
  const caller = callerOf(callId);
  const parent = parentOf(callId);
  const callerName = parent === null ? "the " + call.stage + " stage" : example().calls[parent].qualname;
  const count = invocationsUpTo(callId, step.event);
  const values = (example().invocations[callId]?.values || []).filter((invocation) => invocation.event <= step.event);
  let body = `<div class="call-name mono">${escapeHtml(call.qualname)}</div>
    <div class="muted mono">${escapeHtml(call.module)} · depth ${call.depth} · stage ${escapeHtml(call.stage)}</div>
    <div class="source mono">${escapeHtml(call.source)}</div>
    ${call.doc === "" ? `<p class="doc muted">No docstring.</p>` : `<p class="doc">${escapeHtml(call.doc)}</p>`}
    <div class="muted">Called by <button class="link mono" data-pin="${escapeHtml(caller)}">${escapeHtml(callerName)}</button>,
      ${count} time${count === 1 ? "" : "s"} so far.</div>`;
  if (values.length > 0) {
    const items = values.map((invocation, position) =>
      `<li><div class="muted">Call ${position + 1}</div>${argumentsHtml(invocation.arguments, true)}${outcomeHtml(invocation, true)}</li>`);
    body += `<ul class="invocations">${items.join("")}</ul>`;
    if (count > values.length) {
      body += `<p class="muted">Only the first ${values.length} calls keep their values.</p>`;
    }
  }
  return body;
}

function pinnedStage(stageId, step) {
  const stage = example().stages.find((candidate) => candidate.id === stageId);
  const calls = Object.entries(example().calls).filter(([callId, call]) => call.stage === stage.name
    && parentOf(callId) === null && !(state.internals && call.internal) && invocationsUpTo(callId, step.event) > 0);
  const list = calls.length === 0 ? `<p class="muted">No calls made in this stage yet.</p>`
    : `<div>Calls:</div><ul class="reached-list">${calls.map(([callId, call]) =>
      `<li><button class="link mono" data-pin="${callId}">${escapeHtml(call.qualname)}</button></li>`).join("")}</ul>`;
  const duration = durationText(stage);
  return `<span class="chip">${escapeHtml(stage.name)}</span>
    ${duration === "" ? "" : `<span class="muted">${duration}</span>`}
    <p class="muted">${escapeHtml(stage.description)}</p>${list}
    ${duration === "" ? "" : `<p class="muted">${escapeHtml(TIMING_NOTE)}</p>`}`;
}

function pinnedCriteriaNode(nodeId, step) {
  for (const [identifier, criterionNodes] of Object.entries(example().criteria)) {
    for (const [label, node] of Object.entries(criterionNodes)) {
      if (node.id !== nodeId) {
        continue;
      }
      const evaluations = example().steps.filter((candidate) => candidate.kind === "evaluate"
        && candidate.criterion === identifier && candidate.event <= step.event);
      let status = "";
      if (node.kind === "evaluation") {
        const visit = evaluations.find((evaluation) => evaluation.node === label);
        status = visit === undefined ? `<p class="muted">Not evaluated by this step.</p>`
          : `<p>Evaluated; it reported ${visit.reached.map((reached) =>
            `<code>${escapeHtml(reached)}</code>`).join(", ") || "no criteria"}.</p>`;
      } else if (node.kind === "criterion") {
        const reached = evaluations.some((evaluation) => evaluation.reached.includes(label));
        status = reached ? `<p class="status-good">Reached.</p>` : `<p class="muted">Not reached by this step.</p>`;
      }
      return `<div class="muted">Criteria graph of <code>${escapeHtml(identifier)}</code> · ${node.kind} node</div>
        <div class="call-name">${escapeHtml(label)}</div>
        ${node.summary && node.summary !== label ? `<p>${escapeHtml(node.summary)}</p>` : ""}
        ${node.details ? `<p class="muted">${escapeHtml(node.details)}</p>` : ""}
        ${status}`;
    }
  }
  return `<p class="muted">No details.</p>`;
}

function pinnedCriterion(nodeId, step) {
  const index = Number(nodeId.replace("criterion_", ""));
  const identifier = Object.keys(example().chain.criteria).find((key) => chainOf(key).index === index);
  return `<div class="muted">Criterion</div>
    <div class="call-name mono">${escapeHtml(identifier)}</div>
    <ul class="chain">${criterionChainItems(identifier, step).join("")}</ul>`;
}

function pinnedSection(step) {
  const name = state.pinned;
  let body;
  if (name.startsWith("call_") && example().calls[name] !== undefined) {
    body = pinnedCall(name, step);
  } else if (name.startsWith("stage_")) {
    body = pinnedStage(name, step);
  } else if (name.startsWith("criterion_")) {
    body = pinnedCriterion(name, step);
  } else if (name.startsWith("criteria_")) {
    body = pinnedCriteriaNode(name, step);
  } else if (name === "result") {
    body = resultSection();
  } else {
    body = `<p class="muted">No details.</p>`;
  }
  return `<section class="pinned">
    <div class="pinned-head"><h2>Pinned</h2>
      <button id="unpin" title="Unpin and show the current step" aria-label="Unpin">✕</button></div>
    ${body}
  </section>`;
}

function markPinned() {
  for (const group of nodes.values()) {
    group.classList.remove("is-pinned");
  }
  if (state.pinned !== null) {
    nodes.get(state.pinned)?.classList.add("is-pinned");
  }
}

function pin(name) {
  state.pinned = name;
  markPinned();
  renderPanel(example().steps[state.step]);
  document.getElementById("panel").scrollTo(0, 0);
}

function renderPanel(step) {
  let content = state.pinned === null ? "" : pinnedSection(step);
  content += stageSection(step);
  if (step.kind === "call") {
    content += callSection(step);
  } else if (step.kind === "evaluate") {
    content += evaluationSection(step);
  } else if (step.kind === "result") {
    content += resultSection();
  }
  content += parametersSection(step);
  if (state.criteria) {
    content += criteriaSection(step);
  }
  if (state.forms) {
    content += formsSection(step);
  }
  document.getElementById("panel").innerHTML = content;
}

// Rendering and controls

function render() {
  // Until the example's layouts are unpacked; `selectExample` renders once they are
  if (layoutsExample !== state.example) {
    return;
  }
  drawLayout();
  const steps = example().steps;
  const step = steps[state.step];
  resetGraph();
  for (const shown of shownSteps()) {
    if (shown.index > state.step) {
      break;
    }
    applyStep(shown, shown.index === state.step);
  }
  updateCounts(step.event);
  markPinned();
  renderPanel(step);
  const shown = shownSteps();
  const position = shown.findIndex((candidate) => candidate.index === state.step);
  const scrubber = document.getElementById("scrubber");
  scrubber.max = String(shown.length - 1);
  scrubber.value = String(position);
  document.getElementById("counter").textContent = `step ${position + 1} / ${shown.length}`;
  requestAnimationFrame(followCurrent);
}

function moveBy(offset) {
  const shown = shownSteps();
  const position = shown.findIndex((candidate) => candidate.index === state.step);
  const next = Math.min(shown.length - 1, Math.max(0, position + offset));
  state.step = shown[next].index;
  render();
  return next < shown.length - 1;
}

function setPlaying(playing) {
  state.playing = playing;
  if (playing && state.pinned !== null) {
    state.pinned = null;
    markPinned();
    renderPanel(example().steps[state.step]);
  }
  const button = document.getElementById("play");
  button.textContent = playing ? "⏸ Pause" : "▶ Play";
  button.setAttribute("aria-label", playing ? "Pause" : "Play");
  clearTimeout(state.timer);
  if (playing) {
    scheduleNext();
  }
}

function scheduleNext() {
  state.timer = setTimeout(() => {
    const more = moveBy(1);
    if (more && state.playing) {
      scheduleNext();
    } else {
      setPlaying(false);
    }
  }, 1100 / state.speed);
}

async function selectExample(index) {
  state.example = index;
  state.layout = null;
  state.step = 0;
  state.pinned = null;
  const current = example();
  document.getElementById("inputs").innerHTML = `
    <span>response <code>${escapeHtml(current.response)}</code></span>
    <span>answer <code>${escapeHtml(current.answer)}</code></span>
    <span>params <code>${escapeHtml(JSON.stringify(current.params))}</code></span>`;
  const unpacked = await unpackLayouts(index);
  // Another example can be chosen while these layouts are unpacked
  if (state.example !== index) {
    return;
  }
  layouts = unpacked;
  layoutsExample = index;
  render();
  document.getElementById("graph").scrollTo(0, 0);
}

function setUp() {
  loadSettings();
  const exampleSelect = document.getElementById("example");
  DATA.examples.forEach((current, index) => {
    exampleSelect.add(new Option(current.title, String(index)));
  });
  const depthSelect = document.getElementById("depth");
  for (let depth = 1; depth <= DATA.maxDepth; depth += 1) {
    depthSelect.add(new Option(String(depth), String(depth)));
  }
  depthSelect.value = String(state.depth);
  document.getElementById("speed").value = String(state.speed);
  document.getElementById("show-forms").checked = state.forms;
  document.getElementById("show-values").checked = state.values;
  document.getElementById("show-criteria").checked = state.criteria;
  document.getElementById("hide-internals").checked = state.internals;
  const legend = document.getElementById("legend");
  legend.open = state.sections.legend === true;
  legend.addEventListener("toggle", () => {
    state.sections.legend = legend.open;
    saveSettings();
  });

  exampleSelect.addEventListener("change", () => {
    setPlaying(false);
    selectExample(Number(exampleSelect.value));
  });
  depthSelect.addEventListener("change", () => {
    state.depth = Number(depthSelect.value);
    state.step = nearestShownStep(state.step);
    saveSettings();
    render();
  });
  document.getElementById("speed").addEventListener("change", (event) => {
    state.speed = Number(event.target.value);
    saveSettings();
  });
  document.getElementById("show-forms").addEventListener("change", (event) => {
    state.forms = event.target.checked;
    saveSettings();
    render();
  });
  document.getElementById("show-values").addEventListener("change", (event) => {
    state.values = event.target.checked;
    saveSettings();
    render();
  });
  document.getElementById("show-criteria").addEventListener("change", (event) => {
    state.criteria = event.target.checked;
    state.step = nearestShownStep(state.step);
    saveSettings();
    render();
  });
  document.getElementById("hide-internals").addEventListener("change", (event) => {
    state.internals = event.target.checked;
    state.step = nearestShownStep(state.step);
    if (state.pinned !== null && state.internals && example().calls[state.pinned]?.internal) {
      state.pinned = null;
    }
    saveSettings();
    render();
  });
  document.getElementById("restart").addEventListener("click", () => {
    setPlaying(false);
    state.step = 0;
    render();
  });
  document.getElementById("back").addEventListener("click", () => {
    setPlaying(false);
    moveBy(-1);
  });
  document.getElementById("forward").addEventListener("click", () => {
    setPlaying(false);
    moveBy(1);
  });
  document.getElementById("play").addEventListener("click", () => {
    const shown = shownSteps();
    if (!state.playing && state.step === shown[shown.length - 1].index) {
      state.step = 0;
      render();
    }
    setPlaying(!state.playing);
  });
  document.getElementById("scrubber").addEventListener("input", (event) => {
    setPlaying(false);
    state.pinned = null;
    state.step = shownSteps()[Number(event.target.value)].index;
    render();
  });
  document.getElementById("graph").addEventListener("click", (event) => {
    const group = event.target.closest("g.node");
    if (group === null || group.classList.contains("is-hidden")) {
      return;
    }
    pin(group.querySelector(":scope > title").textContent);
  });
  document.getElementById("panel").addEventListener("click", (event) => {
    if (event.target.closest("#unpin") !== null) {
      state.pinned = null;
      markPinned();
      renderPanel(example().steps[state.step]);
      return;
    }
    const link = event.target.closest("[data-pin]");
    if (link !== null) {
      pin(link.dataset.pin);
    }
  });
  // `toggle` does not bubble, so it is caught on its way down to the section
  document.getElementById("panel").addEventListener("toggle", (event) => {
    const key = event.target.dataset?.section;
    if (key !== undefined && sectionOpen(key) !== event.target.open) {
      state.sections[key] = event.target.open;
      saveSettings();
    }
  }, true);
  document.getElementById("zoom-in").addEventListener("click", () => {
    state.zoom = Math.min(4, state.zoom * 1.25);
    applyZoom();
    saveSettings();
  });
  document.getElementById("zoom-out").addEventListener("click", () => {
    state.zoom = Math.max(0.1, state.zoom / 1.25);
    applyZoom();
    saveSettings();
  });
  document.getElementById("zoom-fit").addEventListener("click", fitZoom);
  document.addEventListener("keydown", (event) => {
    const tag = event.target.tagName;
    if (tag === "SELECT" || (tag === "INPUT" && event.target.type !== "checkbox")) {
      return;
    }
    if (event.key === "ArrowRight") {
      setPlaying(false);
      moveBy(1);
      event.preventDefault();
    } else if (event.key === "ArrowLeft") {
      setPlaying(false);
      moveBy(-1);
      event.preventDefault();
    } else if (event.key === " ") {
      document.getElementById("play").click();
      event.preventDefault();
    }
  });
  selectExample(0);
}

setUp();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
