from typing import TypedDict


class Preview(TypedDict):
    latex: str
    sympy: str


class Result(TypedDict):
    preview: Preview
