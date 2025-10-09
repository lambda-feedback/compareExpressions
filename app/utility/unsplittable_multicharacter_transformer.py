def create_multichar_symbol_transformer(symbol_names_or_dict, enable_numbers=True):
    """
    Create a SymPy transformation function that greedily segments identifiers
    into known symbol names and inserts '*' between adjacent matches.

    This returns a transformation function compatible with sympy.parsing.sympy_parser.parse_expr.

    Args:
        symbol_names_or_dict: iterable of allowed symbol names (strings) or dict mapping names to symbols
        enable_numbers: if True, recognize numbers as single tokens

    Returns:
        A transformation function that takes (tokens, local_dict, global_dict)
        and returns modified tokens.

    Example usage:
        from sympy import parse_expr, Symbol
        from sympy.parsing.sympy_parser import standard_transformations

        local_dict = {'a': Symbol('a'), 'bc': Symbol('bc'), 'd': Symbol('d')}
        transform = create_multichar_symbol_transformer(local_dict)
        transformations = standard_transformations + (transform,)

        expr = parse_expr('a/(bcd)', transformations=transformations, local_dict=local_dict)
    """
    # Handle both dict and iterable
    if isinstance(symbol_names_or_dict, dict):
        name_set = set(symbol_names_or_dict.keys())
        symbol_dict = symbol_names_or_dict
    else:
        name_set = set(symbol_names_or_dict)
        symbol_dict = None

    if not name_set:
        # Return identity transformation
        return lambda tokens, local_dict, global_dict: tokens

    maxlen = max(map(len, name_set))

    def segment_identifier(w: str) -> list:
        """Segment an identifier and return list of token tuples."""
        i = 0
        out = []
        while i < len(w):
            match = None
            # Greedy longest match
            for L in range(min(maxlen, len(w) - i), 0, -1):
                cand = w[i:i + L]
                if cand in name_set:
                    match = cand
                    break
            if match is not None:
                if out:
                    out.append((53, '*'))  # OP token for '*'
                out.append((1, match))  # NAME token
                i += len(match)
            else:
                # No match: treat single char as its own identifier
                if out:
                    out.append((53, '*'))  # OP token for '*'
                out.append((1, w[i]))  # NAME token
                i += 1
        return out

    def multichar_symbol_transformation(tokens, local_dict):
        """
        Transform tokens by segmenting multi-character identifiers.

        Args:
            tokens: list of (token_type, token_string) tuples
            local_dict: local namespace dict

        Returns:
            Modified list of tokens
        """
        from sympy import Symbol

        result = []

        # Merge the symbol_dict into local_dict if provided
        working_dict = dict(local_dict) if local_dict else {}

        if symbol_dict:
            working_dict.update(symbol_dict)

        for i, (tok_type, tok_str) in enumerate(tokens):
            # Token type 1 is NAME in Python's token module
            # Token type 2 is NUMBER
            if tok_type == 1:  # NAME token
                # Check if this is an identifier (not a keyword)
                if tok_str and (tok_str[0].isalpha() or tok_str[0] == '_'):
                    # Segment the identifier
                    segmented = segment_identifier(tok_str)

                    # Ensure all segmented symbols are in local_dict
                    for seg_type, seg_str in segmented:
                        if seg_type == 1 and seg_str not in working_dict:
                            # Auto-create symbol if not present
                            working_dict[seg_str] = Symbol(seg_str)

                    # Update the original local_dict
                    if local_dict is not None:
                        local_dict.update(working_dict)

                    result.extend(segmented)
                else:
                    result.append((tok_type, tok_str))
            else:
                result.append((tok_type, tok_str))

        return result

    return multichar_symbol_transformation