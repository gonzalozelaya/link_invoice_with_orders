from odoo import models, api, fields

class AccountMove(models.Model):
    _inherit = 'sale.order'

    invoice_count_new = fields.Integer('Nuevos invoices',compute='_compute_invoice_count_new', store=True)
    new_invoice_ids = fields.Many2many(
        'account.move',
        string='Facturas Vinculadas',
        relation='sale_order_new_invoice_rel',
        column1='order_id',
        column2='move_id'
    )
    total_invoice_amount = fields.Float('Total facturas',compute='_compute_total_invoice_amount')

    @api.depends('new_invoice_ids')
    def _compute_invoice_count_new(self):
        for order in self:
            count = len(order.new_invoice_ids)
            order.invoice_count_new = count
                         
    @api.depends('new_invoice_ids', 'new_invoice_ids.amount_total')
    def _compute_total_invoice_amount(self):
        for order in self:
            order.total_invoice_amount = sum(
                invoice.amount_total 
                for invoice in order.new_invoice_ids 
                if invoice.state == 'posted'  # Solo facturas validadas
            )

    def action_view_custom_invoices(self):
        """Acción para ver las facturas personalizadas vinculadas a la orden"""
        self.ensure_one()
        
        # Obtener las facturas vinculadas
        invoices = self.new_invoice_ids
        
        # Preparar la acción base
        action = self.env['ir.actions.actions']._for_xml_id('account.action_move_out_invoice_type')
        
        # Configurar la vista según el número de facturas
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.ids)]
        elif len(invoices) == 1:
            form_view = [(self.env.ref('account.view_move_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = invoices.id
        else:
            action = {'type': 'ir.actions.act_window_close'}
        
        # Configurar el contexto
        context = {
            'default_move_type': 'out_invoice',
            'create': False,
            'edit': False,
        }
        
        # Añadir información de la orden si hay una sola
        if len(self) == 1:
            context.update({
                'default_partner_id': self.partner_id.id,
                'default_partner_shipping_id': self.partner_shipping_id.id,
                'default_invoice_payment_term_id': self.payment_term_id.id or 
                                                 self.partner_id.property_payment_term_id.id or 
                                                 self.env['account.move'].default_get(['invoice_payment_term_id']).get('invoice_payment_term_id'),
                'default_invoice_origin': self.name,
            })
        
        action['context'] = context
        return action