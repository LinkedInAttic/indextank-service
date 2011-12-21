from django.conf import settings
from django.contrib import auth
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, Http404, HttpResponseNotFound, \
    HttpResponse, HttpResponseForbidden
from django.shortcuts import render_to_response
from models import PFUser, Worker, WorkerMountInfo, WorkerIndexInfo, \
    WorkerLoadInfo, Index, BetaTestRequest, BetaInvitation, generate_onetimepass, \
    Package, Account, Deploy, IndexConfiguration
from util import Context, login_required, staff_required
import datetime
import forms
import hashlib
import os
import re
import subprocess
import time
import urllib
import urllib2
import rpc
import json

class JsonResponse(HttpResponse):
    def __init__(self, json_object, *args, **kwargs):
        body = json.dumps(json_object)
        if 'callback' in kwargs:
            callback = kwargs.pop('callback')
            if callback:
                body = '%s(%s)' % (callback, body)
        super(JsonResponse, self).__init__(body, *args, **kwargs)

def login(request):
    login_form = forms.LoginForm()
    login_message = ''
    if request.method == 'POST':
        login_form = forms.LoginForm(data=request.POST)
        if login_form.is_valid():
            try:
                username = PFUser.objects.get(email=login_form.cleaned_data['email']).user.username
                user = auth.authenticate(username=username, password=login_form.cleaned_data['password'])
                if user is not None:
                    if user.is_active:
                        auth.login(request, user)
                        return HttpResponseRedirect(request.GET.get('next') or '/');
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
        'next': request.GET.get('next') or '/',
    }
    
    return render_to_response('login.html', Context(context, request))

def logout(request):
    auth.logout(request)
    return HttpResponseRedirect('/') # request.GET['next']);

@staff_required
@login_required
def home(request):
    return HttpResponseRedirect(reverse("operations"))

@login_required
def biz_stats(request):
    context = {}
    return render_to_response('biz_stats.html', Context(context, request))
    
@login_required
def biz_stats_json(request):
    json_string = ''
    with open('/data/logs/stats.json') as f:
        json_string = f.read()
    return HttpResponse(json_string)

@login_required
def biz_stats_json_daily(request):
    json_string_daily = ''
    with open('/data/logs/stats.json.daily') as f:
        json_string_daily = f.read()
    return HttpResponse(json_string_daily)

@staff_required
@login_required
def control_panel(request):
    workers = Worker.objects.all()

    context = {
        'workers': workers,
        'navigation_pos': 'home',
    }

    return render_to_response('control_panel.html', Context(context, request))

@staff_required
@login_required
def manage_worker(request, worker_id=None):
    context = {}
    
    worker = Worker.objects.get(id=worker_id)
    
    mount_infos = WorkerMountInfo.objects.extra(where=['worker_id=%d and timestamp=(select max(timestamp) from %s where worker_id=%d)' % (int(worker_id), WorkerMountInfo._meta.db_table, int(worker_id))], order_by=['-used'])
    indexes_infos = WorkerIndexInfo.objects.extra(where=['worker_id=%d and timestamp=(select max(timestamp) from %s where worker_id=%d)' % (int(worker_id), WorkerIndexInfo._meta.db_table, int(worker_id))], order_by=['-used_mem'])
    load_info = WorkerLoadInfo.objects.extra(where=['worker_id=%d and timestamp=(select max(timestamp) from %s where worker_id=%d)' % (int(worker_id), WorkerLoadInfo._meta.db_table, int(worker_id))])[0]
    
    used_disk_total = 0
    used_mem_total = 0
    
    mount_percentages = {}
    
    for info in mount_infos:
        mount_percentages[info.mount] = (float)(info.used) / (info.used + info.available) * 100
    
    for info in indexes_infos:
        used_disk_total += info.used_disk
        used_mem_total += info.used_mem
        
    context = {
        'mount_infos': mount_infos,
        'mount_percentages': mount_percentages,
        'indexes_infos': indexes_infos,
        'load_info': load_info,
        'used_disk_total': used_disk_total,
        'used_mem_total': used_mem_total,
        'worker': worker,
        'navigation_pos': 'home',
    }        
    
    return render_to_response('manage_worker.html', Context(context, request))

