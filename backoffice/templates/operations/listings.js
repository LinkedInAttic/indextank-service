function load_accounts(target, filter, append) {
	filter = filter || function() { return true; };
	if (!append) target.html(''); 
  var x = $("<div></div>").appendTo(target).html(t('wait', {}));
  var c = $("<div></div>");
	var accs = [];
	$.each(Account.objects.all, function(id, a) {
		if (filter(a)) accs.push([dcount(a),a]);
	});
	if (accs.length) {
  	var h = t('account', {code:'code', email:'Account Email', documents: 'docs', indexes: 'idxs'}).addClass('header').appendTo(c);
    if (!append) h.css('margin-top', '-25px').css('position', 'fixed');
  	accs.sort(function(a,b) { return b[0]-a[0]; });
  	$.eachAsync(accs, function(i,o) { Account.link(o[1]).appendTo(c); }, { end: function() { x.html(c); } });
  } else {
    x.html('');
	}
	return accs.length;
}

function load_indexes(target, filter, append) {
	filter = filter || function() { return true; };
	if (!append) target.html(''); 
  var x = $("<div></div>").appendTo(target).html(t('wait', {}));
  var c = $("<div></div>");
  var idxs = [];
  $.each(Index.objects.all, function(id, i) { if (filter(i)) idxs.push(i); });
  if (idxs.length) {
    var h = t('index', {code:'code', name:'Index Name', documents: '# docs'}).addClass('header').appendTo(c);
    if (!append) h.css('margin-top', '-25px').css('position', 'fixed');
    idxs.sort(function(a,b) { return b.docs-a.docs; });
    $.eachAsync(idxs, function(i,o) { Index.link(o).appendTo(c); }, { end: function() { x.html(c); } });
  } else {
    x.html('');
  }
  return idxs.length;
}

function load_workers(target, filter, append) {
	filter = filter || function() { return true; };
	if (!append) target.html(''); 
  var x = $("<div></div>").appendTo(target).html(t('wait', {}));
  var c = $("<div></div>");
  var wkrs = [];
  $.each(Worker.objects.all, function(id, i) { if (filter(i)) wkrs.push(i); });
  if (wkrs.length) {
    var h = t('worker', {id:'id', depcount:'Worker', used: 'used ', ram: 'total '}).addClass('header').appendTo(c);
    if (!append) h.css('margin-top', '-25px').css('position', 'fixed');
    wkrs.sort(function(a,b) { return b.id-a.id; });
    $.eachAsync(wkrs, function(i,o) { Worker.link(o).appendTo(c); }, { end: function() { x.html(c); } });
  } else {
    x.html('');
  }
  return wkrs.length;
}

function load_packages(target, filter, append) {
	filter = filter || function() { return true; };
	if (!append) target.html(''); 
  var x = $("<div></div>").appendTo(target).html(t('wait', {}));
  var c = $("<div></div>");
  var objs = [];
  $.each(Package.objects.all, function(id, o) { if (filter(o)) objs.push(o); });
  if (objs.length) {
    var h = t('package', {id:'id', name:'Package Name', documents: 'docs', price: 'price'}).addClass('header').appendTo(c);
    if (!append) h.css('margin-top', '-25px').css('position', 'fixed');
    objs.sort(function(a,b) { return b.price-a.price; });
    $.eachAsync(objs, function(i,o) { Package.link(o).appendTo(c); }, { end: function() { x.html(c); } });
  } else {
    x.html('');
  }
  return objs.length;
}

function load_configs(target, filter, append) {
	filter = filter || function() { return true; };
	if (!append) target.html(''); 
  var x = $("<div></div>").appendTo(target).html(t('wait', {}));
  var c = $("<div></div>");
  var objs = [];
  $.each(Config.objects.all, function(id, o) { if (filter(o)) objs.push(o); });
  if (objs.length) {
    var h = t('config', {id:'id', name:'Config Description'}).addClass('header').appendTo(c);
    if (!append) h.css('margin-top', '-25px').css('position', 'fixed');
    objs.sort(function(a,b) { return b.id-a.id; });
    $.eachAsync(objs, function(i,o) { Config.link(o).appendTo(c); }, { end: function() { x.html(c); } });
  } else {
    x.html('');
  }
  return objs.length;
}

