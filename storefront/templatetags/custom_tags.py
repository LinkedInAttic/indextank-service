from django import template
from django.template import Node

from django.conf import settings
import random

register = template.Library()

def var_tag_compiler(params, defaults, name, node_class, parser, token):
    "Returns a template.Node subclass."
    bits = token.split_contents()[1:]
    return node_class(map(parser.compile_filter, bits))

def simple_var_tag(func):
    params, xx, xxx, defaults = template.getargspec(func)

    class SimpleNode(Node):
        def __init__(self, vars_to_resolve):
            self.vars_to_resolve = vars_to_resolve

        def render(self, context):
            resolved_vars = [var.resolve(context, True) for var in self.vars_to_resolve]
            return func(*resolved_vars)

    compile_func = template.curry(var_tag_compiler, params, defaults, getattr(func, "_decorated_function", func).__name__, SimpleNode)
    compile_func.__doc__ = func.__doc__
    register.tag(getattr(func, "_decorated_function", func).__name__, compile_func)
    return func

@simple_var_tag
def static(*parts):
    path = ''.join(parts)
    urls = settings.STATIC_URLS
    size = len(urls)
    h = hash(path) % size
    if h < 0:
        h += size
    return urls[h] + '/' + path

@register.filter(name='random')
def rand(value):
    return random.randint(1,value)

@register.filter(name='concat')
def concat(value, arg):
    return str(value) + str(arg)
 
@register.filter(name='get')
def doget(value,arg):
    return dict(value).get(arg) or '' 

@register.filter(name='range')
def rangefilter(value):
    return xrange(int(value))

@register.simple_tag
def box(kind):
    return '<div class="%s"><div class="%s_bg"><div class="%s_top"><div class="%s_bottom"><div class="%s_main">' % (kind,kind,kind,kind,kind)

@register.simple_tag
def endbox():
    return '</div></div></div></div></div>'

@register.simple_tag
def bg(kind):
    return '<div class="%s"><div class="%s_bg"><div class="%s_top"><div class="%s_bottom">' % (kind,kind,kind,kind)

@register.simple_tag
def endbg():
    return '</div></div></div></div>'
