# -----------------
# UTILITY FUNCTIONS
# -----------------

# Scanner utilities

def catch_undefined(label,content,original,start,end):
    return Token(label,content,original,start,end)

# Parser utilities

def package(production,output):
    label = production[0].label
    handle = production[1]
    children = output[-len(handle):]
    output = output[0:(-len(handle))]
    package_content = "".join(str(children))
    new_package = ExprNode(Token(label,package_content,children[0].original,children[0].start,children[0].end),children)
    output.append(new_package)
    return output

def append(production,output):
    handle = production[1]
    children = output[1-len(handle):]
    output = output[0:(1-len(handle))]
    output[-1].children = children
    output[-1]._print_rule = token_print_prefix
    return output

def join(production,output):
    label = production[0].label
    handle = production[1]
    joined_content = "".join([node.content for node in output[-len(handle):]])
    joined_end = output[-1].end
    output = output[0:(1-len(handle))]
    output[-1].label = label
    output[-1].content = joined_content
    output[-1].end = joined_end
    return output

def node(production,output):
    a = output.pop()
    output.append(ExprNode(a,[]))
    return output

def relabel(production,output):
    a = output.pop()
    output.append(Token(production[0].label,a.content,a.original,a.start,a.end))
    return output

def tag_rule_union(x,y):
    return x | y

def tag_rule_intersection(x,y):
    return x & y

def tag_transfer(production,output,rule=tag_rule_union):
    node = output[-1]
    tags = node.children[0].tags
    for child in node.children[1:]:
        tags = rule(tags,child.tags)
    output[-1].tags.update(tags)
    return output

def tag_removal(production,output,tag,rule=lambda x: True):
    if rule(output[-1].tags) and tag in output[-1].tags:
        output[-1].tags.remove(tag)
    return output

def tag(production,output,tag=None):
    if tag != None:
        if output[-1].tags == None:
            output[-1].tags = set()
        output[-1].tags.add(tag)
    return output

def group(production,output):
    end_delim = output.pop()
    content = output.pop()
    start_delim = output.pop()
    output.append(\
        ExprNode(\
            Token(\
                "GROUP",\
                [start_delim.content,end_delim.content],\
                content.original,\
                start_delim.start,end_delim.end
                ),
            [content],print_rule=token_print_group)
        )
    return output

def infix(handle,output):
    right = output.pop()
    operator = output.pop()
    left = output.pop()
    output.append(ExprNode(operator,[left,right],print_rule=token_print_infix))
    return output

# Node printing utilities

def token_print_prefix(expr_node):
    out = [expr_node.content]
    for x in expr_node.children:
        out += x._print_rule(x)
    return out

def token_print_postfix(expr_node):
    out = []
    for x in expr_node.children:
        out += x._print_rule(x)
    return out+[expr_node.content]

def token_print_infix(expr_node):
    return expr_node.children[0]._print_rule(expr_node.children[0])+[expr_node.content]+expr_node.children[1]._print_rule(expr_node.children[1])

def token_print_group(expr_node):
    out = [expr_node.content[0]]
    for x in expr_node.children:
        out += x._print_rule(x)
    out += [expr_node.content[1]]
    return out

# -------
# CLASSES
# -------

class Token:

    def __init__(self,label,content,original,start,end):
        self.label = label
        self.content = content
        self.original = original
        self.start = start
        self.end = end
        return

    def __eq__(self, other):
        return isinstance(other,Token) and self.label == other.label

    def __hash__(self):
        return hash(self.label)

    def __str__(self):
        return self.label+": "+str(self.content)

    def __repr__(self):
        # REMARK(KarlLundengaard): This is not a good repr function, but it means that the most
        # relevant info is printed in the watch window of my preferred debugger
        return self.label+": "+str(self.content)

