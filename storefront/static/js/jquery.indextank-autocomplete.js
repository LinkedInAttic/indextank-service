/**
 * Indextank autocomplete.
 * 
 * @param url: your Indextank PUBLIC API url. Required.
 * @param indexName: the name of the index to show automcomplete for. Required.
 * @param options: a hash to override default settings. Optional.
 * 
 * @author Diego Buthay <dbuthay@gmail.com>
 * @version 0.1
 */

(function( $ ){

  $.fn.autocompleteWithIndextank = function( url, indexName, options ) {  

    var settings = {
      selectCallback: function( event, ui ) {
                        event.target.value = ui.item.value;
                        event.target.form.submit();
                      }, // select callback
      sourceCallback: function( request, responseCallback ) {
                        $.ajax( {
                          url: url + "/v1/indexes/" + indexName + "/autocomplete",
                          dataType: "jsonp",
                          data: { query: request.term },
                          success: function( data ) { responseCallback( data.suggestions ); }
                        } );
                      }, // source callback
      delay: 100,
      minLength: 2
    }

    return this.each(function() {

      var $this = $(this);
      // If options exist, lets merge them
      // with our default settings
      if ( options ) { 
        $.extend( settings, options );
      }

      $this.autocomplete( {
        source: settings.sourceCallback,
        delay: settings.delay,
        minLength: settings.minLength,
        select: settings.selectCallback
      });

    });

  };
})( jQuery );
