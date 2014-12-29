"""Visitors for Struct ASTs. Analogous to the visitors in the
standard library 'ast' module, with some enhancements.
"""


__all__ = [
    'NodeVisitor',
    'AdvNodeVisitor',
    'NodeTransformer',
    'AdvNodeTransformer',
    'ChangeCounter',
]


from .node import AST


class NodeVisitor:
    
    """Walk a tree, dispatching to different handlers by node type.
    To use, create a subclass and define or override the visit
    methods.
    
    When visit() is called on a node or a tuple, it recursively
    processes the subtree using node_visit(), and various handlers.
    The handler for a given node type is determined by prefixing
    the name of that type with 'visit_', e.g. 'visit_Foo' for node
    type 'Foo'. If the handler is not found, generic_visit() is used
    as the default.
    
    The handler is responsible for recursing over the subtree.
    It controls whether the tree traversal is preorder or postorder,
    or it may prune the traversal by not recursing at all. It should
    process each child by calling self.visit(child). Alternatively,
    it can call self.generic_visit(node) to get them all. Do not call
    self.visit(node), as that would create a call cycle.
    
    To invoke the visitor, call the process() method with the tree.
    Subclasses can override process to do initial setup/teardown
    actions or tweak the returned value. The run() classmethod is
    provided as a shorthand to combine instantiation and processing.
    
    You may have the handlers return a value. In this case, you
    should override generic_visit() and seq_visit() to propagate
    these returned values.
    
    Note that since Struct nodes are immutable, NodeTransformer must
    be used if you want a tree transformation.
    """
    
    @classmethod
    def run(cls, tree, *args, **kargs):
        """Convenience method for instantiating the class and running
        the visitor on tree. args and kargs are passed on to the
        constructor.
        """
        visitor = cls(*args, **kargs)
        result = visitor.process(tree)
        return result
    
    def process(self, tree):
        """Entry point for invoking the visitor."""
        result = self.visit(tree)
        return result
    
    def visit(self, tree):
        """Dispatch on a node or sequence (tuple). Other kinds
        of values are returned without processing.
        """
        if isinstance(tree, AST):
            return self.node_visit(tree)
        elif isinstance(tree, tuple):
            return self.seq_visit(tree)
        else:
            return tree
    
    def node_visit(self, node):
        """Dispatch to a particular node handler if it exists,
        or else to generic_visit().
        """
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        result = visitor(node)
        return result
    
    def seq_visit(self, seq):
        """Dispatch to each item of a sequence."""
        for item in seq:
            self.visit(item)
    
    def generic_visit(self, node):
        """Dispatch to each field of a node."""
        for field in node._fields:
            value = getattr(node, field)
            self.visit(value)


class AdvNodeVisitor(NodeVisitor):
    
    """As above, but tracks context (parent) information and allows
    for passing arbitrary arguments to visit handlers.
    
    The stack of currently visited nodes is made available in the
    _visit_stack attribute. Its format is a list of tuples (most
    recent last) of form (node, field, index):
    
        - node is the AST object being visited for that entry
        
        - field is the name of the parent's field that contains
          this node as a child, or None if there is no parent
        
        - index is the location of this node in the currently
          visited sequence, or None if we are not in a sequence.
    
    Visitors and handlers may pass *args and **kargs, which get
    propagated by the default visitor methods unchanged. However,
    the special keyword arguments '_field' and '_index' are
    intercepted by node_visit() and used to help manage _visit_stack.
    Any override of seq_visit() or generic_visit() should pass these
    keyword arguments to visit().
    """
    
    def process(self, tree):
        """Entry point for invoking the visitor."""
        self._visit_stack = []
        result = super().process(tree)
        assert len(self._visit_stack) == 0, 'Visit stack unbalanced'
        return result
    
    def visit(self, tree, *args, **kargs):
        """Dispatch on a node or sequence (tuple). Other kinds
        of values are returned without processing.
        """
        if isinstance(tree, AST):
            return self.node_visit(tree, *args, **kargs)
        elif isinstance(tree, tuple):
            return self.seq_visit(tree, *args, **kargs)
        else:
            return tree
    
    def node_visit(self, node, *args, _field=None, _index=None, **kargs):
        """Dispatch to a particular node handler if it exists,
        or else to generic_visit().
        """
        entry = (node, _field, _index)
        self._visit_stack.append(entry)
        
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        result = visitor(node, *args, **kargs)
        
        self._visit_stack.pop()
        return result
    
    def seq_visit(self, seq, *args, **kargs):
        """Dispatch to each item of a sequence."""
        for i, item in enumerate(seq):
            self.visit(item, _index=i, *args, **kargs)
    
    def generic_visit(self, node, *args, **kargs):
        """Dispatch to each field of a node."""
        for field in node._fields:
            value = getattr(node, field)
            self.visit(value, _field=field, *args, **kargs)


