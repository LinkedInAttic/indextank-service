from django import shortcuts
from django.utils.translation import check_for_language, activate
from django.contrib.auth.decorators import login_required as dj_login_required
from django.http import HttpResponseRedirect, HttpResponseForbidden
from django.contrib import auth
from django.contrib.auth.models import User
from django.utils.http import urlquote
import socket
import random
import base64
import re
from django.template import RequestContext, loader
from django.conf import settings
#from ncrypt.cipher import CipherType, EncryptCipher, DecryptCipher
import binascii
import random
import hashlib
from lib import encoder
from django.contrib import messages
from templatetags.google_analytics import SCOPE_VISITOR, SCOPE_SESSION, SCOPE_PAGE

extra_context = {}
def render(template, request, context_dict={}):
    ab_test_suffix =  _ab_test_suffix(template, request)
    context = _getEnhacedRequestContext(request, context_dict)
    _fill_analytical_info(request, context, ab_test_suffix)
    if ab_test_suffix:
        return shortcuts.render_to_response(str(template) + str(ab_test_suffix), {}, context)
    else:
        return shortcuts.render_to_response(template, {}, context)

def _ab_test_suffix(template, request):
    try:
        v = request.COOKIES['ab_test_version']
        #this is paranoid, just to prevent injection.
        if not v == '.A':
            v = '.B'
        print 'already there'
    except KeyError:
        if (random.randint(0,1) == 0):
            v = '.A'
        else:
            v = '.B'
        request.COOKIES.set('ab_test_version', str(v))
        print 'setting it'
    print 'template cookie is "%s"' % (v)
    try:
        loader.find_template(template + '.A')
        loader.find_template(template + '.B')
        print 'template alternatives found. Using them.'
        return v
    except:
        print 'no template alternatives. Using base template'
        return None

def _getEnhacedRequestContext(request, context_dict):
    #this constructor calls all the configured processors.
    context = RequestContext(request, dict=context_dict)
    
    #the rest of this method should be probably rewritten an custom processors.
    global extra_context
    context['request'] = request
    
    #django.contrib.auth.context_processors.auth fills user. We should check
    #that it does what we need.
    context['user'] = request.user
    
    #this variables are used by the analytical package
    if request.user.is_authenticated():
        context['google_analytics_var1'] = ('visitor', '0', SCOPE_SESSION)
    else:
        context['google_analytics_var1'] = ('visitor', '1', SCOPE_SESSION)

    context['messages'] =  messages.get_messages(request)
    context['LOCAL'] = settings.LOCAL
    
    if request.user.is_authenticated():
        if request.user.get_profile().account.provisioner:
            context['provisioner'] = request.user.get_profile().account.provisioner.name
        elif request.user.get_profile().account.package.code.startswith('HEROKU_'):
            # HACK UNTIL HEROKU IS SET UP AS A PROVISIONER
            context['provisioner'] = 'heroku'
            

    for k in extra_context:
        if hasattr(extra_context[k], '__call__'):
            context[k] = extra_context[k]()
        else:
            context[k] = extra_context[k]
    return context


def _fill_analytical_info(request, context, ab_test_suffix):
    sp = {}
    e = []
    e.append(('pageview-' + request.path, {}))
    if request.user.is_authenticated():
        if request.user.get_profile().account.provisioner:
            sp['account_source'] = request.user.get_profile().account.provisioner.name
        sp['logged_in'] = 'true'
        sp['with_account'] = 'true'
    else:
        sp['logged_in'] = 'false'
    if context.get('plan'):
        sp['plan'] = context.get('plan')
    if ab_test_suffix:
        sp['variant'] = ab_test_suffix
    if request.method == 'GET':
        if 'utm_campaign' in request.GET:
            sp['utm_campaign'] = str(request.GET['utm_campaign'])
        if 'utm_medium' in request.GET:
            sp['utm_medium'] = str(request.GET['utm_medium'])
        if 'utm_source' in request.GET:
            sp['utm_source'] = str(request.GET['utm_source'])
        if 'ad' in request.GET:
            sp['ad'] = str(request.GET['ad'])
    context['mixpanel'] = {}
    context['mixpanel']['super_properties'] = sp
    context['mixpanel']['events'] = e


