"""Visitors for struct ASTs."""


from iast.node import AST


__all__ = [
    'NodeVisitor',
    'NodeTransformer',
]


class NodeVisitor:
    
    """Similar to ast.NodeVisitor. This version tracks a stack of the
    currently visited nodes. It includes a classmethod for combining
    visitor instantiation with invocation. It can be called on either
    nodes or sequences of nodes.
    
    Note that since struct nodes are immutable, NodeTransformer must be
    used if the tree is to be modified.
    """
    
    @classmethod
    def run(cls, value, *args, **kargs):
        """Convenience method for instantiating the class and running
        the visitor on value. args and kargs are passed on to the
        constructor.
        """
        visitor = cls(*args, **kargs)
        result = visitor.process(value)
        return result
    
    def process(self, value):
        """Entry point for invoking the visitor."""
        self._visit_stack = []
        result = self.visit(value)
        assert len(self._visit_stack) == 0, 'Visit stack unbalanced'
        return result
    
    def visit(self, value):
        """Dispatch on a node or sequence (tuple). Other kinds
        of values are returned without processing.
        """
        if isinstance(value, AST):
            return self.node_visit(value)
        elif isinstance(value, tuple):
            return self.seq_visit(value)
        else:
            return value
    
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
    
    def process(self, value):
        # Intercept None returns, interpret them as leaving the
        # value unchanged.
        result = super().process(value)
        if result is None:
            result = value
        return result
    
    def seq_visit(self, seq):
        # If everything comes back None, return None to avoid
        # unnecessary work. If something comes back non-None,
        # create a new sequence with the new values spliced in.
        
        changed = False
        new_seq = []
        
        for item in seq:
            result = self.visit(item)
            if result is None:
                result = item
            else:
                changed = True
            if isinstance(result, (tuple, list)):
                new_seq.extend(result)
            else:
                new_seq.append(result)
        
        if changed:
            return tuple(new_seq)
        else:
            return None
    
    def generic_visit(self, node):
        # If children return non-None values, form a new node
        # with the new child values.
        
        repls = {}
        for field in node._fields:
            value = getattr(node, field)
            result = self.visit(value)
            if result is not None:
                repls[field] = result
        
        if len(repls) == 0:
            return None
        else:
            return node._replace(**repls)
