import pydot

from enum import Enum
from ..criteria_utilities import Criterion, CriteriaGraphNode, no_feedback

QuantityTags = Enum("QuantityTags", {v: i for i, v in enumerate("UVNR", 1)})

criteria = dict()

criteria["HAS_UNIT"] = Criterion("has(unit(QUANTITY))")
criteria["HAS_UNIT"][True] = lambda inputs: f"{inputs[0].name} has unit: ${inputs[0].unit_latex_string}$"
criteria["HAS_UNIT"][False] = lambda inputs: f"{inputs[0].name} has no unit."

criteria["HAS_VALUE"] = Criterion("has(value(QUANTITY))")
criteria["HAS_VALUE"][True] = lambda inputs: f"{inputs[0].name} has value: ${inputs[0].value_latex_string}$"
criteria["HAS_VALUE"][False] = lambda inputs: f"{inputs[0].name} has no value."

criteria["ONLY_VALUE"] = Criterion("has(value(QUANTITY)) and not(has(unit(QUANTITY)))")
criteria["ONLY_VALUE"][True] = lambda inputs: f"{inputs[0].name} has no unit, only value: ${inputs[0].value_latex_string()}$",
criteria["ONLY_VALUE"][False] = no_feedback  # Unknown how the condition has failed, no feedback in this case

criteria["ONLY_UNIT"] = Criterion("not(has(value(QUANTITY))) and has(unit(QUANTITY))")
criteria["ONLY_UNIT"][True] = lambda inputs: f"{inputs[0].name} has no value, only unit: ${inputs[0].unit_latex_string}$",
criteria["ONLY_UNIT"][False] = no_feedback  # Unknown how the condition has failed, no feedback in this case

criteria["FULL_QUANTITY"] = Criterion("has(value(QUANTITY)) and has(unit(QUANTITY))")
criteria["FULL_QUANTITY"][True] = lambda inputs: f"{inputs[0].name} has both value and unit.<br>Value: {inputs[0].value.content_string()}<br>Unit: ${inputs[0].unit_latex_string}$"
criteria["FULL_QUANTITY"][False] = no_feedback  # Unknown how the condition has failed, no feedback in this case

criteria["NUMBER_VALUE"] = Criterion("is_number(value(QUANTITY))")
criteria["NUMBER_VALUE"][True] = lambda inputs: f"{inputs[0].name} value is a number: ${inputs[0].value_latex_string}$"
criteria["NUMBER_VALUE"][False] = lambda inputs: f"{inputs[0].name} value is not a number."

criteria["EXPR_VALUE"] = Criterion("is_number(value(QUANTITY))")
criteria["EXPR_VALUE"][True] = lambda inputs: f"{inputs[0].name} value is an expression: ${inputs[0].value_latex_string}$"
criteria["EXPR_VALUE"][False] = lambda inputs: f"{inputs[0].name} value is not an expression."

criteria["QUANTITY_MATCH"] = Criterion("QUANTITY matches QUANTITY", doc_string="Checks quantities match")
criteria["QUANTITY_MATCH"][True] = lambda inputs: f"${inputs[0].latex_string}$ matches ${inputs[1].latex_string}$"
criteria["QUANTITY_MATCH"][False] = lambda inputs: f"${inputs[0].latex_string}$ does not match ${inputs[1].latex_string}$"

criteria["DIMENSION_MATCH"] = Criterion("dimension(QUANTITY) matches dimension(QUANTITY)", doc_string="Checks dimensions match")
criteria["DIMENSION_MATCH"][True] = lambda inputs: f"The {inputs[0].name} and {inputs[1].name} have the same dimensions."
criteria["DIMENSION_MATCH"][False] = lambda inputs: f"$Dimension {inputs[0]}$ does not match dimension ${inputs[1]}$"

criteria["MISSING_VALUE"] = Criterion("not(has(value(response))) and has(value(answer))")
criteria["MISSING_VALUE"][True] = lambda inputs: "The response is missing a value."
criteria["MISSING_VALUE"][False] = no_feedback  # Unknown how the condition has failed, no feedback in this case

