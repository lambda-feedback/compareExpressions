from enum import Enum
QuantityTags = Enum("QuantityTags", {v: i for i, v in enumerate("UVNR", 1)})

criteria = {
    "HAS_UNIT": (
        "has(unit(QUANTITY))",
        lambda inputs: "Quantity has unit: "+inputs[0].unit.content_string()
    ),
    "NO_UNIT": (
        "not(has(unit(QUANTITY)))",
        lambda inputs: "Quantity has no unit."
    ),
    "ONLY_UNIT": (
        "not(has(value(QUANTITY)))",
        lambda inputs: "Quantity has no value, only unit(s): "+inputs[0].unit.content_string()
    ),
    "HAS_VALUE": (
        "has(value(QUANTITY))",
        lambda inputs: "Quantity has value: "+inputs[0].value.content_string()
    ),
    "NO_VALUE": (
        "not(has(value(QUANTITY)))",
        lambda inputs: "Quantity has no value."
    ),
    "ONLY_VALUE": (
        "not(has(unit(QUANTITY)))",
        lambda inputs: "Quantity has no unit, only value: "+inputs[0].value.content_string()
    ),
    "FULL_QUANTITY": (
        "has(value(QUANTITY)) and has(unit(QUANTITY))",
        lambda inputs: "Quantity has both value and unit.<br>Value: "+inputs[0].value.content_string+"<br>Unit: "+inputs[0].unit.content_string
    ),
    "NUMBER_VALUE": (
        "is_number(value(QUANTITY))",
        lambda inputs: "Value is a number: "+inputs[0].value.content_string()
    ),
    "EXPR_VALUE": (
        "is_expression(value(QUANTITY))",
        lambda inputs: "Value is an expression: "+inputs[0].value.content_string()
    ),
    "SAME_UNIT": (
        "unit(QUANTITY) matches unit(QUANTITY)",
        lambda inputs: inputs[0].unit.content_string()+" matches "+inputs[1].unit.content_string()
    ),
    "NOT_SAME_UNIT": (
        "unit(QUANTITY) matches unit(QUANTITY)",
        lambda inputs: inputs[0].unit.content_string()+" matches "+inputs[1].unit.content_string()
    ),
    "SAME_VALUE": (
        "not(value(QUANTITY) matches value(QUANTITY))",
        lambda inputs: inputs[0].value.content_string()+" does not match "+inputs[1].value.content_string()
    ),
    "NOT_SAME_VALUE": (
        "not(value(QUANTITY) matches value(QUANTITY))",
        lambda inputs: inputs[0].value.content_string()+" does not match "+inputs[1].value.content_string()
    ),
}

internal = {
    "REVERTED_UNIT": lambda before, content, after: "Possible ambiguity: <strong>`"+content+"`</strong> was not interpreted as a unit in<br>`"+before+"`<strong>`"+content+"`</strong>`"+after+"`"
}