@staff_required
@login_required
def mount_history(request, worker_id=None, mount=None):
    worker = Worker.objects.get(id=worker_id)
    
    if not mount.startswith('/'):
        mount = '/' + mount
    
    mount_infos = WorkerMountInfo.objects.extra(where=['worker_id=%d and mount="%s"' % (int(worker_id), mount)], order_by=['timestamp'])
    mount_percentages = {}
    
    for info in mount_infos:
        mount_percentages[info.timestamp] = (float)(info.used) / (info.used + info.available) * 100

    
    context = {
        'worker': worker,
        'mount': mount,
        'mount_percentages': mount_percentages,
        'mount_infos': mount_infos,
    }
    
    return render_to_response('mount_history.html', Context(context, request))

@staff_required
@login_required
def index_history(request, worker_id=None, index_id=None):
    index = Index.objects.get(id=index_id)
    worker = Worker.objects.get(id=worker_id)
    
    index_infos = WorkerIndexInfo.objects.filter(worker__id=worker_id, deploy__index__id=index_id)

    context = {
        'index': index,
        'worker': worker,
        'index_infos': index_infos,
    }
    
    return render_to_response('index_history.html', Context(context, request))

    
@staff_required
@login_required
def beta_requests_list(request):
    requests = BetaTestRequest.objects.all().order_by('-request_date')
    
    context = {
        'requests': requests,
    }
    
    return render_to_response('beta_requests.html', Context(context, request))

@staff_required
@login_required
def beta_invitation_export(request):
    requests = BetaTestRequest.objects.all().order_by('-request_date')
    invitations = BetaInvitation.objects.filter(beta_requester__isnull=True).order_by('-invitation_date')
    
    context = {
        'requests': requests,
        'invitations': invitations,
    }
    
    return render_to_response('beta_invitation_export.html', Context(context, request))

FORCED_PACKAGE_CODE = 'BETA'

@staff_required
@login_required
def beta_request_invite(request, request_id=None):
    beta_request = BetaTestRequest.objects.get(id=request_id)
    new_invitation = BetaInvitation()
    new_invitation.beta_requester = beta_request
    new_invitation.forced_package = Package.objects.get(code=FORCED_PACKAGE_CODE)

    new_invitation.save()
    new_invitation.password = generate_onetimepass(new_invitation.id)
    new_invitation.save()

    return HttpResponseRedirect(reverse('beta_requests'));

@staff_required
@login_required
def beta_invitations(request):
    if request.method == 'POST':
        form = forms.InvitationForm(data=request.POST)
        if form.is_valid():
            new_invitation = BetaInvitation()
            new_invitation.assigned_customer = form.cleaned_data['requesting_customer']
            new_invitation.forced_package = Package.objects.get(code=FORCED_PACKAGE_CODE)
            
            new_invitation.save()
            new_invitation.password = generate_onetimepass(new_invitation.id)
            new_invitation.save()
            return HttpResponseRedirect(reverse('beta_invitations'));
    else:
        form = forms.InvitationForm()
        
    invitations = BetaInvitation.objects.all().order_by('-invitation_date')

    context = {
        'invitations': invitations,
        'form': form,
    }
    
    return render_to_response('beta_invitations.html', Context(context, request))

@staff_required
@login_required
def load_history(request, worker_id=None):
    worker = Worker.objects.get(id=worker_id)
    
    load_infos = WorkerLoadInfo.objects.extra(where=['worker_id=%d' % (int(worker_id))], order_by=['timestamp'])
    
    context = {
        'worker': worker,
        'load_infos': load_infos,
    }
    return render_to_response('load_history.html', Context(context, request))
    

