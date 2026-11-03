"""Generates the criteria graph images in `app/docs/criteria_graphs/` for the developer documentation.

Each graph is built the way `evaluation_function` builds it (without generating any feedback) and drawn twice:
- `<name>_mermaid.svg`: the mermaid source from `CriteriaGraph.to_mermaid`, rendered with mermaid-cli
  (`npx @mermaid-js/mermaid-cli`).
- `<name>.svg`: drawn with graphviz straight from the graph's evaluation, criterion and output nodes.

Run from the repository root with `python -m scripts.generate_criteria_graphs`.
"""
from __future__ import annotations

import html
import subprocess
import tempfile
import textwrap
from collections.abc import Collection
from pathlib import Path
from typing import Any

import pydot
from lambdafeedback.criteria import CriteriaGraph, EvaluationNode

from app.evaluation import (
    EvaluationResult,
    _build_evaluation_parameters,
    _build_parameters,
    create_criteria_dict,
    parse_reserved_expressions,
    select_context,
)

OUTPUT_DIRECTORY = Path(__file__).resolve().parent.parent / "app" / "docs" / "criteria_graphs"

# (file name, answer, params): one example of each shape of graph the contexts build.
EXAMPLES: list[tuple[str, str, dict[str, Any]]] = [
    ("symbolic_equality", "x + 1", {"criteria": "response = answer"}),
    ("symbolic_equality_of_equations", "x = 1", {"criteria": "response = answer"}),
    ("symbolic_equality_of_sets", "{1, 2}", {"criteria": "response = answer"}),
    ("symbolic_where", "x", {"criteria": "response = answer where x = 0"}),
    ("symbolic_written_as", "x + 1", {"criteria": "response written as answer"}),
    ("symbolic_other", "x", {"criteria": "response contains x"}),
    ("physical_quantity_matches", "1 m", {"physical_quantity": True, "criteria": "response matches answer"}),
    ("physical_quantity_order", "1 m", {"physical_quantity": True, "criteria": "response > answer"}),
]

# Graphviz style for each kind of node, close to the shapes `CriteriaGraph.to_mermaid` uses.
NODE_STYLES = {
    "evaluation": {"shape": "box", "style": "rounded,filled", "fillcolor": "#E5F8FB", "color": "#00B8D4"},
    "criterion": {"shape": "box", "style": "filled", "fillcolor": "#FFFFFF", "color": "#212121"},
    "output": {"shape": "hexagon", "style": "filled", "fillcolor": "#C5CAE9", "color": "#2F3C86"},
}

# Extra style for the nodes and edges on the path a response took (see `add_criteria_graph`).
REACHED_NODE_STYLE = {"color": "#E65100", "penwidth": "3"}
REACHED_EDGE_STYLE = {"color": "#E65100", "penwidth": "2.5"}

# Characters per line of a node's details in the graphviz drawings (mermaid wraps them itself).
DETAILS_WIDTH = 45


def build_graph(answer: str, params: dict[str, Any]) -> CriteriaGraph:
    """The criteria graph `evaluation_function` builds for `answer` and the single criterion in `params`.

    The answer is used as the response too: the graph's shape depends only on the answer, not on the response.
    """
    params = dict(params)
    evaluation_result = EvaluationResult()
    context = select_context(params)
    parameters = _build_parameters(context, params, answer, answer)
    success, reserved_expressions = parse_reserved_expressions(
        context, parameters["reserved_expressions_strings"], parameters, evaluation_result
    )
    if success is False:
        raise ValueError(f"Cannot parse the answer `{answer}`.")
    criteria_parser = context.generate_criteria_parser(reserved_expressions)
    criteria = create_criteria_dict(context, criteria_parser, parameters)
    evaluation_parameters = _build_evaluation_parameters(parameters, reserved_expressions, criteria, evaluation_result)
    graphs = context.feedback_procedure_generator(evaluation_parameters)
    if len(graphs) != 1:
        raise ValueError(f"Expected one criterion, got {len(graphs)}.")
    return next(iter(graphs.values()))


