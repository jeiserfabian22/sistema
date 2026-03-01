from django.contrib import admin

from django.contrib import admin
from software.models.stockModel import Stock
from software.models.transferenciaModel import Transferencia
from software.models.detalleTransferenciaModel import DetalleTransferencia
from software.models.movimientoCajaModel import MovimientoCaja
from software.models.ProformaModel import Proforma
from software.models.ProformaDetalleModel import ProformaDetalle

@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ('id_stock', 'id_almacen', 'get_producto', 'cantidad_disponible', 'estado')
    list_filter = ('id_almacen', 'estado')
    search_fields = ('id_vehiculo__idproducto__nomproducto', 'id_repuesto_comprado__id_repuesto__nombre')
    
    def get_producto(self, obj):
        if obj.id_vehiculo:
            return f"Vehículo: {obj.id_vehiculo.idproducto.nomproducto}"
        elif obj.id_repuesto_comprado:
            return f"Repuesto: {obj.id_repuesto_comprado.id_repuesto.nombre}"
        return "---"
    get_producto.short_description = 'Producto'

@admin.register(Transferencia)
class TransferenciaAdmin(admin.ModelAdmin):
    list_display = ('id_transferencia', 'id_almacen_origen', 'id_almacen_destino', 'fecha_transferencia', 'estado')
    list_filter = ('estado', 'fecha_transferencia')
    search_fields = ('numero_guia', 'observaciones')

@admin.register(DetalleTransferencia)
class DetalleTransferenciaAdmin(admin.ModelAdmin):
    list_display = ('id_detalle_transferencia', 'id_transferencia', 'get_producto', 'cantidad')
    
    def get_producto(self, obj):
        if obj.id_vehiculo:
            return f"Vehículo: {obj.id_vehiculo.idproducto.nomproducto}"
        elif obj.id_repuesto_comprado:
            return f"Repuesto: {obj.id_repuesto_comprado.id_repuesto.nombre}"
        return "---"
    get_producto.short_description = 'Producto'

@admin.register(MovimientoCaja)
class MovimientoCajaAdmin(admin.ModelAdmin):
    list_display = ('id_movimiento_caja', 'tipo_movimiento', 'monto', 'id_caja', 'idusuario', 'fecha_movimiento')
    list_filter = ('tipo_movimiento', 'fecha_movimiento')
    search_fields = ('descripcion',)

@admin.register(Proforma)
class ProformaAdmin(admin.ModelAdmin):
    list_display = ('numero_proforma', 'idcliente', 'fecha_emision', 'total', 'estado')
    list_filter = ('estado', 'fecha_emision')
    search_fields = ('numero_proforma', 'idcliente__razonsocial')

@admin.register(ProformaDetalle)
class ProformaDetalleAdmin(admin.ModelAdmin):
    list_display = ('idproformadetalle', 'idproforma', 'tipo_item', 'cantidad', 'subtotal')
