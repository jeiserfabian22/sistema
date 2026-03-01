from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from software.models.comprasModel import Compras
from software.models.ProveedoresModel import Proveedor
from software.models.FormaPagoModel import FormaPago
from software.models.TipoPagoModel import TipoPago
from software.models.compradetalleModel import CompraDetalle
from software.models.RespuestoCompModel import RepuestoComp
from software.models.VehiculosModel import Vehiculo
from software.models.ProductoModel import Producto
from software.models.RepuestoModel import Repuesto
from software.models.detalletipousuarioxmodulosModel import Detalletipousuarioxmodulos
from software.models.estadoproductoModel import EstadoProducto
from django.db import transaction
from software.models.cuotaModel import Cuota
from software.models.TipoclienteModel import Tipocliente
from software.models.AperturaCierreCajaModel import AperturaCierreCaja
from software.models.UsuarioModel import Usuario
from software.decorators import requiere_caja_aperturada
from software.models.Tipo_entidadModel import TipoEntidad
from datetime import datetime, timedelta
from django.utils import timezone


def compras(request):
    # Obtención del id del tipo de usuario desde la sesión
    id2 = request.session.get('idtipousuario')
    
    if not id2:
        return HttpResponse("<h1>No tiene acceso señor</h1>")
    
    # Validación de permisos
    permisos = Detalletipousuarioxmodulos.objects.filter(idtipousuario=id2)
    
    # FILTRAR COMPRAS POR SUCURSAL
    idusuario = request.session.get('idusuario')
    id_sucursal = request.session.get('id_sucursal')
    es_admin = (id2 == 1)
    
    # Verificar si la sucursal seleccionada es la principal
    es_sucursal_principal = False
    if id_sucursal:
        try:
            from software.models.sucursalesModel import Sucursales
            sucursal = Sucursales.objects.get(id_sucursal=id_sucursal)
            es_sucursal_principal = sucursal.es_principal
        except Sucursales.DoesNotExist:
            es_sucursal_principal = False
    
    # ✅ CONSTRUCCIÓN DE QUERYSET BASE (sin select_related en id_tipo_pago)
    base_queryset = Compras.objects.filter(estado=1).select_related(
        'idproveedor', 
        'idtipocliente', 
        'id_forma_pago',
        'id_sucursal'
    ).prefetch_related(
        'compradetalle',
        'compradetalle__id_vehiculo__idproducto',
        'compradetalle__id_vehiculo__idestadoproducto',
        'compradetalle__id_repuesto_comprado__id_repuesto',
        'cuota'
    )
    
    if es_admin:
        if id_sucursal:
            # Admin con sucursal seleccionada
            compras_registros = base_queryset.filter(
                id_sucursal_id=id_sucursal
            ).order_by('-idcompra')
        else:
            # Admin sin sucursal: ve todas
            compras_registros = base_queryset.order_by('-idcompra')
    else:
        # Usuario normal: solo su sucursal
        try:
            usuario = Usuario.objects.get(idusuario=idusuario)
            compras_registros = base_queryset.filter(
                id_sucursal=usuario.id_sucursal
            ).order_by('-idcompra')
            
            if usuario.id_sucursal:
                es_sucursal_principal = usuario.id_sucursal.es_principal
                
        except Usuario.DoesNotExist:
            compras_registros = Compras.objects.none()
    
    # Catálogos relacionados
    proveedor = Proveedor.objects.filter(estado=1)
    tipocliente = Tipocliente.objects.filter(estado=1)
    formapago = FormaPago.objects.filter(estado=1)
    tipopago = TipoPago.objects.filter(estado=1)
    repuestocomprado = RepuestoComp.objects.filter(estado=1)
    vehiculo = Vehiculo.objects.filter(estado=1)
    producto = Producto.objects.filter(estado=1)
    repuesto = Repuesto.objects.filter(estado=1)
    estadoproducto = EstadoProducto.objects.filter(estado=1)
    tipos_entidad = TipoEntidad.objects.filter(estado=1)

    # Contexto para el template
    data = {
        'compras_registros': compras_registros,
        'proveedor': proveedor,
        'tipo_cliente': tipocliente,
        'forma_pago': formapago,
        'tipo_pago': tipopago,
        'repuestos_comprados': repuestocomprado,
        'vehiculo': vehiculo,
        'producto': producto,
        'catalogo_repuestos': repuesto,
        'estado_producto': estadoproducto,
        'permisos': permisos,
        'es_admin': es_admin,
        'es_sucursal_principal': es_sucursal_principal,
        'tipos_entidad': tipos_entidad,
    }
    
    return render(request, 'compras/compras.html', data)

