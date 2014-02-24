# Takes a text file made from copying and pasting text of
# the ACO list at http://www.cms.gov/Medicare/Medicare-Fee-for-Service-Payment/sharedsavingsprogram/Downloads/2014-ACO-Contacts-Directory.pdf
# and converts that text file to a CSV with the following headers
# ACO Name, Service Area, POC1 Name, POC1 Title, POC1 Phone, POC1 Email, POC2 Name, POC2 Title, POC2 Phone, POC2 Email

# Preprocess the file by removing the new page headers and page number information
original_list = open('./medicare_aco_list', 'r')
post_proc_list = open('./processed_medicare_aco_list', 'w')
for line in original_list:
   if line.startswith("Medicare Shared Savings Program Accountable Care Organizations Start Date: January 1, 2014"):
	   print "Skipping format"
	   pass
   elif line.startswith("Page") and line.endswith("of 41\n"):
	   print "Skipping page"
	   pass
   else:
	   post_proc_list.write(line)
original_list.close()
post_proc_list.close()

# Create the .csv header
csv_headers = "ACO Name, Service Area, POC1 Name, POC1 Title, POC1 Phone, POC1 Email, POC2 Name, POC2 Title, POC2 Phone, POC2 Email\n"
aco_name, service_area, POC1_name, POC1_title, POC1_contact_line, POC2_name, POC2_title, POC2_contact_line = range(8)
csv_format = open('./medicare_aco_list.csv', 'w')
csv_format.write(csv_headers)
post_proc_list = open('./processed_medicare_aco_list', 'r')
i = 0
for line in post_proc_list:
	if i == aco_name:
		csv_format.write(line.replace(",", ";").rstrip('\n') + ",")
	elif i == service_area:
		csv_format.write(line.lstrip("Service Area: ").replace(",", ";").rstrip('\n') + ",")
	elif i == POC1_name or i == POC2_name:
		csv_format.write(line.replace(",", ";").rstrip('\n') + ",")
	elif i == POC1_title or i == POC2_title:
		csv_format.write(line.replace(",", ";").rstrip('\n') + ",")
	elif i == POC1_contact_line or POC2_contact_line:
		csv_format.write(line[0:14] + ",")
		csv_format.write(line[15:].rstrip('\n') + ",")
	if i == POC2_contact_line:
		csv_format.write('\n')
		i = 0
	else:
		i += 1

post_proc_list.close()
csv_format.close()





# Parse the information in the file

