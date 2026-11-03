"""Generates `build/process_animation.html`: an interactive page that animates the process graphs of
`scripts/generate_process_graphs.py`.

Each example is run through `evaluation_function` while recording every call down to `MAX_DEPTH` calls below
`_evaluate`, with its arguments and return value, the forms the response takes, and the evaluations each criteria
graph runs. The calls graph is laid out with graphviz once for each depth, with and without the criteria graphs, and
the page grows it in the order the functions were called. A side panel shows each step's details, and these can be
switched on and off on the page.

The page is a build output and is not committed. Run from the repository root with
`python -m scripts.generate_process_animation` (it needs graphviz, i.e. `dot`), then open the page in a browser.
"""
from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

import pydot

from scripts.generate_criteria_graphs import add_criteria_graph
from scripts.generate_process_graphs import (
    EXAMPLES,
    FIRST_STAGE,
    Recording,
    all_stages,
    calls_to_dot,
    record,
    stage_description,
)

OUTPUT_FILE = Path(__file__).resolve().parent.parent / "build" / "process_animation.html"

# The deepest calls below `_evaluate` recorded, and the deepest the page can show.
MAX_DEPTH = 5

# The depth the page starts at: the depth of the static calls figures.
START_DEPTH = 2


def example_title(name: str) -> str:
    """The name shown on the page for the example `name`, e.g. "Physical quantity" for `process_physical_quantity`."""
    return name.removeprefix("process_").replace("_", " ").capitalize()


def stage_identifier(stage: str) -> str:
    """The graphviz identifier `add_stage_nodes` gives the node of `stage`."""
    return f"stage_{all_stages().index(stage)}"


def build_steps(recording: Recording) -> tuple[list[dict[str, Any]], dict[str, list[int]], list[dict[str, Any]]]:
    """The steps of the animation, the index of the event of each call of each function, and the forms the response
    took, from the events in `recording`.

    Each step is a stage being entered, a function called for the first time from its caller (a node of the calls
    graph appearing), a criteria graph evaluation, or the result. Later calls of the same function only raise its
    count, so they are not steps of their own.
    """
    steps: list[dict[str, Any]] = [{"kind": "stage", "stage": FIRST_STAGE, "event": -1, "depth": 0}]
    invocations: dict[str, list[int]] = {}
    forms: list[dict[str, Any]] = []
    calls = {call.identifier: call for call in recording.calls.values()}
    # The step of each call still running, or None for a call that is not the first of its function.
    running: list[dict[str, Any] | None] = []
    evaluation_step: dict[str, Any] = {}
    for (index, event) in enumerate(recording.events):
        kind = event["kind"]
        if kind == "stage":
            steps.append({"kind": "stage", "stage": event["stage"], "event": index, "depth": 0})
        elif kind == "call":
            invocations.setdefault(event["call"], []).append(index)
            if len(invocations[event["call"]]) == 1:
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
                running.append(step)
            else:
                running.append(None)
        elif kind == "return":
            step = running.pop()
            if step is not None:
                step["returned"] = event["value"]
                step["raised"] = event["raised"]
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
        else:
            raise ValueError(f"Unknown event kind {kind!r}.")
    steps.append({"kind": "result", "event": len(recording.events), "depth": 0})
    for (index, step) in enumerate(steps):
        step["index"] = index
    return (steps, invocations, forms)


def calls_layout(
    recording: Recording, params: dict[str, Any], result: dict[str, Any], depth: int, with_criteria: bool
) -> tuple[pydot.Dot, dict[str, dict[str, str]]]:
    """The calls graph down to `depth`, and with `with_criteria`, each criteria graph beside the `generate_feedback`
    stage, with the graphviz identifier of each of its nodes by criterion and node label.
    """
    dot = calls_to_dot(recording, params, result, depth)
    identifiers: dict[str, dict[str, str]] = {}
    if not with_criteria:
        return (dot, identifiers)
    dot.set("compound", "true")
    for (index, (criterion, graph)) in enumerate(recording.criteria_graphs.items()):
        cluster = pydot.Cluster(f"criteria_{index}", label=f"Criteria graph: {html.escape(criterion)}", color="#9E9E9E")
        identifiers[criterion] = add_criteria_graph(cluster, graph, prefix=f"criteria_{index}_")
        dot.add_subgraph(cluster)
        for start in graph.starting_evaluations(criterion + "_TRUE"):
            dot.add_edge(pydot.Edge(
                stage_identifier("generate_feedback"),
                identifiers[criterion][start],
                style="dashed",
                lhead=cluster.get_name(),
            ))
    return (dot, identifiers)


