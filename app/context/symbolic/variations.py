"""Variations of an expression with one operation changed, used to identify how an incorrect response was computed."""

from __future__ import annotations

from collections.abc import Callable

from sympy import Add, Basic, Pow, Mul


def find_coords_for_node_type(expression: Basic, node_type: type[Basic]) -> list[tuple[int, ...]]:
    stack: list[tuple[Basic, tuple[int, ...]]] = [(expression, tuple())]
    node_coords = []
    while len(stack) > 0:
        (expr, coord) = stack.pop()
        if isinstance(expr, node_type):
            node_coords.append(coord)
        for (k, arg) in enumerate(expr.args):
            stack.append((arg, coord + (k,)))
    return node_coords


def replace_node_variations(
    expression: Basic, type_of_node: type[Basic], replacement_function: Callable[[Basic, int], Basic]
) -> list[Basic]:
    variations = []
    list_of_coords = find_coords_for_node_type(expression, type_of_node)
    for coords in list_of_coords:
        nodes = [expression]
        for coord in coords:
            nodes.append(nodes[-1].args[coord])
        for k in range(0, len(nodes[-1].args)):
            variation = replacement_function(nodes[-1], k)
            for (node, coord) in reversed(list(zip(nodes, coords))):
                new_args = node.args[0:coord] + (variation,) + node.args[coord + 1:]
                variation = type(node)(*new_args)
            variations.append(variation)
    return variations


def one_addition_to_subtraction(expression: Basic) -> list[Basic]:
    def addition_to_subtraction(node: Basic, k: int) -> Basic:
        return node - 2 * node.args[k]
    variations = replace_node_variations(expression, Add, addition_to_subtraction)
    return variations


def one_swap_addition_and_multiplication(expression: Basic) -> list[Basic]:

    def addition_to_multiplication(node: Basic, k: int) -> Basic:
        return node - node.args[k - 1] - node.args[k] + node.args[k - 1] * node.args[k]

    def multiplication_to_addition(node: Basic, k: int) -> Basic:
        return node / (node.args[k - 1] * node.args[k]) * (node.args[k - 1] + node.args[k])

    variations = replace_node_variations(expression, Add, addition_to_multiplication)
    variations += replace_node_variations(expression, Mul, multiplication_to_addition)

    # For a node with two arguments, k-1 wraps around at k = 0, so each pair is changed twice
    return list(dict.fromkeys(variations))


def one_exponent_flip(expression: Basic) -> list[Basic]:
    def exponent_flip(node: Basic, k: int) -> Basic:
        return node**(-1)
    variations = replace_node_variations(expression, Pow, exponent_flip)

    # The flip does not depend on k, so each power would be flipped once per argument
    return list(dict.fromkeys(variations))
