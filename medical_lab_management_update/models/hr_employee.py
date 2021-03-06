# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import timedelta, datetime, date
from odoo.osv import expression


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    appointments_count = fields.Char(string="Appointments")

    # Medical information of employee
    rhesus_factor = fields.Selection([
        ('rh_plus', 'Rh+'),
        ('rh_minus', 'Rh-')
    ], string="Rhesus factor")
    allergy = fields.Char(string="Allergic reactions", compute="_compute_info")
    phys_condition = fields.Char(string="Physiological condition", help="Physiological condition of the patient")
    pathologies = fields.Char(strong="Hereditary pathologies")
    bad_habits = fields.Char(sring="Bad habits")
    blood_group = fields.Selection(
        [('A+', 'A+ve'), ('B+', 'B+ve'), ('O+', 'O+ve'), ('AB+', 'AB+ve'),
         ('A-', 'A-ve'), ('B-', 'B-ve'), ('O-', 'O-ve'), ('AB-', 'AB-ve')],
        'Blood Group')
    preventive_actions = fields.Char(string="Preventive actions", help="Vaccinations")
    chronic_diseases = fields.Char(string="Chronic diseases")
    contraindications = fields.Char(string="Contraindications",
                                    help="Specific situation in which a drug, procedure, or surgery should not be used because it may be harmful to the person.")
    operating_pressure = fields.Char(string="Normal blood pressure", help="Blood pressure of employee")
    blood_donor = fields.Boolean(string='Blood donor')
    work_condition = fields.Boolean(string='Hazardous working conditions')
    is_patient = fields.Boolean(string='Is Patient', default=True)
    patient_id = fields.One2many('lab.patient', 'patient', string="Lab Patient")

    height = fields.Char(string="Height")
    weight = fields.Char(string="Weight")

    # def patient_view(self):
    #     """ Function to open medical card of employee from button
    #     """
    #     lab_ids = []
    #     for each in self:
    #         lab_ids.append(each.id)
    #     view_id = self.env.ref('medical_lab_management.view_lab_patient_form').id
    #     if lab_ids:
    #         value = {
    #             'view_mode': 'form',
    #             'res_model': 'lab.patient',
    #             'view_id': view_id,
    #             'type': 'ir.actions.act_window',
    #             'name': _('Medical Card'),
    #             'res_id': lab_ids and lab_ids[0]
    #         }
    #
    #         return value

    def appointment_view(self):
        for each1 in self:
            lab_patient = self.env['lab.patient'].search([('patient', '=', each1.id)])
            appointment_obj = self.env['lab.appointment'].search([('patient_id', '=', lab_patient.id)])
            appointment_ids = []
            for each in appointment_obj:
                appointment_ids.append(each.id)
            view_id = self.env.ref('medical_lab_management.view_lab_appointment_form').id
            if appointment_ids:
                if len(appointment_ids) <= 1:
                    value = {
                        'view_mode': 'form',
                        'res_model': 'lab.appointment',
                        'view_id': view_id,
                        'type': 'ir.actions.act_window',
                        'name': _('Custody'),
                        'res_id': appointment_ids and appointment_ids[0]
                    }
                else:
                    value = {
                        'domain': str([('id', 'in', appointment_ids)]),
                        'view_mode': 'tree,form',
                        'res_model': 'lab.appointment',
                        'view_id': False,
                        'type': 'ir.actions.act_window',
                        'name': _('Appointments'),
                        'res_id': appointment_ids
                    }

                return value

    @api.depends('address_home_id')
    def _compute_info(self):
        """ Function to get info from medical card to employee passprort
        """
        for emp in self:
            patient = self.env['lab.patient'].search([('patient', '=', emp.id)])
            emp.allergy = ''
            if patient:
                emp.bad_habits = patient.bad_habits
                emp.blood_group = patient.blood_group
                emp.blood_donor = patient.blood_donor
                emp.work_condition = patient.work_condition
                emp.allergy = patient.allergy
                emp.rhesus_factor = patient.rhesus_factor
                emp.phys_condition = patient.phys_condition
                emp.pathologies = patient.pathologies
                emp.preventive_actions = patient.preventive_actions
                emp.chronic_diseases = patient.chronic_diseases
                emp.contraindications = patient.contraindications
                emp.operating_pressure = patient.operating_pressure
                emp.height = patient.height
                emp.weight = patient.weight

    # @api.model
    # def get_dept_employee(self):
    #     examination = self.env['lab.medical.examination'].search([])
    #     data = []
    #     for exam in examination:
    #         if exam.examination_date and exam.examination_date.date() == datetime.now().date():
    #             data.append({
    #                 'label': exam.patient.name,
    #                 'value': exam.permission.capitalize() if exam.permission else 'TBA'
    #             })
    #     return data

    @api.model
    def create_medical_appointment(self):
        """ Function for automated appointment creation from cron
        """
        app_spec = self.env["lab.appointment.specification"].search([])[0]
        app_date_start = app_spec.daily_app_time_from
        duration = app_spec.daily_app_time_to - app_date_start

        tomorrow = datetime.combine(date.today(), datetime.min.time()) + timedelta(days=1) + timedelta(hours=app_date_start) - timedelta(hours=6)
        # Search for all employees which are patients
        employees = self.env["hr.employee"].search([('is_patient', '=', True)])
        # Search for patients cards from employees list
        lab_patient = self.env["lab.patient"].search([('patient', 'in', employees.ids)])
        # Search lab tests which is set as daily
        lab_test = self.env["lab.test"].search([('type_of_appointment', '=', 'daily')])
        if lab_patient:
            for pat in lab_patient:
                # Search if patient have leaves for tomorrow
                employee_leaves = self.env['hr.leave'].search([('employee_id', '=', pat.patient.id),
                                                               ('state', '=', 'validate'),
                                                               ('date_from', '<=', 'tomorrow'),
                                                               ('date_to', '>=', 'tomorrow')])
                # Search if patient have regularization request
                employee_request = self.env['attendance.regular'].search([('employee_id', '=', pat.patient.id),
                                                                          ('state_select', '=', 'approved'),
                                                                          ('from_date', '<=', 'tomorrow'),
                                                                          ('to_date', '>=', 'tomorrow')])
                # Check before creation of appointment.
                if pat.work_condition and not employee_leaves and not employee_request:
                    new_app = self.env["lab.appointment"].sudo().create(
                        {  # Creating and storing new appointment if variable to further use
                            'patient_id': pat.id,
                            'physician_id': app_spec.physician_id.id,
                            'appointment_date': tomorrow,
                            'duration': duration,
                            'type_of_appointment': 'daily',
                        })
                    if lab_test:
                        for lab in lab_test:
                            new_lab_test = self.env["lab.appointment.lines"].sudo().create({
                                'lab_test': lab.id,
                                'test_line_appointment': new_app.id,  # Create link to appointment
                                'cost': lab.test_cost
                            })