function load_deploys(target, filter, append) {
	filter = filter || function() { return true; };
	if (!append) target.html(''); 
  var x = $("<div></div>").appendTo(target).html(t('wait', {}));
  var c = $("<div></div>");
  var objs = [];
  $.each(Deploy.objects.all, function(id, o) { if (filter(o)) objs.push(o); });
  if (objs.length) {
    var h = t('deploy', {id:'id', workerid:'_id', base_port:'port', effective_bdb:'#', effective_xmx: '#'}).addClass('header').appendTo(c);
    if (!append) h.css('margin-top', '-25px').css('position', 'fixed');
    objs.sort(function(a,b) { return (a.status < b.status) ? 1 : ((a.status > b.status) ? -1 : b.id-a.id); });
    $.eachAsync(objs, function(i,o) { Deploy.link(o).appendTo(c); }, { end: function() { x.html(c); } });
  } else {
    x.html('');
  }
  return objs.length;
}

	  function idx_good(id) {
        var n = 0; var controllable = false;
        $.each(_dep.for_index(id), function (k,v) {
          n++; controllable = v.status == 'CONTROLLABLE';
        });
        return (n == 1) && controllable;
      }
      function dep_listing(d) {
        var dep = ap(t('deploy', d), { 'workerid': d.worker }).attr('pk',d.id);
        dep.find('.shortstatus').css('color', d.status == 'CONTROLLABLE' ? '#3B3' : '#33B' );
        dep.find('.status').addClass(d['status']);
        return dep;
      }
      function wdep_listing(d) {
        var i = _ind.get(d.index);
        var a = _acc.get(i.account);
        var opts = {
          ram: d.effective_bdb + d.effective_xmx,
          name: i.name,
          email: a.email,
          docs: human(i.docs)
        };
        var dep = ap(t('wdeploy', d), opts).attr('pk',d.id);
        dep.find('.shortstatus').css('color', d.status == 'CONTROLLABLE' ? '#3B3' : '#33B' );
        return dep;
      }
      function idx_listing(i) {
        var idx = ap(t('index', i), { documents: human(i.docs) }).attr('pk',i.id);
        idx.find('.shortstatus').css('color', idx_good(i.id) ? 'red' : '#3B3');
        return idx;
      }
      function acc_listing(a) {
        var acc = ap(t('account', a), { indexes: human(icount(a)), documents: human(dcount(a)) }).attr('pk',a.id);
        var p = _pkg.get(a.package);
        var usage = parseInt(100.0 * dcount(a) / p.docs);
        acc.find('.usage').css('color', usage > 100 ? 'red' : '#3B3');
        return acc;
      }
      function cfg_listing(c) {
        return t('config', { id: c.id, name: c.description }).attr('pk',c.id);
      }
      function pkg_listing(p) {
        return ap(t('package', p), { documents: human(p.docs) }).attr('pk',p.id);
      }
      function wkr_listing(w) {
        var wkr = t('worker', w).attr('pk',w.id);
        var used = 0;
        var depcount = _dep.for_worker(w.id).count;
        $.each(_dep.for_worker(w.id).all, function(k,v) {
          used += v.effective_xmx;
          used += v.effective_bdb;
        });
        var usage = parseInt(100 * used / w.ram);
        ap(wkr, { usage: usage, used: used, depcount: depcount }); 
        wkr.find('.shortstatus').css('color', w.status == 'CONTROLLABLE' ? '#3B3' : '#B33' );
        wkr.find('.usagebar').css('width', usage+'%');
        return wkr;
      }
