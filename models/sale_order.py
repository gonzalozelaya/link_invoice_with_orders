import logging
from odoo import models, api, fields

_logger = logging.getLogger(__name__)
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

    suggested_subtotal = fields.Monetary(
        'SUBTOTAL SUGERIDO',
        compute='_compute_suggested_subtotal',
        currency_field='currency_id'
    )


    @api.depends('state', 'total_invoice_amount', 'amount_total')
    def _compute_invoice_status(self):
        _logger.warning("Entrando en _compute_invoice_status")
        for order in self:
            _logger.warning(f"Order {order.name} - state: {order.state}, total_invoice_amount: {order.total_invoice_amount}, amount_total: {order.amount_total}")
            if order.new_invoice_ids:
                _logger.warning(f"Order {order.name} tiene facturas vinculadas: {[inv.name for inv in order.new_invoice_ids]}")
                if order.state not in ('sale', 'done'):
                    _logger.warning("Estado no válido para facturación. Marcando como 'no'")
                    order.invoice_status = 'no'
                elif order.total_invoice_amount >= order.amount_total:
                    _logger.warning("Total facturado >= total orden. Marcando como 'invoiced'")
                    order.invoice_status = 'invoiced'
                elif order.total_invoice_amount > 0:
                    _logger.warning("Hay algo facturado pero falta. Marcando como 'to invoice'")
                    order.invoice_status = 'to invoice'
                else:
                    _logger.warning("Nada facturado. Marcando como 'no'")
                    order.invoice_status = 'no'
            else:
                _logger.warning(f"Order {order.name} no tiene facturas personalizadas. Usando compute original.")
                super(AccountMove, order)._compute_invoice_status()
    
    @api.depends('new_invoice_ids')
    def _compute_invoice_count_new(self):
        _logger.warning("Entrando en _compute_invoice_count_new")
        for order in self:
            count = len(order.new_invoice_ids)
            _logger.warning(f"Order {order.name} tiene {count} facturas vinculadas")
            order.invoice_count_new = count
                         
    @api.depends('new_invoice_ids', 'new_invoice_ids.amount_total', 'new_invoice_ids.move_type', 'new_invoice_ids.state')
    def _compute_total_invoice_amount(self):
        _logger.warning("Entrando en _compute_total_invoice_amount")
        for order in self:
            total = 0.0
            for invoice in order.new_invoice_ids.filtered(lambda inv: inv.state == 'posted'):
                _logger.warning(f"Factura {invoice.name} tipo {invoice.move_type} estado {invoice.state} total {invoice.amount_total}")
                if invoice.move_type == 'out_invoice':
                    total += invoice.amount_total
                elif invoice.move_type == 'out_refund':  # Notas de crédito
                    total -= invoice.amount_total
            _logger.warning(f"Total facturado para Order {order.name}: {total}")
            order.total_invoice_amount = total
            """
            order.total_invoice_amount = sum(
                invoice.amount_total 
                for invoice in order.new_invoice_ids 
                if invoice.state == 'posted'  # Solo facturas validadas
            )
            """
    @api.depends('amount_total', 'amount_untaxed', 'amount_tax', 'total_invoice_amount', 'currency_id')
    def _compute_suggested_subtotal(self):
        _logger.warning("Entrando en _compute_suggested_subtotal")
        for order in self:
            pending_total = order.amount_total - order.total_invoice_amount
            _logger.warning(f"Order {order.name} - Pendiente a facturar: {pending_total}")
            
            if pending_total <= 0:
                _logger.warning("Nada pendiente. Subtotal sugerido: 0.0")
                order.suggested_subtotal = 0.0
                continue
            
            tax_ratio = order.amount_tax / order.amount_untaxed if order.amount_untaxed != 0 else 0
            base_subtotal = pending_total / (1 + tax_ratio) if tax_ratio != 0 else pending_total

            if order.currency_id != order.company_id.currency_id:
                base_subtotal = order.currency_id._convert(
                    base_subtotal,
                    order.company_id.currency_id,
                    order.company_id,
                    order.date_order or fields.Date.today()
                )
            _logger.warning(f"Subtotal sugerido para {order.name}: {base_subtotal}")
            order.suggested_subtotal = base_subtotal

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

    