class NodeTransformer(NodeVisitor):
    
    """Visitor that produces a transformed copy of the input tree.
    
    Handlers may return a replacement node, or None to indicate
    no change (note that this differs from ast.NodeTransformer).
    If the node is part of a sequence, it may also return a list or
    tuple (normalized to a tuple) to splice in its place; use the
    empty sequence to delete the node from its sequence.
    """
    
    # In the handlers, "no change" is indicated by returning None
    # or by returning the exact same node as was given. Handlers
    # may assume that their subcalls to visit() will always indicate
    # "no change" by returning the node rather than None; this is
    # ensured by visit(). The same is true of generic_visit().
    #
    # This means that it is impossible to replace a part of the tree
    # with an actual "None" value. For transformers that require this
    # capability, set the class attribute _nochange_none to False,
    # which disables this feature.
    #
    # Returning a node that is equal to ("==") but not identical to
    # ("is") the given node is considered a change. This is because
    # it would be costly to recognize the case where distinct trees
    # are equal to each other. (In fact, it would take quadratic time
    # in the depth of the tree.) For efficiency, avoid returning
    # equal but non-identical values unnecessarily.
    #
    # So long as all children return no change, seq_visit() and
    # generic_visit() return no change. This means that the only
    # nodes that need to be copied are the ones that lie along
    # a path from the changed node to the root of the tree, rather
    # than all the nodes in the tree.
    
    _nochange_none = True
    """If True, when None is returned by a handler it will be
    considered the same as if the given node were returned.
    """
    
    def visit(self, tree):
        result = super().visit(tree)
        if self._nochange_none and isinstance(tree, AST) and result is None:
            result = tree
        return result
    
    def seq_visit(self, seq):
        changed = False
        new_seq = []
        
        for item in seq:
            result = self.visit(item)
            if result is not item:
                changed = True
            if isinstance(result, (tuple, list)):
                new_seq.extend(result)
            else:
                new_seq.append(result)
        
        if changed:
            return tuple(new_seq)
        else:
            # Be sure to return the original tuple so the
            # identity test in generic_visit() succeeds
            # and we potentially avoid a copy.
            return seq
    
    def generic_visit(self, node):
        repls = {}
        for field in node._fields:
            value = getattr(node, field)
            result = self.visit(value)
            if result is not value:
                repls[field] = result
        
        if len(repls) == 0:
            return node
        else:
            return node._replace(**repls)


class AdvNodeTransformer(AdvNodeVisitor):
    
    """As above but with context info and arbitrary parameters."""
    
    _nochange_none = True
    
    def visit(self, tree, *args, **kargs):
        result = super().visit(tree, *args, **kargs)
        if self._nochange_none and isinstance(tree, AST) and result is None:
            result = tree
        return result
    
    def seq_visit(self, seq, *args, **kargs):
        changed = False
        new_seq = []
        
        for i, item in enumerate(seq):
            result = self.visit(item, _index=i, *args, **kargs)
            if result is not item:
                changed = True
            if isinstance(result, (tuple, list)):
                new_seq.extend(result)
            else:
                new_seq.append(result)
        
        if changed:
            return tuple(new_seq)
        else:
            # Be sure to return the original tuple so the
            # identity test in generic_visit() succeeds
            # and we potentially avoid a copy.
            return seq
    
    def generic_visit(self, node, *args, **kargs):
        repls = {}
        for field in node._fields:
            value = getattr(node, field)
            result = self.visit(value, _field=field, *args, **kargs)
            if result is not value:
                repls[field] = result
        
        if len(repls) == 0:
            return node
        else:
            return node._replace(**repls)


class ChangeCounter(NodeTransformer):
    
    """Transformer mixin that instruments the transformation to
    record how much work is being done. Updates an external dictionary
    with the number of new nodes visited and replaced.
    """
    
    def __init__(self, instr, *args, **kargs):
        super().__init__(*args, **kargs)
        instr.setdefault('visited', 0)
        instr.setdefault('changed', 0)
        self.instr = instr
    
    def visit(self, tree):
        self.instr['visited'] += 1
        before = tree
        tree = super().visit(tree)
        if tree is not None and tree is not before:
            self.instr['changed'] += 1
        return tree