# Nueva compra
@requiere_caja_aperturada
def nueva_compra(request):
    if request.method == "POST":
        try:
            print("======= DEBUG POST COMPRA =======")
            for k, v in request.POST.items():
                print(f"{k}: {v}")
            print("=================================")

            # VALIDACIÓN 1: Obtener datos de sesión
            idusuario_session = request.session.get('idusuario')
            id_caja_session = request.session.get('id_caja')
            id_almacen_session = request.session.get('id_almacen')
            id_sucursal_session = request.session.get('id_sucursal')
            
            # VALIDACIÓN 2: Verificar que solo sucursal principal puede comprar
            if not id_sucursal_session:
                return JsonResponse({
                    'ok': False,
                    'error': 'Debe seleccionar una sucursal en el modal de configuración antes de realizar compras.'
                }, status=400)
            
            try:
                from software.models.sucursalesModel import Sucursales
                sucursal = Sucursales.objects.get(id_sucursal=id_sucursal_session)
                
                if not sucursal.es_principal:
                    return JsonResponse({
                        'ok': False,
                        'error': 'Solo la sucursal principal puede realizar compras. Sucursal actual: ' + sucursal.nombre_sucursal,
                        'codigo': 'NO_ES_SUCURSAL_PRINCIPAL'
                    }, status=403)
                    
            except Sucursales.DoesNotExist:
                return JsonResponse({
                    'ok': False,
                    'error': 'La sucursal seleccionada no existe.'
                }, status=400)
            
            # Validar que tenga caja seleccionada
            if not id_caja_session:
                return JsonResponse({
                    'ok': False,
                    'error': 'Debe seleccionar una caja en el modal de configuración antes de comprar.'
                }, status=400)
            
            # Validar que tenga almacén seleccionado
            if not id_almacen_session:
                return JsonResponse({
                    'ok': False,
                    'error': 'Debe seleccionar un almacén en el modal de configuración antes de comprar.'
                }, status=400)
            
            # VALIDACIÓN 3: Verificar que la caja esté aperturada
            apertura = AperturaCierreCaja.objects.filter(
                idusuario_id=idusuario_session,
                id_caja_id=id_caja_session,
                estado__in=['abierta', 'reabierta']
            ).first()
            
            if not apertura:
                return JsonResponse({
                    'ok': False,
                    'error': 'La caja seleccionada no está aperturada. Por favor, aperture la caja antes de realizar compras.',
                    'necesita_aperturar': True
                }, status=400)

            with transaction.atomic():
                # Manejar tipo_pago cuando es crédito
                tipo_pago = request.POST.get("tipo_pago")
                tipo_pago_id = int(tipo_pago) if tipo_pago else None
                
                # Crear compra CON SUCURSAL
                compra = Compras.objects.create(
                    idproveedor_id=int(request.POST.get("proveedor")),
                    idtipocliente_id=int(request.POST.get("tipo_cliente")),
                    id_forma_pago_id=int(request.POST.get("forma_pago")),
                    id_tipo_pago_id=tipo_pago_id,
                    numcorrelativo=request.POST.get("numcorrelativo"),
                    fechacompra=request.POST.get("fechacompra"),
                    id_sucursal_id=id_sucursal_session,
                    estado=1,
                )

                total = 0
                items = int(request.POST.get("items_count") or 0)
                print(f"DEBUG items_count: {items}")

                for i in range(1, items + 1):
                    tipo_item = request.POST.get(f"tipo_item_{i}")
                    if not tipo_item:
                        continue

                    cantidad = int(request.POST.get(f"cantidad_{i}") or 0)
                    precio_compra = float(request.POST.get(f"precio_compra_{i}") or 0)
                    precio_venta = float(request.POST.get(f"precio_venta_{i}") or 0)

                    if tipo_item == "vehiculo":
                        idproducto = request.POST.get(f"idproducto_{i}", "").strip()
                        idestadoproducto = request.POST.get(f"idestadoproducto_{i}", "").strip()
                        
                        if not idproducto:
                            raise ValueError(f"Debe seleccionar un producto para el ítem {i}")
                        
                        if not idestadoproducto:
                            raise ValueError(f"Debe seleccionar el estado del producto para el ítem {i}")
                        
                        vehiculo = Vehiculo.objects.create(
                            idproducto_id=int(idproducto),
                            serie_motor=request.POST.get(f"serie_motor_{i}", "").strip(),
                            serie_chasis=request.POST.get(f"serie_chasis_{i}", "").strip(),
                            anio=request.POST.get(f"anio_{i}", "").strip(),
                            idestadoproducto_id=int(idestadoproducto),
                            imperfecciones=request.POST.get(f"imperfecciones_{i}", "").strip(),
                            placas=request.POST.get(f"placas_{i}", "").strip(),
                            estado=1
                        )
                        CompraDetalle.objects.create(
                            idcompra=compra,
                            id_vehiculo=vehiculo,
                            id_repuesto_comprado=None,
                            cantidad=cantidad,
                            precio_compra=precio_compra,
                            precio_venta=precio_venta,
                            subtotal=cantidad * precio_compra
                        )

                    elif tipo_item == "repuesto":
                        id_repuesto = request.POST.get(f"id_repuesto_{i}", "").strip()
                        
                        if not id_repuesto:
                            raise ValueError(f"Debe seleccionar un repuesto para el ítem {i}")
                        
                        repuesto = RepuestoComp.objects.create(
                            id_repuesto_id=int(id_repuesto),
                            descripcion=request.POST.get(f"descripcion_{i}", "").strip(),
                            codigo_barras=request.POST.get(f"codigo_barras_{i}", "").strip(),
                            modelo=request.POST.get(f"modelo_{i}", "").strip(),
                            estado=1
                        )
                        CompraDetalle.objects.create(
                            idcompra=compra,
                            id_repuesto_comprado=repuesto,
                            id_vehiculo=None,
                            cantidad=cantidad,
                            precio_compra=precio_compra,
                            precio_venta=precio_venta,
                            subtotal=cantidad * precio_compra
                        )

                    total += cantidad * precio_compra

                compra.total_compra = total
                compra.save()

                # Guardar cuotas si aplica
                if request.POST.get("forma_pago") == "2" and request.POST.get("tiene_cuotas") == "1":
                    cuotas = int(request.POST.get("credito_cuotas") or 0)
                    
                    for i in range(1, cuotas + 1):
                        monto_adelanto_cuota = float(request.POST.get(f"monto_adelanto_{i}", 0) or 0)
                        numero_cuota = int(request.POST.get(f"numero_cuota_{i}"))
                        
                        # USAR LA FECHA QUE VIENE DEL FORMULARIO (ya configurada en el modal)
                        fecha_vencimiento_str = request.POST.get(f"fecha_vencimiento_{i}")
                        
                        # Convertir string a date
                        if fecha_vencimiento_str:
                            fecha_vencimiento = datetime.strptime(fecha_vencimiento_str, '%Y-%m-%d').date()
                        else:
                            # Fallback: si no viene fecha, calcular automáticamente
                            fecha_compra = datetime.strptime(request.POST.get("fechacompra"), '%Y-%m-%d').date()
                            fecha_vencimiento = fecha_compra + timedelta(days=30 * numero_cuota)
                        
                        Cuota.objects.create(
                            idcompra=compra,
                            numero_cuota=numero_cuota,
                            monto=float(request.POST.get(f"monto_{i}")),
                            tasa=float(request.POST.get(f"tasa_{i}")),
                            interes=float(request.POST.get(f"interes_{i}")),
                            total=float(request.POST.get(f"total_{i}")),
                            fecha_vencimiento=fecha_vencimiento,  # ✅ Fecha del formulario
                            monto_adelanto=monto_adelanto_cuota,
                            estado=1
                        )

                    print(f"✅ {cuotas} cuotas guardadas correctamente")

                print(f"COMPRA REGISTRADA - ID: {compra.idcompra}")
                print(f"Sucursal: {sucursal.nombre_sucursal}")
                print(f"Caja: {apertura.id_caja.nombre_caja}")

            return JsonResponse({
                'ok': True,
                'message': 'Compra registrada correctamente.'
            })

        except ValueError as ve:
            print(f"ERROR DE VALIDACIÓN: {str(ve)}")
            return JsonResponse({
                'ok': False,
                'error': str(ve)
            })
        except Exception as e:
            print(f"ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            return JsonResponse({
                'ok': False,
                'error': f'Error al procesar la compra: {str(e)}'
            })

    return redirect("compras")


