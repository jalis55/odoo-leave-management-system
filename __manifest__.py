{
    'name': 'Leave Management',
    'version': '1.0.0',
    'category': 'Human Resources',
    'summary': 'Enhanced leave request and allocation management',
    'description': """
        Leave Management
        =================
        - Custom Leave Types & Policies
        - Leave Request Workflows
        - Allocation Tracking
        - Reporting & Dashboards
    """,
    'author': 'Jalis Tarif',
    'website': 'https://example.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'hr',
        'mail',
    ],
    'data': [
        'security/leave_security.xml',
        'security/ir.model.access.csv',
        'views/leave_views.xml',
        'views/leave_request_view.xml',
        'views/leave_allocation_view.xml',
        'security/leave_record_rules.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
