(function(env) { 
	
	// pass the jQuery object as parameter
	env(window.jQuery, window, document);

}(function($, window, document) {
// listen for 
	$(function() {
		// DOM is ready

		// format phone numbers as you type for login/signup pages
	   	var phone_masks = [{ "mask": "(###) ###-####"}];
		$("#login-form-phonenumber").inputmask({ 
	    	mask: phone_masks, 
	    	greedy: false, 
	   		definitions: { '#': { validator: "[0-9]", cardinality: 1}} });
	});
}));





