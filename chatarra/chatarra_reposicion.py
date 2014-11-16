# -*- encoding: utf-8 -*-
from openerp.osv import osv, fields
from openerp import tools
import time
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, float_compare
import logging
_logger = logging.getLogger(__name__)

class chatarra_unit_reposicion(osv.osv):
    _name = 'chatarra.reposicion'
    _description = 'No. de Reposicion'
    _columns = {
        'name'               : fields.char('No. de Reposicion', size=64, readonly=True),
        'unidad_anterior_id' : fields.many2one('chatarra.unit','Unidad anterior:', readonly=True),
        'unidad_nueva_id'    : fields.many2one('chatarra.unit','Unidad nueva:', required=True),
        'date'               : fields.date('Fecha de reposicion', readonly=True),
        'motivo'             : fields.many2one('chatarra.motivo', 'Motivo', required=True),
    }
    _defaults = {
        'date': lambda *a: time.strftime('%Y-%m-%d'),
    }

    def action_reposicion(self, cr, uid, ids, vals, context=None):
        unidad_obj = self.pool.get('chatarra.unit')
        invoice_obj = self.pool.get('account.invoice')
        asignacion_obj = self.pool.get('chatarra.asignacion')
        prod_obj = self.pool.get('product.product')
        prod_id = prod_obj.search(cr, uid, [('chatarra', '=', 1),('active','=', 1)], limit=1)
        product = prod_obj.browse(cr, uid, prod_id, context=None)
        reposicion = self.browse(cr, uid, ids)
        nueva = reposicion.unidad_nueva_id
        anterior = reposicion.unidad_anterior_id
        invoice_anterior_id = invoice_obj.search(cr, uid, [('unit_id','=',anterior.id)])
        invoice_anterior = invoice_obj.browse(cr, uid, invoice_anterior_id, context=None)
        #_logger.error("##################### asignacion : %r", anterior.asignacion_id.id)
        invoice_obj.create(cr, uid, {'partner_id':anterior.asignacion_id.client_id.id,
                                     'contacto_id':anterior.asignacion_id.contacto_id.id,
                                     'agencia_id':anterior.asignacion_id.agencia_id.id,
                                     'asignacion_id':anterior.asignacion_id.id,
                                     'unit_id':nueva.id,
                                     'account_id':anterior.asignacion_id.client_id.property_account_receivable.id,
                                     'origin':(anterior.asignacion_id.name, reposicion.name),
                                     'fiscal_position':anterior.asignacion_id.client_id.property_account_position.id,
                                     'invoice_line':[(0,0,{'product_id':product.id,
                                                           'name':product.description_sale,
                                                           'account_id':product.property_account_income.id,
                                                           'quantity':'1',
                                                           'price_unit':product.lst_price,
                                                           'invoice_line_tax_id':[(6,0,[product.taxes_id.id])],
                                                          })]
                                    }, context=None)
        invoice_nueva_id = invoice_obj.search(cr, uid, [('unit_id','=',nueva.id)])
        invoice_nueva = invoice_obj.browse(cr, uid, invoice_nueva_id, context=None)
        unidad_obj.write(cr, uid, [nueva.id], {'sustituye_id':anterior.id,
                                               'reposicion_id':reposicion.id,
                                               'state':'asignada',
                                               'asignacion_id':anterior.asignacion_id.id,
                                               'facturado':True,
                                               'facturado_por':uid,
                                               'factura_id':invoice_nueva.id,
                                               'fecha_facturado':time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)})
        if anterior.state in ['asignada','completo','seleccion','enviado','elaboracion']:
          unidad_obj.write(cr, uid, [anterior.id], {'repuesta_id':nueva.id,
                                                  'state':'reposicion',
                                                  'reposicion_id':reposicion.id,
                                                  'reposicion_por':uid,
                                                  'fact_cancelada_por':uid,
                                                  'fecha_fact_cancelada':time.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                                                  'fecha_reposicion':time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)})
        else:
          unidad_obj.write(cr, uid, [anterior.id], {'repuesta_id':nueva.id,
                                                  'state':'desestimiento',
                                                  'reposicion_id':reposicion.id,
                                                  'reposicion_por':uid,
                                                  'fact_cancelada_por':uid,
                                                  'fecha_fact_cancelada':time.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                                                  'fecha_reposicion':time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)})
        invoice_obj.write(cr, uid, [invoice_anterior.id], {'state':'cancel'})
        asignacion_obj.write(cr, uid, anterior.asignacion_id.id, {'unit_ids': [(4, nueva.id),(3, anterior.id)]})
        return True

    def create(self, cr, uid, vals, context={}):
        if (not 'name' in vals) or (vals['name'] == False):
            vals['name'] = self.pool.get('ir.sequence').get(cr, uid, 'reposicion.sequence.number')
        return super(chatarra_unit_reposicion, self).create(cr, uid, vals, context)