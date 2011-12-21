function push(node) {
  var id = node.attr('id');
  if (id) {
    $('#'+id).slideUp(400);
  }
  var hidden = node.find(".header");
  hidden.hide();
  slideDown(node.prependTo('.maincontent'), function() {
    hidden.show();
  });
}
function change_data(cl, id, action, header, olddata, newdata, extra) {
  var extra = extra || function() {}; 
  var ch = t('change', {});
  ch.attr('pk', id).attr('type', cl);
  ch.append("<div style='font-weight:bold'>" + cl + " " + id + " [" + action + "]</div>");
  ch.append("<hr>");
  $.each(header, function(k,v) {
    ch.append("<p><em>" + k + "</em> " + v + "</p>");
  });
  if (!($.isEmptyObject(newdata) && $.isEmptyObject(olddata))) {
    ch.append("<hr>");
    $.each(newdata, function(k,v) {
      ch.append("<p class='new'><em>" + k + "</em> " + v + "</p>");
      var node = $('#' + cl + '_' + id + ' .' + k).add('.listing.' + cl.toLowerCase() + '[pk=' + id + '] .' + k);
      var bg = node.css('backgroundColor');
      var col = node.css('color');
      node.animate({ backgroundColor: '#F00', color: '#FFF' }, 300, function() {
        setTimeout(function() {
          node.css('backgroundColor', '#FF0');
          node.css('color', col); 
          node.text(v); 
          node.animate({ backgroundColor: bg }, 1000, function() { node.removeAttr('style'); });
        }, 200); 
      });
      extra(node);
    });
    $.each(olddata, function(k,v) {
      ch.append("<p class='old'><em>" + k + "</em> " + v + "</p>");
    });    
  }
  if (action == 'deleted') {
    var node = $('#' + cl + '_' + id).add('.' + cl.toLowerCase() + '[pk=' + id + ']'); 
    deleted_data(node); 
  }
  change(ch);
}
function created_data(node) {
  slideDown(node.hide());
  var bg = node.css('backgroundColor');
  node.css('backgroundColor', '#F00').animate({ backgroundColor: bg }, 1500, function() { node.removeAttr('style'); });
}
function deleted_data(node) {
  node.slideUp(400, function() { node.remove(); });
}
function build_item(pk, type) {
  var item = t('item', {});
  item.attr('id', type+'_'+pk);
  item.attr('pk', pk);
  item.attr('type', type);
  return item;
}

