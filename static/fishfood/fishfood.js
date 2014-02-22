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
		var add_reminder_form = $("#addReminderForm");
		var add_reminder_button = $("#addReminderButton");
		// ===define and bind event-handlers===================================
		// keystroke handler for patient search-box 
		// instant search
		function get_patient_search_results_list(e) {
			console.log("getting results");
			var dynamicData = {};
			dynamicData['q'] = patient_search_box.val().trim();
			$.ajax({
				url  : "/fishfood/patients/search/",
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
			dynamicData['p_id'] = $(e.target).attr("data-id");
			$.ajax({
				url  : "/fishfood/patients/",
				type : "get",
				data : dynamicData,
				success : function(data) {
					$("#patientView").replaceWith(data).show();
					add_patient_view.hide();
				}
			});
		}
		patient_search_results.on("click", "li", load_patient_view);

		// click handler for add new patient button
		function load_add_patient_view(e){
			$("#patientView").hide();
			$("#addPatientView").fadeIn();
			$("#addReminderForm").hide();
		};
		add_patient_button.on("click", load_add_patient_view);

		// cancel handler for new patient form
		function cancel_new_patient_form(e) {
			$("#addReminderForm").hide();
			$("#addPatientView").hide();
			$("#patientView").fadeIn();
			$("#addPatientForm")[0].reset();
		}
		main_col.on("click", "#addPatientCancel", cancel_new_patient_form);

		// submit handler for new patient form
		function submit_new_patient_form(e) {
			e.preventDefault();
			form = $("#addPatientForm");
			$.ajax({
				url: "/fishfood/patients/new/",
				type: "post",
				data: form.serialize(),
				success: function(data) {
					$("#patientView").replaceWith(data).show();
					$("#addPatientView").hide();
					get_patient_search_results_list()
				}
			});
		}
		$("#addPatientForm").submit(submit_new_patient_form);

		// click handler for add reminder button
		function load_new_reminder_form(e) {
			$("#addReminderForm").fadeIn();
		}
		main_col.on("click", "#addReminderButton", load_new_reminder_form);

		// cancel button handler for new reminder form
		function cancel_new_reminder_form(e) {
			add_reminder_form = $("#addReminderForm");
			add_reminder_form[0].reset();
			add_reminder_form.hide();
		}
		main_col.on("click", "#addReminderCancel", cancel_new_reminder_form);

		// submit button handler for new reminder form
		function submit_new_reminder_form(e) {
			e.preventDefault();

			// send ajax post to create new reminder
			var okToSubmit = false;
			if ( $("input:checkbox:checked").length > 0 ) okToSubmit = true;
			if (okToSubmit) {
				form = $("#addReminderForm");
				p_id = $("#patientView").attr("data-id");
				data = "p_id=" + p_id + "&"
				$.ajax({
					url: "/fishfood/reminders/new/",
					type: "post",
					data: data + form.serialize(),
					success: function(data) {
						// reload main content view to reflect changes
						$.ajax({
							url: "/fishfood/patients/",
							type: "get",
							data: {'p_id': p_id},
							success: function(data) {
								$("#patientView").html(data);
							}
						});
					}	
				});
			}
		}
		main_col.on("click", "#addReminderSubmit", submit_new_reminder_form);
	});
}));