from enum import Enum
from ..criteria_utilities import Criterion, CriteriaGraphNode, no_feedback, generate_svg, flip_bool_result

class DummyInput:

    def __init__(self, name):
        self.name = name
        self.unit_latex_string = name
        self.value_latex_string = name
        self.latex_string = name
        return

    def __str__(self):
        return self.name


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

criteria["QUANTITY_MATCH"] = Criterion("QUANTITY matches QUANTITY", doc_string="Quantities match")
criteria["QUANTITY_MATCH"][True] = lambda inputs: f"${inputs[0].latex_string}$ matches ${inputs[1].latex_string}$"
criteria["QUANTITY_MATCH"][False] = lambda inputs: f"${inputs[0].latex_string}$ does not match ${inputs[1].latex_string}$"

criteria["DIMENSION_MATCH"] = Criterion("dimension(QUANTITY) matches dimension(QUANTITY)", doc_string="Dimensions match")
criteria["DIMENSION_MATCH"][True] = lambda inputs: f"The {inputs[0].name} and {inputs[1].name} have the same dimensions."
criteria["DIMENSION_MATCH"][False] = lambda inputs: f"Dimension of ${inputs[0]}$ does not match dimension of ${inputs[1]}$"

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

criteria["PREFIX_IS_LARGE"] = Criterion("unit(response) >= 1000*unit(answer)", doc_string="The response prefix is much larger than the answer prefix")
criteria["PREFIX_IS_LARGE"][True] = lambda inputs: "The quantity can be written with fewer digits by using a smaller prefix."
criteria["PREFIX_IS_LARGE"][False] = no_feedback

criteria["PREFIX_IS_SMALL"] = Criterion("unit(response)*1000 <= unit(answer)", doc_string="The response prefix is much smaller than the answer prefix")
criteria["PREFIX_IS_SMALL"][True] = lambda inputs: "The quantity can be written with fewer digits by using a larger prefix."
criteria["PREFIX_IS_SMALL"][False] = no_feedback

internal = {
    "REVERTED_UNIT": lambda before, content, after: "Possible ambiguity: <strong>`"+content+"`</strong> was not interpreted as a unit in<br>`"+before+"`<strong>`"+content+"`</strong>`"+after+"`"
}

END = CriteriaGraphNode("END",children=None)

answer_matches_response_graph = CriteriaGraphNode("START")
answer_matches_response_graph.get_by_label("START")[None] = CriteriaGraphNode("MISSING_VALUE", criterion=criteria["MISSING_VALUE"], result_map=flip_bool_result)
answer_matches_response_graph.get_by_label("MISSING_VALUE")[True]  = END
answer_matches_response_graph.get_by_label("MISSING_VALUE")[False] = CriteriaGraphNode("MISSING_UNIT", criterion=criteria["MISSING_UNIT"], result_map=flip_bool_result)
answer_matches_response_graph.get_by_label("MISSING_UNIT")[True]  = END
answer_matches_response_graph.get_by_label("MISSING_UNIT")[False] = CriteriaGraphNode("UNEXPECTED_VALUE", criterion=criteria["UNEXPECTED_VALUE"], result_map=flip_bool_result)
answer_matches_response_graph.get_by_label("UNEXPECTED_VALUE")[True]  = END
answer_matches_response_graph.get_by_label("UNEXPECTED_VALUE")[False] = CriteriaGraphNode("UNEXPECTED_UNIT", criterion=criteria["UNEXPECTED_UNIT"], result_map=flip_bool_result)
answer_matches_response_graph.get_by_label("UNEXPECTED_UNIT")[True]  = END
answer_matches_response_graph.get_by_label("UNEXPECTED_UNIT")[False] = CriteriaGraphNode("DIMENSION_MATCH", criterion=criteria["DIMENSION_MATCH"])
answer_matches_response_graph.get_by_label("DIMENSION_MATCH")[True]  = CriteriaGraphNode("QUANTITY_MATCH", criterion=criteria["QUANTITY_MATCH"])
answer_matches_response_graph.get_by_label("DIMENSION_MATCH")[False] = END
answer_matches_response_graph.get_by_label("QUANTITY_MATCH")[True]  = CriteriaGraphNode("PREFIX_IS_LARGE", criterion=criteria["PREFIX_IS_LARGE"], override=False)
answer_matches_response_graph.get_by_label("QUANTITY_MATCH")[False] = END
answer_matches_response_graph.get_by_label("PREFIX_IS_LARGE")[True]  = END
answer_matches_response_graph.get_by_label("PREFIX_IS_LARGE")[False] = CriteriaGraphNode("PREFIX_IS_SMALL", criterion=criteria["PREFIX_IS_SMALL"], override=False)
answer_matches_response_graph.get_by_label("PREFIX_IS_SMALL")[True]  = END
answer_matches_response_graph.get_by_label("PREFIX_IS_SMALL")[False] = END

if __name__ == "__main__":
    dot_string = generate_svg(answer_matches_response_graph, "app/feedback/quantity_comparison_graph.svg", dummy_input=[DummyInput("response"), DummyInput("answer")])
    print(dot_string)