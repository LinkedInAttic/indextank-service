$(document).ready(function() {
	$('.tab ul li').click(function() {
		$('.tab ul li').children('a').removeClass('active');
		$(this).children('a').addClass('active');
		for ( var i = 1; i < 4; i++) {
			$('#content' + i).hide();
		}
		$('#conten' + $(this).children('a').attr('rel')).show();
	});
});

function go_chat() {
  $('#habla_topbar_div').click(); $('#habla_wcsend_input').focus()
}