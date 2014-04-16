	(function(env) { 
	
	// pass the jQuery object as parameter
	env(window.jQuery, window, document);

}(function($, window, document) {
// listen for 
	$(function() {
		// DOM is ready
		var DEBUG = false;
		if (DEBUG) {
			$(document).click(function(e){console.log(e.target);});
		}

		// cache DOM elements of interest in local vars
		var patient_search_box = $("#patientSearchBox");
		var patient_search_results = $("#patientSearchResults");
		var add_patient_button = $("#addPatientButton");
		var main_col = $("#mainCol");
		var main_content_view = $("#mainContentView");
		var patient_view = $("#patientView");
		var add_patient_view = $("#addPatientView");
		var add_reminder_form = $("#add-reminder-form");
		var add_reminder_button = $("#add-reminder-button");
		var left_col = $("#leftCol");

		// main header states
		var main_header_text_handlers = function() {
			var main_header_text = $("#main-header").text();
			var main_header_text_prev = main_header_text;

			var update_main_header_text = function(new_text) {
				main_header_text_prev = main_header_text;
				main_header_text = new_text;
				$("#main-header").text(main_header_text);
			}; 

			var revert_main_header_text = function() {
				main_header_text = main_header_text_prev;
				$("#main-header").text(main_header_text);
			};

			return [update_main_header_text, revert_main_header_text];
		}();
		var update_main_header_text = main_header_text_handlers[0];
		var revert_main_header_text = main_header_text_handlers[1];

		// ===define and bind event-handlers===================================
		// window resize
		function window_resize_handler() {
			var window_height = $(window).height();
			var window_width = $(window).width();

			// fit left menu
			var left_menu = $("#leftMenu");
			var new_height = 
				window_height - 
				$("#left-menu-footer").height() - 
				left_menu.offset().top;
			left_menu.height(new_height);

			// fit main container
			var main_container = $("#main-container");
			var new_width = 
				window_width -
				$("#leftCol").width();
			main_container.width(new_width);

			var main_view = $("#main-view");
			$("#main-view").css("min-height", window_height - 10);
		}
		window_resize_handler();
		$(window).on("resize", window_resize_handler);

		// sparkline loader functions, called when loading patient profile
		// loads data from server to populate adherence sparklines
		var load_adherence_sparklines = 
		function() {
			var width = 300;
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

			 var svg = d3.selectAll(elemId)
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
			  	 .attr('y2', y(.5));
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
						sparkline('.adherence-sparkline', parsedData);
					}
				});
			};
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
					update_main_header_text("Medication record");
				}
			});
		}
		patient_search_results.on("click", "li", load_patient_view);


		// click handler for add new patient button
		function load_add_patient_view(e){
			$("#mainContentView").children().hide();
			$("#addPatientView").fadeIn();
			$("addPatientButton").fadeIn();
			update_main_header_text("Add a patient");
		}
		add_patient_button.on("click", load_add_patient_view);


		// cancel handler for new patient form
		function cancel_new_patient_form(e) {
			$("#add-reminder-form").hide();
			$("#add-caregiver-form").hide();
			$("#addPatientView").hide();
			$("#patientView").fadeIn();
			$("#addPatientForm")[0].reset();
			revert_main_header_text();
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
					$("#patient-view-reminders-section").show();
					get_patient_search_results_list();
				}
			});
		}
		$("#mainContentView").on("submit", "#addPatientForm", submit_new_patient_form);


		// delete button handler for new patient form
		function delete_patient_button_clicked(e) {
			$(e.target).hide();
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
				data = "p_id=" + p_id + "&";
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


		// delete reminder handler
		function delete_reminder_confirm(e) {
			csrfmiddlewaretoken = $("input[name='csrfmiddlewaretoken']")[0].value; 
			var dynamicData = {'csrfmiddlewaretoken':csrfmiddlewaretoken};
			dynamicData['p_id'] = $("#patientView").attr("data-id");
			// need to get the drug name + time
			var target = $(e.target);
			var prescriptionsListItem = target.parents(".prescriptionsListItem");
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


		function show_reminders_list_item_hover_items(e) {
			var listItem = $(e.target).closest(".remindersListItem"); 
			listItem.find(".deleteReminderButton").show();
			listItem.css("background", "#f1f3fa");
		}
		main_col.on("mouseenter", ".remindersListItem", show_reminders_list_item_hover_items);
		function hide_reminders_list_item_hover_items(e) {
			var listItem = $(e.target).closest(".remindersListItem"); 
			listItem.find(".deleteReminderButton").hide();
			listItem.css("background", "#fff");
		}
		main_col.on("mouseleave", ".remindersListItem", hide_reminders_list_item_hover_items);


		// click handler for add reminder button
		function load_new_caregiver_form(e) {
			$("#add-caregiver-button").hide();
			$("#add-caregiver-form").fadeIn();
		}
		main_col.on("click", "#add-caregiver-button", load_new_caregiver_form);


		// cancel button handler for new reminder form
		function cancel_new_caregiver_form(e) {
			add_caregiver_form = $("#add-caregiver-form");
			add_caregiver_form[0].reset();
			add_caregiver_form.hide();
			$("#add-caregiver-button").show();
		}
		main_col.on("click", "#add-caregiver-cancel", cancel_new_caregiver_form);


		// submit handler for new patient form
		function submit_new_caregiver_form(e) {
			e.preventDefault();
			form = $("#add-caregiver-form");
			p_id = $("#patientView").attr("data-id");
			data = "p_id=" + p_id + "&";
			$.ajax({
				url: "/fishfood/patients/create_safety_net_contact/",
				type: "post",
				data: data + form.serialize(),
				success: function(data) {
					$.ajax({
						url: "/fishfood/patients/caregivers/",
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
		main_col.on("submit", "#add-caregiver-form", submit_new_caregiver_form);


		// delete caregiver handler
		function delete_caregiver_confirm(e) {
			csrfmiddlewaretoken = $("input[name='csrfmiddlewaretoken']")[0].value; 
			var dynamicData = {'csrfmiddlewaretoken':csrfmiddlewaretoken};
			dynamicData['p_id'] = $("#patientView").attr("data-id");

			var target = $(e.target);
			var caregiversListItem = target.parents(".caregivers-list-item");
			dynamicData['target_p_id'] = caregiversListItem.attr("data-id");
			$.ajax({
				url: "/fishfood/patients/delete_safety_net_contact/",
				type: "post",
				data: dynamicData,
				success: function(data) {
					caregiversListItem.fadeOut();
				}
			});
		}
		main_col.on("click", ".delete-caregiver-button", delete_caregiver_confirm);


		function show_caregivers_list_item_hover_items(e) {
			var listItem = $(e.target).closest(".caregivers-list-item"); 
			listItem.find(".delete-caregiver-button").show();
			listItem.css("background", "#f1f3fa");
		}
		main_col.on("mouseenter", ".caregivers-list-item", show_caregivers_list_item_hover_items);
		function hide_caregivers_list_item_hover_items(e) {
			var listItem = $(e.target).closest(".caregivers-list-item"); 
			listItem.find(".delete-caregiver-button").hide();
			listItem.css("background", "#fff");
		}
		main_col.on("mouseleave", ".caregivers-list-item", hide_caregivers_list_item_hover_items);


		// control switching between various patient view sections
		function switch_patient_view_sections(e) {
			$(".patient-section").hide();
			$(".patient-view-nav-tab").removeClass("patient-view-nav-selected");
			var target = $(e.target);
			if (target.is("#patient-view-nav-medlist")) {
				$("#patient-view-reminders-section").show();
			}
			else if (target.is("#patient-view-nav-caregivers")) {
				$("#patient-view-caregivers-section").show();
			}
			target.addClass("patient-view-nav-selected");
		}
		main_col.on("click", ".patient-view-nav-tab", switch_patient_view_sections);


		// load dashboard button handler
		function load_dashboard_view(e){
			$.ajax({
				url  : "/fishfood/dashboard/",
				type : "get",
				success : function(data, request) {
					$("#mainContentView").html(data).show();
					$("#addPatientView").hide();
					update_main_header_text("Dashboard");
					load_med_response_histogram();
				}
			});
		};
		left_col.on("click", "#dashboard-button", load_dashboard_view);

		// poll for med histogram
		(function poll_for_med_histogram(){
			var data = [1, 2, 3, 4, 5, 6, 7];
			var data_labels = [
				"Haven't gotten the chance",
				"Need to refill",
				"Side effects",
				"Meds don't work", 
				"Prescription changed",
				"I feel sad",
				"Other",
			];
		   setTimeout(function(){
		      $.ajax({ 
		      		url: "/fishfood/patients/medication_response_counts/",
		      		type : "get", 
		      		success: function(data){
		      			var chart = d3.select("#med-responses-histogram").selectAll("g").remove();
		      			data = $.parseJSON(data);

						// set up histogram
						var width = 500,
						    barHeight = 35, 
						    offset = 150;

						var x = d3.scale.linear()
						    .domain([0, d3.max(data)])
						    .range([0, width - offset]);

						var chart = d3.select("#med-responses-histogram")
						    .attr("width", width)
						    .attr("height", barHeight * data.length);

						var bar = chart.selectAll("g")
						    .data(data)
						  	.enter().append("g")
						    .attr("transform", 
						    	function(d, i) { return "translate(" + offset + "," + i * barHeight + ")"; });

						bar.append("rect")
						    .attr("width", x)
						    .attr("height", barHeight - 1);

						bar.append("text")
						    .attr("x", function(d) { return -8; })
						    .attr("y", barHeight / 2)
						    .attr("dy", ".35em")
						    .text(function(d, i) { return data_labels[i]; });

						bar.append("text")
						    .attr("x", function(d) { return Math.max(x(d) - 5, 15); })
						    .attr("y", barHeight / 2)
						    .attr("dy", ".35em")
						    .attr("color", "white")
						    .text(function(d, i) { return d });

			        	poll_for_med_histogram();
				}});
		  }, 500);
		})();
	});
}));