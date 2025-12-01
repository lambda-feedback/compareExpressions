from sympy.parsing.sympy_parser import (
    _token_splittable,
    _add_factorial_tokens,
    TOKEN,
    NAME,
    OP,
    NUMBER
)
from sympy import Mul, Pow
import re


def create_multichar_symbol_transformer(unsplittable_symbols):
    """
    Creates a transformer that handles implicit multiplication with higher precedence
    for multi-character symbols.

    When implicit_higher_precedence is set, expressions like a/bcd where 'bc' is a
    multi-character symbol should be parsed as a/(bc*d) rather than (a/bc)*d.
    """

    # Sort symbols by length (longest first) to match greedily
    sorted_symbols = sorted(unsplittable_symbols, key=len, reverse=True)

    def multichar_implicit_multiplication(tokens, local_dict, global_dict):
        """
        Transform tokens to handle implicit multiplication with higher precedence.

        This transformer:
        1. Identifies sequences of adjacent NAME/NUMBER tokens (implicit multiplication)
        2. Groups them together with parentheses after division operators
        3. Handles NAME(expr) as implicit multiplication
        4. Preserves multi-character symbols during this process
        """
        result = []
        i = 0

        while i < len(tokens):
            token = tokens[i]

            # Check if this is a division operator
            if token[0] == OP and token[1] == '/':
                result.append(token)
                i += 1

                # Look ahead to find implicitly multiplied terms after division
                implicit_group = []
                j = i

                while j < len(tokens):
                    next_token = tokens[j]

                    # Stop at explicit operators (except power which binds tighter)
                    if next_token[0] == OP:
                        if next_token[1] in ['*', '/', '+', '-']:
                            break
                        elif next_token[1] == '**':
                            # Include power and its operand
                            if implicit_group:
                                implicit_group.append(next_token)
                                j += 1
                                if j < len(tokens) and tokens[j][0] in [NAME, NUMBER]:
                                    implicit_group.append(tokens[j])
                                    j += 1
                            break

                    # Collect NAME and NUMBER tokens
                    if next_token[0] in [NAME, NUMBER]:
                        implicit_group.append(next_token)
                        j += 1
                    # Handle parentheses as a single unit
                    elif next_token[0] == OP and next_token[1] == '(':
                        paren_count = 1
                        implicit_group.append(next_token)
                        j += 1
                        while j < len(tokens) and paren_count > 0:
                            implicit_group.append(tokens[j])
                            if tokens[j][0] == OP:
                                if tokens[j][1] == '(':
                                    paren_count += 1
                                elif tokens[j][1] == ')':
                                    paren_count -= 1
                            j += 1
                        break
                    else:
                        break

                # If we found multiple implicitly multiplied terms, wrap in parens
                if len(implicit_group) > 1:
                    result.append((OP, '('))
                    result.extend(implicit_group)
                    result.append((OP, ')'))
                    i = j
                else:
                    # Just a single term or no terms, add as-is
                    result.extend(implicit_group)
                    i = j

            # Handle NAME followed by '(' as implicit multiplication: NAME(expr) -> NAME*(expr)
            elif token[0] == NAME and i + 1 < len(tokens) and tokens[i + 1][0] == OP and tokens[i + 1][1] == '(':
                # Check if this NAME is NOT a known function
                name = token[1]
                is_function = (name in local_dict and callable(local_dict[name])) or \
                              (name in global_dict and callable(global_dict[name]))

                # For implicit_higher_precedence, treat NAME(expr) as NAME*(expr)
                # unless it's a known function
                if not is_function:
                    result.append(token)
                    result.append((OP, '*'))
                    i += 1
                else:
                    result.append(token)
                    i += 1
            else:
                result.append(token)
                i += 1

        return result

    return multichar_implicit_multiplication