MOBILE_PATTERN_1 = '/android|avantgo|blackberry|blazer|compal|elaine|fennec|hiptop|ip(hone|od)|iris|kindle|lge |maemo|midp|mmp|mobile|o2|opera mini|palm( os)?|plucker|pocket|pre\/|psp|smartphone|symbian|treo|up\.(browser|link)|vodafone|wap|windows ce; (iemobile|ppc)|xiino/i'
MOBILE_PATTERN_2 = '/1207|6310|6590|3gso|4thp|50[1-6]i|770s|802s|a wa|abac|ac(er|oo|s\-)|ai(ko|rn)|al(av|ca|co)|amoi|an(ex|ny|yw)|aptu|ar(ch|go)|as(te|us)|attw|au(di|\-m|r |s )|avan|be(ck|ll|nq)|bi(lb|rd)|bl(ac|az)|br(e|v)w|bumb|bw\-(n|u)|c55\/|capi|ccwa|cdm\-|cell|chtm|cldc|cmd\-|co(mp|nd)|craw|da(it|ll|ng)|dbte|dc\-s|devi|dica|dmob|do(c|p)o|ds(12|\-d)|el(49|ai)|em(l2|ul)|er(ic|k0)|esl8|ez([4-7]0|os|wa|ze)|fetc|fly(\-|_)|g1 u|g560|gene|gf\-5|g\-mo|go(\.w|od)|gr(ad|un)|haie|hcit|hd\-(m|p|t)|hei\-|hi(pt|ta)|hp( i|ip)|hs\-c|ht(c(\-| |_|a|g|p|s|t)|tp)|hu(aw|tc)|i\-(20|go|ma)|i230|iac( |\-|\/)|ibro|idea|ig01|ikom|im1k|inno|ipaq|iris|ja(t|v)a|jbro|jemu|jigs|kddi|keji|kgt( |\/)|klon|kpt |kwc\-|kyo(c|k)|le(no|xi)|lg( g|\/(k|l|u)|50|54|e\-|e\/|\-[a-w])|libw|lynx|m1\-w|m3ga|m50\/|ma(te|ui|xo)|mc(01|21|ca)|m\-cr|me(di|rc|ri)|mi(o8|oa|ts)|mmef|mo(01|02|bi|de|do|t(\-| |o|v)|zz)|mt(50|p1|v )|mwbp|mywa|n10[0-2]|n20[2-3]|n30(0|2)|n50(0|2|5)|n7(0(0|1)|10)|ne((c|m)\-|on|tf|wf|wg|wt)|nok(6|i)|nzph|o2im|op(ti|wv)|oran|owg1|p800|pan(a|d|t)|pdxg|pg(13|\-([1-8]|c))|phil|pire|pl(ay|uc)|pn\-2|po(ck|rt|se)|prox|psio|pt\-g|qa\-a|qc(07|12|21|32|60|\-[2-7]|i\-)|qtek|r380|r600|raks|rim9|ro(ve|zo)|s55\/|sa(ge|ma|mm|ms|ny|va)|sc(01|h\-|oo|p\-)|sdk\/|se(c(\-|0|1)|47|mc|nd|ri)|sgh\-|shar|sie(\-|m)|sk\-0|sl(45|id)|sm(al|ar|b3|it|t5)|so(ft|ny)|sp(01|h\-|v\-|v )|sy(01|mb)|t2(18|50)|t6(00|10|18)|ta(gt|lk)|tcl\-|tdg\-|tel(i|m)|tim\-|t\-mo|to(pl|sh)|ts(70|m\-|m3|m5)|tx\-9|up(\.b|g1|si)|utst|v400|v750|veri|vi(rg|te)|vk(40|5[0-3]|\-v)|vm40|voda|vulc|vx(52|53|60|61|70|80|81|83|85|98)|w3c(\-| )|webc|whit|wi(g |nc|nw)|wmlb|wonu|x700|xda(\-|2|g)|yas\-|your|zeto|zte\-/i'

def domain():
    if settings.WEBAPP_PORT == 80:
        return settings.COMMON_DOMAIN
    else: 
        return "%s:%d"  % (settings.COMMON_DOMAIN, settings.WEBAPP_PORT)

def is_internal_navigation(request):
    ref = request.META.get('HTTP_REFERER')
    if ref:
        pattern = r'http://[^/]*\.' + domain().replace('.', r'\.')
        if re.match(pattern, ref):
            return True
        else:
            return False
    else:
        return False

def is_mobile(request):
    user_agent = request.META['HTTP_USER_AGENT'].lower()
    match1 = re.search(MOBILE_PATTERN_1, user_agent)
    match2 = re.search(MOBILE_PATTERN_2, user_agent[:4])
    return match1 or match2


def render_to_response(template, context, *args, **kwargs):
    '''TODO: move this to a processor'''
    original_template = template
    if is_mobile(context['request']):
        parts = template.split('/')
        parts[-1] = 'mobile.' + parts[-1]
        template = '/'.join(parts)
    return shortcuts.render_to_response((template, original_template), context, *args, **kwargs)

def login_required(view, *args, **kwargs):
    dj_view = dj_login_required(view, *args, **kwargs)
    def decorated(request, *args, **kwargs):
        return dj_view(request, *args, **kwargs)
    return decorated


def get_index_code(id):
    return encoder.to_key(id)

def get_index_id_for_code(code):
    return encoder.from_key(code);
