from django.db import connection
from django.http import HttpResponse
from django.shortcuts import render
from django.db.models import Sum, Count, F, Q, DecimalField
from django.db.models.functions import TruncDate, Coalesce
from datetime import datetime, timedelta
from decimal import Decimal
import json

from software.models.detalletipousuarioxmodulosModel import Detalletipousuarioxmodulos
from software.models.VentasModel import Ventas
from software.models.VentaDetalleModel import VentaDetalle
from software.models.ProductoModel import Producto
from software.models.VehiculosModel import Vehiculo
from software.models.RepuestoModel import Repuesto
from software.models.RespuestoCompModel import RepuestoComp
from software.models.marcaModel import Marca
from software.models.categoriaModel import Categoria


def cpanel(request):
    """Vista del dashboard con estadísticas avanzadas"""
    # Obtener datos de sesión del usuario
    id2 = request.session.get('idtipousuario')
    nombrecompleto = request.session.get('nombrecompleto')

    if not id2:
        return HttpResponse("<h1>No tiene acceso señor</h1>")

    # Permisos del tipo de usuario
    permisos = Detalletipousuarioxmodulos.objects.filter(idtipousuario=id2)

    # ========================================
    # FILTROS DE FECHA
    # ========================================
    hoy = datetime.now().date()
    inicio_mes_actual = hoy.replace(day=1)
    
    # Mes anterior
    if hoy.month == 1:
        inicio_mes_anterior = hoy.replace(year=hoy.year - 1, month=12, day=1)
        fin_mes_anterior = hoy.replace(day=1) - timedelta(days=1)
    else:
        inicio_mes_anterior = hoy.replace(month=hoy.month - 1, day=1)
        fin_mes_anterior = inicio_mes_actual - timedelta(days=1)
    
    # Semana actual (lunes a domingo)
    inicio_semana = hoy - timedelta(days=hoy.weekday())
    fin_semana = inicio_semana + timedelta(days=6)

    # ========================================
    # 1. VENTAS TOTALES DEL MES ACTUAL
    # ========================================
    ventas_mes_actual = Ventas.objects.filter(
        estado=1,
        fecha_venta__date__gte=inicio_mes_actual,
        fecha_venta__date__lte=hoy
    ).aggregate(
        total=Coalesce(Sum('total_venta'), Decimal('0'), output_field=DecimalField())
    )['total']

    # Ventas del mes anterior
    ventas_mes_anterior = Ventas.objects.filter(
        estado=1,
        fecha_venta__date__gte=inicio_mes_anterior,
        fecha_venta__date__lte=fin_mes_anterior
    ).aggregate(
        total=Coalesce(Sum('total_venta'), Decimal('0'), output_field=DecimalField())
    )['total']

    # Calcular porcentaje de cambio
    if ventas_mes_anterior > 0:
        porcentaje_cambio = ((ventas_mes_actual - ventas_mes_anterior) / ventas_mes_anterior) * 100
    else:
        porcentaje_cambio = 100 if ventas_mes_actual > 0 else 0

    # ========================================
    # 2. VENTAS DE LA SEMANA
    # ========================================
    ventas_semana = Ventas.objects.filter(
        estado=1,
        fecha_venta__date__gte=inicio_semana,
        fecha_venta__date__lte=fin_semana
    ).aggregate(
        total=Coalesce(Sum('total_venta'), Decimal('0'), output_field=DecimalField())
    )['total']

    # Top categorías de la semana
    detalles_semana = VentaDetalle.objects.filter(
        idventa__estado=1,
        idventa__fecha_venta__date__gte=inicio_semana,
        idventa__fecha_venta__date__lte=fin_semana,
        estado=1
    ).select_related('id_vehiculo__idproducto__idcategoria', 'id_repuesto_comprado')

    categorias_semana = {}
    for detalle in detalles_semana:
        if detalle.tipo_item == 'vehiculo' and detalle.id_vehiculo:
            categoria = detalle.id_vehiculo.idproducto.idcategoria.nomcategoria
        else:
            categoria = 'Repuestos'
        
        if categoria not in categorias_semana:
            categorias_semana[categoria] = Decimal('0')
        categorias_semana[categoria] += detalle.subtotal or Decimal('0')

    # Ordenar y tomar top 3
    top_categorias_semana = sorted(
        categorias_semana.items(), 
        key=lambda x: x[1], 
        reverse=True
    )[:3]

    # ========================================
    # 3. DESCUENTOS SEMANALES
    # ========================================
    # Calcular descuentos como diferencia entre precio contado y precio con descuento
    detalles_con_descuento = VentaDetalle.objects.filter(
        idventa__estado=1,
        idventa__fecha_venta__date__gte=inicio_semana,
        idventa__fecha_venta__date__lte=fin_semana,
        idventa__id_forma_pago_id=1,  # Solo contado
        estado=1
    )

    total_descuentos = Decimal('0')
    cantidad_descuentos = 0

    for detalle in detalles_con_descuento:
        # Si el subtotal es menor al precio_venta_contado * cantidad, hay descuento
        precio_contado = detalle.precio_venta_contado or Decimal('0')
        cantidad = detalle.cantidad or 0
        subtotal = detalle.subtotal or Decimal('0')
        precio_sin_descuento = precio_contado * cantidad
        if subtotal < precio_sin_descuento:
            descuento = precio_sin_descuento - subtotal
            total_descuentos += descuento
            cantidad_descuentos += 1

    # ========================================
    # 4. VENTAS DIARIAS DEL MES (PARA GRÁFICO DE LÍNEA)
    # ========================================
    ventas_diarias = Ventas.objects.filter(
        estado=1,
        fecha_venta__date__gte=inicio_mes_actual,
        fecha_venta__date__lte=hoy
    ).annotate(
        dia=TruncDate('fecha_venta')
    ).values('dia').annotate(
        total=Coalesce(Sum('total_venta'), Decimal('0'), output_field=DecimalField())
    ).order_by('dia')

    # Crear serie completa de días del mes actual (rellenar días sin ventas con 0)
    dias_mes = {}
    dia_actual = inicio_mes_actual
    while dia_actual <= hoy:
        dias_mes[dia_actual.strftime('%Y-%m-%d')] = 0
        dia_actual += timedelta(days=1)

    # Llenar con datos reales del mes actual
    for venta in ventas_diarias:
        dias_mes[venta['dia'].strftime('%Y-%m-%d')] = float(venta['total'])

    # ── Mes anterior diario ──
    ventas_diarias_anterior = Ventas.objects.filter(
        estado=1,
        fecha_venta__date__gte=inicio_mes_anterior,
        fecha_venta__date__lte=fin_mes_anterior
    ).annotate(
        dia=TruncDate('fecha_venta')
    ).values('dia').annotate(
        total=Coalesce(Sum('total_venta'), Decimal('0'), output_field=DecimalField())
    ).order_by('dia')

    # Crear serie completa de días del mes anterior
    dias_mes_anterior = {}
    dia_iter = inicio_mes_anterior
    while dia_iter <= fin_mes_anterior:
        dias_mes_anterior[dia_iter.strftime('%Y-%m-%d')] = 0
        dia_iter += timedelta(days=1)

    for venta in ventas_diarias_anterior:
        dias_mes_anterior[venta['dia'].strftime('%Y-%m-%d')] = float(venta['total'])

    # Alinear ambas series por día del mes (1..31)
    # El eje X usa los días del mes más largo de los dos
    max_days = max(len(dias_mes), len(dias_mes_anterior))
    categories = list(range(1, max_days + 1))

    data_actual   = list(dias_mes.values())
    data_anterior = list(dias_mes_anterior.values())

    # Rellenar con 0 si un mes tiene menos días
    while len(data_actual) < max_days:
        data_actual.append(0)
    while len(data_anterior) < max_days:
        data_anterior.append(0)

    # Preparar datos para ApexCharts
    ventas_mes_chart = {
        'categories': categories,
        'data_actual': data_actual,
        'data_anterior': data_anterior,
    }


    # ========================================
    # 5. VENTAS POR MARCA (DONUT CHART)
    # ========================================
    # Obtener ventas de vehículos por marca
    ventas_vehiculos_marca = VentaDetalle.objects.filter(
        idventa__estado=1,
        tipo_item='vehiculo',
        estado=1
    ).values(
        marca_nombre=F('id_vehiculo__idproducto__idmarca__nombremarca')
    ).annotate(
        cantidad=Sum('cantidad')
    )

    # Obtener ventas de repuestos por marca
    ventas_repuestos_marca = VentaDetalle.objects.filter(
        idventa__estado=1,
        tipo_item='repuesto',
        estado=1
    ).values(
        marca_nombre=F('id_repuesto_comprado__id_repuesto__idmarca__nombremarca')
    ).annotate(
        cantidad=Sum('cantidad')
    )

    # Combinar ambas
    marcas_dict = {}
    for item in ventas_vehiculos_marca:
        marca = item['marca_nombre']
        if marca:
            marcas_dict[marca] = marcas_dict.get(marca, 0) + item['cantidad']

    for item in ventas_repuestos_marca:
        marca = item['marca_nombre']
        if marca:
            marcas_dict[marca] = marcas_dict.get(marca, 0) + item['cantidad']

    # Preparar para donut chart (top 10)
    marcas_sorted = sorted(marcas_dict.items(), key=lambda x: x[1], reverse=True)[:10]
    ventas_marca_donut = {
        'labels': [m[0] for m in marcas_sorted],
        'series': [m[1] for m in marcas_sorted]
    }

    # ========================================
    # 6. RENDIMIENTO POR MARCA (BAR CHART)
    # ========================================
    # Ingresos por marca
    ingresos_vehiculos_marca = VentaDetalle.objects.filter(
        idventa__estado=1,
        tipo_item='vehiculo',
        estado=1
    ).values(
        marca_nombre=F('id_vehiculo__idproducto__idmarca__nombremarca')
    ).annotate(
        total=Coalesce(Sum('subtotal'), Decimal('0'), output_field=DecimalField())
    )

    ingresos_repuestos_marca = VentaDetalle.objects.filter(
        idventa__estado=1,
        tipo_item='repuesto',
        estado=1
    ).values(
        marca_nombre=F('id_repuesto_comprado__id_repuesto__idmarca__nombremarca')
    ).annotate(
        total=Coalesce(Sum('subtotal'), Decimal('0'), output_field=DecimalField())
    )

    # Combinar
    ingresos_marca_dict = {}
    for item in ingresos_vehiculos_marca:
        marca = item['marca_nombre']
        if marca:
            ingresos_marca_dict[marca] = ingresos_marca_dict.get(marca, Decimal('0')) + item['total']

    for item in ingresos_repuestos_marca:
        marca = item['marca_nombre']
        if marca:
            ingresos_marca_dict[marca] = ingresos_marca_dict.get(marca, Decimal('0')) + item['total']

    # Ordenar y tomar top 10
    ingresos_sorted = sorted(ingresos_marca_dict.items(), key=lambda x: x[1], reverse=True)[:10]
    rendimiento_marca_bar = {
        'categories': [m[0] for m in ingresos_sorted],
        'data': [float(m[1]) for m in ingresos_sorted]
    }

    # ========================================
    # 7. TOP PRODUCTOS
    # ========================================
    # Top vehículos
    top_vehiculos = VentaDetalle.objects.filter(
        idventa__estado=1,
        tipo_item='vehiculo',
        estado=1
    ).values(
        producto_nombre=F('id_vehiculo__idproducto__nomproducto')
    ).annotate(
        cantidad=Sum('cantidad'),
        total=Coalesce(Sum('subtotal'), Decimal('0'), output_field=DecimalField())
    ).order_by('-total')[:5]

    # Top repuestos
    top_repuestos = VentaDetalle.objects.filter(
        idventa__estado=1,
        tipo_item='repuesto',
        estado=1
    ).values(
        producto_nombre=F('id_repuesto_comprado__id_repuesto__nombre')
    ).annotate(
        cantidad=Sum('cantidad'),
        total=Coalesce(Sum('subtotal'), Decimal('0'), output_field=DecimalField())
    ).order_by('-total')[:5]

    # Combinar y ordenar
    top_productos_list = []
    for item in top_vehiculos:
        top_productos_list.append({
            'nombre': item['producto_nombre'],
            'cantidad': item['cantidad'],
            'total': float(item['total'])
        })
    
    for item in top_repuestos:
        top_productos_list.append({
            'nombre': item['producto_nombre'],
            'cantidad': item['cantidad'],
            'total': float(item['total'])
        })

    # Ordenar por total y tomar top 10
    top_productos_list = sorted(top_productos_list, key=lambda x: x['total'], reverse=True)[:10]

    # ========================================
    # PREPARAR CONTEXTO
    # ========================================
    data = {
        "permisos": permisos,
        'nombrecompleto': nombrecompleto,
        
        # Tarjetas
        'ventas_totales': float(ventas_mes_actual),
        'porcentaje_cambio': round(float(porcentaje_cambio), 2),
        'ventas_semana': float(ventas_semana),
        'top_categorias_semana': [(cat, float(total)) for cat, total in top_categorias_semana],
        'total_descuentos': float(total_descuentos),
        'cantidad_descuentos': cantidad_descuentos,
        
        # Variables para leyenda del gráfico
        'hoy_mes': hoy.month,
        'hoy_anio': hoy.year,
        'mes_anterior_num': inicio_mes_anterior.month,
        'mes_anterior_anio': inicio_mes_anterior.year,
        'mes_actual_nombre': hoy.strftime('%B %Y').replace('January','Enero').replace('February','Febrero').replace('March','Marzo').replace('April','Abril').replace('May','Mayo').replace('June','Junio').replace('July','Julio').replace('August','Agosto').replace('September','Septiembre').replace('October','Octubre').replace('November','Noviembre').replace('December','Diciembre'),
        'mes_anterior_nombre': inicio_mes_anterior.strftime('%B %Y').replace('January','Enero').replace('February','Febrero').replace('March','Marzo').replace('April','Abril').replace('May','Mayo').replace('June','Junio').replace('July','Julio').replace('August','Agosto').replace('September','Septiembre').replace('October','Octubre').replace('November','Noviembre').replace('December','Diciembre'),

        # Gráficos (JSON)
        'ventas_mes_chart': json.dumps(ventas_mes_chart),
        'ventas_marca_donut': json.dumps(ventas_marca_donut),
        'rendimiento_marca_bar': json.dumps(rendimiento_marca_bar),
        
        # Top productos
        'top_productos': top_productos_list,
    }

    return render(request, 'cpanel.html', data)
