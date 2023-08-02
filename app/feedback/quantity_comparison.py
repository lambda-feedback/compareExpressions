from enum import Enum
from ..criteria_utilities import Criterion, CriteriaGraphNode, CriteriaGraphContainer, END, flip_bool_result, no_feedback, generate_svg

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
criteria["NUMBER_VALUE"][True] = no_feedback #  lambda inputs: f"{inputs[0].name} value is a number: ${inputs[0].value_latex_string}$"
criteria["NUMBER_VALUE"][False] = no_feedback #  lambda inputs: f"{inputs[0].name} value is not a number."

criteria["EXPR_VALUE"] = Criterion("is_number(value(QUANTITY))")
criteria["EXPR_VALUE"][True] = lambda inputs: f"{inputs[0].name} value is an expression: ${inputs[0].value_latex_string}$"
criteria["EXPR_VALUE"][False] = lambda inputs: f"{inputs[0].name} value is not an expression."

criteria["QUANTITY_MATCH"] = Criterion("QUANTITY matches QUANTITY", doc_string="Quantities match")
criteria["QUANTITY_MATCH"][True] = lambda inputs: f"${inputs[0].latex_string}$ matches ${inputs[1].latex_string}$"
criteria["QUANTITY_MATCH"][False] = lambda inputs: f"${inputs[0].latex_string}$ does not match ${inputs[1].latex_string}$"

criteria["DIMENSION_MATCH"] = Criterion("dimension(QUANTITY) matches dimension(QUANTITY)", doc_string="Dimensions match")
criteria["DIMENSION_MATCH"][True] = lambda inputs: f"The {inputs[0].name} and {inputs[1].name} have the same dimensions."
criteria["DIMENSION_MATCH"][False] = lambda inputs: f"Dimensions of ${inputs[0].latex_string}$ does not match the dimensions of ${inputs[1].latex_string}$"

criteria["MISSING_VALUE"] = Criterion("not(has(value(response))) and has(value(answer))", doc_string="Response is missing value when answer has value")
criteria["MISSING_VALUE"][True] = lambda inputs: "The response is missing a value."
criteria["MISSING_VALUE"][False] = no_feedback  # Unknown how the condition has failed, no feedback in this case

criteria["MISSING_UNIT"] = Criterion("not(has(unit(response))) and has(unit(answer))", doc_string="Response is missing unit when answer has unit")
criteria["MISSING_UNIT"][True] = lambda inputs: "The response is missing unit(s)."
criteria["MISSING_UNIT"][False] = no_feedback  # Unknown how the condition has failed, no feedback in this case

criteria["UNEXPECTED_VALUE"] = Criterion("has(value(response)) and not(has(value(answer)))", doc_string="Response has value when when answer has only unit")
criteria["UNEXPECTED_VALUE"][True] = lambda inputs: "The response is expected only have unit(s), no value."
criteria["UNEXPECTED_VALUE"][False] = no_feedback  # Unknown how the condition has failed, no feedback in this case

criteria["UNEXPECTED_UNIT"] = Criterion("has(unit(response)) and not(has(unit(answer)))", doc_string="Response has unit when when answer has only value")
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

answer_matches_response_graph = CriteriaGraphContainer(criteria)
answer_matches_response_graph.attach("START", "MISSING_VALUE", result_map=flip_bool_result)
answer_matches_response_graph.finish("MISSING_VALUE", True)
answer_matches_response_graph.attach("MISSING_VALUE", "MISSING_UNIT", False, result_map=flip_bool_result)
answer_matches_response_graph.finish("MISSING_UNIT", True)
answer_matches_response_graph.attach("MISSING_UNIT", "UNEXPECTED_VALUE", False, result_map=flip_bool_result)
answer_matches_response_graph.finish("UNEXPECTED_VALUE", True)
answer_matches_response_graph.attach("UNEXPECTED_VALUE", "UNEXPECTED_UNIT", False, result_map=flip_bool_result)
answer_matches_response_graph.finish("UNEXPECTED_UNIT", True)
answer_matches_response_graph.attach("UNEXPECTED_UNIT", "DIMENSION_MATCH", False)
answer_matches_response_graph.attach("DIMENSION_MATCH", "QUANTITY_MATCH", True)
answer_matches_response_graph.finish("DIMENSION_MATCH", False)
answer_matches_response_graph.attach("QUANTITY_MATCH", "PREFIX_IS_LARGE", True, override=False)
answer_matches_response_graph.finish("QUANTITY_MATCH", False)
answer_matches_response_graph.finish("PREFIX_IS_LARGE", True)
answer_matches_response_graph.attach("PREFIX_IS_LARGE", "PREFIX_IS_SMALL", False, override=False)
answer_matches_response_graph.finish("PREFIX_IS_SMALL", True)
answer_matches_response_graph.finish("PREFIX_IS_SMALL", False)

if __name__ == "__main__":
    generate_svg(answer_matches_response_graph.START, "app/docs/quantity_comparison_graph.svg", dummy_input=[DummyInput("response"), DummyInput("answer")])
