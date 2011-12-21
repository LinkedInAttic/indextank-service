google.load("jquery", "1.4.4");
google.load("visualization", "1", {packages: ["table", "annotatedtimeline", "corechart"]});

const MS = ["01","02","03","04","05","06","07","08","09","10"];

function dateFormat(d) {
  var dd = d.getUTCDate();
  var mm = d.getUTCMonth();
  var ms = (mm < 10)? MS[mm]:mm;
  var yy = d.getUTCFullYear();
  if(dd < 10) dd = MS[dd-1];
  return yy+"-"+ms+"-"+dd;
}

var rawJsonData = null;

var activityTable = null;
var activityData = null;
var activityDataReset = null;
var activitySetup = {
  allowHtml: true,
  showRowNumber: true,
  width: 1000,
  sortColumn: 0,
  sortAscending: false,
  cssClassNames: {tableCell: "tss8pt", headerCell: "hss8pt"}
};

const activityDataColumnIndexPackage = 4;
const activityDataColumnIndexCount = 5;

const historyDataColumnIndexPackage = 3;

var historyTable = null;
var historyData = null;
var historyDataReset = null;
var historySetup = {
  allowHtml: true,
  showRowNumber: true,
  width: 1000,
  sortColumn: 7,
  sortAscending: false,
  cssClassNames: {tableCell: "tss8pt", headerCell: "hss8pt"}
};
//,cssClassNames: {tableCell: "ss8pt", headerCell: "ss8pt", headerRow: "bs_header"}

function historyTableHideDataColumns(columns) {
//  historyTable.hideDataColumns(0);
//  historyData.removeColumn(0);

//  historyTable.draw(historyData, historySetup);
}

function historyTablePackageFilter(packageNames) {
  var rows = historyData.getNumberOfRows();
  var toBeRemoved = [];
  for(var i = 0; i < rows; i++) {
    var value = historyData.getValue(i, historyDataColumnIndexPackage);
    for(var j = 0; j < packageNames.length; j++) {
      var packageName = packageNames[j];
      if(packageName == value) {
        toBeRemoved.push(i);
      }
    }
  }
  for(var i = toBeRemoved.length-1; i >= 0; i--) {
    historyData.removeRow(toBeRemoved[i]);
  }
  historyTable.draw(historyData, historySetup);
}

function historyTablePackageFilterOnly(packageNames) {
  var rows = historyData.getNumberOfRows();
  var toBeRemoved = [];
  for(var i = 0; i < rows; i++) {
    var value = historyData.getValue(i, historyDataColumnIndexPackage);
    for(var j = 0; j < packageNames.length; j++) {
      var packageName = packageNames[j];
      if(packageName != value) {
        toBeRemoved.push(i);
      }
    }
  }
  for(var i = toBeRemoved.length-1; i >= 0; i--) {
    historyData.removeRow(toBeRemoved[i]);
  }
  historyTable.draw(historyData, historySetup);
}

function activityTableCountFilter() {
  var rows = activityData.getNumberOfRows();
  var toBeRemoved = [];
  for(var i = 0; i < rows; i++) {
    var value = activityData.getValue(i, activityDataColumnIndexCount);
    if(value <= 0) {
      toBeRemoved.push(i);
    }
  }
  for(var i = toBeRemoved.length-1; i >= 0; i--) {
    activityData.removeRow(toBeRemoved[i]);
  }
  activityTable.draw(activityData, activitySetup);
}

function activityTablePackageFilter(packageNames) {
  var rows = activityData.getNumberOfRows();
  var toBeRemoved = [];
  for(var i = 0; i < rows; i++) {
    var value = activityData.getValue(i, activityDataColumnIndexPackage);
    for(var j = 0; j < packageNames.length; j++) {
      var packageName = packageNames[j];
      if(packageName == value) {
        toBeRemoved.push(i);
      }
    }
  }
  for(var i = toBeRemoved.length-1; i >= 0; i--) {
    activityData.removeRow(toBeRemoved[i]);
  }
  activityTable.draw(activityData, activitySetup);
}

function activityTablePackageFilterOnly(packageNames) {
  var rows = activityData.getNumberOfRows();
  var toBeRemoved = [];
  for(var i = 0; i < rows; i++) {
    var value = activityData.getValue(i, activityDataColumnIndexPackage);
    for(var j = 0; j < packageNames.length; j++) {
      var packageName = packageNames[j];
      if(packageName != value) {
        toBeRemoved.push(i);
      }
    }
  }
  for(var i = toBeRemoved.length-1; i >= 0; i--) {
    activityData.removeRow(toBeRemoved[i]);
  }
  activityTable.draw(activityData, activitySetup);
}

