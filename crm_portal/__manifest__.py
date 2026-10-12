{
    'name': 'CRM Portal',
    'version': '19.0.1.0.0',
    'category': 'Sales/CRM',
    'summary': 'CRM portal for portal users',
    'description': """
        CRM Portal for Odoo portal users.

        Provides:
        - CRM dashboard
        - Leads
        - Opportunities
        - CRM activities
    """,
    'depends': [
        'crm',
        'portal',
        'website',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/crm_portal_security.xml',
        'views/portal_templates.xml',
        'views/lead_templates.xml',
        'views/oppertunity_templates.xml',
        'views/activity_templates.xml',
        'views/portal_home.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'crm_portal/static/src/css/crm_portal.css',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
