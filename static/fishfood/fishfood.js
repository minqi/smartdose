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
		var patient_search_box = $("#patientSearchBox");
		var patient_search_results = $("#patientSearchResults");
		var add_patient_button = $("#addPatientButton");
		var main_col = $("#mainCol")
		var main_content_view = $("#mainContentView");
		var patient_view = $("#patientView");
		var add_patient_view = $("#addPatientView");
		var add_reminder_form = $("#add-reminder-form");
		var add_reminder_button = $("#add-reminder-button");

		// ===define and bind event-handlers===================================

		// sparkline loader functions, called when loading patient profile
		// loads data from server to populate adherence sparklines

		var load_adherence_sparklines = 
		function() {
			var width = 250;
			var height = 100;
			var x = d3.scale.linear().range([0, width-4]);
			var y = d3.scale.linear().range([height, 0]);
			var parseDate = d3.time.format("%e-%b-%y").parse;
			var line = d3.svg.line()
			             .interpolate("basis")
			             .x(function(d) { return x(d.date); })
			             .y(function(d) { return y(d.adherence_rate); });
			function sparkline(elemId, data) {
			  data.forEach(function(d) {
			    d.date = parseDate(d.date);
			    d.adherence_rate = +d.adherence_rate;
			  });
			  x.domain(d3.extent(data, function(d) { return d.date; }));
			  y.domain([0, 1]);
			  // y.domain(d3.extent(data, function(d) { return d.adherence_rate; }));

			 var svg = d3.select(elemId)
			              .append('svg')
			              .attr('width', width)
			              .attr('height', height)
			              .append('g')
			              .attr('transform', 'translate(0, 0)');
			  svg.append('line')
			  	 .attr('class', 'sparkthreshold')
			  	 .attr('x1', x(data[0].date))
			  	 .attr('y1', y(.5))
			  	 .attr('x2', x(data[data.length-1].date))
			  	 .attr('y2', y(.5))
			  svg.append('path')
			     .datum(data)
			     .attr('class', 'sparkline')
			     .attr('d', line)
			     .style('stroke-width', 1.5)
			     .style('stroke', '#777');
			  svg.append('circle')
			     .attr('class', 'sparkcircle')
			     .attr('cx', x(data[data.length-1].date))
			     .attr('cy', y(data[data.length-1].adherence_rate))
			     .attr('r', 2); 
			}

			return function (e) {
				// retrieve adherence time-series
				var dynamicData = {};
				dynamicData['p_id'] = $("#patientView").attr("data-id");
				$.ajax({
					url  : "/fishfood/patients/adherence_history_csv/",
					type : "get",
					data : dynamicData,
					success : function(data) {
						parsedData = d3.csv.parse(data);
						console.log(parsedData)
						sparkline('#spark-vod', parsedData);
					}
				});
			}
		}();

		// keystroke handler for patient search-box 
		// instant search
		function get_patient_search_results_list(e) {
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
					load_adherence_sparklines();
				}
			});
		}
		patient_search_results.on("click", "li", load_patient_view);

		// click handler for add new patient button
		function load_add_patient_view(e){
			$("#patientView").hide();
			$("#addPatientView").fadeIn();
			$("#add-reminder-form").hide();
		};
		add_patient_button.on("click", load_add_patient_view);

		// cancel handler for new patient form
		function cancel_new_patient_form(e) {
			$("#add-reminder-form").hide();
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
			$("#add-reminder-form").fadeIn();
			$("#add-reminder-button").hide();
		}
		main_col.on("click", "#add-reminder-button", load_new_reminder_form);

		// cancel button handler for new reminder form
		function cancel_new_reminder_form(e) {
			add_reminder_form = $("#add-reminder-form");
			add_reminder_form[0].reset();
			add_reminder_form.hide();
			$("#add-reminder-button").show();
			$(".day-label").removeClass("selectedDay");
			$(".inner-check").removeClass("selected-inner-check");
		}
		main_col.on("click", "#addReminderCancel", cancel_new_reminder_form);

		// highlight selected days in add reminder form
		function highlight_selected_day(e) {
			$(e.target).toggleClass("selectedDay");
		}
		main_col.on("click", ".day-label", highlight_selected_day);

		// highlight selected reminder options in add reminder form
		function highlight_selected_reminder_option(e) {
			var target = $(e.target).toggleClass("selected-inner-check");
		}
		// main_col.on("click", ".outer-check", highlight_selected_reminder_option);
		main_col.on("click", ".inner-check", highlight_selected_reminder_option);

		// submit button handler for new reminder form
		function submit_new_reminder_form(e) {
			e.preventDefault();

			// send ajax post to create new reminder
			var okToSubmit = false;
			if ( $("input:checkbox:checked").length > 0 ) okToSubmit = true;
			if (okToSubmit) {
				form = $("#add-reminder-form");
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
								load_adherence_sparklines();
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