(function(env) { 
	
	// pass the jQuery object as parameter
	env(window.jQuery, window, document);

}(function($, window, document) {
// listen for 
	$(function() {
		// DOM is ready
		function window_resize_handler() {
			var window_height = $(window).height();
			var window_width = $(window).width();

			var hero_unit = $("#hero-unit");
			var hero_unit_height = window_height - hero_unit.offset().top;
			hero_unit.css("height", hero_unit_height);

			var hero_contents = $("#hero-content");
			var hero_contents_margin_top = (hero_unit_height - hero_contents.height())/2.0;
			hero_contents.css("margin-top", hero_contents_margin_top);

		}
		window_resize_handler();
		$(window).on("resize", window_resize_handler);

		function earlysignup_submit_handler(e) {
			e.preventDefault();

			form = $("#hero-signup-form");
			var kicker = $("#kicker");
			var kicker_height = kicker.height();
			kicker.height(kicker_height).text("Great! We'll be in touch.");
			form.css("visibility", "hidden");
			
			var data = form.serialize();
			$.ajax({
				url: "/early_signup/",
				type: "post",
				data: data,
				success: function(data) {
				}
			});
		}
		$("#hero-unit").on("click", "#hero-signup-form input[name=submit]", 
			earlysignup_submit_handler);
	});
}));