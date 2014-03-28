(function(env) { 
	
	// pass the jQuery object as parameter
	env(window.jQuery, window, document);

}(function($, window, document) {
// listen for 
	$(function() {
		// DOM is ready

		// format phone numbers as you type for login/signup pages
	   	var phone_masks = [{ "mask": "(###) ###-####"}];
		$("input[name=primary_phone_number]").inputmask({ 
	    	mask: phone_masks, 
	    	greedy: false, 
	   		definitions: { '#': { validator: "[0-9]", cardinality: 1}}
	   	});

		$("#login-form-submit").on("click", function(e) {
			if ($("input[name=primary_phone_number]").val().length == 0 || 
				$("input[name=password]").val().length == 0) {
				e.preventDefault();
			}
		});

		$("#signup-form-submit").on("click", function(e) {
			if ($("input[name=full_name]").val().length == 0 ||
				$("input[name=primary_phone_number]").val().length == 0 ||
				$("input[name=email]").val().length == 0 || 
				$("input[name=password1]").val().length == 0 ||
				$("input[name=password2]").val().length == 0) {
				e.preventDefault();
				console.log("clicked");
			}
		});

		var otp_masks = [{ "mask": "#####"}];
		$("input[name=otp").inputmask({ 
	    	mask: otp_masks, 
	    	greedy: false, 
	   		definitions: { '#': { validator: "[0-9]", cardinality: 1}}, 
	   		placeholder:"" });
	});
}));