function activityTableReset() {
  activityData = activityDataReset;
  activityDataReset = activityData.clone();
  activityTable.draw(activityData, activitySetup);
}

google.setOnLoadCallback(function() {
  $(function() {

    function descriptiveLogStats(logStats) {
      return "<pre><tt>"
        + "Mean:   " + logStats.mean + "ms\n"
        + "Median: " + logStats.median + "ms\n"
        + "Min:    " + logStats.min + "ms\n"
        + "Max:    " + logStats.max + "ms\n"
        + "95% (" + logStats.Q95K + ") are less than " + logStats.Q95V + "ms"
        + "</tt></pre>";
    }

    function activity(data) {
      
      var s = data.getHistory.length;
      //console.log(data.getHistory);
      
      return "" 
      //+ "<h5>API elapsed time per operation (per account indexes, all accounts)</h5>"
      //+ descriptiveLogStats(data.logStats)
      + "<h5>API elapsed time per Get hit (per account indexes, all accounts)</h5>"
      + descriptiveLogStats(data.logGetStats)
      //+ "<h5>API Put elapsed time per operation (per account indexes, all accounts)</h5>"
      //+ descriptiveLogStats(data.logPutStats)
      //+ "\n"
      ;
    }

    function revenue(data) {
      //TODO: change this to use package.base_price
      //TODO: account.package.code.startswith('HEROKU_')
      var herokuProfit = .7;
      var accountList = data.accountPaymentList;
      var herokuAmountTotal = 0;
      var amountTotal = 0;
      var typeMap = {};
      for(var i = 0; i < accountList.length; i++) {
        if(accountList[i].package.substring(0,"HEROKU".length) === "HEROKU")
          herokuAmountTotal += parseInt(accountList[i].packagePrice);
        else {
          var gatewayPrice = parseInt(accountList[i].gatewayPrice);
          amountTotal += gatewayPrice;
          var prev = typeMap[accountList[i].subscription];
          if(prev == undefined)
            typeMap[accountList[i].subscription] = gatewayPrice;
          else
            typeMap[accountList[i].subscription] = prev + gatewayPrice; 
        }
      }

      var herokuNetTotal = Math.round(herokuProfit * herokuAmountTotal);

      var total = herokuNetTotal + amountTotal;
      var gateways = "";
      $.each(typeMap, function(k,v) {
        gateways += k + "\t\t: " + v + " usd\n"; 
      });

      return ""
        + "<h5>Monthly subscriptions</h5>"
        + "<pre><tt>"
        + gateways
        + "Heroku addon    : " + herokuNetTotal + " usd (" + herokuAmountTotal + " gross)\n"
        + "Total           : " + total + " usd\n"
        + "</tt></pre>"
      ;
    }

    function renderSubscriptionList(accountSubscriptionList) {
      var data = new google.visualization.DataTable();
      data.addColumn("number", "Id");
      data.addColumn("string", "First Name");
      data.addColumn("string", "Last Name");
      data.addColumn("string", "Country");
      data.addColumn("string", "Start Date");
      data.addColumn("number", "Amount");
      data.addColumn("number", "AmountDue");
      data.addRows(accountSubscriptionList.length);
      for(var i = 0; i < accountSubscriptionList.length; i++) {
        
        data.setCell(i, 0, parseInt(accountSubscriptionList[i].id));
        data.setCell(i, 1, accountSubscriptionList[i].fistName);
        data.setCell(i, 2, accountSubscriptionList[i].lastName);
        data.setCell(i, 3, accountSubscriptionList[i].country);
        data.setCell(i, 4, accountSubscriptionList[i].startDate);
        data.setCell(i, 5, parseFloat(accountSubscriptionList[i].amount));
        data.setCell(i, 6, parseFloat(accountSubscriptionList[i].amountDue));
      }
      var table = new google.visualization.Table(document.getElementById("subscriptionsList"));
      
      var setup = {
        allowHtml: true,
        showRowNumber: true,
        sortColumn: 0,
        sortAscending: false,
        cssClassNames: {tableCell: "ss8pt", headerCell: "ss8pt"}
      };
      
      var sortInfoColumn = 0;
      var sortInfoAscending = false;
      google.visualization.events.addListener(table, "sort", function(e) {
        sortInfoAscending = (sortInfoColumn == e.column)? !sortInfoAscending : false;
        sortInfoColumn = e.column;
        setup.sortColumn = sortInfoColumn;
        setup.sortAscending = sortInfoAscending; 
        table.draw(data, setup); 
      });
      
      table.draw(data, setup);

    }

    function renderPaymentList(list) {
      var data = new google.visualization.DataTable();
      data.addColumn("number", "Id");
      data.addColumn("string", "Email");
      data.addColumn("string", "Creation");
      data.addColumn("string", "Package");
      data.addColumn("number", "Amount");
      data.addColumn("number", "Total");
      data.addRows(list.length);
      for(var i = 0; i < list.length; i++) {
        
        var amount;
        var packagePrice = parseInt(list[i].packagePrice);
        var gatewayPrice = parseInt(list[i].gatewayPrice);
        var monthsBetween = parseInt(list[i].monthsBetween);
        if(gatewayPrice == 0) {
          amount = packagePrice;
        } else  {
          amount = gatewayPrice;
        }
        var amountTotal = amount * monthsBetween;
        j = 0;
        data.setCell(i, j++, parseInt(list[i].id));
        data.setCell(i, j++, list[i].email);
        data.setCell(i, j++, list[i].creation);
        data.setCell(i, j++, list[i]['package']);
        data.setCell(i, j++, amount);
        data.setCell(i, j++, amountTotal);
      }
      var table = new google.visualization.Table(document.getElementById("subscriptionsList"));
      
      var setup = {
        allowHtml: true,
        showRowNumber: true,
        sortColumn: 0,
        sortAscending: false,
        cssClassNames: {tableCell: "ss8pt", headerCell: "ss8pt"}
      };
      
      var sortInfoColumn = 0;
      var sortInfoAscending = false;
      google.visualization.events.addListener(table, "sort", function(e) {
        sortInfoAscending = (sortInfoColumn == e.column)? !sortInfoAscending : false;
        sortInfoColumn = e.column;
        setup.sortColumn = sortInfoColumn;
        setup.sortAscending = sortInfoAscending; 
        table.draw(data, setup); 
      });
      
      table.draw(data, setup);

    }    
    function renderTwitterHistory(accountHistory) {
      var data = new google.visualization.DataTable();
      data.addColumn("date", "Date");
      data.addColumn("number", "Tweets");
      
      data.addRows(accountHistory.length);
      
      for(var i = 0; i < accountHistory.length; i++) {
        data.setCell(i, 0, new Date(accountHistory[i].date));
        data.setCell(i, 1, parseInt(accountHistory[i].count));
      }
      
      var annotatedtimeline = new google.visualization.AnnotatedTimeLine(document.getElementById("visualization"));
      annotatedtimeline.draw(data, {
        "displayAnnotations": false,
        "displayRangeSelector": true,
        "displayZoomButtons": false,
        "fill": 50,
        "colors": ["black"]
      });
    }
    
    function renderActivationAARRR(hist) {
      var data = new google.visualization.DataTable();
      data.addColumn("date", "Date");
      data.addColumn("number", "% Created an index");
      data.addColumn("number", "% Used an index");
      
      var keys = Object.keys(hist);
      data.addRows(keys.length);

      for(var i = 0; i < keys.length; i++) {
        var k = keys[i];
        var v = hist[k];
        var j = 0;
        var t = parseInt(v[0]);
        data.setCell(i, j++, new Date(k));
        data.setCell(i, j++, Math.round(100*parseInt(v[1])/t), v[1]);
        data.setCell(i, j++, Math.round(100*parseInt(v[2])/t), v[2]);
      }
      
      var annotatedtimeline = new google.visualization.AnnotatedTimeLine(document.getElementById("activationAARRRVisualization"));
      annotatedtimeline.draw(data, {
        "displayAnnotations": false,
        "displayRangeSelector": false,
        "displayZoomButtons": false,
        "fill": 50,
        "colors": ["silver", "gray", "black"]
      });
    }
    
    function renderRetentionAARRR(hist) {
      var data = new google.visualization.DataTable();
      data.addColumn("date", "Date");
      data.addColumn("number", "% GET");
      data.addColumn("number", "% PUT");
      data.addColumn("number", "% GET/PUT");
      
      var keys = Object.keys(hist);
      data.addRows(keys.length);
      
      for(var i = 0; i < keys.length; i++) {
        var k = keys[i];
        var v = hist[k];
        var j = 0;
        var t = parseInt(v[0]);
        data.setCell(i, j++, new Date(k));
        data.setCell(i, j++, Math.round(100*parseInt(v[1])/t), v[1]);
        data.setCell(i, j++, Math.round(100*parseInt(v[2])/t), v[2]);
        data.setCell(i, j++, Math.round(100*parseInt(v[3])/t), v[3]);
      }
      
      var annotatedtimeline = new google.visualization.AnnotatedTimeLine(document.getElementById("retentionAARRRVisualization"));
      annotatedtimeline.draw(data, {
        "displayAnnotations": false,
        "displayRangeSelector": false,
        "displayZoomButtons": false,
        "fill": 50,
        "colors": ["silver", "gray", "black"]
      });
    }
    
    function renderAccountHistory(accountHistory) {
      var data = new google.visualization.DataTable();
      data.addColumn("date", "Date");
      data.addColumn("number", "Total");
      data.addColumn("number", "New");
      
      data.addRows(accountHistory.length);
      
      for(var i = 0; i < accountHistory.length; i++) {
        data.setCell(i, 0, new Date(accountHistory[i].date));
        data.setCell(i, 1, parseInt(accountHistory[i].total));
        data.setCell(i, 2, parseInt(accountHistory[i].count));
      }

      var annotatedtimeline = new google.visualization.AnnotatedTimeLine(document.getElementById("accountsHistoryVisualization"));
      annotatedtimeline.draw(data, {
        "displayAnnotations": false,
        "displayRangeSelector": true,
        "displayZoomButtons": false,
        "fill": 50,
        "colors": ["black"]
      });
    }
    
    function renderAdoptionAARRR1(accountHistory, element) {
      var data = new google.visualization.DataTable();
      data.addColumn("string", "Date");
      data.addColumn("number", "New Accounts");

      var length = Object.keys(accountHistory).length;
      data.addRows(length);

      var i = 0;
      $.each(accountHistory, function(k,v) {
        data.setValue(i, 0, k);
        data.setValue(i, 1, v);
        i++;
      });
      var vis = new google.visualization.LineChart(element);
      vis.draw(data, {});
    }
    
    function renderAdoptionAARRR2(accountHistory, element) {
      var data = new google.visualization.DataTable();
      data.addColumn("date", "Date");
      data.addColumn("number", "New Accounts");

      var length = Object.keys(accountHistory).length;
      data.addRows(length);

      var i = 0;
      $.each(accountHistory, function(k,v) {
        data.setValue(i, 0, new Date(v.date));
        data.setValue(i, 1, parseInt(v.count));
        i++;
      });
      var vis = new google.visualization.LineChart(element);
      vis.draw(data, {});
    }

    function renderAdoptionAARRR(json) {
      renderAdoptionAARRR1(json.monthAccountHistory, document.getElementById("adoptionAARRRVisualization"));
      renderAdoptionAARRR1(json.weekAccountHistory, document.getElementById("adoptionAARRRVisualization1"));
      renderAdoptionAARRR2(json.accountHistory, document.getElementById("adoptionAARRRVisualization2"));
    }
    
    function renderAARRR(data) {
      var d = new Date();
      // prev week
      var w = new Date(d.getTime() - 604800000);
      // first ms prev week
      var lastWeekMillis = new Date(w.getFullYear(), w.getMonth(), w.getDate());

      var accountCreatedPerWeek = {};
      var accountIndexCreatedPerWeek = {};
      var accountIndexUsedPerWeek = {};
      
      for(var i = 0; i < data.accountList.length; i++) {
        var e = data.accountList[i];
        
        if(new Date(e.creation).getTime() >= lastWeekMillis) {
          accountCreatedPerWeek[e.name] = e.name;
        }
      }
      
      for(var i = 0; i < data.indexList.length; i++) {
        var j = 0;
        var e = data.indexList[i];
        var documentCount = parseInt(e.documentCount);
        
        if(e.indexName == "DemoIndex") {
          continue;
        }
          
        if(new Date(e.accountCreation).getTime() >= lastWeekMillis) {
          if(new Date(e.creation).getTime() >= lastWeekMillis) {
            accountIndexCreatedPerWeek[e.name] = e.name;
            if(documentCount > 0) {
              accountIndexUsedPerWeek[e.name] = e.name;
            }
          }
        }

      }

      var accountCreatedPerWeekTotal = Object.keys(accountCreatedPerWeek).length;
      var accountIndexCreatedPerWeekTotal = Object.keys(accountIndexCreatedPerWeek).length;
      var accountIndexUsedPerWeekTotal = Object.keys(accountIndexUsedPerWeek).length;
      
      var accountIndexCreatedPerWeekPercent = accountIndexCreatedPerWeekTotal / accountCreatedPerWeekTotal;
      var accountIndexUsedPerWeekPercent = accountIndexUsedPerWeekTotal / accountCreatedPerWeekTotal;
      
      
      return ""
        + "<h5>Weekly account activations</h5>"
        + "<pre><tt>"
        + "Total new accounts : " + accountCreatedPerWeekTotal + " (last 7 days)\n"
        + "Created an index   : " + Math.round(100*accountIndexCreatedPerWeekPercent) + "% ("+ accountIndexCreatedPerWeekTotal +")\n"
        + "Used an index      : " + Math.round(100*accountIndexUsedPerWeekPercent) + "% ("+ accountIndexUsedPerWeekTotal +") \n"   
        + "</tt></pre>"
      ;
    }

    function renderGlobalHistory(gets, puts) {
      var data = new google.visualization.DataTable();
      data.addColumn("date", "Date");
      data.addColumn("number", "Get hits");
      data.addColumn("number", "Put hits");
      data.addColumn("number", "Total hits");

      var keys = Object.keys(gets);
      data.addRows(keys.length);
      
      for(var i = 0; i < keys.length; i++) {
        data.setCell(i, 0, new Date(keys[i]));
        var g = parseInt(gets[keys[i]]);
        var p = parseInt(puts[keys[i]]);
        var t = p + g;
        data.setCell(i, 1, g);
        data.setCell(i, 2, p);
        data.setCell(i, 3, t);
      }

      var annotatedtimeline = new google.visualization.AnnotatedTimeLine(document.getElementById("globalHistoryVisualization"));
      annotatedtimeline.draw(data, {
        "displayAnnotations": false,
        "displayRangeSelector": false,
        "displayZoomButtons": false,
        "fill": 50,
        "colors": ["black", "gray", "silver"]
      });
    }

    function renderIndexList(indexList) {
      var data = new google.visualization.DataTable();
      data.addColumn("string", "Account");
      data.addColumn("string", "Email");
      data.addColumn("string", "Index");
      data.addColumn("number", "Documents");
      data.addColumn("number", "Id");
      data.addColumn("string", "Code");
      data.addColumn("string", "Creation");

      data.addRows(indexList.length);
      
      for(var i = 0; i < indexList.length; i++) {
        var j = 0;
        var e = indexList[i];
        var documentCount = parseInt(indexList[i].documentCount);
        
        data.setCell(i, j++, indexList[i].name);
        data.setCell(i, j++, indexList[i].email);
        data.setCell(i, j++, indexList[i].indexName);
        data.setCell(i, j++, documentCount);
        data.setCell(i, j++, parseInt(indexList[i].indexId));
        data.setCell(i, j++, indexList[i].indexCode);
        data.setCell(i, j++, e.creation);
      }
      
      var table = new google.visualization.Table(document.getElementById("indexesList"));
      
      var setup = {
        allowHtml: true,
        showRowNumber: true,
        sortColumn: 6,
        sortAscending: false,
        cssClassNames: {tableCell: "ss8pt", headerCell: "ss8pt"}
      };
      
      var sortInfoColumn = 6;
      var sortInfoAscending = false;
      google.visualization.events.addListener(table, "sort", function(e) {
        sortInfoAscending = (sortInfoColumn == e.column)? !sortInfoAscending : false;
        sortInfoColumn = e.column;
        setup.sortColumn = sortInfoColumn;
        setup.sortAscending = sortInfoAscending; 
        table.draw(data, setup); 
      });
      
      table.draw(data, setup);
    }

    function renderQosList(customMap, accountEmail) {
      var data = new google.visualization.DataTable();
      data.addColumn("string", "<div style=\"text-align:right\">"+"Account"+"</div>");
      data.addColumn("string", "<div style=\"text-align:left\">"+"Email"+"</div>");
      data.addColumn("string", "<div style=\"text-align:right\">"+"HTTP"+"</div>");
      for(var i = 0; i < 24; i++) {
        data.addColumn("number", "<div style=\"text-align:right;width:20px\">"+i+"</div>");
      }

      // if we're showing per account rows:
      //data.addRows(Object.keys(customMap).length);

      var df = dateFormat(new Date());
      var i = 0;
      $.each(customMap, function(k,v) {
        // if we're showing all http codes:
        //data.addRows(Object.keys(v).length);
        $.each(v, function(k1, v1) {
          // return only http code 200
          if(k1 != 200) return;
          data.addRows(1);
          var j = 0;
          data.setCell(i, j++, k);
          if(accountEmail != undefined && k in accountEmail)
            data.setCell(i, j, accountEmail[k]);
          j++;
          data.setCell(i, j++, k1);
          $.each(v1, function(k2, v2) {
            var gmtHour = k2.split(" ")[1];
            var d = df+" "+gmtHour;
            var vv2 = v1[d];
            if(vv2 != undefined) {
              data.setCell(i, parseInt(gmtHour)+3, Math.round(v2[1]/v2[0]));
            }
          });
          i++;
        });
      });
      
      var table = new google.visualization.Table(document.getElementById("qosList"));
      
      var setup = {
          allowHtml: true,
          showRowNumber: true,
          sortColumn: 0,
          sortAscending: false,
          cssClassNames: {tableCell: "tss8pt", headerCell: "tss8pt"}
      };
      
      var sortInfoColumn = 0;
      var sortInfoAscending = false;
      google.visualization.events.addListener(table, "sort", function(e) {
        sortInfoAscending = (sortInfoColumn == e.column)? !sortInfoAscending : false;
        sortInfoColumn = e.column;
        setup.sortColumn = sortInfoColumn;
        setup.sortAscending = sortInfoAscending; 
        table.draw(data, setup); 
      });
      
      table.draw(data, setup);
    }
    

    function renderQosErrorList(customMap, accountEmail) {
      var data = new google.visualization.DataTable();
      
      var d = new Date();
      var ds = new Array();

      //generate prev 5 days keys
      const days = 5;
      for(var k = days-1; k >= 0; k--) {
        ds[k] = dateFormat(d);
        d = new Date( d.getTime() - 86400000 );
      }
      
      data.addColumn("string", "<div style=\"text-align:right\">"+"Account"+"</div>");
      data.addColumn("string", "<div style=\"text-align:left\">"+"Email"+"</div>");
      for(var i = 0; i < days; i++) {
        data.addColumn("number", "<div style=\"text-align:right\">"+ds[i]+"</div>");
      }

      data.addRows(Object.keys(customMap).length);

      var i = 0;
      $.each(customMap, function(k,v) {
        var j = 0;
        // account code
        data.setCell(i, j++, k);
        // account email
        if(accountEmail != undefined && k in accountEmail)
          data.setCell(i, j, accountEmail[k]);
        j++;
        for(var l=0; l < days; l++) {
          var vv = v[ds[l]];
          if(vv != undefined) {
            data.setCell(i, j+l, parseInt(vv));
          }
        }
        i++;
      });
      
      var table = new google.visualization.Table(document.getElementById("qosErrorList"));
      
      var setup = {
          allowHtml: true,
          showRowNumber: true,
          sortColumn: 6,
          sortAscending: false,
          cssClassNames: {tableCell: "tss8pt", headerCell: "tss8pt"}
      };
      
      var sortInfoColumn = 6;
      var sortInfoAscending = false;
      google.visualization.events.addListener(table, "sort", function(e) {
        sortInfoAscending = (sortInfoColumn == e.column)? !sortInfoAscending : false;
        sortInfoColumn = e.column;
        setup.sortColumn = sortInfoColumn;
        setup.sortAscending = sortInfoAscending; 
        table.draw(data, setup); 
      });
      
      table.draw(data, setup);
    }
    

    function renderQos95List(customMap, accountEmail) {
      var data = new google.visualization.DataTable();
      
      data.addColumn("string", "<div style=\"text-align:right\">"+"Account"+"</div>");
      data.addColumn("string", "<div style=\"text-align:left\">"+"Email"+"</div>");
      data.addColumn("number", "<div style=\"text-align:right\">Q95</div>");

      data.addRows(Object.keys(customMap).length);

      var i = 0;
      $.each(customMap, function(k,v) {
        var j = 0;
        // account code
        // account email
        if(accountEmail != undefined && k in accountEmail) {
          data.setCell(i, j++, k);
          data.setCell(i, j++, accountEmail[k]);
          data.setCell(i, j++, Math.round(v*1000));
        }
        i++;
      });
      
      var table = new google.visualization.Table(document.getElementById("qos95List"));
      
      var setup = {
          allowHtml: true,
          showRowNumber: true,
          sortColumn: 2,
          sortAscending: false,
          cssClassNames: {tableCell: "tss8pt", headerCell: "tss8pt"}
      };
      
      var sortInfoColumn = 2;
      var sortInfoAscending = false;
      google.visualization.events.addListener(table, "sort", function(e) {
        sortInfoAscending = (sortInfoColumn == e.column)? !sortInfoAscending : false;
        sortInfoColumn = e.column;
        setup.sortColumn = sortInfoColumn;
        setup.sortAscending = sortInfoAscending; 
        table.draw(data, setup); 
      });
      
      table.draw(data, setup);
    }
    
    
    function renderAccountHistoryList(accountList) {
      var d = new Date();
      var ds = new Array();

      //generate prev 5 days keys
      for(var k = 0; k < 5; k++) {
        var dd = d.getUTCDate();
        var mm = d.getUTCMonth();
        var ms = (mm < 10)? MS[mm]:mm;
        var yy = d.getUTCFullYear();
        if(dd < 10) dd = MS[dd-1];
        ds[k] = yy+"-"+ms+"-"+dd;
        d = new Date( d.getTime() - 86400000 );
      }

      var data = new google.visualization.DataTable();
      data.addColumn("number", "<div style=\"text-align:right\">"+"Id"+"</div>");
      data.addColumn("string", "<div style=\"text-align:left\">"+"Email"+"</div>");
      data.addColumn("string", "<div style=\"text-align:left\">"+"Name"+"</div>");
      data.addColumn("string", "<div style=\"text-align:left\">"+"Package"+"</div>");
      data.addColumn("number", "<div style=\"text-align:right\">"+"Documents"+"</div>");
      data.addColumn("number", "<div style=\"text-align:right\">"+ds[4]+"</div>");
      data.addColumn("number", "<div style=\"text-align:right\">"+ds[3]+"</div>");
      data.addColumn("number", "<div style=\"text-align:right\">"+ds[2]+"</div>");
      data.addColumn("number", "<div style=\"text-align:right\">"+ds[1]+"</div>");
      data.addColumn("number", "<div style=\"text-align:right\">"+ds[0]+"</div>");
      data.addColumn("number", "<div style=\"text-align:right\">"+"Average"+"</div>");

      data.addRows(accountList.length);
      
      for(var i = 0; i < accountList.length; i++) {
        var j = 0;
        var count = parseInt(accountList[i].count);
        var email = accountList[i].email;
        if(email.length > 35)
          email = email.substring(0, 35) + "...";

        data.setCell(i, j++, parseInt(accountList[i].id));
        data.setCell(i, j++, email);
        data.setCell(i, j++, accountList[i].name);
        data.setCell(i, j++, accountList[i].package);
        var documentCount = parseInt(accountList[i].indexCount);
        if(documentCount > 0) data.setCell(i, j, documentCount); j++;

        if(accountList[i].getHistory != undefined) {
          var tqs = 0;
          for(var k = 0; k < ds.length; k++) {
            var qs = accountList[i].getHistory[ds[4-k]];
            if(qs != undefined && k < 4)
              tqs += qs;
            data.setCell(i, j++, qs);
          }
          var average = Math.round(tqs/4);
          if(average > 0) data.setCell(i, j++, average);
        }

      }

      var table = new google.visualization.Table(document.getElementById("historyList"));

      var sortInfoColumn = 7;
      var sortInfoAscending = false;
      google.visualization.events.addListener(table, "sort", function(e) {
        sortInfoAscending = (sortInfoColumn == e.column)? !sortInfoAscending : false;
        sortInfoColumn = e.column;
        historySetup.sortColumn = sortInfoColumn;
        historySetup.sortAscending = sortInfoAscending; 
        table.draw(data, historySetup); 
      });

      table.draw(data, historySetup);

      historyTable = table;
      historyData = data;
      historyDataReset = data.clone();
      
    }    


    function renderAccountList(accountList) {
      var data = new google.visualization.DataTable();

      data.addColumn("number", "<div style=\"text-align:right\">"+"Id"+"</div>");
      data.addColumn("string", "<div style=\"text-align:left\">"+"Email"+"</div>");
      data.addColumn("string", "<div style=\"text-align:left\">"+"Name"+"</div>");
      data.addColumn("string", "<div style=\"text-align:left\">"+"Creation"+"</div>");
      data.addColumn("string", "<div style=\"text-align:left\">"+"Package"+"</div>");
      //data.addColumn("number", "<div style=\"text-align:right\">"+"Count"+"</div>");
      //data.addColumn("number", "<div style=\"text-align:right\">"+"AvgSecs"+"</div>");
      data.addColumn("string", "<div style=\"text-align:right\">"+"LastGET"+"</div>");
      data.addColumn("string", "<div style=\"text-align:right\">"+"LastPUT"+"</div>");
      data.addColumn("number", "<div style=\"text-align:right\">"+"GET"+"</div>");
      data.addColumn("number", "<div style=\"text-align:right\">"+"PUT"+"</div>");
      data.addColumn("number", "<div style=\"text-align:right\">"+"Documents"+"</div>");
      data.addColumn("number", "<div style=\"text-align:right\">"+"Indexes"+"</div>");

      //data.addColumn("number", "Usage Ratio (GET/PUT)");

      //data.addColumn("string", "Country");
      //data.addColumn("string", "Start Date");
      //data.addColumn("string", "Amount");
      //data.addColumn("string", "Amount Billed");

      data.addRows(accountList.length);
      
      for(var i = 0; i < accountList.length; i++) {
        var j = 0;
        var count = parseInt(accountList[i].count);
        var avg = parseFloat(accountList[i].avg);
        var ratio = parseFloat(accountList[i].ratio);
        var getCount = parseInt(accountList[i].getCount);
        var putCount = parseInt(accountList[i].putCount);
        var indexes = parseInt(accountList[i].indexCount);
        var documents = parseInt(accountList[i].documentCount);
        var email = accountList[i].email;
        if(email.length > 35)
          email = email.substring(0, 35) + "...";

        data.setCell(i, j++, parseInt(accountList[i].id));
        data.setCell(i, j++, email);
        data.setCell(i, j++, accountList[i].name);
        data.setCell(i, j++, accountList[i].creation);
        data.setCell(i, j++, accountList[i].package);
        //if(count > 0) data.setCell(i, j, count); j++;
        //if(avg > 0) data.setCell(i, j, avg); j++;
        data.setCell(i, j++, accountList[i].get);
        data.setCell(i, j++, accountList[i].put);
        //if(ratio > 0) data.setCell(i, j, ratio); j++;
        if(getCount > 0) data.setCell(i, j, getCount); j++;
        if(putCount > 0) data.setCell(i, j, putCount); j++;
        //data.setCell(i, j++, accountList[i].country);
        //data.setCell(i, j++, accountList[i].startDate);
        //data.setCell(i, j++, accountList[i].amount);
        //data.setCell(i, j++, accountList[i].amountDue);
        if(indexes > 0) data.setCell(i, j, indexes); j++;
        if(documents > 0) data.setCell(i, j, documents); j++;
      }

      var table = new google.visualization.Table(document.getElementById("accountsList"));

      var sortInfoColumn = 0;
      var sortInfoAscending = false;
      google.visualization.events.addListener(table, "sort", function(e) {
        sortInfoAscending = (sortInfoColumn == e.column)? !sortInfoAscending : false;
        sortInfoColumn = e.column;
        activitySetup.sortColumn = sortInfoColumn;
        activitySetup.sortAscending = sortInfoAscending; 
        table.draw(data, activitySetup); 
      });
      
      table.draw(data, activitySetup);
      
      activityTable = table;
      activityData = data;
      activityDataReset = data.clone();
      
    }    
    
    $.getJSON("/biz_stats.json.daily", {}, function(data) {
      renderActivationAARRR(data.activations);
      renderRetentionAARRR(data.retentions);

      $.getJSON("/biz_stats.json", {}, function(data) {
        rawJsonData = data;
        $("div#activityStats")
          .append(revenue(data))
          .append(renderAARRR(data))
          .append(activity(data))
          ;
        renderAccountList(data.accountList);
        renderIndexList(data.indexList);
        renderAccountHistoryList(data.accountList);
        //
        renderAdoptionAARRR(data);
        renderAccountHistory(data.accountHistory);
        renderGlobalHistory(data.getHistory, data.putHistory);
        //renderSubscriptionList(data.accountSubscriptionList);
        renderPaymentList(data.accountPaymentList);
        renderQosList(data.accountGetHistoryHourly, data.accountEmail);
        renderQos95List(data.account95HistoryMonthly, data.accountEmail);
        renderQosErrorList(data.accountErrorHistoryDaily, data.accountEmail);
        $("div#revenue").append(revenue(data));
        hide("activity");
        hide("accounts");
        hide("accountsHistory");
        hide("subscriptions");
        hide("history");
        hide("globalHistory");
        hide("indexes");
        hide("qos");
        hide("activationAARRR");
        show("activity");
      });
      
    });

    $.ajax({
      url: "http://tweets-cron.appspot.com/json",
      dataType: "jsonp",
      success: function(data) { 
        renderTwitterHistory(data.tweets);
        hide("tweets");
      }
    });    
    
  }); // $ fun
}); // g callback

function show(id) {
  document.getElementById(id).style.display="block";
}

function hide(id) {
  document.getElementById(id).style.display="none";
  document.getElementById(id).style.visibility="visible";
}

function hideAll() {
  hide("activationAARRR");
  hide("tweets");
  hide("subscriptions");
  hide("accountsHistory");
  hide("accounts");
  hide("activity");
  hide("history");
  hide("qos");
  hide("globalHistory");
  hide("indexes");
}

function hideAllAndShow(id) {
  hideAll();
  show(id);
}