criteria["MISSING_UNIT"] = Criterion("not(has(unit(response))) and has(unit(answer))")
criteria["MISSING_UNIT"][True] = lambda inputs: "The response is missing unit(s)."
criteria["MISSING_UNIT"][False] = no_feedback  # Unknown how the condition has failed, no feedback in this case

criteria["UNEXPECTED_VALUE"] = Criterion("has(value(response)) and not(has(value(answer)))")
criteria["UNEXPECTED_VALUE"][True] = lambda inputs: "The response is expected only have unit(s), no value."
criteria["UNEXPECTED_VALUE"][False] = no_feedback  # Unknown how the condition has failed, no feedback in this case

criteria["UNEXPECTED_UNIT"] = Criterion("has(unit(response)) and not(has(unit(answer)))")
criteria["UNEXPECTED_UNIT"][True] = lambda inputs: "The response is expected to be a value without unit(s)."
criteria["UNEXPECTED_UNIT"][False] = no_feedback  # Unknown how the condition has failed, no feedback in this case

criteria["PREFIX_IS_LARGE"] = Criterion("unit(response) >= 1000*unit(answer)", doc_string="Check if prefix is much larger for the response than the answer")
criteria["PREFIX_IS_LARGE"][True] = lambda inputs: "The quantity can be written with fewer digits by using a larger prefix."
criteria["PREFIX_IS_LARGE"][False] = no_feedback

criteria["PREFIX_IS_SMALL"] = Criterion("unit(response)*1000 <= unit(answer)", doc_string="Check if prefix is much smaller for the response than the answer")
criteria["PREFIX_IS_SMALL"][True] = lambda inputs: "The quantity can be written with fewer digits by using a smaller prefix."
criteria["PREFIX_IS_SMALL"][False] = no_feedback

internal = {
    "REVERTED_UNIT": lambda before, content, after: "Possible ambiguity: <strong>`"+content+"`</strong> was not interpreted as a unit in<br>`"+before+"`<strong>`"+content+"`</strong>`"+after+"`"
}

END = CriteriaGraphNode("END",children=None)

answer_matches_response_graph = CriteriaGraphNode(
    "START", children={
        None: CriteriaGraphNode(
            "DIMENSION_MATCH",
            criteria["DIMENSION_MATCH"],
            {
                True: CriteriaGraphNode(
                    "QUANTITY_MATCH", 
                    criteria["QUANTITY_MATCH"],
                    {
                        True: CriteriaGraphNode(
                            "PREFIX_IS_LARGE", 
                            criteria["PREFIX_IS_LARGE"],
                            {
                                True: END,
                                False: CriteriaGraphNode(
                                    "PREFIX_IS_SMALL",
                                    criteria["PREFIX_IS_SMALL"],
                                    {
                                        True: END,
                                        False: END
                                    }
                                ),
                            }
                        ),
                        False: END,
                    }
                ),
                False: END,
            }
        ),
    }
)

if __name__ == "__main__":
    # Generates a graphviz description of the criteria graphs(s) that can be used to generate visualize the graph
    shape = "polygon"
    style = "filled"
    fillcolor = "#FFFFCC"
    nodes_to_be_processed = [answer_matches_response_graph]
    nodes_already_processed = []
    nodes = []
    edges = []
    while len(nodes_to_be_processed) > 0:
        node = nodes_to_be_processed.pop()
        label = node.label
        tooltip = node.label
        if node.criterion is not None:
            label = node.criterion.check
            if node.criterion.doc_string is not None:
                label = node.criterion.doc_string
            nodes.append(f'{node.label} [label="{label}" tooltip="{tooltip}" shape="{shape}" style="{style}" fillcolor="{fillcolor}"]')
        for (result, target) in node.children.items():
            edges.append(f'{node.label} -> {target.label} [label="{str(result)}"]')
            if target not in nodes_already_processed and target not in nodes_to_be_processed:
                nodes_to_be_processed.append(target)
        nodes_already_processed.append(node)
    dot_string = "digraph {\n"+"\n".join(nodes+edges)+"\n}"
    graphs = pydot.graph_from_dot_data(dot_string)
    graph = graphs[0]
    graph.write_svg("app/feedback/output.svg")