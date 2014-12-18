"""Visitors for struct ASTs."""


__all__ = [
    'NodeVisitor',
    'NodeTransformer',
    'ChangeCounter',
]


from .node import AST


class NodeVisitor:
    
    """Similar to ast.NodeVisitor. This version tracks a stack of the
    currently visited nodes. It includes a classmethod for combining
    visitor instantiation with invocation. It can be called on either
    nodes or sequences of nodes.
    
    Note that since struct nodes are immutable, NodeTransformer must be
    used if the tree is to be modified.
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
        self._visit_stack = []
        result = self.visit(tree)
        assert len(self._visit_stack) == 0, 'Visit stack unbalanced'
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
        """Dispatch to a particular node kind's visit method,
        or to generic_visit().
        """
        self._visit_stack.append(node)
        
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        result = visitor(node)
        
        self._visit_stack.pop()
        return result
    
    # Unlike ast.NodeVisitor, our list dispatching is factored out
    # into a separate method, instead of put in generic_visit().
    
    def seq_visit(self, seq):
        """Dispatch to each item of a sequence."""
        for item in seq:
            self.visit(item)
    
    def generic_visit(self, node):
        """Dispatch to each field of a node."""
        for field in node._fields:
            value = getattr(node, field)
            self.visit(value)


class NodeTransformer(NodeVisitor):
    
    """Visitor that produces a transformed copy of the input tree.
    Visit methods may return a replacement node, or None to indicate
    no change (note that this differs from ast.NodeTransformer).
    If the node is part of a sequence, it may also return a sequence
    to splice in its place -- use the empty sequence to delete the
    node.
    """
    
    # In the visitors, "no change" is indicated by returning None
    # or by returning the exact same node as was given. Returning
    # a node that is equal to ("==") but not identical to ("is")
    # the given node is considered a change. This is for efficiency.
    #
    # So long as all children return no change, seq_visit() and
    # generic_visit() return no change.
    
    def process(self, tree):
        # Intercept None returns, interpret them as leaving the
        # tree unchanged.
        result = super().process(tree)
        if result is None:
            result = tree
        return result
    
    def seq_visit(self, seq):
        changed = False
        new_seq = []
        
        for item in seq:
            result = self.visit(item)
            if result is None:
                result = item
            if result is not item:
                changed = True
            if isinstance(result, (tuple, list)):
                new_seq.extend(result)
            else:
                new_seq.append(result)
        
        if changed:
            return tuple(new_seq)
        else:
            return seq
    
    def generic_visit(self, node):
        repls = {}
        for field in node._fields:
            value = getattr(node, field)
            result = self.visit(value)
            if not (result is None or result is value):
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
