(function($){
    if(!$.Indextank){
        $.Indextank = new Object();
    };
    
    $.Indextank.InstantSearch = function(el, options){
        // To avoid scope issues, use 'base' instead of 'this'
        // to reference this class from internal events and functions.
        var base = this;
        
        // Access to jQuery and DOM versions of element
        base.$el = $(el);
        base.el = el;
        
        // Add a reverse reference to the DOM object
        base.$el.data("Indextank.InstantSearch", base);
        
        base.init = function(){
            base.options = $.extend({},$.Indextank.InstantSearch.defaultOptions, options);
           
            // make autocomplete trigger a query when suggestions appear
            base.$el.bind( "Indextank.Autocomplete.success", function (event, suggestions ) {
                base.$el.trigger( "Indextank.AjaxSearch.runQuery", suggestions );
            });
            
            // make autocomplete focus trigger an AjaxSearch, only if requested
            if (base.options.focusTriggersSearch) { 
                base.$el.bind( "autocompletefocus", function (event, ui) {
                    base.$el.trigger( "Indextank.AjaxSearch.runQuery", ui.item.value );
                }); 
            } 

        };
        
        // Sample Function, Uncomment to use
        // base.functionName = function(paramaters){
        // 
        // };
        
        // Run initializer
        base.init();
    };
    
    $.Indextank.InstantSearch.defaultOptions = {
        // trigger a query whenever an option on the autocomplete box is 
        // focused. Either by keyboard or mouse hover.
        // Note that setting this to true can be annoying if your search box is
        // above the result set, as moving the mouse over the suggestions will
        // change the result set.
        focusTriggersSearch : false
    };
    
    $.fn.indextank_InstantSearch = function(options){
        return this.each(function(){
            (new $.Indextank.InstantSearch(this, options));
        });
    };
    
})(jQuery);
