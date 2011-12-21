
  function ap(n, opts) {
    $.each(opts, function (k,v) {
      var f = n.find('.'+k);
      if (f != 'undefined') f.text(v);
    });
    return n;
  }
  
  function t(temp, opts) {
    var n = $('#templates .' + temp).clone();
    return ap(n, opts);
  }
