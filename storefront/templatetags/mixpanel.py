"""
Mixpanel template tags and filters.
"""

from __future__ import absolute_import

import re

from django import template
from django.template import Library, Node, TemplateSyntaxError
from django.utils import simplejson

from templatetags.utils import is_internal_ip, disable_html, get_identity, get_required_setting


MIXPANEL_API_TOKEN_RE = re.compile(r'^[0-9a-f]{32}$')
TRACKING_CODE = """
    <script type="text/javascript">
      var mpq = [];
      mpq.push(['init', '%(token)s']);
      %(commands)s
      (function() {
        var mp = document.createElement("script"); mp.type = "text/javascript"; mp.async = true;
        mp.src = (document.location.protocol == 'https:' ? 'https:' : 'http:') + "//api.mixpanel.com/site_media/js/api/mixpanel.js";
        var s = document.getElementsByTagName("script")[0]; s.parentNode.insertBefore(mp, s);
      })();
    </script>
"""
IDENTIFY_CODE = "mpq.push(['identify', '%s']); mpq.push(['name_tag', '%s']);"
EVENT_CODE = "mpq.push(['track', '%(name)s', %(properties)s]);"
SUPER_PROPERTY_CODE = "mpq.push(['register',  %(super_properties)s, 'all', '14']);"

#register = Library()
register = template.Library()


@register.simple_tag
def mixpanel_log_event(in_script, eventName, properties):
    if properties:
        code =  'mpq.push(["track", "%s", %s])' % (eventName, properties)
    else:
        code = 'mpq.push("track", "%s")' % (eventName)
    if not in_script:
        code = '<script type="text/javascript">' + code + '</script>'
    return code

@register.tag
def mixpanel(parser, token):
    """
    Mixpanel tracking template tag.

    Renders Javascript code to track page visits.  You must supply
    your Mixpanel token in the ``MIXPANEL_API_TOKEN`` setting.
    """
    bits = token.split_contents()
    if len(bits) > 1:
        raise TemplateSyntaxError("'%s' takes no arguments" % bits[0])
    return MixpanelNode()

class MixpanelNode(Node):
    def __init__(self):
        self.token = get_required_setting(
                'MIXPANEL_API_TOKEN', MIXPANEL_API_TOKEN_RE,
                "must be a string containing a 32-digit hexadecimal number")

    def render(self, context):
        commands = []
        data = context.get('mixpanel')
        commands.append(SUPER_PROPERTY_CODE % (data))
        for name, properties in data.get('events'):
            print 'name=%s, prop=%s' % (name, properties)
            commands.append(EVENT_CODE % {'name': name, 'properties': simplejson.dumps(properties)})

        identity = get_identity(context, 'mixpanel')
        if identity is not None:
            commands.append(IDENTIFY_CODE % (identity, identity))


        html = TRACKING_CODE % {'token': self.token, 'commands': " ".join(commands)}
        if is_internal_ip(context, 'MIXPANEL'):
            html = disable_html(html, 'Mixpanel')
        return html


def contribute_to_analytical(add_node):
    MixpanelNode()  # ensure properly configured
    add_node('head_bottom', MixpanelNode)
