import pydot # Used for creating visualization of criteria graph

def undefined_key(key):
    raise KeyError("No feedback defined for key: "+str(key))


def no_feedback(inputs):
    return ""


def flip_bool_result(result):
    return not result

class Criterion:

    def __init__(self, check, feedback_for_undefined_key=undefined_key, doc_string=None):
        self.check = check
        self.feedback = dict()
        self.feedback_for_undefined_key = feedback_for_undefined_key
        self.doc_string = doc_string
        return

    def __getitem__(self, key):
        if key in self.feedback.keys():
            return self.feedback[key]
        else:
            return self.feedback_for_undefined_key

    def __setitem__(self, key, value):
        self.feedback.update({key: value})
        return

undefined_optional_parameter = object()

class CriteriaGraphNode:

    def __init__(self, label, criterion=None, children=undefined_optional_parameter, override=True, result_map=None):
        self.label = label
        self.criterion = criterion
        self.result_map = result_map
        self.override = override
        if children is undefined_optional_parameter:
            self.children = dict()
        else:
            self.children = children
        return

    def __getitem__(self, key):
        if key in self.children.keys():
            return self.children[key]
        else:
            return None

    def __setitem__(self, key, value):
        self.children.update({key: value})
        return

    def traverse(self, check, previous_result=None):
        if self.criterion is None or self.override is False:
            result = previous_result
        else:
            result = check(self.label, self.criterion)
        if self.children is not None:
            try:
                if self.children[result] is not None:
                    prev_res = result
                    if self.result_map is not None:
                        prev_res = self.result_map(result)
                    result = self.children[result].traverse(check, previous_result=prev_res)
            except KeyError as exc:
                raise Exception(f"Unexpected result ({str(result)}) in criteria {self.label}.") from exc
        return result

    def get_by_label(self, label):
        if self.label == label:
            return self
        else:
            if self.children is not None:
                for child in self.children.values():
                    result = None
                    if child is not None:
                        result = child.get_by_label(label)
                    if result is not None:
                        return result
        return None

END = CriteriaGraphNode("END", children=None)

class CriteriaGraphContainer:
    '''
    This container class provides the following utility functionality:
        - Ensures that an appropriate START node is created
        - Streamlines graph specification via the attach and finish functions
    '''
    # Consider adding the following functionality:
    #    - Allow attaching graphnodes or other containers directly

    def __init__(self, criteria_dict):
        self.START = CriteriaGraphNode("START")
        self.criteria = criteria_dict
        return

    def get_by_label(self, label):
        return self.START.get_by_label(label)

    def attach(self, source, label, result=None, criterion=undefined_optional_parameter, **kwargs):
        try:
            source = self.get_by_label(source)
        except KeyError as exc:
            raise KeyError(f"Unknown connection node: {source}") from exc
        if criterion is undefined_optional_parameter:
            try:
                criterion = self.criteria[label]
            except KeyError as exc:
                raise KeyError(f"Unknown criteria: {label}") from exc
        source[result] = CriteriaGraphNode(label, criterion, **kwargs)
        return

    def finish(self, source, result):
        try:
            source = self.get_by_label(source)
        except KeyError as exc:
            raise KeyError(f"Unknown connection node: {source}") from exc
        source[result] = END
        return

def traverse(node, check):
    if isinstance(node, CriteriaGraphContainer):
        node = node.START
    result = None
    while node.children is not None:
        result_map = None
        if node.result_map is not None:
            result_map = node.result_map
        if node.criterion is not None and node.override is True:
            result = check(node.label, node.criterion)
        try:
            if node.children[result] is not None:
                node = node.children[result]
        except KeyError as exc:
            raise Exception(f"Unexpected result ({str(result)}) in criteria {node.label}.") from exc
        if result_map is not None:
            result = result_map(result)
    return result

def generate_svg(root_node, filename, dummy_input=None):
    # Generates a dot description of the subgraph with the given node as root and uses graphviz generate a visualization the graph in svg format
    splines = "spline"
    style = "filled"
    rankdir = "TB"
    result_compass = None
    if rankdir == "TB":
        result_compass = ("n","s")
    if rankdir == "LR":
        result_compass = ("w","e")
    graph_attributes = [f'splines="{splines}"', f'node [style="{style}"]', f'rankdir="{rankdir}"']
    criteria_shape = "polygon"
    special_shape = "ellipse"
    criteria_color = "#00B8D4"
    special_color = "#2F3C86"
    criteria_fillcolor = "#E5F8FB"
    result_fillcolor = "#C5CAE9"
    special_fillcolor = "#4051B5"
    criteria_fontcolor = "#212121"
    special_fontcolor = "#FFFFFF"
    nodes_to_be_processed = [root_node]
    nodes_already_processed = []
    nodes = []
    edges = []
    number_of_ghost_nodes = 0
    while len(nodes_to_be_processed) > 0:
        node = nodes_to_be_processed.pop()
        label = node.label
        tooltip = node.label
        shape = special_shape
        color = special_color
        fillcolor = special_fillcolor
        fontcolor = special_fontcolor
        feedback_descriptions = dict()
        if node.criterion is not None:
            shape = criteria_shape
            color = criteria_color
            fillcolor = criteria_fillcolor
            fontcolor = criteria_fontcolor
            label = node.criterion.check
            feedback_descriptions.update({key: value(dummy_input) for (key, value) in node.criterion.feedback.items()})
            if node.criterion.doc_string is not None:
                tooltip = node.criterion.doc_string
        nodes.append(f'{node.label} [label="{label}" tooltip="{tooltip}" shape="{shape}" color="{color}" fillcolor="{fillcolor}" fontcolor="{fontcolor}"]')
        if node.children is not None:
            for (result, target) in node.children.items():
                if result is None:
                    edges.append(f'{node.label} -> {target.label}')
                else:
                    ghost_label = f'GHOST_NODE_{str(number_of_ghost_nodes)}'
                    result_feedback = feedback_descriptions.get(result,"")
                    if result_feedback.strip() == "":
                        result_feedback = 'No new feedback produced'
                    nodes.append(f'{ghost_label} [label="{str(result)}" fillcolor="{result_fillcolor}" tooltip="{result_feedback}"]')
                    number_of_ghost_nodes += 1
                    edges.append(f'{node.label}:{result_compass[1]} -> {ghost_label}:{result_compass[0]} [arrowhead="none"]')
                    edges.append(f'{ghost_label}:{result_compass[1]} -> {target.label}')
                if target not in nodes_already_processed and target not in nodes_to_be_processed:
                    nodes_to_be_processed.append(target)
            nodes_already_processed.append(node)
    dot_preamble = 'digraph {'+'\n'.join(graph_attributes)+'\n'
    dot_postamble = '\n}'
    dot_string = dot_preamble+"\n".join(nodes+edges)+dot_postamble
    graphs = pydot.graph_from_dot_data(dot_string)
    graph = graphs[0]
    graph.write_svg(filename)
    return dot_string