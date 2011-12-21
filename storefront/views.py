from django.contrib.auth.models import User
from django.contrib import auth

from util import render, login_required, get_index_code, get_index_id_for_code
from models import PFUser, Account, Package, Index, ScoreFunction, BetaTestRequest, BetaInvitation, AccountPayingInformation, PaymentSubscription, ContactInfo, BlogPostInfo
import forms
from django.http import HttpResponseRedirect, Http404, HttpResponseNotFound,\
  HttpResponse, HttpResponseForbidden, HttpResponsePermanentRedirect,\
    HttpResponseBadRequest
from django.db import IntegrityError
from datetime import timedelta
import datetime
import time
from forms import IndexForm, ScoreFunctionForm, BetaTestForm
from django.core.urlresolvers import reverse
from django.template import TemplateDoesNotExist, loader
from lib.indextank.client import ApiClient, IndexAlreadyExists, TooManyIndexes, InvalidDefinition, InvalidQuery
from django.db.models import Max
from django.utils import simplejson as json

from models import generate_forgotpass

from lib.authorizenet import AuthorizeNet, BillingException
from lib import mail, encoder

import hashlib
import urllib, urllib2

import os
from django.conf import settings

from flaptor.indextank.rpc import DeployManager as TDeployManager

from thrift.transport import TSocket
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol
from thrift.server import TServer

from django.core.mail import send_mail
from django.forms.models import ModelForm
from django.contrib import messages
from django.contrib.auth.management.commands.createsuperuser import is_valid_email

import csv
from django.template.context import Context

class JsonResponse(HttpResponse):
    def __init__(self, json_object, *args, **kwargs):
        body = json.dumps(json_object)
        if 'callback' in kwargs:
            callback = kwargs.pop('callback')
            if callback:
                body = '%s(%s)' % (callback, body)
        super(JsonResponse, self).__init__(body, *args, **kwargs)

def force_https(func):
    if settings.DEBUG:
        return func
    def wrapped_func(request,*args,**kwargs):
        if request.is_secure():
            return func(request,*args,**kwargs)
        else:
            return HttpResponsePermanentRedirect("https://%s%s" % (request.get_host(), request.get_full_path()))
    return wrapped_func

def root(request):
    if request.user.is_authenticated():
        return HttpResponseRedirect(reverse('dashboard'))
    return home(request) 

def poweredby(request):
    #Eventually we may want to track this links separated from the rest of the page.
    return HttpResponseRedirect(reverse('root'))

