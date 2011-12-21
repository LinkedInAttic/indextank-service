(function($){
    if(!$.Indextank){
        $.Indextank = new Object();
    };
    
    $.Indextank.StatsRenderer = function(el, options){
        // To avoid scope issues, use 'base' instead of 'this'
        // to reference this class from internal events and functions.
        var base = this;
        
        // Access to jQuery and DOM versions of element
        base.$el = $(el);
        base.el = el;
        
        // Add a reverse reference to the DOM object
        base.$el.data("Indextank.StatsRenderer", base);
        
        base.init = function(){
            base.options = $.extend({},$.Indextank.StatsRenderer.defaultOptions, options);


            base.$el.bind( "Indextank.AjaxSearch.success", function (event, data) {
                base.$el.show();
                base.$el.html("");

                var stats = base.options.format(data);
                stats.appendTo(base.$el);
            });
        };
        
        
        // Run initializer
        base.init();
    };
    
    $.Indextank.StatsRenderer.defaultOptions = {
        format: function (data) {
            var r = $("<div></div>")
                        .append( $("<strong></strong>").text(data.matches) )
                        .append( $("<span></span>").text(" " + (data.matches == 1 ? "result":"results" )+ " for ") )
                        .append( $("<strong></strong>").text(data.query) )
                        .append( $("<span></span>").text(" in ") )
                        .append( $("<strong></strong>").text(data.search_time) )
                        .append( $("<span></span>").text(" seconds.") );

            return r;
        }
    };
    
    $.fn.indextank_StatsRenderer = function(options){
        return this.each(function(){
            (new $.Indextank.StatsRenderer(this, options));
        });
    };
    
})(jQuery);
