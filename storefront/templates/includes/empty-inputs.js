$(function() {
    var elems = $('input.empty');
    elems.blur(function() { 
        var e = $(this); 
        if (this.value == '') {
            e.addClass('empty');
            this.value = this.getAttribute('emptyvalue');
            if (this.type == 'password') {
                this.setAttribute('ispass', true);
                this.type = 'text';
            }
        } 
    }); 
    elems.focus(function() { 
        var e = $(this); 
        if (e.hasClass('empty')) {
            e.removeClass('empty');
            this.value = '';
            if (this.getAttribute('ispass')) {
                this.type = 'password';
            }
        } 
    });
    elems.removeClass('empty');
    elems.blur();
    $('form').submit(function() {
        $('input.empty').val('');
    });
});