@staff_required
@login_required
def log_info(request):
    class ddict(dict):
      def __init__(self, default):
        self.default = default
      def __getitem__(self, key):
        return self.setdefault(key, self.default())
    ndict = lambda: ddict(lambda: 0)

    ps = subprocess.Popen('tail -1000000 /data/logs/api.log | grep "Search:INFO"', shell=True, stdout=subprocess.PIPE)

    sums = ddict(ndict)
    sucs = ddict(ndict)
    cnts = ddict(ndict)

    for l in ps.stdout:
      m = re.match(r'.*(\d{2}/\d{2}-\d{2}.\d)\d.*\[(\d{3})] in (\d+\.\d{3})s for \[(.*) /v1/indexes/([^\]]*)/([^\]]*)\]', l)
      if m:
        dt = m.group(1)
        code = m.group(2)
        time = float(m.group(3))
        act = m.group(4)
        cod = m.group(5)
        met = m.group(6)
        req = act +' ' + met
        sums[req][dt] += time
        cnts[req][dt] += 1
        if code == '200':
          sucs[req][dt] += 1
    count = 1
    rows_by_req = {}
    for req,v in sums.iteritems():
        rows = []
        rows_by_req[req] = rows
        count += 1
        for dt,time in v.iteritems():
            y = 2010
            m = int(dt[3:5]) - 1
            d = int(dt[0:2])
            h = int(dt[6:8])
            i = int(dt[9:10])*10
            avg = time / cnts[req][dt]
            rows.append('[new Date(%d, %d, %d, %d, %d), %f]' % (y,m,d,h,i,avg))
    context = { 'rows_by_req': rows_by_req }
    return render_to_response('log_info.html', Context(context, request))

@staff_required
@login_required
def accounts_info(request):
    context = { 'accounts': Account.objects.all().order_by('package', 'creation_time') }
    return render_to_response('accounts_info.html', Context(context, request))

def _size(deploy):
    try:
        return deploy.index.current_docs_number
    except Index.DoesNotExist:
        return 0

@staff_required
@login_required
def resource_map(request):
    if request.method == 'POST':
        if request.POST['task'] == 'redeploy':
            id = request.POST['index_id']
            rpc.get_deploy_manager().redeploy_index(Index.objects.get(pk=id).code)
            return HttpResponseRedirect('/resource_map')
    workers = [w for w in Worker.objects.select_related(depth=5).order_by('id').all()]
    for w in workers:
        w.sorted_deploys = sorted(w.deploys.all(), key=_size, reverse=True)
        w.used = w.get_used_ram()
     
    context = { 
        'workers': workers,
        'packages': Package.objects.all() 
    }
    
    return render_to_response('resource_map.html', Context(context, request))

def deploy_dict(d):
    return dict(
        id=d.id,
        index=d.index_id,
        worker=d.worker_id,
        base_port=d.base_port,
        status=d.status,
        timestamp=time.mktime(d.timestamp.timetuple())*1000 if d.timestamp else None,
        parent=d.parent_id,
        effective_xmx=d.effective_xmx,
        effective_bdb=d.effective_bdb
    )
    
def index_dict(i):
    return dict(
        id=i.id,
        account=i.account_id,
        code=i.code,
        name=i.name,
        creation_time=time.mktime(i.creation_time.timetuple())*1000 if i.creation_time else None,
        analyzer_config=i.analyzer_config,
        configuration=i.configuration_id,
        public_api=i.public_api,
        docs=i.current_docs_number,
        status=i.status
    )

def account_dict(a):
    return dict(
        id=a.id,
        package=a.package_id,
        code=a.get_public_apikey(),
        private_url=a.get_private_apiurl(),
        public_url=a.get_public_apiurl(),
        creation_time=time.mktime(a.creation_time.timetuple())*1000 if a.creation_time else None,
        #default_analyzer_config=a.default_analyzer,
        configuration=a.configuration_id,
        status=a.status,
        email=a.user.email if a.user else None,
    )

def configuration_dict(c):
    return dict(
        id=c.id,
        description=c.description,
        creation_date=time.mktime(c.creation_date.timetuple())*1000 if c.creation_date else None,
        data=c.get_data()
    )

def package_dict(p):
    return dict(
        id=p.id,
        name=p.name,
        code=p.code,
        price=p.base_price,
        docs=p.index_max_size,
        indexes=p.max_indexes,
        configuration=p.configuration.id
    )

def worker_dict(w):
    return dict(
        id=w.id,
        wan_dns=w.wan_dns,
        lan_dns=w.lan_dns,
        name=w.instance_name,
        status=w.status,
        ram=w.ram
    )

