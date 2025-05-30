from odoo import models, api, fields, api
import logging

_logger = logging.getLogger(__name__)
class AccountMove(models.Model):
    _inherit = 'account.move'

    new_order_count = fields.Integer('Cuenta de ordenes')

    @api.model
    def create(self, vals):
        # Primero creamos el registro
        move = super(AccountMove, self).create(vals)
        # Luego actualizamos las órdenes relacionadas
        if move.invoice_origin and move.move_type in ('out_invoice', 'out_refund'):
            move._update_related_orders()
        return move

    def _update_related_orders(self):
        for move in self:
            if not move.invoice_origin:
                continue
                
            _logger.info(f'Actualizando órdenes para factura {move.name}')
            
            # Extraer nombres de órdenes
            order_names = [name.strip() for name in move.invoice_origin.split(',')]
            
            # Buscar órdenes relacionadas
            orders = self.env['sale.order'].search([
                ('name', 'in', order_names),
                ('company_id', '=', move.company_id.id),
            ])
            
            # Actualizar conteo en la factura
            move.new_order_count = len(orders)
            
            # Actualizar las órdenes (si existen campos personalizados)
            if hasattr(orders, 'invoice_count_new'):
                for order in orders:
                    order.write({
                        'new_invoice_ids': [(4, move.id)],
                    })

    
    def action_view_source_sale_orders_from_invoice_origin(self):
        self.ensure_one()
        
        if not self.invoice_origin:
            return {'type': 'ir.actions.act_window_close'}
        
        # Extraer los números de orden de venta del campo invoice_origin
        order_names = [name.strip() for name in self.invoice_origin.split(',')]
        
        # Buscar las órdenes de venta correspondientes
        sale_orders = self.env['sale.order'].search([('name', 'in', order_names)])
        
        # Preparar la acción de ventana
        result = self.env['ir.actions.act_window']._for_xml_id('sale.action_orders')
        
        if len(sale_orders) > 1:
            result['domain'] = [('id', 'in', sale_orders.ids)]
        elif len(sale_orders) == 1:
            result['views'] = [(self.env.ref('sale.view_order_form', False).id, 'form')]
            result['res_id'] = sale_orders.id
        else:
            result = {'type': 'ir.actions.act_window_close'}
        
        return result

    