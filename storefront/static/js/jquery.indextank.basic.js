(function($){
    if(!$.Indextank){
        $.Indextank = new Object();
    };
    
    $.Indextank.Basic = function(el, apiurl, indexName, options){
        // To avoid scope issues, use 'base' instead of 'this'
        // to reference this class from internal events and functions.
        var base = this;
        
        // Access to jQuery and DOM versions of element
        base.$el = $(el);
        base.el = el;
        
        // Add a reverse reference to the DOM object
        base.$el.data("Indextank.Basic", base);
        
        base.init = function(){
            base.apiurl = apiurl;
            base.indexName = indexName;
            
            base.options = $.extend({},$.Indextank.Basic.defaultOptions, options);
        
            // create a form
            base.form = $("<form></form>");
            base.form.indextank_Ize(apiurl, indexName);
            base.form.attr("id","IndextankBasicForm");
            base.form.appendTo(base.$el);

            // create an input
            base.queryInput = $("<input></input>");
            base.queryInput.appendTo(base.form);
            base.queryInput.indextank_Autocomplete();


            // create a result div
            base.resultDiv = $("<div></div>");
            base.resultDiv.attr("id","IndextankBasicResults");
            base.resultDiv.indextank_Renderer();
            base.resultDiv.appendTo(base.$el);

            // make queryInput send its results to the renderer
            base.queryInput.indextank_AjaxSearch({listeners: base.resultDiv});
        };
        
        // Sample Function, Uncomment to use
        // base.functionName = function(paramaters){
        // 
        // };
        
        // Run initializer
        base.init();
    };
    
    $.Indextank.Basic.defaultOptions = {
    };
    
    $.fn.indextank_Basic = function(apiurl, indexName, options){
        return this.each(function(){
            (new $.Indextank.Basic(this, apiurl, indexName, options));
        });
    };
    
})(jQuery);