@staff_required
@login_required
def operations(request):
    #if request.method == 'POST':
    #    if request.POST['task'] == 'redeploy':
    #        id = request.POST['index_id']
    #        rpc.get_deploy_manager().redeploy_index(Index.objects.get(pk=id).code)
    #        return HttpResponseRedirect('/resource_map')
    
    level = request.GET.get('level', 'top')
    if level == 'top':
        return render_to_response('operations/index.html', Context({}, request))
    elif level == 'refresh':
        data = {
            'Config': map(configuration_dict, IndexConfiguration.objects.all()),
            'Account': map(account_dict, Account.objects.select_related('user').all()),
            'Deploy': map(deploy_dict, Deploy.objects.all()),
            'Index': map(index_dict, Index.objects.all()),
            'Package': map(package_dict, Package.objects.all()),
            'Worker': map(worker_dict, Worker.objects.all()),
        }
        return JsonResponse(data)
    elif level == 'index':
        id = request.GET.get('id')
        index = Index.objects.get(pk=id);
        data = {
            'Index': index_dict(index),
            'Deploy': map(deploy_dict, index.deploys.all()),
        }
        return JsonResponse(data)
    elif level == 'stats':
        id = request.GET.get('id')
        d = Deploy.objects.get(pk=id)
        client = rpc.getThriftIndexerClient(d.worker.lan_dns, int(d.base_port), 3000)
        return JsonResponse(client.get_stats())
    elif level == 'log':
        id = request.GET.get('id')
        file = request.GET.get('file')
        d = Deploy.objects.get(pk=id)
        client = rpc.get_worker_controller(d.worker, 4000)
        lines = client.tail(file, 300, d.index.code, d.base_port)
        return JsonResponse(lines)
    elif level == 'redeploy':
        id = request.GET.get('id')
        rpc.get_deploy_manager().redeploy_index(Index.objects.get(pk=id).code)
        return HttpResponse()
    elif level == 'decommission':
        id = request.GET.get('id')
        Worker.objects.filter(id=id).update(status=Worker.States.decommissioning)
        return JsonResponse(worker_dict(Worker.objects.get(id=id))) 
    elif level == 'delete_worker':
        id = request.GET.get('id')
        w = Worker.objects.get(id=id)
        if w.status != Worker.States.decommissioning:
            return HttpResponse('worker not decommissioning', status=409)
        if w.deploys.count():
            return HttpResponse('worker not empty', status=409)
        w.delete()
        return HttpResponse()
    elif level == 'delete_account':
        id = request.GET.get('id')
        a = Account.objects.get(id=id)
        user = a.user.user
        if a.indexes.count():
            return HttpResponse('account has index', status=409)
        if a.payment_informations.count():
            return HttpResponse('account has payment information', status=409)
        user = a.user.user
        a.delete()
        user.delete()
        return HttpResponse()
    elif level == 'account_set_pkg':
        id = request.GET.get('id')
        pid = request.GET.get('pkg')
        p = Package.objects.get(id=pid)
        updated = Account.objects.filter(id=id).update(package=p)
        if updated:
            return JsonResponse(account_dict(Account.objects.get(id=id)))
        else:
            return HttpResponse('account not found', status=409)
    elif level == 'account_set_cfg':
        id = request.GET.get('id')
        cid = request.GET.get('cfg')
        c = IndexConfiguration.objects.get(id=cid)
        updated = Account.objects.filter(id=id).update(configuration=c)
        if updated:
            return JsonResponse(account_dict(Account.objects.get(id=id)))
        else:
            return HttpResponse('account not found', status=409)
    elif level == 'index_set_cfg':
        id = request.GET.get('id')
        cid = request.GET.get('cfg')
        c = IndexConfiguration.objects.get(id=cid)
        updated = Index.objects.filter(id=id).update(configuration=c)
        if updated:
            return JsonResponse(index_dict(Index.objects.get(id=id)))
        else:
            return HttpResponse('index not found', status=409)
    return HttpResponseNotFound()

@staff_required
@login_required
def worker_resource_map(request, worker_id):
    w = Worker.objects.get(id=int(worker_id))
    w.sorted_deploys = sorted(w.deploys.all(), key=_size, reverse=True)
    xmx = 0
    for d in w.sorted_deploys:
      xmx += d.effective_xmx
    w.xmx = xmx
    w.used = w.get_used_ram()


    context = {
        'worker' : w
    }

    return render_to_response('worker_resource_map.html', Context(context,request))