class ExprNode(Token):

    def __init__(self,token,children,tags=None,print_rule=token_print_prefix):
        super().__init__(token.label,token.content,token.original,token.start,token.end)
        self.children = []
        for child in children:
            if isinstance(child,ExprNode):
                self.children.append(child)
            elif isinstance(child,Token):
                self.children.append(ExprNode(child,[]))
            else:
                raise Exception(f"Invalid child {str(child)}")
        if tags == None:
            self.tags = set()
        else:
            self.tags = tags
        self._print_rule = print_rule
        return

    def tree_string(self):
        n = len(self.children)
        s = str(self)
        for k,child in enumerate(self.children):
            padding = "\n|   " if k < len(self.children)-1 else "\n    "
            s += "\n"+str(k)+": "+child.tree_string().replace("\n",padding)
        return s

    def content_string(self,print_rule=None):
        if print_rule != None:
            out = print_rule(self)
        else:
            out = self._print_rule(self)
        return "".join(out)

    def original_string(self):
        left_children = self.children
        right_children = self.children
        start = self.start
        end = self.end
        while len(left_children) > 0:
            start = min(start,left_children[0].start)
            left_children = left_children[0].children
        while len(right_children) > 0:
            end = max(end,right_children[-1].end)
            right_children = right_children[-1].children
        return self.original[start:end+1]

    def __str__(self):
        return self.label+": "+str(self.content)+" tags: "+str(self.tags)

    def __repr__(self):
        # REMARK(KarlLundengaard): This is not a good repr function, but it means that the most
        # relevant info is printed in the watch window of my preferred debugger
        return self.label+": "+str(self.content)+" tags: "+str(self.tags)