def home(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        if name and email:
            try:
                ci = ContactInfo()
                ci.name = name
                ci.email = email
                ci.source = 'contestinfo@home'
                ci.save()
                messages.success(request, 'We\'ve added %s. Thanks for subscribing for details on our upcoming contests.' % email)
                return HttpResponseRedirect(reverse('home'))
            except:
                messages.error(request, 'You need to enter both your name and email.')
        else:
            messages.error(request, 'You need to enter both your name and email')
    
    blog_posts = []

    try:
      blog_posts_obj = BlogPostInfo.objects.all().order_by('-date')[:3]
      for post in blog_posts_obj:
        blog_posts.append({
          'url':post.url, 
          'title':post.title, 
          'date':post.date.strftime('%B %d'), 
          'author':post.author})

    except:
      pass

    return render('home.html', request, context_dict={'navigation_pos': 'home', 'blog_posts': blog_posts})
  
def pricing(request):
    return render('pricing.html', request, context_dict={'navigation_pos': 'pricing',})

def packages(request):
    return render('packages.html', request, context_dict={'navigation_pos': 'home'})

def quotes(request):
    return render('quotes.html', request, context_dict={'navigation_pos': 'home'})

def documentation(request, path='documentation'):
    if '.' in path[-5:]:
        template = 'documentation/%s' % path
    else:
        template = 'documentation/%s.html' % path
    try:
        return render(template, request, context_dict={'navigation_pos': 'documentation'})
    except TemplateDoesNotExist:
        return render('coming-soon.html', request, context_dict={'navigation_pos': 'documentation'})

def search(request):
    if request.method == 'GET':
        query = request.GET.get('query').strip()
        context = {'query': query}
        return render('search_results.html', request, context_dict=context)
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


@force_https
def login(request):
    login_form = forms.LoginForm()
    login_message = ''
    if request.method == 'POST':
        login_form = forms.LoginForm(data=request.POST)
        if login_form.is_valid():
            try:
                email = login_form.cleaned_data['email']
                if email == 'apiurl@indextank.com':
                    username = email
                else:
                    username = PFUser.objects.get(email=email).user.username
                user = auth.authenticate(username=username, password=login_form.cleaned_data['password'])
                if user is not None:
                    if user.is_active:
                        auth.login(request, user)
                        return HttpResponseRedirect(request.GET.get('next') or '/dashboard');
                    else:
                        login_message = 'Account disabled'
                else:
                    login_message = 'Wrong email or password'
            except PFUser.DoesNotExist: #@UndefinedVariable
                login_message = 'Wrong email or password'

    context = {
        'login_form': login_form,
        'login_message': login_message,
        'navigation_pos': 'home',
        'next': request.GET.get('next') or '/dashboard',
    }
    
    return render('login.html', request, context_dict=context)

@force_https
def forgot_password(request):
    forgot_form = forms.ForgotPassForm()
    message = ''
    if request.method == 'POST':
        forgot_form = forms.ForgotPassForm(data=request.POST)
        if forgot_form.is_valid():
            try:
                pfuser = PFUser.objects.get(email=forgot_form.cleaned_data['email'])
                if pfuser is not None:
                    if pfuser.user.is_active:
                        new_pass = generate_forgotpass(pfuser.id)
                        pfuser.user.set_password(new_pass)
                        pfuser.user.save()
                        pfuser.change_password = True
                        pfuser.save()
                        send_mail('IndexTank password reset', 'Your IndexTank password has been reset to: ' + new_pass, 'IndexTank <betatesting@indextank.com>', [pfuser.email], fail_silently=False)
                        messages.success(request, 'Password reset successfully. Check your email inbox.')
                        return HttpResponseRedirect(reverse('login'))
                    else:
                        message = 'Account disabled'
                else:
                    message = 'The email address does not belong to an IndexTank account'
            except PFUser.DoesNotExist: #@UndefinedVariable
                message = 'The email address does not belong to an IndexTank account'

    context = {
        'forgot_form': forgot_form,
        'message': message,
        'navigation_pos': 'home',
    }
    
    return render('forgot_pass.html', request, context_dict=context)

def default_sso_account_fetcher(id):
    return Account.objects.get(apikey__startswith=id+'-')
def heroku_sso_account_fetcher(id):
    return Account.objects.get(id=id)

def sso_heroku(request, id):
    return sso(request, id, fetcher=heroku_sso_account_fetcher)
    
def sso(request, id, fetcher=default_sso_account_fetcher):
    '''
        SSO for provisioners
    '''
    timestamp = int(request.GET.get('timestamp',0))
    token = request.GET.get('token','')
    calculated_token = hashlib.sha1("%s:%s:%s"%(id,'D9YmWpRfZv0pJn05',timestamp)).hexdigest()
    # check token
    if token != calculated_token:
        return HttpResponseForbidden("token")

    # token expire on a 5 minute window
    if abs(int(time.time()) - timestamp) > 300:
        return HttpResponseForbidden("expired")

    # so, just log him in.
    account = fetcher(id)
    user = auth.authenticate(username=account.user.user.username, password=account.apikey.split('-', 1)[1])
    if user is not None:
        if user.is_active:
            auth.login(request,user)
            
            cookies = {}
            request.session['provisioner_navbar_html'] = ''
            #if account.provisioner and account.provisioner.name == 'heroku':
            # HACK TO SUPPORT HEROKU TRANSITION (UNTIL IT's A PROVISIONER)
            if fetcher == heroku_sso_account_fetcher:
                # fetch heroku css and html nav bar
                hrequest = urllib2.Request('http://nav.heroku.com/v1/providers/header')
                hrequest.add_header('Accept','application/json')
                data = urllib2.urlopen(hrequest).read()
                if data:
                    request.session['provisioner_navbar_html'] = data
                cookies['heroku-nav-data'] = request.GET.get('nav-data', '')
            if account.provisioner and account.provisioner.name == 'appharbor':
                # fetch heroku css and html nav bar
                hrequest = urllib2.Request('http://appharbor.com/header')
                #jsonrequest.add_header('Accept','application/json')
                data = urllib2.urlopen(hrequest).read()
                if data:
                    request.session['provisioner_navbar_html'] = data
                cookies['appharbor-nav-data'] = request.GET.get('nav-data', '')

            #request.session['heroku'] = True
            response = HttpResponseRedirect('/dashboard')
            for k,v in cookies.items():
                max_age = 365*24*60*60  #one year
                expires = datetime.datetime.strftime(datetime.datetime.utcnow() + datetime.timedelta(seconds=max_age), "%a, %d-%b-%Y %H:%M:%S GMT")
                response.set_cookie(k, v, max_age=max_age, expires=expires, domain=settings.SESSION_COOKIE_DOMAIN, secure=settings.SESSION_COOKIE_SECURE or None)
            return response
    
    return HttpResponseForbidden()


def do_sign_up(request, form_data, package=None, invitation=None):
    dt = datetime.datetime.now()
    email = form_data.get('email')
    password = form_data.get('password')
    account, pfu = Account.create_account(dt, email, password)
    if invitation:
        invitation.account = account
        invitation.save()
        account.apply_package(invitation.forced_package)
    else:
        account.apply_package(package)
    
    account.save()
    
    user = auth.authenticate(username=pfu.user.username, password=password)
    auth.login(request, user)

    return account

@force_https
def upgrade(request):
    pass

@force_https
def get_started(request):
    if request.user.is_authenticated():
        package = request.user.get_profile().account.package
        plan = package.code
    else:
        plan = request.GET.get('plan', 'FREE')
        package = Package.objects.get(code=plan)
    if request.is_ajax() and request.method == 'POST':
        email = request.POST['email']
        try:
            is_valid_email(email)
        except:
            return HttpResponse('Invalid email address', status=400)
            
        try:
            account = create_account(request, email, package)
        except IntegrityError:
            return HttpResponse('Email address already used', status=400)
        
        return JsonResponse({'private_api_url':account.get_private_apiurl(), 'public_api_url':account.get_public_apiurl(), 'email': email})
    
    context = {
        'navigation_pos': 'get_started',
        'package': package,
        'plan': plan
    }
    return render('get_started.html', request, context_dict=context)
    
def why(request):
    context = {
        'navigation_pos': 'why_us',
    }
    return render('why_us.html', request, context_dict=context)
    
    
def create_account(request, email, package):
    dt = datetime.datetime.now()
    account, pfu = Account.create_account(dt, email)
    account.apply_package(package)
    
    # Demo index creation
    account.create_demo_index()
    
    if account.package.base_price == 0:
        account.status = Account.Statuses.operational
            
    mail.report_new_account(account)
    account.save()
    password=account.apikey.split('-', 1)[1]
    
    user = auth.authenticate(username=pfu.user.username, password=password)
    auth.login(request, user)

    send_mail('Welcome to IndexTank!', 'Thanks signing-up for IndexTank!\nYour password for logging in to your dashboard is %s' % (password), 'IndexTank <support@indextank.com>', [email], fail_silently=False)
    return account

@force_https
def old_get_started(request):
    if request.user.is_authenticated():
        account = request.user.get_profile().account 
        if account.package.base_price == 0 or account.payment_informations.count():
            logout(request)
        
    plan = request.GET.get('plan')
    if plan is None:
        return _get_started_step1(request)
    else:
        return _get_started_step2(request, plan)

def _get_started_step3(request):
    messages.success(request, "Great! You have successfully created an IndexTank account.")
    return HttpResponseRedirect(reverse('dashboard'))


@login_required
def enter_payment(request):
    message = None
    account = request.user.get_profile().account
    package = account.package
    plan = account.package.code
    data = request.POST if request.method == 'POST' else None

    if package.base_price == 0:
        return HttpResponseRedirect(reverse('dashboard'))
    
    if account.payment_informations.count() > 0:
        messages.info(request, "You have already entered your payment information. If you wish to change it please contact us.")
        return HttpResponseRedirect(reverse('dashboard'))
        
    payment_form = forms.PaymentInformationForm(data=data)

    if data:
        if payment_form.is_valid():
            form_data = payment_form.cleaned_data
            try:
                process_payment_information(account, form_data)
                account.status = Account.Statuses.operational
                account.save()
                
                #mail.report_payment_data(account)
                
                return _get_started_step3(request)
            except BillingException, e:
                message = e.msg
            if message is None:
                messages.success(request, "You have successfully entered your payment information.")
                return HttpResponseRedirect(reverse('dashboard'))
    context = {
        'navigation_pos': 'get_started',
        'payment_form': payment_form,
        'message': message, 
        'step': '2',
        'package': package, 
    }
    return render('enter_payment.html', request, context_dict=context)


def _get_started_step2(request, plan):
    message = None
    data = request.POST if request.method == 'POST' else None
    account = None
    package = Package.objects.get(code=plan)
    if request.user.is_authenticated():
        sign_up_form = None
        account = request.user.get_profile().account
        account.apply_package(package)
        account.save()
        if package.base_price > 0:
            payment_form = forms.PaymentInformationForm(data=data)
        else:
            return _get_started_step3(request)
    else:
        sign_up_form = forms.SignUpForm(data=data)
        if package.base_price > 0:
            payment_form = forms.PaymentInformationForm(data=data)
        else:
            payment_form = None

    if data:
        sign_up_ok = sign_up_form is None or sign_up_form.is_valid()
        payment_ok = payment_form is None or payment_form.is_valid()
        if sign_up_ok and payment_ok:
            if sign_up_form is not None:
                form_data = sign_up_form.cleaned_data
                try:
                    account = do_sign_up(request, form_data, package)
                    sign_up_form = None
                except IntegrityError, e:
                    message = 'Email already exists.'
            if message is None and payment_form is not None:
                form_data = payment_form.cleaned_data
                try:
                    process_payment_information(account, form_data)
                    account.status = Account.Statuses.operational
                    account.save()
                    
                    mail.report_new_account(account)
                    
                    return _get_started_step3(request)
                except BillingException, e:
                    message = e.msg
            if message is None:
                return _get_started_step3(request)

    context = {
        'navigation_pos': 'get_started',
        'sign_up_form': sign_up_form,
        'payment_form': payment_form,
        'message': message, 
        'step': '2',
        'package': package,
        'next': request.GET.get('next') or '/',
    }
    return render('get_started.html',request, context_dict=context)

def _get_started_step1(request):
    context = {
        'navigation_pos': 'get_started',
        'step': '1',
        'step_one': True,
        'next': request.GET.get('next') or '/',
    }
    return render('get_started.html', request, context_dict=context)

def beta_request(request):
    form = None
    message = None
    if request.method == 'GET':
        form = forms.BetaTestForm()
    else:
        form = forms.BetaTestForm(data=request.POST)
        if form.is_valid():
            form_data = form.cleaned_data
            try:
                email = form_data.get('email')
                summary = form_data.get('summary')
                site_url = form_data.get('site_url')
                
                beta_request = BetaTestRequest(site_url=site_url, email=email, summary=summary)
                beta_request.save()

                send_mail('IndexTank beta testing account', 'Thanks for requesting a beta testing account for IndexTank! We\'ll get back to you shortly', 'IndexTank <betatesting@indextank.com>', [email], fail_silently=False)
                
                #do_sign_up(request, form_data)
                return HttpResponseRedirect(reverse('thanks_notice'))
            except IntegrityError, e:
                message = 'Email already used.'

    context = {
        'request_form': form,
        'message': message, 
        'navigation_pos': 'beta_request',
        'next': request.GET.get('next') or '/',
    }

    return render('beta_request.html', request, context_dict=context)

def thanks_notice(request):
    return render('thanks_notice.html', request)

def invite_sign_up(request, password=None):
    try:
        invitation = BetaInvitation.objects.get(password=password)
        if invitation.account:
            return render('used_invite.html', request)
    except BetaInvitation.DoesNotExist:
        return HttpResponseNotFound()
    
    form = None
    message = None
    if request.method == 'GET':
        if invitation.beta_requester:
            form = forms.SignUpForm(initial={'email':invitation.beta_requester.email})
        else:
            form = forms.SignUpForm()
    else:
        form = forms.SignUpForm(data=request.POST)
        if form.is_valid():
            form_data = form.cleaned_data
            try:
                do_sign_up(request, form_data, invitation)
                return HttpResponseRedirect(request.GET.get('next') or '/')
            except IntegrityError, e:
                message = 'Email already exists.'

    context = {
        'invitation': invitation,
        'sign_up_form': form,
        'message': message, 
        'navigation_pos': 'get_started',
        'next': request.GET.get('next') or '/',
    }

    return render('sign_up.html', request, context_dict=context)
    
@force_https
def sign_up(request, package=None):
    account_package = None

    if package:
        account_package = Package.objects.get(code=package)

    if request.user.is_authenticated():
        account = request.user.get_profile().account 
        if account.payment_informations.count():
            raise Http404
        else:
            account.apply_package(account_package)
            return HttpResponseRedirect(reverse('dashboard'))        
            	    	   		    

    form = None
    message = None
    if request.method == 'GET':
        form = forms.SignUpForm()
    else:
        form = forms.SignUpForm(data=request.POST)
        if form.is_valid():
            form_data = form.cleaned_data
            try:
                do_sign_up(request, form_data, package=account_package)
                return HttpResponseRedirect(request.GET.get('next') or '/')
            except IntegrityError, e:
                message = 'Email already exists.'

    context = {
        'sign_up_form': form,
        'message': message, 
        'navigation_pos': 'get_started',
        'next': request.GET.get('next') or '/',
        'package': package,
    }

    return render('sign_up.html', request, context_dict=context) 

@login_required
@force_https
def close_account(request):
    user = request.user
    message = None
    if request.method == 'GET':
        form = forms.CloseAccountForm()
    else:
        form = forms.CloseAccountForm(data=request.POST)
        
        if form.is_valid():
            form_data = form.cleaned_data
            
            password = form_data.get('password')
            
            if user.check_password(password):
                user.get_profile().account.close()
                return HttpResponseRedirect(reverse('logout'))
            else:
                message = 'Wrong password' 

    context = {
        'form': form,
        'message': message, 
        'navigation_pos': 'dashboard',
    }
    
    return render('close_account.html', request, context_dict=context)
    

@login_required
@force_https
def change_password(request):
    user = request.user
    message = None
    if request.method == 'GET':
        form = forms.ChangePassForm()
    else:
        form = forms.ChangePassForm(data=request.POST)
        
        if form.is_valid():
            form_data = form.cleaned_data
            
            old_pass = form_data.get('old_password')
            new_pass = form_data.get('new_password')
            new_pass_again = form_data.get('new_password_again')
            
            if user.check_password(old_pass):
                user.set_password(new_pass)
                user.save()
                user.get_profile().change_password = False
                user.get_profile().save()
                messages.success(request, 'Your password was changed successfully.')
                return HttpResponseRedirect(reverse('dashboard'))
            else:
                message = 'Current password is wrong' 

    context = {
        'form': form,
        'message': message, 
        'navigation_pos': 'dashboard',
    }
    
    return render('change_password.html', request, context_dict=context)


@login_required
def dashboard(request):
    # Possible statuses:
    #    - No index
    #    - Index but no docs
    #    - Index with docs

    account_status = None
    
    if request.user.get_profile().change_password:
        messages.info(request, 'Your password was reset and you need to change it.')
        return HttpResponseRedirect(reverse('change_password'))
    
    account = request.user.get_profile().account
    
    #if not account.package:
    #    return HttpResponseRedirect(reverse('select_package'))
    if not account.status == Account.Statuses.operational and not account.payment_informations.count():
        if account.package.base_price > 0:
            messages.info(request, 'Before accessing your dashboard you need to enter your payment information')
            return HttpResponseRedirect(reverse('enter_payment'))
        elif account.status == Account.Statuses.creating:
            account.status = Account.Statuses.operational
            
            mail.report_new_account(account)
            account.save()
        else:
            return HttpResponseRedirect(reverse('logout'))
    
    indexes = account.indexes.filter(deleted=False)
    
    has_indexes_left = (len(indexes) < account.package.max_indexes)
  
    totals = dict(size=0, docs=0, qpd=0)  
    for index in indexes:
        totals['docs'] += index.current_docs_number
        totals['size'] += index.current_size
        totals['qpd'] += index.queries_per_day
  
    if len(indexes) == 0:
        account_status = 'NOINDEX'
    elif totals['docs'] == 0:
        account_status = 'INDEXNODOCS'
    else:
        account_status = 'INDEXWITHDOCS'
    
    percentages = {}
    def add_percentage(k, max, t, p):
        p[k] = 100.0 * t[k] / max
    
    KB = 1024
    MB = KB * KB
    max_docs = account.package.index_max_size
    max_size = account.package.max_size_mb()
    max_qpd = account.package.searches_per_day
    
    add_percentage('docs', max_docs, totals, percentages)
    add_percentage('size', max_size, totals, percentages)
    add_percentage('qpd', max_qpd, totals, percentages)
    
    for index in indexes:
        insights = {}
        insights_update = {}
        #for i in index.insights.all():
        #    try:
        #        insights[i.code] = json.loads(i.data)
        #        insights_update[i.code] = i.last_update
        #    except:
        #        print 'Failed to load insight %s for %s' % (i.code, index.code)
        #index.insights_map = insights
        #index.insights_update = insights_update
  
    context = {
        'account': account,
        'indexes': indexes,
        'has_indexes_left': has_indexes_left,
        'account_status': account_status,
        'totals': totals,
        'percentages': percentages,
        'navigation_pos': 'dashboard',
    }

    return render('dashboard.html', request, context_dict=context)

@login_required
def heroku_dashboard(request):
    # Possible statuses:
    #    - No index
    #    - Index but no docs
    #    - Index with docs

    account_status = None
    
    if request.user.get_profile().change_password:
        messages.info(request, 'Your password was reset and you need to change it.')
        return HttpResponseRedirect(reverse('change_password'))
    
    account = request.user.get_profile().account
    
    indexes = account.indexes.all()
    
    has_indexes_left = (len(indexes) < account.package.max_indexes)
  
    totals = dict(size=0, docs=0, qpd=0)  
    for index in indexes:
        totals['docs'] += index.current_docs_number
        totals['size'] += index.current_size
        totals['qpd'] += index.queries_per_day
  
    if len(indexes) == 0:
        account_status = 'NOINDEX'
    elif totals['docs'] == 0:
        account_status = 'INDEXNODOCS'
    else:
        account_status = 'INDEXWITHDOCS'
    
    percentages = {}
    def add_percentage(k, max, t, p):
        p[k] = 100.0 * t[k] / max
    
    KB = 1024
    MB = KB * KB
    max_docs = account.package.index_max_size
    max_size = account.package.max_size_mb()
    max_qpd = account.package.searches_per_day
    
    add_percentage('docs', max_docs, totals, percentages)
    add_percentage('size', max_size, totals, percentages)
    add_percentage('qpd', max_qpd, totals, percentages)
  
    context = {
        'account': account,
        'indexes': indexes,
        'has_indexes_left': has_indexes_left,
        'account_status': account_status,
        'totals': totals,
        'percentages': percentages,
        'navigation_pos': 'dashboard',
    }

    return render('heroku-dashboard.html', request, context_dict=context)


@login_required
@force_https
def enter_payment_information(request):
    account = request.user.get_profile().account
    
    if request.method == 'GET':
        form = forms.PaymentInformationForm()
    else:
        form = forms.PaymentInformationForm(data=request.POST)
        if form.is_valid():
            form_data = form.cleaned_data
            
            try:
                if account.package.base_price > 0:
                    process_payment_information(account, form_data)
                
                account.status = Account.Statuses.operational
                mail.report_new_account(account)
                account.save()
                
                return HttpResponseRedirect(reverse('dashboard'))
            except BillingException, e:
                messages.error(request, e.msg)
            

    context = {
        'form': form,
        'navigation_pos': 'get_started',
        'next': request.GET.get('next') or '/',
        'account': account,
    }
    
    return render('payment_info.html', request, context_dict=context)
    
def process_payment_information(account, form_data):
    
    payment_infos = account.payment_informations.all()

    # Right now there can only be ONE payment info per account
    if payment_infos:
        pass
    else:
        payment_info = AccountPayingInformation()

        payment_info.account = account
        
        payment_info.first_name = form_data['first_name']
        payment_info.last_name = form_data['last_name']
        payment_info.address = form_data['address']
        payment_info.city = form_data['city']
        payment_info.state = form_data['state']
        payment_info.zip_code = form_data['zip_code']
        payment_info.country = form_data['country']

        payment_info.contact_email = account.user.email
        payment_info.monthly_amount = str(account.package.base_price)
        payment_info.subscription_status = 'Active'
        payment_info.subscription_type = 'Authorize.net'

        cc_number = form_data['credit_card_number']
        exp_month, exp_year = form_data['exp_month'].split('/', 1)
        payment_info.credit_card_last_digits = cc_number[-4:]

        auth = AuthorizeNet()
        
        # add one day to avoid day change issues
        today = (datetime.datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d') 
        payment_info.save()
        
        ref_id = str(payment_info.id)
        freq_length = 1
        freq_unit = 'months'
        
        try:
            subscription_id = auth.subscription_create(ref_id, 'IndexTank - ' + account.package.name, str(freq_length), freq_unit, today, '9999', '1', 
                                "%.2f" % account.package.base_price, '0', cc_number, '20' + exp_year + '-' + exp_month, payment_info.first_name, payment_info.last_name,
                                "", payment_info.address, payment_info.city, payment_info.state, payment_info.zip_code, payment_info.country)
        except BillingException, e:
            payment_info.delete()
            raise e
        except Exception, e:
            payment_info.delete()
            raise BillingException('An error occurred when verifying the credit card. Please try again later')
        
        payment_subscription = PaymentSubscription()
        
        payment_subscription.account = payment_info
        payment_subscription.subscription_id = subscription_id
        payment_subscription.reference_id = ref_id
        payment_subscription.amount = str(account.package.base_price)

        payment_subscription.start_date = today
        payment_subscription.frequency_length = freq_length
        payment_subscription.frequency_unit = freq_unit
        
        payment_subscription.save()
        
        #### CREATE IN AUTHORIZE NET
        
        
    
@login_required
def insights(request, index_code=None):
    index = Index.objects.get(code=index_code)
    insights = {}
    insights_update = {}
    for i in index.insights.all():
        try:
            insights[i.code] = json.loads(i.data)
            insights_update[i.code] = i.last_update
        except:
            print 'Failed to load insight %s for %s' % (i.code, index.code)
    
    context = {
         'account': request.user.get_profile().account,
         'navigation_pos': 'dashboard',
         'index': index,
         'insights': insights,
         'insights_update': insights_update,
         'index_code': index_code,
    }
    
    return render('insights.html', request, context_dict=context)


@login_required
def manage_index(request, index_code=None):
    account = request.user.get_profile().account
    
    index = Index.objects.get(code=index_code)
    
    if index:
        if index.account == account:
            if request.method == 'GET':
                index = Index.objects.get(code=index_code)
            
                largest_func = max([int(f.name) + 1 for f in index.scorefunctions.all()] + [5])
                functions = get_functions(index, upto=largest_func)
             
                context = {
                  'account': request.user.get_profile().account,
                  'navigation_pos': 'dashboard',
                  'functions': functions,
                  'index': index,
                  'index_code': index_code,
                  'largest_func': largest_func
                }

                if 'query' in request.GET:
                    maxim = int(request.GET.get('max', '25'))
                    index_client = ApiClient(account.get_private_apiurl()).get_index(index.name)
                    context['results'] = index_client.search(request.GET['query'], length=max)
                    context['query'] = request.GET['query']
                    context['more'] = maxim + 25

                
                return render('manage_index.html', request, context_dict=context)
            else:
                if 'definition' in request.POST:
                    name = request.POST['name']
                    definition = request.POST['definition']       
                
                    client = ApiClient(account.get_private_apiurl()).get_index(index.name)
                    try:
                        if definition:
                            client.add_function(int(name), definition)
                        else:
                            client.delete_function(int(name))
                    except InvalidDefinition, e: 
                        return HttpResponse('Invalid function', status=400)
                          
                    return JsonResponse({'largest': 5})
                elif 'public_api' in request.POST:
                    index.public_api = request.POST['public_api'] == 'true'
                    index.save()
                    return JsonResponse({'public_api': index.public_api})
        else:
            raise HttpResponseForbidden
        
    else:
        raise Http404

functions_number = 6
@login_required
def manage_inspect(request, index_code=None):
    account = request.user.get_profile().account
    
    index = Index.objects.get(code=index_code)
    
    if index:
        if index.account == account:
            context = {
              'account': request.user.get_profile().account,
              'navigation_pos': 'dashboard',
              'index_code': index_code,
              'index': index
            }
                
            return render('manage_inspect.html', request, context_dict=context)
        else:
            raise HttpResponseForbidden
    else:
        raise Http404



@login_required
def score_functions(request):
    #TODO: make it part of index/package configuration
    account = request.user.get_profile().account
    if request.method == 'GET':
        index_code = request.GET['index_code']
        index = Index.objects.get(code=index_code)
    
        functions = get_functions(index)
    
        form = ScoreFunctionForm()
     
        context = {
          'form': form,
          'account': request.user.get_profile().account,
          'navigation_pos': 'dashboard',
          'functions': functions,
          'index_code': index_code,
          'functions_available': len(functions) < functions_number,
        }
        
        return render('score_functions.html', request, context_dict=context)
    else:
        form = ScoreFunctionForm(data=request.POST)
    
        if form.is_valid():
            index_code = request.POST['index_code']
            index = Index.objects.get(code=index_code)
            name = form.cleaned_data['name']
            definition = form.cleaned_data['definition']       
    
            client = ApiClient(account.get_private_apiurl()).get_index(index.name)
            try:
                client.add_function(int(name), definition)
            except InvalidDefinition, e: 
                index = Index.objects.get(code=index_code)
                functions = get_functions(index)
                form = ScoreFunctionForm(initial={'name': name, 'definition': definition})
                messages.error(request, 'Problem processing your formula: %s', str(e))
              
                context = {
                    'form': form,
                    'account': request.user.get_profile().account,
                    'navigation_pos': 'dashboard',
                    'functions': functions,
                    'index_code': index_code,
                    'functions_available': len(functions) < functions_number,
                }
    
                return render('score_functions.html', request, context_dict=context)
      
    return HttpResponseRedirect(reverse('score_functions') + '?index_code=' + index_code)

@login_required
def remove_function(request):
    account = request.user.get_profile().account
    if request.method == 'GET':
        index_code = request.GET['index_code']
        index = Index.objects.get(code=index_code)
        function_name = request.GET['function_name']
        client = ApiClient(account.get_private_apiurl()).get_index(index.name)
        client.delete_function(function_name)
    
    return HttpResponseRedirect(reverse('score_functions') + '?index_code=' + index_code)

def get_functions(index, upto=5):
    functions = index.scorefunctions.order_by('name')
    functions_dict = {}
    final_functions = []
    
    for function in functions:
        functions_dict[function.name] = function
    
    max_key = 0
    if functions_dict.keys():
        max_key = max(functions_dict.keys())
    
    for i in xrange(upto+1):
        pos = i
        if pos in functions_dict:
            final_functions.append(functions_dict[pos])
        else:
            new_function = ScoreFunction(name=str(pos), definition=None)
            final_functions.append(new_function)
    
    return final_functions


def select_package(request):
  account = request.user.get_profile().account
  if request.method == 'GET':
    packages_list = Package.objects.all()
    packages = {}
    package_availability = {}
    for package in packages_list:
      packages[package.code] = package
      package_availability[package.code] = package.max_indexes >= Index.objects.filter(account=account).count()
    
    context = {
      'account': account,
      'packages': packages,
      'package_availability': package_availability,
      'navigation_pos': 'dashboard',
    }
    return render('packages.html', request, context_dict=context)
  else:
    package = Package.objects.get(id=request.POST['package_id'])
    account.apply_package(package)
    account.save()
    return HttpResponseRedirect(reverse('dashboard'))



@login_required
def demo_index(request):
    '''
        Renders the demo frontend for INSTRUMENTS index.
        if we want to do it for every index, sometime in the future,
        just add an 'index=' parameter to this view.
    '''
    account = request.user.get_profile().account
    for index in account.indexes.all():

        if index.is_demo():
            context = {
                'index': index
            }
            return render('instruments.html', request, context_dict=context)
        # else continue

    # no index -> 404
    return render("404.html", request)
        



# Search API hack 
BASE_URL = 'http://api.indextank.com/api/v0'
def call_api_delete(index):
    url = BASE_URL + '/inform_del_index?apikey=' + urllib.quote(index.account.apikey) + '&indexcode=' + urllib.quote(index.code)    
    data = urllib.urlopen(url).read()

def call_api_create(index):
    url = BASE_URL + '/inform_add_index?apikey=' + urllib.quote(index.account.apikey) + '&indexcode=' + urllib.quote(index.code)    
    data = urllib.urlopen(url).read()

# End hack

def delete_index(request):
  if request.method == 'GET':
    return HttpResponseRedirect(reverse('dashboard'))
  else:
    index = Index.objects.get(id=request.POST['index_id'])
    
    index_client = ApiClient(index.account.get_private_apiurl()).get_index(index.name)
    index_client.delete_index()

    return HttpResponseRedirect(reverse('dashboard'))

def get_max_function(index):
    max_function = ScoreFunction.objects.filter(index=index).aggregate(Max('name'))['name__max']
    if max_function == None:
        max_function = 0
    return max_function

STARTING_BASE_PORT = 20000

def create_index(request):
    account = request.user.get_profile().account
    if request.method == 'GET':
        index_qty = len(account.indexes.all())
        default_name = '' #'Index_' + str(index_qty + 1)
        
        form = IndexForm(initial={'name': default_name}) 
        context = {
          'form': form,
          'account': request.user.get_profile().account,
          'navigation_pos': 'dashboard',
        }
        return render('new-index.html', request, context_dict=context)
    else:
        form = IndexForm(data=request.POST)
        if form.is_valid():
            try:
                client = ApiClient(account.get_private_apiurl())
                client.create_index(form.cleaned_data['name'])
                messages.success(request, 'New index created successfully.')
            except IndexAlreadyExists:
                context = {
                  'form': form,
                  'account': request.user.get_profile().account,
                  'navigation_pos': 'dashboard',
                }
                messages.error(request, 'You already have an Index with that name.')
                return render('new-index.html', request, context_dict=context)
            except TooManyIndexes:
                context = {
                  'form': form,
                  'account': request.user.get_profile().account,
                  'navigation_pos': 'dashboard',
                }
                messages.error(request, 'You already have the maximum number of indexes allowed for your account. If you need more, please contact support.')
                return render('new-index.html', request, context_dict=context)
            except Exception, e:
                print e
                messages.error(request, 'Unexpected error creating the index. Try again in a few minutes')
            return HttpResponseRedirect(reverse('dashboard'))     
        else:
            context = {
              'form': form,
              'account': request.user.get_profile().account,
              'navigation_pos': 'dashboard',
            }
            return render('new-index.html', request, context_dict=context)

def logout(request):
    is_heroku_logout = request.user.get_profile().account.provisioner and request.user.get_profile().account.provisioner.name == 'heroku' 

    auth.logout(request)
    # In case this was a 
    request.session['heroku'] = False
  
    if is_heroku_logout:
        return HttpResponseRedirect('http://api.heroku.com/logout')
  
    return HttpResponseRedirect('/') # request.GET['next']);


## MOCK ##
def api_register_index(request):
    apikey = request.GET['api_key']
    index_name = request.GET['index_name']
    
    try:
        account = Account.objects.get(apikey=apikey)
    except Account.DoesNotExist: #@UndefinedVariable
        return HttpResponse('{"status":"ERROR", "message":"Invalid account"}')
    
    if len(account.indexes.all()) >= account.package.max_indexes:
        return HttpResponse('{"status":"ERROR", "message":"Account limit reached"}')
    else:
        index = Index()
        index.populate_for_account(account);
        index.name = index_name
        index.creation_time = datetime.datetime.now()
        index.language_code = 'en'
        try:
                index.save()
        except IntegrityError, ie:
                print('integrityError in api_register_index.', ie)
                return HttpResponse('{"status":"ERROR", "message":"You already have and Index with that name or code."}')
        
        index.base_port = STARTING_BASE_PORT + 10 * index.id
        index.code = get_index_code(index.id)
        index.save()
        start_index(index)
        response = '{"status":"OK", "index_code":"%s"}' % (index.code)
        return HttpResponse(response)
     
def api_delete_index(request):
    apikey = request.GET['apikey']
    index_name = request.GET['indexcode']
    
    index = None
    
    try:
        account = Account.objects.get(apikey=apikey)
    except Account.DoesNotExist: #@UndefinedVariable
        return HttpResponse("1")
      
    try:
        index = Index.objects.get(code=index_name, account=account)
    except Index.DoesNotExist: #@UndefinedVariable
        return HttpResponse("2")
      
    stop_index(index)
    index.delete()
    
    return HttpResponse("0")

def api_list(request):
    apikey = request.GET['apikey']
    
    try:
        account = Account.objects.get(apikey=apikey)
    except Account.DoesNotExist: #@UndefinedVariable
        return HttpResponse(",")
    
    list = [x.code for x in account.indexes.all()]
    
    return HttpResponse(','.join(list))

def start_index(index):
    dm = getThriftDeployManagerClient()
    dm.start_index(index.code, 1000) #  TODO get ram from package.

def stop_index(index):
    dm = getThriftDeployManagerClient()
    dm.delete_index(index.code)

'''
THRIFT STUFF
'''
deploymanager_port = 8899
def getThriftDeployManagerClient():
    protocol, transport = __getThriftProtocolTransport('deploymanager',deploymanager_port)
    client = TDeployManager.Client(protocol)
    transport.open()
    return client

def __getThriftProtocolTransport(host, port=0):
    ''' returns protocol,transport'''
    # Make socket
    transport = TSocket.TSocket(host, port)

    # Buffering is critical. Raw sockets are very slow
    transport = TTransport.TBufferedTransport(transport)

    # Wrap in a protocol
    protocol = TBinaryProtocol.TBinaryProtocol(transport)
    return protocol, transport

def is_luhn_valid(cc):
    num = map(int, cc)
    return not sum(num[::-2] + map(lambda d: sum(divmod(d * 2, 10)), num[-2::-2])) % 10