# OBTENER COMPRA PARA EDICIÓN
def obtener_compra(request, id):
    """Obtiene los datos de una compra para edición"""
    try:
        compra = Compras.objects.get(idcompra=id, estado=1)
        detalles = CompraDetalle.objects.filter(idcompra=compra).select_related(
            'id_vehiculo__idproducto',
            'id_vehiculo__idestadoproducto',
            'id_repuesto_comprado__id_repuesto'
        )
        
        # Formatear detalles
        detalles_list = []
        for d in detalles:
            if d.id_vehiculo:
                detalles_list.append({
                    'tipo': 'vehiculo',
                    'id_producto': d.id_vehiculo.idproducto.idproducto,
                    'nombre': d.id_vehiculo.idproducto.nomproducto,
                    'serie_motor': d.id_vehiculo.serie_motor or '',
                    'serie_chasis': d.id_vehiculo.serie_chasis or '',
                    'estado_producto': d.id_vehiculo.idestadoproducto.idestadoproducto,
                    'placas': d.id_vehiculo.placas or '',
                    'imperfecciones': d.id_vehiculo.imperfecciones or '',
                    'cantidad': d.cantidad,
                    'precio_compra': float(d.precio_compra),
                    'precio_venta': float(d.precio_venta)
                })
            elif d.id_repuesto_comprado:
                detalles_list.append({
                    'tipo': 'repuesto',
                    'id_repuesto': d.id_repuesto_comprado.id_repuesto.id_repuesto,
                    'nombre': d.id_repuesto_comprado.id_repuesto.nombre,
                    'codigo_barras': d.id_repuesto_comprado.codigo_barras or '',
                    'modelo': d.id_repuesto_comprado.modelo or '',
                    'descripcion': d.id_repuesto_comprado.descripcion or '',
                    'cantidad': d.cantidad,
                    'precio_compra': float(d.precio_compra),
                    'precio_venta': float(d.precio_venta)
                })
        
        #CORRECCIÓN: Obtener cuotas con related_name='cuota'
        cuotas = []
        if compra.cuota.exists():
            for cuota in compra.cuota.all():
                cuotas.append({
                    'numero_cuota': cuota.numero_cuota,
                    'monto': float(cuota.monto),
                    'tasa': float(cuota.tasa),
                    'interes': float(cuota.interes),
                    'total': float(cuota.total),
                    'fecha_vencimiento': cuota.fecha_vencimiento.strftime('%Y-%m-%d'),
                    'monto_adelanto': float(cuota.monto_adelanto)
                })
        
        return JsonResponse({
            'success': True,
            'compra': {
                'idcompra': compra.idcompra,
                'idproveedor': compra.idproveedor.idproveedor,
                'proveedor_nombre': compra.idproveedor.razonsocial,
                'numcorrelativo': compra.numcorrelativo,
                'fechacompra': compra.fechacompra.strftime('%Y-%m-%d'),
                'idtipocliente': compra.idtipocliente.idtipocliente,
                'id_forma_pago': compra.id_forma_pago.id_forma_pago,
                'id_tipo_pago': compra.id_tipo_pago.id_tipo_pago if compra.id_tipo_pago else None,
                'total_compra': float(compra.total_compra)
            },
            'detalles': detalles_list,
            'cuotas': cuotas
        })
        
    except Compras.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Compra no encontrada'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# ACTUALIZAR COMPRA