def _node_label(label: str, details: str) -> str:
    """A graphviz HTML-like label with the node's label in bold above its details, wrapped to `DETAILS_WIDTH`."""
    details_lines = "<br/>".join(html.escape(line) for line in textwrap.wrap(details, DETAILS_WIDTH))
    return f"<<b>{html.escape(label)}</b><br/><font point-size='10'>{details_lines}</font>>"


def reached_nodes(graph: CriteriaGraph, reached_criteria: Collection[str]) -> set[str]:
    """The labels of the nodes on the path through `graph` that reached `reached_criteria`.

    These are the reached criteria, the evaluations that reported them and the output nodes they lead to.
    """
    reached = {label for label in graph.criteria if label in reached_criteria}
    for (label, node) in graph.evaluations.items():
        if any(edge.target.label in reached for edge in node.outgoing):
            reached.add(label)
    for label in graph.outputs:
        if any(edge.source.label in reached for edge in graph.outputs[label].incoming):
            reached.add(label)
    return reached


def add_criteria_graph(
    container: pydot.Graph, graph: CriteriaGraph, prefix: str = "", reached_criteria: Collection[str] = ()
) -> dict[str, str]:
    """Adds the nodes and edges of `graph` to `container` and returns the graphviz identifier of each node label.

    Sufficiencies are dotted edges. The path that reached `reached_criteria` is highlighted, and `prefix` keeps the
    identifiers apart from other nodes in the same drawing.
    """
    groups = [("evaluation", graph.evaluations), ("criterion", graph.criteria), ("output", graph.outputs)]
    identifiers = {label: f"{prefix}{kind}_{index}" for (kind, nodes) in groups for (index, label) in enumerate(nodes)}
    reached = reached_nodes(graph, reached_criteria)
    for (kind, nodes) in groups:
        for (label, node) in nodes.items():
            style = dict(NODE_STYLES[kind])
            if label in reached:
                style.update(REACHED_NODE_STYLE)
            container.add_node(pydot.Node(identifiers[label], label=_node_label(label, node.details), **style))
    for (kind, nodes) in groups:
        for (label, node) in nodes.items():
            for edge in node.outgoing:
                if label in reached and edge.target.label in reached:
                    container.add_edge(pydot.Edge(identifiers[label], identifiers[edge.target.label], **REACHED_EDGE_STYLE))
                else:
                    container.add_edge(pydot.Edge(identifiers[label], identifiers[edge.target.label]))
            if isinstance(node, EvaluationNode):
                for sufficiency in node.sufficiencies:
                    if sufficiency in identifiers:
                        container.add_edge(pydot.Edge(identifiers[label], identifiers[sufficiency], style="dotted"))
    return identifiers


def new_drawing() -> pydot.Dot:
    """An empty top-to-bottom graphviz drawing with the styles shared by the documentation graphs."""
    dot = pydot.Dot(graph_type="digraph", rankdir="TB", fontname="Helvetica", bgcolor="white")
    dot.set_node_defaults(fontname="Helvetica", fontsize="12")
    return dot


def graph_to_dot(graph: CriteriaGraph) -> pydot.Dot:
    """`graph` drawn with graphviz from its nodes and edges; sufficiencies are dotted edges."""
    dot = new_drawing()
    add_criteria_graph(dot, graph)
    return dot


def render_mermaid(mermaid: str, target: Path) -> None:
    """Renders the mermaid source `mermaid` to the SVG file `target`; the source itself is not kept."""
    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory) / "graph.mmd"
        source.write_text(mermaid + "\n")
        subprocess.run(
            ["npx", "--yes", "@mermaid-js/mermaid-cli@11.4.2", "--quiet", "-i", str(source), "-o", str(target)],
            check=True,
        )


def main() -> None:
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    for (name, answer, params) in EXAMPLES:
        graph = build_graph(answer, params)
        graph_to_dot(graph).write_svg(str(OUTPUT_DIRECTORY / f"{name}.svg"))
        render_mermaid(graph.to_mermaid(), OUTPUT_DIRECTORY / f"{name}_mermaid.svg")
        print(f"Generated {name}")


if __name__ == "__main__":
    main()
