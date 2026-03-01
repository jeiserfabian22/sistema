
from django.urls import path



from .views import login
from .views import categorias
from .views import marcas
from .views import colores
from .views import cilindradas
from .views import estadoproductos
from .views import configuracion
from .views import compras
from .views import productos
from .views import repuestos
from .views import unidades
from .views import usuarios
from .views import ventas
from .views import permisos
from .views import cpanel
from .views import tipoUsuarios
from .views import registroCaja
from .views import stock
from .views import password_reset
from .views import transferencias
from .views import movimientosCaja
from .views import creditos
from .views import clientes
from .views import proveedores
from .views import imposicionPlacas
from .views import regiones
from .views import provincias
from .views import distritos
from .views import sucursales
from .views import almacenes
from .views import cajas
from .views import historialCajas
from .views import tipo_comprobante
from .views import serie_comprobante
from .views import proforma




urlpatterns = [


    #login
    path('', login.index, name="index"),
    path('login', login.login, name="login"),
    path('logout', login.logout, name="logout"),


    
    # Recuperación de contraseña
    path('recuperar-contrasena/', password_reset.solicitar_recuperacion, name="solicitar_recuperacion"),
    path('restablecer-contrasena/<str:token>/', password_reset.restablecer_contrasena, name="restablecer_contrasena"),

    # Nuevas rutas para manejo de caja
    path('api/obtener-datos-apertura/', login.obtener_datos_apertura, name="obtener_datos_apertura"),
    path('api/obtener-cajas-almacenes/', login.obtener_cajas_almacenes, name="obtener_cajas_almacenes"),
    path('api/cambiar-contexto/', login.cambiar_contexto, name="cambiar_contexto"),
    path('api/abrir-caja/', login.abrir_caja, name="abrir_caja"),
    path('api/cerrar-caja/', login.cerrar_caja, name="cerrar_caja"),
    path('api/obtener-saldo-actual/', login.obtener_saldo_actual, name='obtener_saldo_actual'),

    # Unidades
    path('unidades/', unidades.unidades, name='unidades'),
    path('unidades/activo/<int:id>/', unidades.activo, name='unidadesActivo'),
    path('unidades/desactivo/<int:id>/', unidades.desactivo, name='unidadesDesactivo'),
        
    #Usuarios
    path('usuarios', usuarios.usuarios, name="usuarios"),
    path('usuarios/agregar', usuarios.agregar, name="usuarioAgregar"),
    path('usuarios/editar', usuarios.editar, name="usuarioEditar"),
    path('usuarios/eliminar/<int:id>', usuarios.eliminar, name="usuarioEliminar"),
    
    # compras
    path('compras/', compras.compras, name="compras"),
    path('compras/agregar/', compras.nueva_compra, name="agregarCompras"), 
    path('api/obtener-compra/<int:id>/', compras.obtener_compra, name='obtener_compra'),
    path('compras/actualizar/<int:id>/', compras.actualizar_compra, name='actualizar_compra'),
    path('compras/eliminar/<int:id>/', compras.eliminar_compra, name='eliminar_compra'),
    path('stock/', stock.stock, name='stock'),
     
    # ventas
    path('ventas/', ventas.ventas, name="ventas"),
    path('ventas/nueva/', ventas.nueva_venta, name="nuevaVenta"),
    path('ventas/obtener-series/', ventas.obtener_series, name="obtenerSeries"),
    path('ventas/imprimir/<int:idventa>/', ventas.imprimir_comprobante, name="imprimir_comprobante"),
    path('ventas/obtener/<int:id>/', ventas.obtener_venta, name='obtener_venta'),
    path('ventas/actualizar/<int:id>/', ventas.actualizar_venta, name='actualizar_venta'),
    path('ventas/eliminar/<int:id>/', ventas.eliminar_venta, name='eliminar_venta'),

    #categorias
    path('categorias', categorias.categorias, name="categorias"),
    path('categorias/agregar', categorias.agregar, name="agregarCategorias"),
    path('categorias/editar', categorias.editar, name="editarCategorias"),
    path('categorias/eliminarCategoria/<int:id>', categorias.eliminar, name="categoriasEliminar"),
    
    # Marcas
    path('marcas', marcas.marcas, name="marcas"),
    path('marcas/agregar', marcas.agregar, name="agregarMarcas"),
    path('marcas/editar', marcas.editar, name="editarMarcas"),
    path('marcas/eliminarMarca/<int:id>', marcas.eliminar, name="marcasEliminar"),

    # Colores
    path('colores', colores.colores, name="colores"),
    path('colores/agregar', colores.agregar, name="agregarColores"),
    path('colores/editar', colores.editar, name="editarColores"),
    path('colores/eliminarColor/<int:id>', colores.eliminar, name="coloresEliminar"),

    # Cilindradas
    path('cilindradas', cilindradas.cilindradas, name="cilindradas"),
    path('cilindradas/agregar', cilindradas.agregar, name="agregarCilindradas"),
    path('cilindradas/editar', cilindradas.editar, name="editarCilindradas"),
    path('cilindradas/eliminarCilindrada/<int:id>', cilindradas.eliminar, name="cilindradasEliminar"),
    
    # Estado Producto
    path('estadoproductos', estadoproductos.estadoproductos, name="estadoproductos"),
    path('estadoproductos/agregar', estadoproductos.agregar, name="agregarEstadoProductos"),
    path('estadoproductos/editar', estadoproductos.editar, name="editarEstadoProductos"),
    path('estadoproductos/eliminarEstadoProducto/<int:id>', estadoproductos.eliminar, name="estadoproductosEliminar"),

    #Permisos
    path('permisos', permisos.permisos, name="permisos"),
    path('permisos/agregaPermiso', permisos.agregaPermiso, name="agregaPermiso"),
    path('editarPermiso/', permisos.editarPermiso, name='editarPermiso'),
    path('permisos/eliminarPermiso/<int:id>', permisos.eliminarPermiso, name="eliminarPermiso"),
     
    #productos
    path('productos', productos.productos, name="productos"),
    path('productos/agregar', productos.agregar, name="productosAgregar"),
    path('productos/editar', productos.editado, name="productosEditado"),
    path('productos/eliminarProducto/<int:idproducto>', productos.eliminar, name="eliminarProducto"),

    #Repuestos
    path('repuestos', repuestos.repuestos, name="repuestos"),
    path('repuestos/agregar', repuestos.agregar_repuesto, name="agregarRepuesto"),
    path('repuestos/editar', repuestos.editar_repuesto, name="editarRepuesto"),
    path('repuestos/eliminar/<int:id_repuesto>', repuestos.eliminar_repuesto, name="eliminarRepuesto"),
    
    #configuracion
    path('configuracion', configuracion.configuracion, name="configuracion"),
    path('configuracion/editarEmpresa', configuracion.editarEmpresa, name="editarEmpresa"),
    path('configuracion/produccion/<int:id>', configuracion.produccion, name="produccion"),
    path('configuracion/desarrollo/<int:id>', configuracion.desarrollo, name="desarrollo"),
    path('obtener-empresa-ruc/', configuracion.obtener_datos_empresa_por_ruc, name='obtener_empresa_ruc'),

    #cpanel
    path('cpanel', cpanel.cpanel, name="cpanel"),

    #Tipo usuarios
    path('tipousuarios', tipoUsuarios.tipoUsuarios, name="tipoUsuarios"),
    path('tipousuarios/agregar', tipoUsuarios.tipousuariosAgregar, name="tipousuariosAgregar"),
    path('tipousuarios/editar', tipoUsuarios.tipousuariosEditar, name="tipousuariosEditar"),
    path('tipousuarios/eliminar/<int:id>', tipoUsuarios.tipousuariosEliminar, name="tipousuariosEliminar"),

    # TRANSFERENCIAS
    path('transferencias/', transferencias.transferencias, name='transferencias'),
    path('transferencias/nueva/', transferencias.nueva_transferencia, name='nueva_transferencia'),
    path('transferencias/confirmar/<int:id>/', transferencias.confirmar_transferencia, name='confirmar_transferencia'),
    path('transferencias/rechazar/<int:id>/', transferencias.rechazar_transferencia, name='rechazar_transferencia'),
   
    # API para obtener stock
    path('api/obtener-stock-almacen/', transferencias.obtener_stock_almacen, name='obtener_stock_almacen'),
    path('stock/', stock.stock, name='stock'),
    
    #REGISTROS DE CAJA
    path('cajas/', cajas.cajas, name='cajas'),
    path('cajas/eliminar/<int:id>/', cajas.cajasEliminar, name='cajasEliminar'),
    path('cajas/agregar/', cajas.agregarCajas, name='agregarCajas'),
    path('cajas/editar/', cajas.editarCajas, name='editarCajas'),
    path('cajas/obtener-sucursales/', cajas.obtenerSucursalesPorEmpresa, name='obtenerSucursalesPorEmpresaCajas'),
    


    # MOVIMIENTOS DE CAJA
    path('movimientos-caja/', movimientosCaja.movimientos_caja, name='movimientos_caja'),
    path('movimientos-caja/registrar-egreso/', movimientosCaja.registrar_egreso, name='registrar_egreso'),
    path('movimientos-caja/reporte/', movimientosCaja.reporte_caja, name='reporte_caja'),

    
    # MÓDULO DE CRÉDITOS
    path('creditos/', creditos.creditos, name='creditos'),
    path('creditos/detalle/<int:idcredito>/', creditos.detalle_credito, name='detalle_credito'),
    path('creditos/pagar-cuota/<int:idcuotaventa>/', creditos.pagar_cuota, name='pagar_cuota'),
    path('creditos/anular-pago/<int:idpagocuota>/', creditos.anular_pago, name='anular_pago'),
    path('creditos/reportes/', creditos.reportes_creditos, name='reportes_creditos'),
    path('creditos/buscar-cuotas-cliente/', creditos.buscar_cuotas_cliente, name='buscar_cuotas_cliente'),

    # IMPRIMIR CRONOGRAMA
    path('ventas/imprimir-cronograma/<int:idventa>/', creditos.imprimir_cronograma_credito, name='imprimir_cronograma'),
    path('creditos/recibo-pago/<int:idpagocuota>/', creditos.imprimir_recibo_pago, name='imprimir_recibo_pago'),

    # Clientes
    path('clientes/', clientes.clientes, name='clientes'),
    path('clientes/agregar/', clientes.agregar_cliente, name='agregar_cliente'),
    path('clientes/editar/', clientes.editar_cliente, name='editar_cliente'),
    path('clientes/eliminar/<int:id>/', clientes.eliminar_cliente, name='eliminar_cliente'),
    path('api/autocompletar-cliente/', clientes.autocompletar_cliente, name='autocompletar_cliente'),

    # Proveedores
    path('proveedores/', proveedores.proveedores, name='proveedores'),
    path('proveedores/agregar/', proveedores.agregar_proveedor, name='agregar_proveedor'),
    path('proveedores/editar/', proveedores.editar_proveedor, name='editar_proveedor'),
    path('proveedores/eliminar/<int:id>/', proveedores.eliminar_proveedor, name='eliminar_proveedor'),
    path('api/autocompletar-proveedor/', proveedores.autocompletar_proveedor, name='autocompletar_proveedor'),
    path('api/obtener-ultimo-proveedor/', proveedores.obtener_ultimo_proveedor, name='obtener_ultimo_proveedor'),


    # Imposición de Placas
    path('imposicion-placas/', imposicionPlacas.imposicion_placas, name='imposicion_placas'),
    path('imposicion-placas/nueva/', imposicionPlacas.nueva_imposicion, name='nueva_imposicion'),
    path('imposicion-placas/editar/<int:id>/', imposicionPlacas.editar_imposicion, name='editar_imposicion'),
    path('imposicion-placas/cambiar-estado/<int:id>/', imposicionPlacas.cambiar_estado_imposicion, name='cambiar_estado_imposicion'),
    path('imposicion-placas/eliminar/<int:id>/', imposicionPlacas.eliminar_imposicion, name='eliminar_imposicion'),
    path('imposicion-placas/detalle/<int:id>/', imposicionPlacas.detalle_imposicion, name='detalle_imposicion'),
    path('imposicion-placas/vehiculos-venta/', imposicionPlacas.obtener_vehiculos_venta, name='obtener_vehiculos_venta'),
    path('imposicion-placas/imprimir/<int:id>/', imposicionPlacas.imprimir_constancia, name='imprimir_constancia_placa'),

    #Regiones
    path('regiones/', regiones.regiones, name='regiones'),
    path('regiones/eliminar/<int:id>/', regiones.regionesEliminar, name='regionesEliminar'),
    path('regiones/agregar/', regiones.agregarRegiones, name='agregarRegiones'),
    path('regiones/editar/', regiones.editarRegiones, name='editarRegiones'),

    #Provincias
    path('provincias/', provincias.provincias, name='provincias'),
    path('provincias/eliminar/<int:id>/', provincias.provinciasEliminar, name='provinciasEliminar'),
    path('provincias/agregar/', provincias.agregarProvincias, name='agregarProvincias'),
    path('provincias/editar/', provincias.editarProvincias, name='editarProvincias'),

    #Distritos
    path('distritos/', distritos.distritos, name='distritos'),
    path('distritos/eliminar/<int:id>/', distritos.distritosEliminar, name='distritosEliminar'),
    path('distritos/agregar/', distritos.agregarDistritos, name='agregarDistritos'),
    path('distritos/editar/', distritos.editarDistritos, name='editarDistritos'),
    path('distritos/obtener-provincias/', distritos.obtenerProvinciasPorRegion, name='obtenerProvinciasPorRegion'),

    #Sucursales
    path('sucursales/', sucursales.sucursales, name='sucursales'),
    path('sucursales/eliminar/<int:id>/', sucursales.sucursalesEliminar, name='sucursalesEliminar'),
    path('sucursales/agregar/', sucursales.agregarSucursales, name='agregarSucursales'),
    path('sucursales/editar/', sucursales.editarSucursales, name='editarSucursales'),
    path('sucursales/obtener-provincias/', sucursales.obtenerProvinciasPorRegion, name='obtenerProvinciasPorRegionSucursales'),
    path('sucursales/obtener-distritos/', sucursales.obtenerDistritosPorProvincia, name='obtenerDistritosPorProvincia'),

    #Almacenes
    path('almacenes/', almacenes.almacenes, name='almacenes'),
    path('almacenes/eliminar/<int:id>/', almacenes.almacenesEliminar, name='almacenesEliminar'),
    path('almacenes/agregar/', almacenes.agregarAlmacenes, name='agregarAlmacenes'),
    path('almacenes/editar/', almacenes.editarAlmacenes, name='editarAlmacenes'),
    path('almacenes/obtener-sucursales/', almacenes.obtenerSucursalesPorEmpresa, name='obtenerSucursalesPorEmpresa'),


    # Historial de Cajas
    path('historial-cajas/', historialCajas.historial_cajas, name='historial_cajas'),
    path('historial-cajas/solicitar-reapertura/<int:id_movimiento>/', historialCajas.solicitar_reapertura, name='solicitar_reapertura'),
    path('historial-cajas/verificar-codigo/', historialCajas.verificar_codigo_reapertura, name='verificar_codigo_reapertura'),
    path('historial-cajas/cerrar-reabierta/<int:id_movimiento>/', historialCajas.cerrar_caja_reabierta, name='cerrar_caja_reabierta'),


    # Tipo Compprobante
    path('tipo-comprobante/', tipo_comprobante.tipo_comprobante, name='tipo_comprobante'),
    path('agregar-tipo-comprobante/', tipo_comprobante.agregar_tipo_comprobante, name='agregar_tipo_comprobante'),
    path('editar-tipo-comprobante/', tipo_comprobante.editar_tipo_comprobante, name='editar_tipo_comprobante'),
    path('eliminar-tipo-comprobante/<int:id>/', tipo_comprobante.eliminar_tipo_comprobante, name='eliminar_tipo_comprobante'),

    # Series de Comprobante
    path('serie-comprobante/', serie_comprobante.serie_comprobante, name='serie_comprobante'),
    path('agregar-serie-comprobante/', serie_comprobante.agregar_serie_comprobante, name='agregar_serie_comprobante'),
    path('editar-serie-comprobante/', serie_comprobante.editar_serie_comprobante, name='editar_serie_comprobante'),
    path('eliminar-serie-comprobante/<int:id>/', serie_comprobante.eliminar_serie_comprobante, name='eliminar_serie_comprobante'),

    # Proformas 
    path('proformas/', proforma.proformas, name='proformas'),
    path('proformas/nueva/', proforma.nueva_proforma, name='nueva_proforma'),
    path('proformas/pdf/<int:idproforma>/', proforma.proforma_pdf, name='proforma_pdf'),
    path('proformas/anular/<int:idproforma>/', proforma.eliminar_proforma, name='anular_proforma'),

]