@requiere_caja_aperturada
@transaction.atomic
def actualizar_compra(request, id):
    """Actualiza una compra existente - CON REUTILIZACIÓN DE REPUESTOS/VEHÍCULOS"""
    if request.method == "POST":
        try:
            print("======= DEBUG POST ACTUALIZAR COMPRA =======")
            for k, v in request.POST.items():
                print(f"{k}: {v}")
            print("=================================")
            
            # Obtener la compra existente
            compra = Compras.objects.get(idcompra=id, estado=1)
            
            # Guardar datos anteriores para auditoría
            datos_anteriores = {
                'numcorrelativo': compra.numcorrelativo,
                'proveedor': compra.idproveedor.razonsocial,
                'total': float(compra.total_compra),
                'fecha': str(compra.fechacompra),
                'forma_pago': compra.id_forma_pago.nombre,
                'tipo_pago': compra.id_tipo_pago.nombre if compra.id_tipo_pago else 'Crédito'
            }
            
            # Actualizar datos principales
            compra.idproveedor_id = int(request.POST.get("proveedor"))
            compra.idtipocliente_id = int(request.POST.get("tipo_cliente"))
            compra.id_forma_pago_id = int(request.POST.get("forma_pago"))
            
            tipo_pago = request.POST.get("tipo_pago")
            compra.id_tipo_pago_id = int(tipo_pago) if tipo_pago else None
            
            compra.numcorrelativo = request.POST.get("numcorrelativo")
            compra.fechacompra = request.POST.get("fechacompra")
            
            #CORRECCIÓN: Soft delete de detalles antiguos en lugar de eliminar
            CompraDetalle.objects.filter(idcompra=compra).delete()
            
            # Eliminar cuotas antiguas si existen
            Cuota.objects.filter(idcompra=compra).delete()
            
            # Agregar nuevos detalles con REUTILIZACIÓN
            total = 0
            items = int(request.POST.get("items_count") or 0)
            
            for i in range(1, items + 1):
                tipo_item = request.POST.get(f"tipo_item_{i}")
                if not tipo_item:
                    continue

                cantidad = int(request.POST.get(f"cantidad_{i}") or 0)
                precio_compra = float(request.POST.get(f"precio_compra_{i}") or 0)
                precio_venta = float(request.POST.get(f"precio_venta_{i}") or 0)

                if tipo_item == "vehiculo":
                    idproducto = request.POST.get(f"idproducto_{i}", "").strip()
                    idestadoproducto = request.POST.get(f"idestadoproducto_{i}", "").strip()
                    serie_motor = request.POST.get(f"serie_motor_{i}", "").strip()
                    serie_chasis = request.POST.get(f"serie_chasis_{i}", "").strip()
                    placas = request.POST.get(f"placas_{i}", "").strip()
                    imperfecciones = request.POST.get(f"imperfecciones_{i}", "").strip()
                    anio_str = request.POST.get(f"anio_{i}", "").strip()
                    anio = int(anio_str) if anio_str else None
                    
                    if not idproducto:
                        raise ValueError(f"Debe seleccionar un producto para el ítem {i}")
                    
                    if not idestadoproducto:
                        raise ValueError(f"Debe seleccionar el estado del producto para el ítem {i}")
                    
                    # BUSCAR O CREAR - No duplica si ya existe
                    if serie_motor and serie_chasis:
                        vehiculo, created = Vehiculo.objects.get_or_create(
                            serie_motor=serie_motor,
                            serie_chasis=serie_chasis,
                            defaults={
                                'idproducto_id': int(idproducto),
                                'idestadoproducto_id': int(idestadoproducto),
                                'imperfecciones': imperfecciones,
                                'placas': placas,
                                'anio': anio,
                                'estado': 1
                            }
                        )
                        if not created:
                            vehiculo.idproducto_id = int(idproducto)
                            vehiculo.idestadoproducto_id = int(idestadoproducto)
                            vehiculo.imperfecciones = imperfecciones
                            vehiculo.placas = placas
                            vehiculo.anio = anio
                            vehiculo.save()
                    else:
                        vehiculo = Vehiculo.objects.create(
                            idproducto_id=int(idproducto),
                            serie_motor=serie_motor,
                            serie_chasis=serie_chasis,
                            anio=anio,
                            idestadoproducto_id=int(idestadoproducto),
                            imperfecciones=imperfecciones,
                            placas=placas,
                            estado=1
                        )
                    
                    CompraDetalle.objects.create(
                        idcompra=compra,
                        id_vehiculo=vehiculo,
                        id_repuesto_comprado=None,
                        cantidad=cantidad,
                        precio_compra=precio_compra,
                        precio_venta=precio_venta,
                        subtotal=cantidad * precio_compra
                    )

                elif tipo_item == "repuesto":
                    id_repuesto = request.POST.get(f"id_repuesto_{i}", "").strip()
                    codigo_barras = request.POST.get(f"codigo_barras_{i}", "").strip()
                    modelo = request.POST.get(f"modelo_{i}", "").strip()
                    descripcion = request.POST.get(f"descripcion_{i}", "").strip()
                    
                    if not id_repuesto:
                        raise ValueError(f"Debe seleccionar un repuesto para el ítem {i}")
                    
                    #BUSCAR O CREAR - No duplica si ya existe
                    if codigo_barras:
                        repuesto, created = RepuestoComp.objects.get_or_create(
                            codigo_barras=codigo_barras,
                            defaults={
                                'id_repuesto_id': int(id_repuesto),
                                'descripcion': descripcion,
                                'modelo': modelo,
                                'estado': 1
                            }
                        )
                        if not created:
                            repuesto.id_repuesto_id = int(id_repuesto)
                            repuesto.descripcion = descripcion
                            repuesto.modelo = modelo
                            repuesto.save()
                    else:
                        repuesto = RepuestoComp.objects.create(
                            id_repuesto_id=int(id_repuesto),
                            descripcion=descripcion,
                            codigo_barras=codigo_barras,
                            modelo=modelo,
                            estado=1
                        )
                    
                    CompraDetalle.objects.create(
                        idcompra=compra,
                        id_repuesto_comprado=repuesto,
                        id_vehiculo=None,
                        cantidad=cantidad,
                        precio_compra=precio_compra,
                        precio_venta=precio_venta,
                        subtotal=cantidad * precio_compra
                    )

                total += cantidad * precio_compra
            
            # Actualizar total
            compra.total_compra = total
            compra.save()
            
            # Guardar cuotas si aplica
            if request.POST.get("forma_pago") == "2" and request.POST.get("tiene_cuotas") == "1":
                cuotas = int(request.POST.get("credito_cuotas") or 0)
                
                for i in range(1, cuotas + 1):
                    monto_adelanto_cuota = float(request.POST.get(f"monto_adelanto_{i}", 0) or 0)
                    numero_cuota = int(request.POST.get(f"numero_cuota_{i}"))
                    
                    # ✅ USAR LA FECHA QUE VIENE DEL FORMULARIO
                    fecha_vencimiento_str = request.POST.get(f"fecha_vencimiento_{i}")
                    
                    if fecha_vencimiento_str:
                        fecha_vencimiento = datetime.strptime(fecha_vencimiento_str, '%Y-%m-%d').date()
                    else:
                        # Fallback
                        fecha_compra = datetime.strptime(request.POST.get("fechacompra"), '%Y-%m-%d').date()
                        fecha_vencimiento = fecha_compra + timedelta(days=30 * numero_cuota)
                    
                    Cuota.objects.create(
                        idcompra=compra,
                        numero_cuota=numero_cuota,
                        monto=float(request.POST.get(f"monto_{i}")),
                        tasa=float(request.POST.get(f"tasa_{i}")),
                        interes=float(request.POST.get(f"interes_{i}")),
                        total=float(request.POST.get(f"total_{i}")),
                        fecha_vencimiento=fecha_vencimiento,  # ✅ Fecha del formulario
                        monto_adelanto=monto_adelanto_cuota,
                        estado=1
                    )
            
            # REGISTRAR EN AUDITORÍA
            from software.models.AuditoriaComprasModel import AuditoriaCompras
            AuditoriaCompras.objects.create(
                idcompra=id,
                accion='EDICION',
                motivo='Compra actualizada',
                idusuario_id=request.session.get('idusuario'),
                datos_anteriores=datos_anteriores
            )
            
            print(f"COMPRA ACTUALIZADA - ID: {compra.idcompra}")
            
            return JsonResponse({
                'ok': True,
                'message': 'Compra actualizada correctamente'
            })
            
        except Compras.DoesNotExist:
            return JsonResponse({
                'ok': False,
                'error': 'La compra no existe o ya fue eliminada'
            }, status=404)
        except ValueError as ve:
            print(f"ERROR DE VALIDACIÓN: {str(ve)}")
            return JsonResponse({
                'ok': False,
                'error': str(ve)
            })
        except Exception as e:
            print(f"ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            return JsonResponse({
                'ok': False,
                'error': f'Error al actualizar la compra: {str(e)}'
            }, status=400)
    
    return redirect("compras")