class SLR_Parser:

    def __init__(self,token_list,productions,start_symbol,end_symbol,null_symbol):
        self.token_list = token_list
        self.token_list.sort(key=lambda x: -len(x[0]))
        self.productions = productions
        self.start_symbol = start_symbol
        self.end_symbol = end_symbol
        self.null_symbol = null_symbol
        self.start_token = self.scan(start_symbol,mode="bnf")[0]
        self.end_token = self.scan(end_symbol,mode="bnf")[0]
        self.null_token = self.scan(null_symbol,mode="bnf")[0]
        start_token = self.start_token
        end_token = self.end_token
        null_token = self.null_token

        # Tokenize productions
        productions_token = [
            (self.scan(x[0],mode="bnf")[0],self.scan(x[1],mode="bnf")) for x in productions
            ]
        self.productions_token = productions_token

        # Analyse productions to find terminals and non-terminals
        non_terminals = []
        terminals = []
        for token in [prod[0] for prod in productions]:
            if token not in non_terminals:
                non_terminals.append(token)
        for production in productions:
            for token in production[1]:
                if token not in terminals and token not in non_terminals:
                    terminals.append(token)
        terminals += [end_symbol,null_symbol]
        self.terminals = terminals
        self.non_terminals = non_terminals
        self.symbols = terminals+non_terminals
        terminals_token = [self.scan(x,mode="bnf")[0] for x in terminals]
        non_terminals_token = [self.scan(x,mode="bnf")[0] for x in non_terminals]
        self.terminals_token = terminals_token
        self.non_terminals_token = non_terminals_token

        # Create reductions dictionary
        self.reductions = { tuple(productions_token[k][1]): productions[k][2] for k in range(0,len(productions)) }

        # Compute dictionary with FIRST for all single tokens
        first_dict = {**{x: [x] for x in terminals_token},**{x: [] for x in non_terminals_token}}
        lengths = [-1]*len(non_terminals)
        any_first_changed = True
        while any_first_changed:
            any_first_changed = False
            for k,x in enumerate(non_terminals_token):
                if lengths[k] != len(first_dict[x]):
                    lengths[k] = len(first_dict[x])
                    any_first_changed = True
            for nt in non_terminals_token:
                prods = [x[1] for x in productions_token if x[0] == nt ]
                for prod in prods:
                    for token in prod:
                        for x in first_dict[token]:
                            if x not in first_dict[nt]:
                                first_dict[nt].append(x)
                        if null_token not in first_dict[token]:
                            break
        self._first_dict = first_dict

        # Compute dictionary with FOLLOW for all non_terminals
        first = self.first
        follow = {x: [] for x in non_terminals_token}
        follow[start_token].append(end_token)
        lengths = [-1]*len(non_terminals)
        while lengths != [len(follow[x]) for x in non_terminals_token]:
            lengths = [len(follow[x]) for x in non_terminals_token]
            for (head,body) in productions_token:
                for k,token in enumerate(body):
                    if token in non_terminals_token:
                        if null_token in self.first(body[k+1:]) or len(body[k+1:]) == 0:
                            for item in follow[head]:
                                if item not in follow[token]:
                                    follow[token].append(item)
                        for item in first(body[k+1:]):
                            if item != null_token and item not in follow[token]:
                                follow[token].append(item)
        self._follow = follow

        # Compute all states and the transitions between them
        closure = self.closure
        compute_transitions = self.compute_transitions
        start_productions = tuple([(k,0) for k in range(0,len(productions_token)) if productions_token[k][0] == start_token])
        states = {start_productions: closure(start_productions)}
        transitions = {}
        new_states = [start_productions]
        while len(new_states) > 0:
            state = new_states.pop(0)
            trans = compute_transitions(closure(list(state)))
            transitions.update({state: trans})
            for t in trans:
                if tuple(t[1]) not in states.keys():
                    states.update({tuple(t[1]): closure(t[1])})
                    new_states.append(tuple(t[1]))
        self.states = states
        self.transitions = transitions

        # Create index dictionaries to simplify state table construction
        states_index = {}
        for i,s in enumerate(states):
            states_index.update({s: i, i: s})
        self._states_index = states_index

        symbols_index = {}
        symbols = terminals_token+non_terminals_token
        for j,h in enumerate(symbols):
            symbols_index.update({h: j, j: h})
        self._symbols_index = symbols_index

        # Compute parsing table
        parsing_table = []
        for i in range(0,len(states)):
            parsing_table.append([])
            for j in range(0,len(symbols)):
                parsing_table[i].append([])

        for state in states:
            for (production_index,dot_index) in closure(state):
                # Fill in shift actions and goto table
                (head,body) = productions_token[production_index]
                if dot_index < len(body):
                    a = body[dot_index]
                    table_entry = parsing_table[states_index[state]][symbols_index[a]]
                    for (symbol,next_state) in transitions[state]:
                        if symbol == a:
                            table_entry.append((production_index,states_index[tuple(next_state)]))
                            break
                elif head == self.start_token:
                    parsing_table[states_index[state]][symbols_index[self.end_token]].append((production_index,len(self.states)))
                else:
                    # Fill in reduce actions
                    for a in follow[head]:
                        table_entry = parsing_table[states_index[state]][symbols_index[a]]
                        table_entry.append((production_index,len(states)+production_index))

        # Choose correct table entry based on precedence,
        # precedence is determined by location in productions
        # array (higher index in array means higher precedence)
        for i in range(0,len(states)):
            for j in range(0,len(symbols)):
                table_entry = parsing_table[i][j]
                if len(table_entry) == 0:
                    parsing_table[i][j] = -1
                elif len(table_entry) == 1:
                    parsing_table[i][j] = table_entry[0][1]
                else:
                    precedence = table_entry[0][0]
                    index = 0
                    for k, action in enumerate(table_entry[1:],1):
                        if precedence < action[0]:
                            precedence = action[0]
                            index = k
                    parsing_table[i][j] = table_entry[index][1]
        self.parsing_table = parsing_table

        # Check for unreachable states and reductions
        unreachable = list(range(0,len(states)+len(self.reductions)))
        for i in range(0,len(states)):
            for j in range(0,len(symbols)):
                if parsing_table[i][j] in unreachable:
                    unreachable.remove(parsing_table[i][j])
        self.parsing_table = parsing_table

        if len(unreachable) > 1:
            print("Unreachable states:")
            for x in [y for y in unreachable if y < len(states)]:
                print("\t"+self.state_string(self._states_index[x]))
            print("Unreachable reductions:")
            for x in [y for y in unreachable if y >= len(states) and y < len(states)+len(productions_token)]:
                print("\t"+self.productions[x-len(states)][0]+"-->"+str(self.productions[x-len(states)][1]))

        return

    def scan(self,expr,mode="expression"):
        token_list = self.token_list
        end_symbol = self.end_symbol
        tokens = []

        new_token = lambda l,c,s,e: Token(l,c,expr,s,e)

        token_catch_undefined = [x for x in token_list if len(x) > 2 and x[2] == catch_undefined]
        if len(token_catch_undefined) > 1:
            raise Exception("Only one token type can be used to catch undefined lexemes.")
        elif len(token_catch_undefined) < 1:
            token_catch_undefined = None
        else:
            token_catch_undefined = token_catch_undefined[0]

        if "expression" in mode:
            token_rules = [x for x in token_list if len(x) > 2 and x[2] not in {None,catch_undefined}]
            token_symbols = [x for x in token_list if len(x) == 2]
        elif "bnf" in mode:
            token_rules = []
            token_symbols = [(x[0],x[1]) for x in token_list]

        index = 0
        string = ""
        added_token = False
        while index-len(string) < len(expr):
            end_token = None
            for (content,label) in token_symbols:
                if expr.startswith(content,index):
                    end_token = new_token(label,content,index,index+len(content)-1)
                    index += len(content)
                    break
            if (end_token != None or index >= len(expr)) and len(string) > 0:
                end_token_length = 0 if end_token == None else len(end_token.content)
                added_token = False
                for token in token_rules:
                    content = token[2](string)
                    if content != None:
                        tokens.append(new_token(token[1],content,index-len(string)-end_token_length,index-end_token_length-1))
                        added_token = True
                        break
                if not added_token:
                    if token_catch_undefined != None:
                        tokens.append(token_catch_undefined[2](token_catch_undefined[1],string,expr,index-len(string)-end_token_length,index-end_token_length-1))
                    else:
                        raise Exception(f"Undefined input: {string}")
                string = ""
            elif end_token == None and index < len(expr):
                string = string+expr[index]
                index += 1
            if end_token != None:
                tokens.append(end_token)
        return tokens

    def process(self,tokens,rules):
        rules_token = [(self.scan(x[0],mode="bnf")[0],self.scan(x[1],mode="bnf"),x[2]) for x in rules]
        rules_token.sort(key=lambda x: -len(x[1]))
        index = 0
        output = list(tokens)
        output_changed = True
        k = 0
        while index < len(output) or output_changed:
            k += 1
            output_changed = False
            for (head,body,action) in rules_token:
                if output[index:index+len(body)] == body:
                    handle = output[index:index+len(body)]
                    pre = output[0:index]
                    post = output[index+len(body):]
                    output = pre + action((head,tuple(body)),handle) + post
                    output_changed = True
                    index = 0
            if not output_changed:
                index += 1
        return output

    def closure(self,item_set):
        non_terminals = self.non_terminals
        productions = self.productions
        # Items are represented as (i,j) where i indicates index
        # in production list and j position of inserted dot
        closure_set = []
        offset = -1
        new_items = item_set
        added_to_closure = [False]*len(non_terminals)
        repeat = True
        while len(new_items) > 0:
            closure_set += new_items
            offset += len(new_items)
            new_items = []
            for item in closure_set:
                i = item[0]
                j = item[1]
                follow = None
                if j < len(productions[i][1]):
                    for k,nt in enumerate(non_terminals):
                        if productions[i][1][j] == nt:
                            follow = k
                            break
                    if follow != None and not added_to_closure[follow]:
                        for k,production in enumerate(productions):
                            if production[0] == non_terminals[follow]:
                                new_items.append((k,0))
                        added_to_closure[follow] = True
        return closure_set

    def compute_transitions(self,item_set):
        productions_token = self.productions_token
        offset = 0
        transitions = []
        for item in item_set:
            i = item[0]
            j = item[1]
            if j < len(productions_token[i][1]):
                token = productions_token[i][1][j]
                if token not in [x[0] for x in transitions]:
                    transitions.append((token,[(i,j+1)]))
                else:
                    transitions[[x[0] for x in transitions].index(token)][1].append((i,j+1))
        return transitions

    def goto(state,symbol):
        items = [] 
        for (production,item) in state:
            (head,body) = productions_index[production]
            if body[item] == symbol and item < len(body):
                items.append((production,item+1))
        return self.closure(items)

    def first(self,tokens):
        # Computes FIRST for strings of tokens
        null_token = self.null_token
        first_dict = self._first_dict
        if len(tokens) == 1:
            return first_dict[tokens[0]]
        fs = []
        for token in tokens:
            for item in first_dict[token]:
                if item not in fs and item != null_token:
                    fs.append(item)
            if token != null_token:
                break
        return fs

    def parsing_table_to_string(self):
        parsing_table = self.parsing_table
        symbols = [x.content for x in self.terminals_token+self.non_terminals_token]
        states = self.states
        parsing_table_string = ["\t"+"\t".join(symbols)+"\n"]
    
        for i in range(0,len(parsing_table)):
            parsing_table_string += [str(i)+"\t"]
            for j in range(0,len(parsing_table[i])):
                if parsing_table[i][j] < 0:
                    parsing_table_string += ['x']
                elif parsing_table[i][j] < len(states):
                    parsing_table_string += ['s'+str(parsing_table[i][j])]
                else:
                    parsing_table_string += ['r'+str(parsing_table[i][j]-len(states))]
                parsing_table_string += ['\t']
            parsing_table_string += ['\n']
    
        return "".join(parsing_table_string)

    def state_string(self,state):
        items = self.closure(state)
        prod_strings = []
        for k in range(0,len(items)):
            production = self.productions_token[items[k][0]]
            dot_index =  items[k][1]
            prod_string = "".join(x.content for x in production[1][0:dot_index])+"."+"".join(x.content for x in production[1][dot_index:])
            prod_strings.append(prod_string)
        return "I"+str(self._states_index[state])+": ("+", ".join(prod_strings)+")"

    def state_string_list(self,state):
        items = self.closure(state)
        prod_strings = []
        for k in range(0,len(items)):
            production = self.productions_token[items[k][0]]
            dot_index =  items[k][1]
            prod_string = "".join(x.content for x in production[1][0:dot_index])+"."+"".join(x.content for x in production[1][dot_index:])
            prod_strings.append(prod_string)
        return ["I"+str(self._states_index[state])]+prod_strings

    def parsing_action(self,s,a):
        return self.parsing_table[s][self._symbols_index[a]]

    def parse(self,input_tokens,verbose=False,restart_on_error=False):
        productions_token = self.productions_token
        tokens = list(input_tokens)+[self.end_token]
        a = tokens.pop(0)
        stack = [0]
        output = []
        while True:
            parse_action = self.parsing_action(stack[-1],a)
            if parse_action < 0:
                if restart_on_error:
                    stack.append(0)
                    if a == self.end_token:
                        break
                    output.append(a)
                    a = tokens.pop(0)
                    continue
                else:
                    m = 70
                    raise Exception(f"{'-'*m}\nERROR:\n{'-'*m}\naccepted: {input_tokens[:-len(tokens)]}\ncurrent: {a}, {self._symbols_index[a]}\nremaining: {tokens}\nstack: {stack}\noutput: {output}\n{'-'*m}")
            if parse_action < len(self.states):
                stack.append(parse_action)
                output.append(a)
                if verbose:
                    print("shift and transition to: "+self.state_string(self._states_index[parse_action])+"  \t"+str(output))
                a = tokens.pop(0)
            elif parse_action == len(self.states):
                if verbose:
                    print("ACCEPT")
                break
            elif parse_action <= len(self.states)+len(self.productions_token):
                production = productions_token[parse_action-len(self.states)]
                reduction = self.reductions[tuple(production[1])]
                output = reduction(production,output)
                stack = stack[0:-len(production[1])]
                stack.append(self.parsing_action(stack[-1],production[0]))
                if verbose:
                    print("reduce by: "+str(production[0].content)+" --> "+"".join([x.content for x in production[1]])+"  \t"+str(output))
                    print("new state: "+self.state_string(self._states_index[stack[-1]]))
                    print("next input: "+str(a))
            else:
                m = 70
                raise Exception(f"{'-'*m}\nINVALID ENTRY:\n{'-'*m}\naccepted: {input_tokens[:-len(tokens)]}\ncurrent: {a}\nremaining: {tokens}\nstack: {stack}\noutput: {output}\n{'-'*m}")
                break
        return output

