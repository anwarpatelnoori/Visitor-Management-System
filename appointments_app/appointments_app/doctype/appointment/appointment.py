# Copyright (c) 2023, Build With Hussain and contributors
# For license information, please see license.txt

import frappe
import random
from frappe.model.document import Document
class Appointment(Document):
	def validate(self):
		# validate the contact_number to be a valid 10 digit phone number except the country code,
		# if it does not have a country code, prepend +91
		# if not self.contact_number:
		# 	frappe.throw("Please enter a valid contact number")
		# if len(self.contact_number) == 10:
		# 	self.contact_number = f"+91{self.contact_number}"
		# elif len(self.contact_number) == 13 and self.contact_number.startswith("+91"):
		# 	pass
		# else:
		# 	frappe.throw("Please enter a valid contact number")
		pass


	# def after_insert(self):
	# 	self.queue_number = self.add_to_appointment_queue()
	# 	# attach csrf token + queue number as key and queue number as value
	# 	frappe.cache.set_value(f"{frappe.session.sid}:queue_number", self.queue_number)
	# 	self.save(ignore_permissions=True)
	# 	self.send_confirmation_message()
	# 	self.submit()
	def after_insert(self):
    # ##Initial check to add to queue after insertion if already approved
		if self.workflow_state == "Approved":
			self.add_to_appointment_queue()

	def on_update(self):
    ### Check and add to queue on update if workflow_state is 'Approved'
		if self.workflow_state == "Approved" and not self.is_already_in_queue():
			self.otp = self.generate_otp()
			self.save(ignore_permissions =True)
			email_message = f'''<h2 style="font-family: Arial, sans-serif;">E-Pass Details</h2><table style="width: 100%; border-collapse: collapse;">
    <tr>
        <th style="border: 1px solid black; padding: 8px; text-align: left; background-color: #f2f2f2;">Detail</th>
        <th style="border: 1px solid black; padding: 8px; text-align: left; background-color: #f2f2f2;">Description</th>
    </tr>
	    <tr>
        <td style="border: 1px solid black; padding: 8px; text-align: left;">Guest Name</td>
        <td style="border: 1px solid black; padding: 8px; text-align: left;">{self.patient_name}</td>
    </tr>
	<tr>
        <td style="border: 1px solid black; padding: 8px; text-align: left;">Appointment</td>
        <td style="border: 1px solid black; padding: 8px; text-align: left;">Approved</td>
    </tr>
    <tr>
        <td style="border: 1px solid black; padding: 8px; text-align: left;">OTP</td>
        <td style="border: 1px solid black; padding: 8px; text-align: left;">{self.otp}</td>
    </tr>
    <tr>
        <td style="border: 1px solid black; padding: 8px; text-align: left;">WiFi</td>
        <td style="border: 1px solid black; padding: 8px; text-align: left;">Airtel Fibre</td>
    </tr>
    <tr>
        <td style="border: 1px solid black; padding: 8px; text-align: left;">Password</td>
        <td style="border: 1px solid black; padding: 8px; text-align: left;">0980889</td>
    </tr>
	<tr>
        <td style="border: 1px solid black; padding: 8px; text-align: left;">Reason</td>
        <td style="border: 1px solid black; padding: 8px; text-align: left;">{self.reasons_for_rejectionapproval}</td>
    </tr>
</table>'''
			# frappe.msgprint('Appointment is confirmed and the otp {self.otp} has been sent to')
			frappe.sendmail(recipients=[self.contact_number,self.meeting_host_email_id],sender='anwar@standardtouch.com',subject='E-Pass Status',message=email_message)
			self.add_to_appointment_queue()
		if self.workflow_state == 'Rejected':
			email_message = f'''<h2 style="font-family: Arial, sans-serif;">Appointment Rejected</h2><table style="width: 100%; border-collapse: collapse;">
    <tr>
        <th style="border: 1px solid black; padding: 8px; text-align: left; background-color: #f2f2f2;">Detail</th>
        <th style="border: 1px solid black; padding: 8px; text-align: left; background-color: #f2f2f2;">Description</th>
    </tr>
	<tr>
        <td style="border: 1px solid black; padding: 8px; text-align: left;">Guest Name</td>
        <td style="border: 1px solid black; padding: 8px; text-align: left;">{self.patient_name}</td>
    </tr>
    <tr>
        <td style="border: 1px solid black; padding: 8px; text-align: left;">Appointment Status</td>
        <td style="border: 1px solid black; padding: 8px; text-align: left;">Rejected</td>
    </tr>
    <tr>
        <td style="border: 1px solid black; padding: 8px; text-align: left;">Reason</td>
        <td style="border: 1px solid black; padding: 8px; text-align: left;">{self.reasons_for_rejectionapproval}</td>
    </tr>
</table>'''
			# frappe.msgprint('Appointment is confirmed and the otp {self.otp} has been sent to')
			frappe.sendmail(recipients=[self.contact_number,self.meeting_host_email_id],sender='anwar@standardtouch.com',subject='E-Pass Status',message=email_message)
			# frappe.msgprint('Your Appointment is not scheduled today. Host is not available')
	def is_already_in_queue(self):
    ##### Check if the appointment is already in the queue
		return frappe.db.exists("Appointment Queue", {"appointment": self.name})
		
	def add_to_appointment_queue(self):
		if self.workflow_state != 'Approved':
			return 0
		filters = {
			"date": self.date,
			"shift": self.shift,
			"clinic": self.clinic,
		}
		appointment_queue_exists = frappe.db.exists(
			"Appointment Queue",
			filters,
		)

		if appointment_queue_exists:
			q = frappe.get_doc("Appointment Queue", filters)
		else:
			q = frappe.new_doc("Appointment Queue")
			q.update(filters)
			q.save(ignore_permissions=True)

		q.append("queue", {"appointment": self.name, "status": "Pending"})
		q.save(ignore_permissions=True)

		return len(q.queue)

	def send_confirmation_message(self):
		shift_title = frappe.db.get_value("Schedule Shift", self.shift, "title")
		message = f"Hi {self.patient_name}, your appointment for {self.clinic} on {self.date} ({shift_title}) has been booked. Your queue number is {self.queue_number}."

		frappe.enqueue(
			"appointments_app.utils.send_message",
			body=message,
			from_=frappe.db.get_single_value(
				"Appointments Twilio Settings", "from_phone_number"
			),
			to=self.contact_number,
		)

	def generate_otp(self):
		return(random.randint(1000,9999))