def svg_markup(dot: pydot.Dot) -> str:
    """`dot` drawn as an SVG element, without the XML declaration and doctype in front of it."""
    svg = dot.create(format="svg").decode("utf-8")
    return svg[svg.index("<svg"):]


def criteria_data(recording: Recording, identifiers: dict[str, dict[str, str]]) -> dict[str, Any]:
    """The graphviz identifier, kind and details of each node of each criteria graph, by criterion and node label."""
    data: dict[str, Any] = {}
    for (criterion, graph) in recording.criteria_graphs.items():
        nodes = {}
        groups = [("evaluation", graph.evaluations), ("criterion", graph.criteria), ("output", graph.outputs)]
        for (kind, group) in groups:
            for (label, node) in group.items():
                nodes[label] = {"id": identifiers[criterion][label], "kind": kind, "details": node.details}
        data[criterion] = nodes
    return data


def example_data(name: str, response: str, answer: str, params: dict[str, Any]) -> dict[str, Any]:
    """Everything the page needs to animate one example."""
    (recording, result) = record(response, answer, params, depth=MAX_DEPTH, record_values=True)
    (steps, invocations, forms) = build_steps(recording)
    layouts = {}
    criteria_identifiers: dict[str, dict[str, str]] = {}
    for depth in range(1, MAX_DEPTH + 1):
        for with_criteria in (False, True):
            (dot, identifiers) = calls_layout(recording, params, result, depth, with_criteria)
            layouts[f"{depth}{'c' if with_criteria else ''}"] = svg_markup(dot)
            if with_criteria:
                criteria_identifiers = identifiers
    calls = {
        call.identifier: {
            "qualname": call.qualname,
            "module": call.module,
            "depth": call.depth,
            "stage": call.stage,
            "parent": None if call.parent is None else call.parent.identifier,
        }
        for call in recording.calls.values()
    }
    stages = all_stages()
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
            }
            for stage in stages
        ],
        "calls": calls,
        "steps": steps,
        "invocations": invocations,
        "forms": forms,
        "criteria": criteria_data(recording, criteria_identifiers),
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
    for (name, response, answer, params) in EXAMPLES:
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
.zoom {
  position: absolute;
  right: 12px;
  top: 12px;
  display: flex;
  gap: 4px;
  z-index: 1;
}
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
    <div class="zoom">
      <button id="zoom-out" title="Zoom out" aria-label="Zoom out">−</button>
      <button id="zoom-fit" title="Fit to width">Fit</button>
      <button id="zoom-in" title="Zoom in" aria-label="Zoom in">+</button>
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
  speed: 1,
  zoom: 0.9,
  // The index in the example's steps of the step shown.
  step: 0,
  playing: false,
  timer: null,
  layout: null,
};

// The node and edge groups of the drawn SVG, by their graphviz title.
let nodes = new Map();
let edges = new Map();
let clusters = new Map();

function loadSettings() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
    for (const key of ["depth", "forms", "values", "criteria", "speed", "zoom"]) {
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
    const { depth, forms, values, criteria, speed, zoom } = state;
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ depth, forms, values, criteria, speed, zoom }));
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
  if (step.kind === "evaluate") {
    return state.criteria;
  }
  return step.depth <= state.depth;
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
  const call = example().calls[callId];
  if (call.parent === null) {
    return stageOf(call.stage).id;
  }
  return call.parent;
}

function invocationsUpTo(callId, event) {
  let count = 0;
  for (const index of example().invocations[callId] || []) {
    if (index <= event) {
      count += 1;
    }
  }
  return count;
}

// Drawing

