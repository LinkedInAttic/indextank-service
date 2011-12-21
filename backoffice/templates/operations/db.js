      function DB(name, rfields) {
        rfields = rfields || [];
        var db = { 
          name: name,
          rel_fields: rfields,
          rels: {},
          count: 0,
          all: {},
          add: function(o) {
            if (o.id in this.all) return;
            this.count++;
            this.all[o.id] = o;
            $.each(this.rels, function(r,db) {
              db.get(o[r]).add(o);
            });
          },
          remove: function(k) {
            var db = this;
            if (k in this.all) {
              var o = this.all[k];
              $.each(db.rel_fields, function (i,r) {
                var rdb = db.rels[r];
                rdb.get(o[r]).remove(k);
              });
              delete this.all[k];
              this.count--;
            }
          },
          load: function(ls) {
            var cl = eval(name); 
            var db = this;
            var ndb = DB(name, rfields);
            $.each(this.rel_fields, function (i,r) { 
              ndb.rels[r] = RelDB(name, r); 
            });
            $.each(ls, function(i, n) {
              ndb.add(n);
            }); 
            if (db.count) {
              var old = db.all;
              setTimeout(function() { 
                db.all = ndb.all;
                db.count = ndb.count;
                db.rels = ndb.rels;
              }, 0);
              $.each(ndb.all, function(k,v) {
                if (k in old) {
                  var o = old[k];
                  if (!equals(o,v)) {
                    setTimeout(function() { cl.changed(k, o, v); }, 0);
                  }
                } else {
                  setTimeout(function() { cl.created(k, v); }, 0);
                }
              });
              $.each(old, function(k,v) {
                if (!(k in ndb.all)) {
                  cl.deleted(k, v);
                }
              });
            } else {
              db.all = ndb.all;
              db.count = ndb.count;
              db.rels = ndb.rels;
            }
          },
          get: function(k) { return this.all[k] },
          update: function (a, b) {
            var db = this;   
            var cl = eval(db.name);
            $.each(b, function(k,v) {
              if (k in a) {
                var o = a[k];
                if (!equals(o,v)) {
                  setTimeout(function() { cl.changed(k, o, v); }, 0);
                  db.remove(k);
                  db.add(v);
                }
              } else {
                setTimeout(function() { cl.created(k, v); }, 0);
                db.add(v);
              }
            });
            $.each(a, function(k,v) {
              if (!(k in b)) {
                cl.deleted(k, v);
                db.remove(k);
              }
            });
          },
        };
        $.each(db.rel_fields, function (i,r) { 
          db.rels[r] = RelDB(name, r); 
          db['for_' + r] = function(k) {
            return db.rels[r].get(k);
          }
        });
        return db;
      }
      function RelDB(parent, child) {
        return {
          get: function(k) {
            //if ('id' in k) k = k.id;
            if (!(k in this)) {
              this[k] = DB(parent+'['+k+'].'+child);
            }
            return this[k];
          },
        };
      }