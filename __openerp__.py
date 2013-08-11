# -*- coding: utf-8 -*-
{
    'name': 'OpenERP git Integration',
    'version': '1.0',
    'category': '',
    "sequence": 14,
    'complexity': "easy",
    'category': 'Hidden',
    'description': """
        OpenERP Git integration
    """,
    'author': 'Ruchir Shukla',
    'website': 'www.bizzappdev.com',
    'depends': ["project"],
    'data': [
        'project_view.xml',
        'git_commit_view.xml',
        'git_setting_view.xml',
        'project_sequence.xml',
    ],
    'external_dependencies': {
        'python': ['git'],
    },
    'installable': True,
    'auto_install': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