function drawLayout() {
  const key = String(state.depth) + (state.criteria ? "c" : "");
  const layoutId = state.example + ":" + key;
  if (state.layout === layoutId) {
    return;
  }
  state.layout = layoutId;
  const graph = document.getElementById("graph");
  graph.innerHTML = example().layouts[key];
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

const STATE_CLASSES = ["is-hidden", "is-waiting", "is-current", "is-stack", "is-visited", "is-reached", "appear", "draw"];

function resetGraph() {
  for (const group of [...nodes.values(), ...edges.values(), ...clusters.values()]) {
    group.classList.remove(...STATE_CLASSES);
  }
  for (const [name, group] of nodes) {
    if (name.startsWith("call_") || name.startsWith("criteria_")) {
      group.classList.add("is-hidden");
    } else {
      group.classList.add("is-waiting");
    }
  }
  for (const [name, group] of edges) {
    const target = name.split("->")[1];
    if (target.startsWith("call_") || target.startsWith("criteria_")) {
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

function showCriteriaGraphs(isCurrent) {
  for (const [name, group] of clusters) {
    if (name.startsWith("cluster_criteria_")) {
      reveal(group, isCurrent, "appear");
    }
  }
  for (const [name, group] of nodes) {
    if (name.startsWith("criteria_")) {
      reveal(group, isCurrent, "appear");
    }
  }
  for (const [name, group] of edges) {
    if (name.split("->")[1].startsWith("criteria_")) {
      reveal(group, isCurrent, "appear");
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
    if (step.stage === "generate_feedback_procedures") {
      showCriteriaGraphs(isCurrent);
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
  let current = example().calls[callId];
  while (current.parent !== null) {
    stack.unshift(current.parent);
    current = example().calls[current.parent];
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

function stageSection(step) {
  const stage = stageOf(stepStage(step));
  return `<section>
    <h2>Stage</h2>
    <span class="chip">${escapeHtml(stage.name)}</span>
    <p class="muted">${escapeHtml(stage.description)}</p>
  </section>`;
}

function callSection(step) {
  const call = example().calls[step.call];
  const stack = [stepStage(step), ...callStack(step.call).map((id) => example().calls[id].qualname), call.qualname];
  const count = invocationsUpTo(step.call, step.event);
  const total = (example().invocations[step.call] || []).length;
  let body = `<div class="call-name mono">${escapeHtml(call.qualname)}</div>
    <div class="muted mono">${escapeHtml(call.module)} · depth ${call.depth}</div>
    <div class="stack">${stack.map((name) => `<span class="mono">${escapeHtml(name)}</span>`).join("")}</div>`;
  if (total > 1) {
    body += `<p class="muted">First of ${total} calls from this caller; the rest raise the count on its node.</p>`;
  }
  if (state.values) {
    if (step.arguments.length > 0) {
      body += `<dl class="values">${step.arguments.map(([name, value]) =>
        `<dt>${escapeHtml(name)}</dt><dd>${escapeHtml(value)}</dd>`).join("")}</dl>`;
    } else {
      body += `<p class="muted">No arguments.</p>`;
    }
    if (step.raised) {
      body += `<div class="returned raised mono">raised an exception</div>`;
    } else {
      body += `<div class="returned mono">↩ ${escapeHtml(step.returned)}</div>`;
    }
  }
  return `<section><h2>Call</h2>${body}</section>`;
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
  return `<section><h2>Response forms</h2><ul class="forms">${items.join("")}</ul></section>`;
}

function resultSection() {
  const result = example().result;
  const verdict = result.is_correct ? "correct" : "incorrect";
  let preview = "";
  if (result.response_latex !== "") {
    preview = `<div class="muted">Preview LaTeX: <span class="mono">${escapeHtml(result.response_latex)}</span></div>
      <div class="muted">Simplified: <span class="mono">${escapeHtml(result.response_simplified)}</span></div>`;
  }
  return `<section>
    <h2>Result</h2>
    <div class="result-box">
      <div class="verdict ${verdict}">is_correct: ${result.is_correct}</div>
      <p>${escapeHtml(result.feedback)}</p>
      <div class="muted">Tags</div>
      <ul class="reached-list">${result.tags.map((tag) => `<li class="mono">${escapeHtml(tag)}</li>`).join("")}</ul>
      ${preview}
    </div>
  </section>`;
}

function renderPanel(step) {
  let content = stageSection(step);
  if (step.kind === "call") {
    content += callSection(step);
  } else if (step.kind === "evaluate") {
    content += evaluationSection(step);
  } else if (step.kind === "result") {
    content += resultSection();
  }
  if (state.forms) {
    content += formsSection(step);
  }
  document.getElementById("panel").innerHTML = content;
}

// Rendering and controls

function render() {
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

function selectExample(index) {
  state.example = index;
  state.layout = null;
  state.step = 0;
  const current = example();
  document.getElementById("inputs").innerHTML = `
    <span>response <code>${escapeHtml(current.response)}</code></span>
    <span>answer <code>${escapeHtml(current.answer)}</code></span>
    <span>params <code>${escapeHtml(JSON.stringify(current.params))}</code></span>`;
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
    state.step = shownSteps()[Number(event.target.value)].index;
    render();
  });
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