# ELIMINAR COMPRA (Eliminación lógica - SOLO ADMIN)
def eliminar_compra(request, id):
    """Eliminación lógica de una compra (cambia estado a 0) - SOLO ADMIN"""
    if request.method == "POST":
        try:
            # VALIDAR PERMISOS: Solo admin puede eliminar
            id_tipo_usuario = request.session.get('idtipousuario')
            
            if id_tipo_usuario != 1:  # 1 = Admin
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'error': 'No tiene permisos para eliminar compras. Solo administradores pueden realizar esta acción.',
                        'codigo': 'SIN_PERMISOS'
                    }, status=403)
                return redirect('compras')
            
            motivo = request.POST.get('motivo', '')
            idusuario = request.session.get('idusuario')
            
            # Cambiar estado de la compra
            compra = Compras.objects.get(idcompra=id)
            
            # Guardar datos para auditoría
            datos_compra = {
                'numcorrelativo': compra.numcorrelativo,
                'proveedor': compra.idproveedor.razonsocial,
                'total': float(compra.total_compra),
                'fecha': str(compra.fechacompra)
            }
            
            compra.estado = 0
            compra.save()
            
            # REGISTRAR EN AUDITORÍA
            from software.models.AuditoriaComprasModel import AuditoriaCompras
            AuditoriaCompras.objects.create(
                idcompra=id,
                accion='ELIMINACION',
                motivo=motivo,
                idusuario_id=idusuario,
                datos_anteriores=datos_compra
            )
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Compra eliminada correctamente'
                })
            
            return redirect('compras')
            
        except Compras.DoesNotExist:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': 'La compra no existe'
                }, status=404)
            return redirect('compras')
            
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': str(e)
                }, status=400)
            return redirect('compras')
    
    return redirect("compras")