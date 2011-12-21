$(document).ready(function(){
	$('.work_tab ul li').click(function(){
		var tabs = $(this).parent().children('.work_tab ul li').children('a');
		tabs.removeClass('active');
		var tgt = $(this).children('a').attr('rel');
		$('.'+tgt).show();
		tabs.each(function() {
			var rel = $(this).attr('rel');
			if (rel != tgt) {
				$('.'+rel).hide();
			}
		});
		$(this).children('a').addClass('active');
	});
});
