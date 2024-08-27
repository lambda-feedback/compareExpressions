import json

evaluation_style = ("([", "])")
starting_evaluation_style = (">", "]")
criterion_style = ("[", "]")
output_style = ("{{", "}}")
special_style = ("[[", "]]")


class CriteriaGraph:

    class Node:
        def __init__(self, label, summary, details):
            self.label = label
            self.summary = summary
            self.details = details
            self.incoming = []
            self.outgoing = []
            return

        def __eq__(self, other):
            return self.label == other.label and self.summary == other.summary and self.details == other.details

    class Evaluation(Node):
        def __init__(self, label, summary, details, evaluate, replacement=None):
            super().__init__(label, summary, details)
            self.results = self.outgoing
            self.evaluate = evaluate
            self.replacement = replacement
            return

    class Criterion(Node):
        def __init__(self, label, summary, details, tags=None, feedback_string_generator=None):
            super().__init__(label, summary, details)
            self.consequences = self.outgoing
            if feedback_string_generator is not None:
                self.feedback_string_generator = feedback_string_generator
            else:
                self.feedback_string_generator = lambda x: None
            if tags is None:
                self.tags = set()
            else:
                self.tags = tags
            return

    class Output(Node):
        def __init__(self, label, summary, details, tags=None):
            super().__init__(label, summary, details)
            self.outgoing = []
            if tags is None:
                self.tags = set()
            else:
                self.tags = tags
            return

    class Edge:
        def __init__(self, source, target):
            self.source = source
            self.target = target
            return

        def __eq__(self, other):
            return self.source.label == other.source.label and self.target.label == other.target.label

        def __hash__(self):
            return (self.source.label, self.target.label).__hash__()

    RETURN = Output("RETURN", "RETURN", "Reached a previously visited node.")
    END = Output("END", "END", "Evaluation completed.")

    class Tree(Node):

        def __init__(self, node, parent=None, outgoing=None, identifier=0, main_criteria=None):
            super().__init__(node.label, node.summary, node.details)
            self.identifier = "_"+str(identifier)
            self.style = self.get_node_style(node)
            self.type_label = self.get_node_type(node, main_criteria)
            if parent is not None:
                self.incoming = [parent]
            if isinstance(node, CriteriaGraph.Output) or outgoing is None:
                self.outgoing = []
            else:
                self.outgoing = outgoing
            return

        def get_node_type(self, node, main_criteria=None):
            if main_criteria is None:
                main_criteria = []
            if isinstance(node, CriteriaGraph.Evaluation):
                type_label = "evaluation"
            elif isinstance(node, CriteriaGraph.Criterion):
                if node.label in main_criteria:
                    type_label = "main_criterion"
                else:
                    type_label = "criterion"
            elif isinstance(node, CriteriaGraph.Output):
                type_label = "output"
            else:
                raise Exception("Cannot find style for this kind of node.")
            return type_label

        def get_node_style(self, node):
            if isinstance(node, CriteriaGraph.Evaluation):
                style = evaluation_style
            elif isinstance(node, CriteriaGraph.Criterion):
                style = criterion_style
            elif isinstance(node, CriteriaGraph.Output):
                style = output_style
            else:
                raise Exception("Cannot find style for this kind of node.")
            return style

        def mermaid(self, special_nodes=None):
            if special_nodes is None:
                special_nodes = []
            nodes = [self.label+self.identifier+('"'+self.summary+'"').join(starting_evaluation_style)]
            edges = [self.label+self.identifier+" --> "+child.label+child.identifier for child in self.outgoing]
            stack = self.outgoing
            while len(stack) > 0:
                child = stack.pop()
                if child.label in special_nodes:
                    style = special_style
                else:
                    style = child.style
                nodes.append(child.label+child.identifier+('"'+child.summary+'"').join(style))
                edges += [child.label+child.identifier+" --> "+next_child.label+next_child.identifier for next_child in child.outgoing]
                stack += child.outgoing
            output = ["graph TD"]+nodes+edges
            return "\n\t".join(output)

        def as_dictionary(self):
            tree_dict = {
                "label": self.label,
                "summary": self.summary,
                "details": self.details,
                "type": self.type_label,
                "children": [node.as_dictionary() for node in self.outgoing]
            }
            return tree_dict

        def json(self):
            return str(json.dumps(self.as_dictionary()))

    def __init__(self, identifier, entry_evaluations=None):
        self.identifier = identifier
        self.evaluations = {}
        self.criteria = {}
        self.outputs = {}
        self.sufficiencies = {}
        self.entry_evaluations = entry_evaluations
        return

    def json(self):
        graph = {
            "evaluations": {
                label: {
                    "summary": node.summary,
                    "details": node.details,
                    "incoming": [n.source.label for n in node.incoming],
                    "outgoing": [n.target.label for n in node.outgoing]
                } for (label, node) in self.evaluations.items()
            },
            "criteria": {
                label: {
                    "summary": node.summary,
                    "details": node.details,
                    "incoming": [n.source.label for n in node.incoming],
                    "outgoing": [n.target.label for n in node.outgoing]
                } for (label, node) in self.criteria.items()
            },
            "outputs": {
                label: {
                    "summary": node.summary,
                    "details": node.details,
                    "incoming": [n.source.label for n in node.incoming]
                } for (label, node) in self.outputs.items()
            },
            "sufficiencies": {label: sufficiency for (label, sufficiency) in self.sufficiencies.items() if sufficiency is not None},
        }
        return str(json.dumps(graph))

    def mermaid(self):
        output = ["graph TD"]
        edges = set()
        sufficiencies = set()
        node_sets = [self.evaluations, self.criteria, self.outputs]
        node_styles = [evaluation_style, criterion_style, output_style]
        for set_index, nodes in enumerate(node_sets):
            style = node_styles[set_index]
            for (label, node) in nodes.items():
                output.append(label+style[0]+'"'+node.summary+'"'+style[1])
                edges.update([(edge.source.label, edge.target.label) for edge in node.outgoing+node.incoming])
                if self.sufficiencies.get(label, None) is not None:
                    sufficiencies.update([(label, sufficiency) for sufficiency in self.sufficiencies.get(label, None)])
        for edge in edges:
            output.append(" --> ".join(edge))
        for sufficiency in sufficiencies:
            output.append(" -.-> ".join(sufficiency))
        return "\n\t".join(output)

    def add_evaluation_node(self, label, summary, details, sufficiencies=None, evaluate=None, feedback_string_generator=None):
        if feedback_string_generator is not None:
            raise Exception(f"{label} is an evaluation node, evaluation nodes cannot generate feedback strings.")
        if label in self.evaluations.keys():
            raise Exception(f"Evaluation node {label} is already defined.")
        else:
            node = CriteriaGraph.Evaluation(label, summary, details, evaluate)
            self.evaluations.update({label: node})
            self.sufficiencies.update({label: sufficiencies})
        return node

    def add_criterion_node(self, label, summary, details, sufficiencies=None, evaluate=None, feedback_string_generator=None):
        if label in self.criteria.keys():
            raise Exception(f"Criterion node {label} is already defined.")
        if sufficiencies is not None:
            raise Exception("Criterion nodes cannot have sufficiencies.")
        node = CriteriaGraph.Criterion(label, summary=summary, details=details, feedback_string_generator=feedback_string_generator)
        self.criteria.update({label: node})
        self.sufficiencies.update({label: sufficiencies})
        return node

    def add_output_node(self, label, summary, details):
        if label in self.outputs.keys():
            raise Exception(f"Output node {label} is already defined.")
        else:
            node = CriteriaGraph.Output(label, summary, details)
            self.outputs.update({label: node})
        return node

    def add_node(self, node):
        if isinstance(node, CriteriaGraph.Evaluation):
            self.add_evaluation_node(node.label, node.summary, node.details, node.sufficiencies)
        elif isinstance(node, CriteriaGraph.Criterion):
            self.add_criterion_node(node.label, node.summary, node.details)
        elif isinstance(node, CriteriaGraph.Output):
            self.add_output_node(node.label, node.summary, node.details)
        else:
            raise Exception("Can only add evaluation, criterion or output nodes to criteria graph.")

    def attach(self, source_label, target_label, summary=None, details=None, sufficiencies=None, evaluate=None, feedback_string_generator=None):
        source = self.evaluations.get(source_label, None)
        if source is None:
            source = self.criteria.get(source_label, None)
        if source is None:
            raise Exception(f"Unknown node {source_label}.")

        if isinstance(source, CriteriaGraph.Evaluation):
            target_set = self.criteria
            target_generator = self.add_criterion_node
            target_alternative_set = {}
            target_wrong_type_set = self.evaluations
            type_name = "evaluation"
            other_type_name = "criterion"
        elif isinstance(source, CriteriaGraph.Criterion):
            target_set = self.evaluations
            target_generator = self.add_evaluation_node
            target_alternative_set = self.outputs
            target_wrong_type_set = self.criteria
            type_name = "criterion"
            other_type_name = "evaluation"
        elif isinstance(source, CriteriaGraph.Output):
            raise Exception(f"{source_label} is an output nodes. Output nodes cannot have outgoing edges.")
        else:
            raise Exception(f"Source node {source_label} is an invalid type.")

        target = target_set.get(target_label, None)
        if target is None:
            target = target_alternative_set.get(target_label, None)
            if target is None:
                target = target_wrong_type_set.get(target_label, None)
                if target is None:
                    if summary is None or details is None:
                        raise Exception(f"Unknown node {target_label}. If you wish to create a new node summary and details must be specified.")
                    else:
                        target = target_generator(target_label, summary=summary, details=details, sufficiencies=sufficiencies, evaluate=evaluate, feedback_string_generator=feedback_string_generator)
                else:
                    raise Exception(f"Both {source_label} and {target_label} are {type_name} nodes. Only {other_type_name} nodes can be attached to {type_name} nodes.")

        edge = CriteriaGraph.Edge(source, target)
        if edge in source.outgoing:
            raise Exception(f"{target_label} is already attached to {source_label}.")
        else:
            source.outgoing.append(edge)
            target.incoming.append(edge)
        return

    def add_sufficiencies(self, source_label, sufficiencies):
        if source_label in self.evaluations.keys():
            if self.sufficiencies.get(source_label, None) is None:
                self.sufficiencies.update({source_label: []})
            for sufficiency in sufficiencies:
                if sufficiency not in self.sufficiencies[source_label]:
                    self.sufficiencies[source_label].append(sufficiency)
        else:
            raise Exception(f"Unknown evaluation node {source_label}. Only evaluation nodes can have sufficiencies.")
        return

    def starting_evaluations(self, label):
        # TODO: Consider if starting evaluations should only accept evaluation nodes
        #       instead of guessing the intent when using criteria nodes as targets
        if label in self.criteria.keys():
            main_criteria = self.criteria[label]
            base_starting_evaluations = set(edge.source.label for edge in main_criteria.incoming)
        elif label in self.evaluations.keys():
            base_starting_evaluations = set([label])
        else:
            raise Exception(f"No criterion or evaluation with label {label}.")
        starting_evaluations = set()
        candidate_starting_evaluations = base_starting_evaluations
        while len(candidate_starting_evaluations) > 0:
            label = candidate_starting_evaluations.pop()
            if self.sufficiencies.get(label, None) is None:
                starting_evaluations.update([label])
            else:
                for sufficiency in self.sufficiencies.get(label, []):
                    candidate_starting_evaluations.update([edge.source.label for edge in self.criteria[sufficiency].incoming])
        if len(starting_evaluations) == 0:
            starting_evaluations = base_starting_evaluations
        return starting_evaluations

    def build_tree(self, starting_evaluation, return_node=RETURN, main_criteria=None):
        node = self.evaluations.get(starting_evaluation, None)
        if node is None:
            raise Exception(f"Unknown evaluation node {node.label}.")
        identifier = 0
        root_node = CriteriaGraph.Tree(node, identifier=identifier, main_criteria=main_criteria)
        stack = [(edge.target, root_node) for (k, edge) in enumerate(node.outgoing)]
        visited_nodes = [node.label]
        while len(stack) > 0:
            node, parent = stack.pop()
            if node.label in visited_nodes:
                parent.outgoing.append(CriteriaGraph.Tree(CriteriaGraph.Output("RETURN"+str(identifier), "Go to: "+node.label, "Reached a previously visited node."), parent=parent, identifier=identifier, main_criteria=main_criteria))
            else:
                tree_node = CriteriaGraph.Tree(node, parent=parent, identifier=identifier, main_criteria=main_criteria)
                parent.outgoing.append(tree_node)
                if not isinstance(node, CriteriaGraph.Output):
                    visited_nodes.append(node.label)
                stack += [(edge.target, tree_node) for (k, edge) in enumerate(node.outgoing)]
            identifier += 1
        return root_node

    def trees(self, label):
        trees = [self.build_tree(start, main_criteria=[label]) for start in self.starting_evaluations(label)]
        return trees

    def generate_feedback(self, response, main_criteria):
        evaluations = set().union(self.starting_evaluations(main_criteria))
        visited_evaluations = set()
        feedback = dict()
        while len(evaluations) > 0:
            e = evaluations.pop()
            if e in self.evaluations.keys() and self.evaluations[e].replacement is not None:
                visited_evaluations.update({e})
                e = self.evaluations[e].replacement.label
            if e not in visited_evaluations and e in self.evaluations.keys():
                visited_evaluations.update({e})
                try:
                    results = self.evaluations[e].evaluate(response)
                except Exception as exc:
                    print(e)
                    print(self.evaluations)
                    raise exc
                feedback.update(results)
                for criterion in results.keys():
                    labels = {edge.target.label for edge in self.criteria[criterion].outgoing}
                    evaluations = evaluations.union(labels)
        return feedback
