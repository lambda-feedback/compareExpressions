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
        return self.label == other.label and self.content == other.content

    def __hash__(self):
        return hash((self.label,self.content))

    def __str__(self):
        return self.label+": "+str(self.content)

    def __repr__(self):
        # REMARK(KarlLundengaard): This is not a good repr function, but it means that the most
        # relevant info is printed in the watch window of my preferred debugger
        return self.label+": "+str(self.content)

    def set_content(self,content):
        self.content = content
        return

class ExprNode(Token):

    def __init__(self,token,children):
        super().__init__(token.label,token.content,token.original,token.start,token.end)
        self.children = []
        for child in children:
            if isinstance(child,ExprNode):
                self.children.append(child)
            elif isinstance(child,Token):
                self.children.append(ExprNode(child,[]))
            else:
                raise Exception(f"Invalid child {str(child)}")
        return

    def tree_string(self,depth=0):
        n = len(self.children)
        s = self.label+": "+str(self.content)
        for k,child in enumerate(self.children):
            s += "\n"+str(k)+": "+child.tree_string().replace("\n","\n|   ")
        return s

class SLR_Parser:

    def __init__(self,token_list,productions,start_symbol,end_symbol,null_symbol):
        self.token_list = token_list
        self.productions = productions
        self.start_symbol = start_symbol
        self.end_symbol = end_symbol
        self.null_symnol = null_symbol
        self.start_token = self.scan(start_symbol)[0]
        self.end_token = self.scan(end_symbol)[0]
        self.null_token = self.scan(null_symbol)[0]
        start_token = self.start_token
        end_token = self.end_token
        null_token = self.null_token

        # Tokenize productions
        productions_token = [(self.scan(x[0])[0],self.scan(x[1])) for x in productions]
        self.productions_token = productions_token

        # Analyse productions to find terminals and non-terminals
        non_terminals = []
        terminals = []
        for token in [prod[0] for prod in productions]:
            if token not in non_terminals:
                non_terminals.append(token)
        for production in productions:
            for token in production[1]:
                if token not in non_terminals:
                    terminals.append(token)
        terminals += [end_symbol]
        self.terminals = terminals
        self.non_terminals = non_terminals
        self.symbols = terminals+non_terminals
        terminals_token = [self.scan(x)[0] for x in terminals]
        non_terminals_token = [self.scan(x)[0] for x in non_terminals]
        self.terminals_token = [self.scan(x)[0] for x in terminals]
        self.non_terminals_token = [self.scan(x)[0] for x in non_terminals]

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
        states = {((0,0),): closure([(0,0)])}
        transitions = {}
        new_states = [((0,0),)]
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

        for state in transitions.keys():
            for (production_index,dot_index) in closure(state):
                # Fill in shift actions and goto table
                (head,body) = productions_token[production_index]
                if dot_index < len(body):
                    a = body[dot_index]
                    table_entry = parsing_table[states_index[state]][symbols_index[a]]
                    for (symbol,next_state) in transitions[state]:
                        if symbol == a:
                            table_entry.append((production_index,states_index[tuple(next_state)]))
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

        return

    def scan(self,expr):
        token_list = self.token_list
        end_symbol = self.end_symbol
        tokens = []
    
        index = [0]
        new_token = lambda l,c,s,e: Token(l,c,expr,s,e)
        index = 0
        string = ""
        while index < len(expr):
            added_token = False
            for (content,label) in token_list:
                if expr.startswith(content,index):
                    if len(string) > 0:
                        tokens.append(new_token("STRING",string,index,index+len(string)))
                        string = ""
                    tokens.append(new_token(label,content,index,index+len(content)))
                    index += len(content)
                    added_token = True
                    break
            if not added_token:
                string = string+expr[index]
                index += 1
        if len(string) > 0:
            tokens.append(new_token("STRING",string,index,index+len(string)))
        return tokens

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

    def parsing_action(self,s,a):
        return self.parsing_table[s][self._symbols_index[a]]

    def parse(self,input_tokens):
        productions_token = self.productions_token
        tokens = list(input_tokens)+[self.end_token]
        a = tokens.pop(0)
        stack = [0]
        output = []
        while True:
            parse_action = self.parsing_action(stack[-1],a)
            if parse_action < 0:
                print("ERROR")
                break
            if parse_action < len(self.states):
                stack.append(parse_action)
                a = tokens.pop(0)
            elif parse_action == len(self.states):
                #print("ACCEPT")
                break
            elif parse_action < len(self.states)+len(self.symbols):
                production = productions_token[parse_action-len(self.states)]
                handle = production[1]
                reduction = self.reductions[tuple(production[1])]
                reduction(handle,output)
                stack = stack[0:-len(production[1])]
                #print("reduce by: "+str(production[0])+" --> "+str(production[1]))
                if len(stack) == 0:
                    stack.append(self._symbols_index[a])
                    a = tokens.pop(0)
                else:
                    stack.append(self.parsing_action(stack[-1],production[0]))
            else:
                print("INVALID ENTRY")
                break
        return output

# -----------------
# UTILITY FUNCTIONS
# -----------------

leaf =  lambda handle, output: output.append(ExprNode(handle[0],[]))

#TODO: Implement the fllowing utility functions:
#   - join: joins (string) content from two childless nodes into one childless node
#   - append: adds one node as a child of another
#   - delimit: same as group but with delimiters as input

def group(handle,output):
    content = output.pop()
    output.append(\
        ExprNode(\
            Token(\
                "GROUP",\
                [handle[0],handle[2]],\
                handle[0].original,\
                handle[0].start,handle[2].end
                ),
            [content])
        )
    return

def infix(handle,output):
    b = output.pop()
    a = output.pop()
    output.append(ExprNode(handle[1],[a,b]))
    return

# -------
# TESTING
# -------

if __name__ == "__main__":

    productions = [\
        ( "S", "E"  , leaf  ),
        ( "E", "E+E", infix ),
        ( "E", "E*E", infix ),
        ( "E", "(E)", group ),
        ( "E", "I"  , leaf  )
        ]

    start_symbol = "S"
    end_symbol = "$"
    null_symbol = "e"

    infix_operators = ["+","*"]
    delimiters = ["(",")"]
    token_list = [(start_symbol, "START"),("E","EXPRESSION"),("I","IDENTIFIER")]\
        +[(x,"INFIX") for x in infix_operators]\
        +[("(","START_DELIMITER"),(")","END_DELIMITER")]\
        +[(end_symbol,"END"),(null_symbol,"NULL")]

    test_parser = SLR_Parser(token_list,productions,start_symbol,end_symbol,null_symbol)
    #print(test_parser.parsing_table_to_string())

    test_tokens = test_parser.scan("(I+I)*I+I")
    #print([token.label for token in test_tokens])

    output = test_parser.parse(test_tokens)
    print(output[0].tree_string())
