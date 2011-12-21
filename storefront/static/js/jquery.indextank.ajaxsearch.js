/** XXX XXX THIS IS A MODIFIED VERSION OF INDEXTANK-JQUERY .. DON'T UPDATE IT IF NOT SURE ABOUT WHAT YOU ARE DOING .. */

(function($){
    if(!$.Indextank){
        $.Indextank = new Object();
    };
    
    $.Indextank.AjaxSearch = function(el, options){
        // To avoid scope issues, use 'base' instead of 'this'
        // to reference this class from internal events and functions.
        var base = this;
        
        // Access to jQuery and DOM versions of element
        base.$el = $(el);
        base.el = el;
        
        // Add a reverse reference to the DOM object
        base.$el.data("Indextank.AjaxSearch", base);
        
        base.init = function(){
            
            base.options = $.extend({},$.Indextank.AjaxSearch.defaultOptions, options);
            base.xhr = undefined;
            
            
            // TODO: make sure ize is an Indextank.Ize element somehow
            base.ize = $(base.el.form).data("Indextank.Ize");
            base.ize.$el.bind("submit", base.hijackFormSubmit);


            // make it possible for other to trigger an ajax search
            base.$el.bind( "Indextank.AjaxSearch.runQuery", base.runQuery );
        };
        
        // Sample Function, Uncomment to use
        // base.functionName = function(paramaters){
        // 
        // };

            base.runQuery = function( event, term, start, rsLength ) {
                // don't run a query twice
                var query = base.options.rewriteQuery( term || base.el.value );
                start = start || base.options.start;
                rsLength = rsLength || base.options.rsLength;

                if (base.query == query && base.start == start && base.rsLength == rsLength ) {
                    return;
                } 
                
                // if we are running a query, an old one makes no sense.
                if (base.xhr != undefined ) {
                    base.xhr.abort();
                }
               

                // remember the current running query
                base.query = query;
                base.start = start;
                base.rsLength = rsLength;

                base.options.listeners.trigger("Indextank.AjaxSearch.searching");
                base.$el.trigger("Indextank.AjaxSearch.searching");


                // run the query, with ajax
                base.xhr = $.ajax( {
                    url: base.ize.apiurl + "/v1/indexes/" + base.ize.indexName + "/search",
                    dataType: "jsonp",
                    timeout: 10000,
                    data: { 
                            "q": query, 
                            "fetch": base.options.fields, 
                            "snippet": base.options.snippets, 
                            "function": base.options.scoringFunction,
                            "start": start,
                            "len": rsLength,
                            "fetch_variables": base.options.fetchVariables,
                            "fetch_categories": base.options.fetchCategories

                          },
                    success: function( data ) { 
                                // Indextank API does not send the query, nor start or rsLength
                                // I'll save the current query inside 'data',
                                // so our listeners can use it.
                                data.query = query;
                                data.start = start;
                                data.rsLength = rsLength;
                                base.options.listeners.trigger("Indextank.AjaxSearch.success", data);
                                },
                    error: function( jqXHR, textStatus, errorThrown) {
                                base.options.listeners.trigger("Indextank.AjaxSearch.failure");
                    }
                } );
            } 

        base.hijackFormSubmit = function(event) {
            // make sure the form is not submitted
            event.preventDefault();
            base.runQuery();
        };


        // unbind everything
        base.destroy = function() {
            base.$el.unbind("Indextank.AjaxSearch.runQuery", base.runQuery);
            base.ize.$el.unbind("submit", base.hijackFormSubmit);
            base.$el.removeData("Indextank.AjaxSearch");
        };


        // Run initializer
        base.init();
    };
    
    $.Indextank.AjaxSearch.defaultOptions = {
        // first result to fetch .. it can be overrided at query-time,
        // but we need a default. 99.95% of the times you'll want to keep the default
        start : 0,
        // how many results to fetch on every query? 
        // it can be overriden at query-time.
        rsLength : 10, 
        // default fields to fetch .. 
        fields : "name,title,image,url,link",
        // fields to make snippets for
        snippets : "text",
        // no one listening .. sad
        listeners: $([]),
        // scoring function to use
        scoringFunction: 0,
        // fetch variables ?
        fetchVariables: true,
        // fetch categories ?
        fetchCategories: true,
        // the default query re-writer is identity
        rewriteQuery: function(q) {return q}

    };
    
    $.fn.indextank_AjaxSearch = function(options){
        return this.each(function(){
            (new $.Indextank.AjaxSearch(this, options));
        });
    };
    
})(jQuery);
