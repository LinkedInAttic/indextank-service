(function($){
    if(!$.Indextank){
        $.Indextank = new Object();
    };
    
    $.Indextank.Ize = function(el, apiurl, indexName, options){
        // To avoid scope issues, use 'base' instead of 'this'
        // to reference this class from internal events and functions.
        var base = this;
        
        // Access to jQuery and DOM versions of element
        base.$el = $(el);
        base.el = el;
       
        // some parameter validation
        var urlrx = /http(s)?:\/\/[a-z0-9]+.api.indextank.com/
        //if (!urlrx.test(apiurl)) throw("invalid api url!");
        if (indexName == undefined) throw("index name is not defined!");

        // Add a reverse reference to the DOM object
        base.$el.data("Indextank.Ize", base);
        
        base.init = function(){
            base.apiurl = apiurl;
            base.indexName = indexName;
            
            base.options = $.extend({},$.Indextank.Ize.defaultOptions, options);
            
            // Put your initialization code here
        };
        
        // Sample Function, Uncomment to use
        // base.functionName = function(paramaters){
        // 
        // };
        
        // Run initializer
        base.init();
    };
    
    $.Indextank.Ize.defaultOptions = {
    };
    
    $.fn.indextank_Ize = function(apiurl, indexName, options){
        return this.each(function(){
            (new $.Indextank.Ize(this, apiurl, indexName, options));
        });
    };
    
    // This function breaks the chain, but returns
    // the Indextank.Ize if it has been attached to the object.
    $.fn.getIndextank_Ize = function(){
        this.data("Indextank.Ize");
    };
    
})(jQuery);
