(function(env) { 
	
	// pass the jQuery object as parameter
	env(window.jQuery, window, document);

}(function($, window, document) {
// listen for 
	$(function() {
		// DOM is ready
		var DEBUG = true;
		if (DEBUG) {
			$(document).click(function(e){console.log(e.target)});
		}

		// cache DOM elements of interest in local vars
		var patient_search_box = $("#patient_search_box");
		var patient_search_results = $("#patient_search_results");
		var add_patient_button = $("#add_patient_button");
		var main_col = $("#mainCol")
		var main_content_view = $("#mainContentView");
		var patient_view = $("#patientView");
		var add_patient_view = $("#addPatientView");
		var reminder_fields = $(".reminderFields");
		var add_reminder_button = $("#addReminderButton");
		// ===define and bind event-handlers===================================
		// keystroke handler for patient search-box 
		// instant search
		function get_patient_search_results_list(e) {
			var dynamicData = {};
			dynamicData['q'] = patient_search_box.val().trim();
			$.ajax({
				url  : "patient/search/",
				type : "get",
				data : dynamicData,
				success : function(data) {
					patient_search_results.html(data);
				}
			});
		};
		patient_search_box.on("keyup", get_patient_search_results_list);

		// click handler for patient search result list items
		function load_patient_view(e){
			var dynamicData = {};
			dynamicData['id'] = $(e.target).attr("data-id");
			$.ajax({
				url  : "patient/",
				type : "get",
				data : dynamicData,
				success : function(data) {
					$("#patientView").replaceWith(data);
					add_patient_view.hide();
				}
			});
		}
		patient_search_results.on("click", "li", load_patient_view);

		// click handler for add new patient button
		function load_add_patient_view(e){
			patient_view = $("#patientView");
			add_patient_view = $("#addPatientView");
			reminder_fields = $(".reminderFields");

			patient_view.hide();
			add_patient_view.fadeIn();
			reminder_fields.hide();
		};
		add_patient_button.on("click", load_add_patient_view);

		// click handler for add reminder button
		function load_reminder_fields(e) {
			reminder_fields = $(".reminderFields");
			reminder_fields.fadeIn();
		}
		main_col.on("click", "#addReminderButton", load_reminder_fields);
	});

}));