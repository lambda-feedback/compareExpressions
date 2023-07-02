from enum import Enum
from ..criteria_utilities import Criterion, no_feedback

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

criteria["QUANTITY_MATCH"] = Criterion("QUANTITY matches QUANTITY")
criteria["QUANTITY_MATCH"][True] = lambda inputs: f"${inputs[0].latex_string}$ matches ${inputs[1].latex_string}$"
criteria["QUANTITY_MATCH"][False] = lambda inputs: f"${inputs[0].latex_string}$ does not match ${inputs[1].latex_string}$"

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

internal = {
    "REVERTED_UNIT": lambda before, content, after: "Possible ambiguity: <strong>`"+content+"`</strong> was not interpreted as a unit in<br>`"+before+"`<strong>`"+content+"`</strong>`"+after+"`"
}