# -------
# TESTING
# -------

if __name__ == "__main__":

    productions = [\
        ( "S", "E"  , node    ),
        ( "E", "E+E", infix   ),
        ( "E", "E*E", infix   ),
        ( "E", "(E)", group   ),
        ( "E", "I"  , relabel )
        ]

    start_symbol = "S"
    end_symbol = "$"
    null_symbol = "e"

    infix_operators = ["+","*"]
    delimiters = ["(",")"]
    token_list = [(start_symbol, "START"),("E","EXPRESSION"),("I","IDENTIFIER")]\
        +[(x,"INFIX"+x) for x in infix_operators]\
        +[("(","START_DELIMITER"),(")","END_DELIMITER")]\
        +[(end_symbol,"END"),(null_symbol,"NULL")]

    test_parser = SLR_Parser(token_list,productions,start_symbol,end_symbol,null_symbol)
    print(test_parser.parsing_table_to_string())

    ref_string ='\t+\t*\t(\t)\tI\t$\te\tS\tE\n0\tx\tx\ts2\tx\ts3\tx\tx\tx\ts1\t\n1\ts4\ts5\tx\tx\tx\tr0\tx\tx\tx\t\n2\tx\tx\ts2\tx\ts3\tx\tx\tx\ts6\t\n3\tr4\tr4\tx\tr4\tx\tr4\tx\tx\tx\t\n4\tx\tx\ts2\tx\ts3\tx\tx\tx\ts7\t\n5\tx\tx\ts2\tx\ts3\tx\tx\tx\ts8\t\n6\ts4\ts5\tx\ts9\tx\tx\tx\tx\tx\t\n7\tr1\ts5\tx\tr1\tx\tr1\tx\tx\tx\t\n8\tr2\tr2\tx\tr2\tx\tr2\tx\tx\tx\t\n9\tr3\tr3\tx\tr3\tx\tr3\tx\tx\tx\t\n'

    if ref_string != test_parser.parsing_table_to_string():
        print(" ***************************************\n * WARNING: test parsing table changed *\n ***************************************")

    test_tokens = test_parser.scan("(I+I)*I+I")
    print([token.label for token in test_tokens])

    output = test_parser.parse(test_tokens)
    print(output)
    print(output[0].tree_string())
