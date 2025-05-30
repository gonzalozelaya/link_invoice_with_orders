# -*- coding: utf-8 -*-
{
    'name': "Linkear orden de venta con factura",

    'summary': "Linkear orden de venta con factura",
    
    'description': """
    Este módulo permite vincular una orden de venta con una factura en Odoo.
    """,

    'author': "OutsourceArg",
    'website': "https://www.outsourcearg.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Accounting',
    'version': '1.0',

    # any module necessary for this one to work correctly
    'depends': ['account','sale'],
    'data':[
        'views/account_move.xml',
    ],
    # only loaded in demonstration mode
    'installable':True,
    'application':False,
}