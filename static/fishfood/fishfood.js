(function(env) { 
	
	// pass the jQuery object as parameter
	env(window.jQuery, window, document);

}(function($, window, document) {
// listen for 
	$(function() {
		// DOM is ready
		var DEBUG = false;
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
				success : function(data, request) {
					$("#mainContentView").html(data).show();
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
					$("#mainContentView").html(data).show();
					$("#addPatientView").hide();
					get_patient_search_results_list()
				}
			});
		}
		$("#mainContentView").on("submit", "#addPatientForm", submit_new_patient_form);

		// delete button handler for new patient form
		function delete_patient_button_clicked(e) {
			$(e.target).hide();
			$(".deletePatientConfirm").fadeIn();
			$(".deletePatientConfirmYes").fadeIn();
			$(".deletePatientConfirmNo").fadeIn();
		}
		main_col.on("click", ".deletePatientButton", delete_patient_button_clicked);

		function delete_patient_cancel(e) {
			$(".deletePatientConfirm").hide();
			$(".deletePatientConfirmYes").hide();
			$(".deletePatientConfirmNo").hide();
			$(".deletePatientButton").fadeIn();
		}
		main_col.on("click", ".deletePatientConfirmNo", delete_patient_cancel);

		function delete_patient_confirm(e) {
			csrfmiddlewaretoken = $("input[name='csrfmiddlewaretoken']")[0].value; 
			var dynamicData = {'csrfmiddlewaretoken':csrfmiddlewaretoken};
			dynamicData['p_id'] = $("#patientView").attr("data-id");
			$.ajax({
				url: "/fishfood/patients/delete/",
				type: "post",
				data: dynamicData,
				success: function(data) {
					document.open();
					document.write(data);
					document.close();
				}
			});
		}
		main_col.on("click", ".deletePatientConfirmYes", delete_patient_confirm);

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
								$("#mainContentView").html(data);
							}
						});
					}	
				});
			}
		}
		main_col.on("click", "#addReminderSubmit", submit_new_reminder_form);

		function delete_reminder_confirm(e) {
			csrfmiddlewaretoken = $("input[name='csrfmiddlewaretoken']")[0].value; 
			var dynamicData = {'csrfmiddlewaretoken':csrfmiddlewaretoken};
			dynamicData['p_id'] = $("#patientView").attr("data-id");
			// need to get the drug name + time
			var target = $(e.target);
			var prescriptionsListItem = target.parents(".prescriptionsListItem")
			dynamicData['drug_name'] = 
				prescriptionsListItem.children(".prescriptionDrugName").text();
			dynamicData['reminder_time'] = target.siblings(".remindersListItemTime").text();
			$.ajax({
				url: "/fishfood/reminders/delete/",
				type: "post",
				data: dynamicData,
				success: function(data) {
					var remindersListItem = target.parents(".remindersListItem");
					remindersListItem.fadeOut();
					if (prescriptionsListItem.find(".remindersListItem").length == 1) {
						prescriptionsListItem.fadeOut();
					}
					remindersListItem.promise().done(function(){
						remindersListItem.remove();
						if (prescriptionsListItem.find(".remindersListItem").length == 0) {
							prescriptionsListItem.remove();
						}
					});
				}
			});
		}
		main_col.on("click", ".deleteReminderButton", delete_reminder_confirm);

	});
}));