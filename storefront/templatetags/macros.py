from django import template
from django.template import TemplateSyntaxError

register = template.Library()

"""
    The MacroRoot node (= %enablemacros% tag) functions quite similar to 
    the ExtendsNode from django.template.loader_tags. It will capture 
    everything that follows, and thus should be one of the first tags in 
    the template. Because %extends% also needs to be the first, if you are 
    using template inheritance, use %extends_with_macros% instead.
    
    This whole procedure is necessary because otherwise we would have no
    possiblity to access the blocktag referenced by a %repeat% (we could 
    do it for %macro%, but not for %block%, at least not without patching
    the django source).
    
    So what we do is add a custom attribute to the parser object and store
    a reference to the MacroRoot node there, which %repeat% object will
    later be able to access when they need to find a block.
    
    Apart from that, the node doesn't do much, except rendering it's childs.
"""
class MacroRoot(template.Node):
    def __init__(self, nodelist=[]):
        self.nodelist = nodelist
        
    def render(self, context):
        return self.nodelist.render(context)
        
    def find(self, block_name, parent_nodelist=None):        
        # parent_nodelist is internally for recusion, start with root nodelist
        if parent_nodelist is None: parent_nodelist = self.nodelist
        
        from django.template.loader_tags import BlockNode
        for node in parent_nodelist:
            if isinstance(node, (MacroNode, BlockNode)):                
                if node.name == block_name:
                    return node
            if hasattr(node, 'nodelist'):               
                result = self.find(block_name, node.nodelist)
                if result:
                    return result
        return None # nothing found
        
def do_enablemacros(parser, token):
    # check that there are no arguments
    bits = token.split_contents()
    if len(bits) != 1:
        raise TemplateSyntaxError, "'%s' takes no arguments" % bits[0]
    # create the Node object now, so we can assign it to the parser
    # before we continue with our call to parse(). this enables repeat
    # tags that follow later to already enforce at the parsing stage
    # that macros are correctly enabled.
    parser._macro_root = MacroRoot()
    # capture the rest of the template
    nodelist = parser.parse()
    if nodelist.get_nodes_by_type(MacroRoot):
        raise TemplateSyntaxError, "'%s' cannot appear more than once in the same template" % bits[0]
    # update the nodelist on the previously created MacroRoot node and
    # return  it.
    parser._macro_root.nodelist = nodelist
    return parser._macro_root
    
def do_extends_with_macros(parser, token):
    from django.template.loader_tags import do_extends
    # parse it as an ExtendsNode, but also create a fake MacroRoot node
    # and add it to the parser, like we do in do_enablemacros().
    parser._macro_root = MacroRoot()
    extendsnode = do_extends(parser, token)
    parser._macro_root.nodelist = extendsnode.nodelist
    return extendsnode

"""
    %macro% is pretty much exactly like a %block%. Both can be repeated, but
    the macro does not output it's content by itself, but *only* if it is 
    called via a %repeat% tag.    
"""

from django.template.loader_tags import BlockNode, do_block

class MacroNode(BlockNode):
    def render(self, context):
        return ''
        
    # the render that actually works
    def repeat(self, context):        
        return super(MacroNode, self).render(context)

def do_macro(parser, token):
    # let the block parse itself
    result = do_block(parser, token)
    # "upgrade" the BlockNode to a MacroNode and return it. Yes, I was not 
    # completely comfortable with it either at first, but Google says it's ok.
    result.__class__ = MacroNode
    return result
      
"""
    This (the %repeast%) is the heart of the macro system. It will try to 
    find the specified %macro% or %block% tag and render it with the most 
    up-to-date context, including any number of additional parameters passed 
    to the repeat-tag itself.
"""    
class RepeatNode(template.Node):    
    def __init__(self, block_name, macro_root, extra_context):
        self.block_name = block_name
        self.macro_root = macro_root
        self.extra_context = extra_context

    def render(self, context):
        block = self.macro_root.find(self.block_name)
        if not block:
            # apparently we are not supposed to raise exceptions at rendering 
            # stage, but this is serious, and we cannot do it while parsing.
            # once again, it comes down to being able to support repeating of
            # standard blocks. If we would only support our own %macro% tags,
            # we would not need the whole %enablemacros% stuff and could do
            # things differently.
            raise TemplateSyntaxError, "cannot repeat '%s': block or macro not found" % self.block_name
        else:
            # resolve extra context variables
            resolved_context = {}
            for key, value in self.extra_context.items():
                resolved_context[key] = value.resolve(context)
            # render the block with the new context
            context.update(resolved_context)
            if isinstance(block, MacroNode):
                result = block.repeat(context)
            else:
                result = block.render(context)
            context.pop()
            return result

def do_repeat(parser, token):
    # Stolen from django.templatetags.i18n.BlockTranslateParser
    # Parses something like  "with x as y, i as j", and 
    # returns it as a  context dict.
    class RepeatTagParser(template.TokenParser):
        def top(self):
            extra_context = {}
            # first tag is the blockname
            try: block_name = self.tag()
            except TemplateSyntaxError: 
                raise TemplateSyntaxError("'%s' requires a block or macro name" % self.tagname)
            # read param bindings
            while self.more():
                tag = self.tag()
                if tag == 'with' or tag == 'and':
                    value = self.value()
                    if self.tag() != 'as':
                        raise TemplateSyntaxError, "variable bindings in %s must be 'with value as variable'" % self.tagname
                    extra_context[self.tag()] = parser.compile_filter(value)                
                else:
                    raise TemplateSyntaxError, "unknown subtag %s for '%s' found" % (tag, self.tagname)
            return self.tagname, block_name, extra_context
    
    # parse arguments
    (tag_name, block_name, extra_context) = \
        RepeatTagParser(token.contents).top()
    # return as a RepeatNode
    if not hasattr(parser, '_macro_root'):
        raise TemplateSyntaxError, "'%s' requires macros to be enabled first" % tag_name
    return RepeatNode(block_name, parser._macro_root, extra_context)

# register all our tags
register.tag('repeat', do_repeat)
register.tag('macro', do_macro)
register.tag('enablemacros', do_enablemacros)
register.tag('extends_with_macros', do_extends_with_macros)