function render_index(pk) {  
  var item = build_item(pk, 'Index');
  var i = _ind.get(pk);
  var a = _acc.get(i.account);
  var p = _pkg.get(a.package);
  var cfg = _cfg.get(i.configuration);
  var usage = parseInt(100.0 * i.docs / p.docs);
  var opts = {
    id: i.id,
    status: i.status,
    name: i.name,
    code: i.code,
    documents: i.docs,
    usage: usage,
    maxdocs: human(p.docs),
    configdesc: cfg.description,
    xmx: cfg.data.xmx,
    bdb: cfg.data.bdb_cache || 0,
    package: p.name,
    maxdocs: human(p.docs),
    docs: human(i.docs),
    usage: usage,
    created: new Date(i.creation_time).format('yyyy/mm/dd HH:MM:ss')
  };
  var index = t('index_det', opts);
  var rels = index.find('.rels');
  acc_listing(a).appendTo(rels);
  cfg_listing(cfg).appendTo(rels);
  $.each(_dep.for_index(pk).all, function(k,v) {
    dep_listing(v).appendTo(rels);
  });
  index.appendTo(item.find('.content'));
  return item;
}
function render_deploy(pk) {
  var item = build_item(pk, 'Deploy');
  var d = _dep.get(pk);
  var i = _ind.get(d.index);
  var w = _wkr.get(d.worker);
  var opts = {
    worker_dns: w.wan_dns,
    index_code: i.code,
    created: new Date(d.timestamp).format('yyyy/mm/dd HH:MM:ss')
  };
  var deploy = ap(t('deploy_det', d), opts);
  var rels = deploy.find('.rels');
  idx_listing(i).appendTo(rels);
  wkr_listing(w).appendTo(rels);
  deploy.appendTo(item.find('.content'));
  return item;
}
function render_worker(pk) {
  var item = build_item(pk, 'Worker');
  var w = _wkr.get(pk);
  var used = 0;
  var deps = []
  $.each(_dep.for_worker(pk).all, function(k,v) {
    deps.push([_ind.get(v.index).docs,v]);
    used += v.effective_xmx;
    used += v.effective_bdb;
  });
  var usage = parseInt(100 * used / w.ram); 
  var worker = ap(t('worker_det', w), { used_ram: used, usage: usage });
  var rels = worker.find('.rels');
  deps.sort(function(a,b) { return b[0]-a[0]; });
  t('wdeploy', {id:'id', email:'Account Email', name:'Index Name', docs:'#', ram: 'ram ', status: 'status'}).addClass('header').css('position', 'absolute').css('margin-top', '-20px').appendTo(rels);
  $.each(deps, function(k,v) {
    wdep_listing(v[1]).appendTo(rels);
  });
  worker.appendTo(item.find('.content'));
  return item;
}
function render_config(pk) {
  var item = build_item(pk, 'Config');
  var c = _cfg.get(pk);
  var cc = $('<div class="statsdict"></div>');
  cc.append('<h1>' + c.description + '</h1>')
  var pkgs = _pkg.for_configuration(pk);
  var right = $('<div style="float:right"></div>'); 
  $.each(pkgs.all, function(k,v) {
    pkg_listing(v).appendTo(right);
  });
  if (pkgs.count == 0) {
    right.append('<div style="text-align:right;margin-bottom:5px; color:red; font-size:14px;font-weight:bold">THIS CONFIG IS CUSTOM (No package)</div>');
    $.each(_acc.for_configuration(pk).all, function(k,v) {
      acc_listing(v).appendTo(right);
    });
    $.each(_ind.for_configuration(pk).all, function(k,v) {
      idx_listing(v).appendTo(right);
    });
  }
  right.appendTo(cc)
  cc.append('<p><em>Created</em> ' + new Date(c.creation_date).format('yyyy/mm/dd'));
  cc.append('<p><em>Accounts</em> <a href="javascript:void(0)" class="listaccounts">' + _acc.for_configuration(pk).count + ' accounts</a>');
  cc.append('<p><em>Indexes</em> <a href="javascript:void(0)" class="listindexes">' + _ind.for_configuration(pk).count + ' indexes</a>');
  cc.append('<hr>');
  var pairs = [];
  $.each(c.data, function(k,v) {
    pairs.push([k,v]);
  })
  pairs.sort();
  $.each(pairs, function(i,pair) {
    cc.append('<p><em>' + pair[0] + '</em> ' + pair[1]);
  })
  cc.append('<div style="clear:left"></div>');
  cc.append('<div class="btn choose">Choose Config</div>');
  cc.append('<div style="clear:both"></div>');
  cc.appendTo(item.find('.content'));
  return item;
}
function render_package(pk) {
  var item = build_item(pk, 'Package');
  var p = _pkg.get(pk);
  var c = _cfg.get(p.configuration);
  var package = ap(t('package_det', p), { accounts: _acc.for_package(pk).count });
  var rels = package.find('.rels');
  cfg_listing(c).appendTo(rels);
  /*var relslong = package.find('.relslong');
  $.each(_acc.for_package(pk).all, function(k,v) {
    acc_listing(v).appendTo(relslong);
  });*/
  package.appendTo(item.find('.content'));
  return item;
}
function render_deploy_stats(pk) {
  var item = build_item(pk, 'DeployStats');
  var c = item.find('.content');
  t('load',{}).appendTo(c);
  var dep = Deploy.objects.get(pk);
  var ind = Index.objects.get(dep.index);
  var acc = Account.objects.get(ind.account);
  $.ajax({
    url: 'operations?level=stats&id=' + pk,
    success: function (d) {
      var cc = $('<div class="statsdict"></div>');
      var pairs = [];
      $.each(d, function(k,v) {
        pairs.push([k,v]);
      })
      pairs.sort();
      $.each(pairs, function(i,pair) {
        var val = pair[1];
        if (!isNaN(val)) {
          if (Math.abs(val - 1300000000) < 315360000) {
            // within 10 years of a recent date
            val = new Date(val * 1000).format('yyyy/mm/dd HH:MM:ss'); 
          } else if (val >= 1000) {
            val = val + ' (' + human(val) + ')';
          }
        }
        cc.append('<p><em>' + pair[0] + '</em> ' + val);
      })
      c.html(cc);
      $('<div style="float:right" class="rels"></div>').append(dep_listing(dep)).prependTo(c);
      c.prepend("<h1>stats for deploy " + pk + "</h1>");
    },
    dataType: 'json'
  });
  return item;
}
function render_deploy_config(pk) {
	var item = build_item(pk, 'DeployConfigFile');
	var c = item.find('.content');
	t('load',{}).appendTo(c);
	var cc = $('<div class="statsdict"></div>');
	$.ajax({
		url: 'operations?level=log&file=indexengine_config&id=' + pk,
		success: function (d) {
			try {
				var cfg = $.parseJSON(d);
				$.each(cfg, function(k,v) {
					$('<p><em>' + k + '</em> ' + v + '</p>').appendTo(cc);
				});
			} catch(e) {
			    cc.append(d);
			}
			c.html(cc);
		},
		dataType: 'json'
	});
	return item;
}
function render_deploy_log(pk) {
  var item = build_item(pk, 'DeployLog');
  var c = item.find('.content');
  t('load',{}).appendTo(c);
  $.ajax({
    url: 'operations?level=log&file=logs/indextank.log&id=' + pk,
    success: function (d) {
      d = d.split('\n');
      var cc = $('<div class="log"></div>');
      $.each(d, function(i,line) {
        $('<div class="line"></div>').text(line).appendTo(cc);
      });
      c.html(cc);
      cc.animate({ scrollTop: cc.attr("scrollHeight") }, 1000);
    },
    dataType: 'json'
  });
  return item;
}
function render_deploy_gclog(pk) {
  var item = build_item(pk, 'DeployGCLog');
  var c = item.find('.content');
  t('load',{}).appendTo(c);
  $.ajax({
    url: 'operations?level=log&file=logs/gc.log&id=' + pk,
    success: function (d) {
      d = d.split('\n');
      var cc = $('<div class="log"></div>');
      $.each(d, function(i,line) {
        $('<div class="line"></div>').text(line).appendTo(cc);
      });
      c.html(cc);
      cc.animate({ scrollTop: cc.attr("scrollHeight") }, 1000);
    },
    dataType: 'json'
  });
  return item;
}
function render_account(pk) {  
    var item = build_item(pk, 'Account');
    var a = _acc.get(pk);
    var p = _pkg.get(a.package);
    var c = _cfg.get(a.configuration);
    var pc = _cfg.get(p.configuration);
    var usage = parseInt(100.0 * dcount(a) / p.docs);
    var account = ap(t('account_det', a), { package: p.name, maxdocs: human(p.docs), maxidxs: human(p.indexes), usage:usage, created: new Date(a.creation_time).format('yyyy/mm/dd HH:MM:ss') });
    var rels = account.find('.rels');
    pkg_listing(p).appendTo(rels);
    cfg_listing(c).appendTo(rels);
    var idxs = [];
    $.each(_ind.for_account(pk).all, function(k,v) {
      idxs.push(v);
    });
    idxs.sort(function(a,b) { return b.docs-a.docs; });
    $.each(idxs, function(i,o) {
      idx_listing(o).appendTo(rels);
    });
    account.appendTo(item.find('.content'));
    return item;
}
