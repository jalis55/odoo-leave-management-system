from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError


# ==========================================================================
# Leave Type
# ==========================================================================
class LeaveType(models.Model):
    _name = "leave.type"
    _description = "Leave Type"

    name = fields.Char(required=True)
    code = fields.Char()
    max_days = fields.Integer()
    requires_allocation = fields.Boolean()
    active = fields.Boolean(default=True)
    color = fields.Integer()


# ==========================================================================
# Leave Request
# ==========================================================================
class LeaveRequest(models.Model):
    _name = "leave.request"
    _description = "Leave Request"
    _inherit = ['mail.thread', 'mail.activity.mixin']


    name=fields.Char(compute="_compute_name",store=True)
    employee_id=fields.Many2one("hr.employee",string="Employee",required=True)
    leave_type_id=fields.Many2one("leave.type",string="Leave Type",compute="_compute_manager_id",store=True,required=True)
    manager_id=fields.Many2one("hr.employee",string="Manager",required=True)
    date_from=fields.Date(string="Date From",required=True)
    date_to=fields.Date(string="Date To",required=True)
    reason=fields.Text(string="Reason",required=True)
    number_of_days=fields.Integer(compute="_compute_number_of_days", store=True)
    available_balance = fields.Float(
        string='Available Balance',
        compute='_compute_available_balance',
        store=False
    )
    
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('confirm', 'To Approve'),
            ('approved', 'Approved'),
            ('refused', 'Refused'),
            ('cancelled', 'Cancelled'),
        ], string='Status', default='draft', tracking=True)

    leave_type_color = fields.Integer(
        related="leave_type_id.color",
        store=True,
    )

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        """Ensure the start date is not after the end date."""
        for record in self:
            if record.date_from > record.date_to:
                raise ValidationError("start date cannot be greater than end date")

    @api.constrains('date_from', 'date_to', 'employee_id', 'state')
    def _check_overlapping_leaves(self):
        """Prevent overlapping leave requests for the same employee."""
        for rec in self:
            # Only check when the leave is being confirmed or approved
            if rec.state not in ('confirm', 'approved'):
                continue

            if not rec.date_from or not rec.date_to or not rec.employee_id:
                continue

            # Search for other leaves of the same employee that overlap
            overlapping = self.search([
                ('id', '!=', rec.id),
                ('employee_id', '=', rec.employee_id.id),
                ('state', 'in', ['confirm', 'approved']),
                ('date_from', '<=', rec.date_to),
                ('date_to', '>=', rec.date_from),
            ], limit=1)

            if overlapping:
                raise ValidationError(
                    "You already have a leave request during this period.\n"
                    f"Existing leave: {overlapping.date_from} → {overlapping.date_to} "
                    f"({overlapping.leave_type_id.name})"
                )

    # ------------------------------------------------------------------
    # Compute Methods
    # ------------------------------------------------------------------
    @api.depends('employee_id', 'leave_type_id')
    def _compute_available_balance(self):
        for rec in self:
            if not rec.employee_id or not rec.leave_type_id:
                rec.available_balance = 0.0
                continue

            allocations = self.env['leave.allocation'].search([
                ('employee_id', '=', rec.employee_id.id),
                ('leave_type_id', '=', rec.leave_type_id.id),
                ('state', '=', 'approved'),
            ])
            total_allocated = sum(allocations.mapped('number_of_days'))

            taken_leaves = self.env['leave.request'].search([
                ('employee_id', '=', rec.employee_id.id),
                ('leave_type_id', '=', rec.leave_type_id.id),
                ('state', '=', 'approved'),
                ('id', '!=', rec.id),  # exclude current record
            ])
            total_taken = sum(taken_leaves.mapped('number_of_days'))

            # Available balance = allocated days minus already-approved usage
            rec.available_balance = total_allocated - total_taken

    @api.depends("employee_id")
    def _compute_manager_id(self):
        """Auto-fill the manager from the employee's hierarchy."""
        for record in self:
            record.manager_id = record.employee_id.parent_id.id if record.employee_id else False

    @api.depends("date_from", "date_to")
    def _compute_number_of_days(self):
        """Calculate the inclusive number of days between date_from and date_to."""
        for record in self:
            if record.date_from and record.date_to:
                total_days = (record.date_to - record.date_from).days + 1
                record.number_of_days = total_days
    

    @api.depends("employee_id", "leave_type_id", "date_from", "date_to")
    def _compute_name(self):
        """Build a human-readable display name for the leave request."""
        for record in self:
            if record.employee_id:
                record.name = f"{record.employee_id.name} - {record.leave_type_id.name} - {record.date_from} to {record.date_to}"
            else:
                record.name = ""


    def _check_manager_access(self):
        """Only the employee's manager or a user with high privilege can approve/refuse."""
        for rec in self:
            current_employee = self.env.user.employee_id

            # Allow system admin / HR managers (users with group_hr_manager)
            if self.env.user.has_group('hr.group_hr_manager'):
                continue

            # Check if current user is the manager of this employee
            if not current_employee or current_employee != rec.manager_id:
                raise UserError(
                    "Only the employee's manager can approve or refuse this leave request.\n"
                    f"Manager: {rec.manager_id.name or 'Not set'}"
                )

    # ------------------------------------------------------------------
    # Workflow Methods
    # ------------------------------------------------------------------
    def action_approve(self):
        """Approve the leave request after verifying manager access and balance."""
        self._check_manager_access()
        for record in self:
            if record.available_balance < record.number_of_days:
                raise ValidationError("You don't have enough leave balance.")
            record.state = 'approved'

    def action_refuse(self):
        """Refuse the leave request (manager access required)."""
        self._check_manager_access()
        for record in self:
            record.state = 'refused'

    def action_confirm(self):
        """Move the request to 'To Approve' after verifying sufficient balance."""
        for record in self:
            if record.number_of_days > record.available_balance:
                raise ValidationError("Insufficient leave balance")
            record.state = 'confirm'

    def action_cancel(self):
        """Cancel the leave request."""
        for record in self:
            record.state = 'cancelled'

    def action_draft(self):
        """Reset the leave request back to draft."""
        for record in self:
            record.state = 'draft'




# ==========================================================================
# Leave Allocation
# ==========================================================================
class LeaveAllocation(models.Model):
    _name = 'leave.allocation'
    _description = 'Leave Allocation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Allocation Name', required=True, tracking=True)
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        tracking=True,
    )
    leave_type_id = fields.Many2one(
        'leave.type',
        string='Leave Type',
        required=True,
        tracking=True,
    )
    number_of_days = fields.Integer(
        string='Number of Days',
        required=True,
        tracking=True,
    )
    date_from = fields.Date(string='Date From', tracking=True)
    date_to = fields.Date(string='Date To', tracking=True)
    notes = fields.Text(string='Notes')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'To Approve'),
        ('approved', 'Approved'),
        ('refused', 'Refused'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True, copy=False)

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_to < rec.date_from:
                raise ValidationError("Date To cannot be earlier than Date From.")

    @api.constrains('number_of_days')
    def _check_days(self):
        for rec in self:
            if rec.number_of_days <= 0:
                raise ValidationError("Number of Days must be greater than zero.")

    # ------------------------------------------------------------------
    # Workflow buttons
    # ------------------------------------------------------------------
    def action_confirm(self):
        self.write({'state': 'confirm'})

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_refuse(self):
        self.write({'state': 'refused'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_draft(self):
        self.write({'state': 'draft'})

