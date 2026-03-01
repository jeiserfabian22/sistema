"""
Vista del módulo de Proformas (Cotizaciones Comerciales).
Permite crear, listar y generar PDF de proformas para vehículos y repuestos.
"""
import json
from datetime import date, datetime, timedelta
from decimal import Decimal
from io import BytesIO

from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse, FileResponse
from django.db import transaction

# ReportLab para generación de PDF profesional
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm, cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT, TA_JUSTIFY

# Modelos
from software.models.ProformaModel import Proforma
from software.models.ProformaDetalleModel import ProformaDetalle
from software.models.ClienteModel import Cliente
from software.models.UsuarioModel import Usuario
from software.models.VehiculosModel import Vehiculo
from software.models.ProductoModel import Producto
from software.models.RepuestoModel import Repuesto
from software.models.RespuestoCompModel import RepuestoComp
from software.models.compradetalleModel import CompraDetalle
from software.models.stockModel import Stock
from software.models.empresaModel import Empresa
from software.models.Tipo_entidadModel import TipoEntidad


# ─────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────
def _numero_proforma():
    """Genera el siguiente número correlativo de proforma (PRO-000001)."""
    ultima = Proforma.objects.order_by('-idproforma').first()
    if ultima:
        try:
            ultimo_num = int(ultima.numero_proforma.split('-')[1])
        except Exception:
            ultimo_num = 0
        nuevo_num = ultimo_num + 1
    else:
        nuevo_num = 1
    return f"PRO-{str(nuevo_num).zfill(6)}"


def _catalogo_productos(request):
    """
    Construye el catálogo de productos y repuestos con stock disponible.
    Mismo patrón que la vista de ventas.
    """
    id_almacen_session = request.session.get('id_almacen')
    productos_stock = {}
    repuestos_stock = {}

    # Vehículos
    for producto in Producto.objects.filter(estado=1):
        vehiculos = Vehiculo.objects.filter(idproducto=producto, estado=1)
        disponibles = []
        for vehiculo in vehiculos:
            if id_almacen_session:
                stock_qs = Stock.objects.filter(
                    id_almacen_id=id_almacen_session,
                    id_vehiculo=vehiculo,
                    estado=1,
                    cantidad_disponible__gt=0
                ).select_related('idcompradetalle')
                for stock_rec in stock_qs:
                    detalle = stock_rec.idcompradetalle or CompraDetalle.objects.filter(
                        id_vehiculo=vehiculo).order_by('-idcompradetalle').first()
                    if detalle:
                        disponibles.append({
                            'id_vehiculo': vehiculo.id_vehiculo,
                            'serie_motor': vehiculo.serie_motor,
                            'serie_chasis': vehiculo.serie_chasis,
                            'anio': vehiculo.anio,
                            'marca': str(producto.idmarca),
                            'color': str(producto.idcolor),
                            'cilindrada': str(producto.idcilindrada),
                            'precio_venta': float(detalle.precio_venta),
                            'precio_compra': float(detalle.precio_compra),
                            'stock_disponible': stock_rec.cantidad_disponible,
                        })
        if disponibles:
            productos_stock.setdefault(producto.nomproducto, []).extend(disponibles)

    # Repuestos
    for repuesto_obj in Repuesto.objects.filter(estado=1):
        repuestos_comp = RepuestoComp.objects.filter(id_repuesto=repuesto_obj, estado=1)
        disponibles = []
        for rc in repuestos_comp:
            if id_almacen_session:
                stock_qs = Stock.objects.filter(
                    id_almacen_id=id_almacen_session,
                    id_repuesto_comprado=rc,
                    estado=1,
                    cantidad_disponible__gt=0
                ).select_related('idcompradetalle')
                for stock_rec in stock_qs:
                    detalle = stock_rec.idcompradetalle or CompraDetalle.objects.filter(
                        id_repuesto_comprado=rc).order_by('-idcompradetalle').first()
                    if detalle:
                        disponibles.append({
                            'id_repuesto_comprado': rc.id_repuesto_comprado,
                            'codigo_barras': rc.codigo_barras if rc.codigo_barras else 'N/A',
                            'marca': str(repuesto_obj.idmarca),
                            'color': str(repuesto_obj.idcolor),
                            'precio_venta': float(detalle.precio_venta),
                            'precio_compra': float(detalle.precio_compra),
                            'stock_disponible': stock_rec.cantidad_disponible,
                        })
        if disponibles:
            repuestos_stock.setdefault(repuesto_obj.nombre, []).extend(disponibles)

    return json.dumps(productos_stock), json.dumps(repuestos_stock)


# ─────────────────────────────────────────────────
#  Vistas principales
# ─────────────────────────────────────────────────
def proformas(request):
    """Listado de proformas emitidas."""
    idusuario = request.session.get('idusuario')
    idempresa = request.session.get('idempresa')

    registros = Proforma.objects.filter(estado=1).select_related(
        'idcliente', 'idusuario'
    ).order_by('-idproforma')

    return render(request, 'proformas/proformas.html', {
        'proformas': registros,
        'idusuario': idusuario,
    })


def nueva_proforma(request):
    """Interfaz interactiva para crear una nueva proforma."""
    if request.method == 'POST':
        return _guardar_proforma(request)

    # GET: renderizar el formulario
    idusuario = request.session.get('idusuario')
    clientes = Cliente.objects.filter(estado=1)
    productos_stock_json, repuestos_stock_json = _catalogo_productos(request)

    return render(request, 'proformas/nueva_proforma.html', {
        'clientes': clientes,
        'productos_stock': productos_stock_json,
        'repuestos_stock': repuestos_stock_json,
        'idusuario': idusuario,
        'tipos_entidad': TipoEntidad.objects.filter(estado=1),
        'hoy': date.today().strftime('%Y-%m-%d'),
        'vencimiento_default': (date.today() + timedelta(days=15)).strftime('%Y-%m-%d'),
    })


@transaction.atomic
def _guardar_proforma(request):
    """Procesa y guarda la proforma recibida por POST (AJAX)."""
    try:
        idusuario_session = request.session.get('idusuario')
        idcliente_str = request.POST.get('cliente', '').strip()
        if not idcliente_str:
            return JsonResponse({'ok': False, 'error': 'Debe seleccionar un cliente.'})

        items = int(request.POST.get('items_count', 0))
        if items == 0:
            return JsonResponse({'ok': False, 'error': 'Debe agregar al menos un ítem.'})

        forma_pago  = request.POST.get('forma_pago', 'Contado')
        tiempo_entrega = request.POST.get('tiempo_entrega', 'Inmediata')
        garantia    = request.POST.get('garantia', 'Según fabricante')
        observaciones = request.POST.get('observaciones', '')
        fecha_vencimiento_str = request.POST.get('fecha_vencimiento', '')

        numero = _numero_proforma()
        idempresa = request.session.get('idempresa')

        proforma = Proforma.objects.create(
            numero_proforma=numero,
            idcliente_id=int(idcliente_str),
            idusuario_id=idusuario_session,
            fecha_vencimiento=fecha_vencimiento_str or None,
            idempresa=idempresa,
            forma_pago=forma_pago,
            tiempo_entrega=tiempo_entrega,
            garantia=garantia,
            observaciones=observaciones,
            subtotal=0,
            igv=0,
            descuento=0,
            total=0,
        )

        subtotal_total = Decimal('0')
        descuento_total = Decimal('0')

        for i in range(1, items + 1):
            tipo_item = request.POST.get(f'tipo_item_{i}')
            if not tipo_item:
                continue

            cantidad = int(request.POST.get(f'cantidad_{i}', 1))
            precio_unitario = Decimal(request.POST.get(f'precio_venta_contado_{i}', '0'))
            precio_descuento_str = request.POST.get(f'precio_descuento_{i}', '')
            precio_descuento = Decimal(precio_descuento_str) if precio_descuento_str.strip() else None

            descuento_item = Decimal('0')
            precio_final = precio_unitario
            if precio_descuento and precio_descuento < precio_unitario:
                descuento_item = (precio_unitario - precio_descuento) * cantidad
                precio_final = precio_descuento

            subtotal_item = precio_final * cantidad

            kwargs = {
                'idproforma': proforma,
                'tipo_item': tipo_item,
                'cantidad': cantidad,
                'precio_unitario': precio_unitario,
                'descuento_item': descuento_item,
                'subtotal': subtotal_item,
            }

            if tipo_item == 'vehiculo':
                id_vehiculo = request.POST.get(f'id_vehiculo_{i}', '').strip()
                if not id_vehiculo:
                    raise ValueError(f'Debe seleccionar un vehículo para el ítem {i}.')
                kwargs['id_vehiculo_id'] = int(id_vehiculo)
            elif tipo_item == 'repuesto':
                id_repuesto = request.POST.get(f'id_repuesto_{i}', '').strip()
                if not id_repuesto:
                    raise ValueError(f'Debe seleccionar un repuesto para el ítem {i}.')
                # id_repuesto = id_repuesto_comprado de la vista, obtenemos el Repuesto padre
                repuesto_comp = RepuestoComp.objects.get(id_repuesto_comprado=int(id_repuesto))
                kwargs['id_repuesto_id'] = repuesto_comp.id_repuesto_id
            else:
                continue

            ProformaDetalle.objects.create(**kwargs)
            subtotal_total += subtotal_item
            descuento_total += descuento_item

        igv_monto = (subtotal_total * Decimal('0.18')).quantize(Decimal('0.01'))
        total_final = subtotal_total + igv_monto - descuento_total

        proforma.subtotal = subtotal_total
        proforma.igv = igv_monto
        proforma.descuento = descuento_total
        proforma.total = total_final
        proforma.save()

        return JsonResponse({
            'ok': True,
            'message': f'Proforma {numero} creada correctamente.',
            'numero_proforma': numero,
            'idproforma': proforma.idproforma,
        })

    except ValueError as ve:
        return JsonResponse({'ok': False, 'error': str(ve)})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'ok': False, 'error': f'Error al guardar la proforma: {str(e)}'})


def proforma_pdf(request, idproforma):
    """
    Genera el documento PDF profesional de la proforma en formato A4.
    Diseño corporativo estilo concesionario automotriz.
    """
    proforma = get_object_or_404(Proforma, idproforma=idproforma)
    detalles = ProformaDetalle.objects.filter(idproforma=proforma).select_related(
        'id_vehiculo__idproducto__idmarca',
        'id_vehiculo__idproducto__idcolor',
        'id_vehiculo__idproducto__idcilindrada',
        'id_repuesto__idmarca',
        'id_repuesto__idcolor',
    )

    # Datos de empresa
    empresa = Empresa.objects.filter(activo=True).first()

    # ── Buffer PDF ────────────────────────────────────────────────────
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=2 * cm,
    )

    # ── Paleta de colores corporativa ─────────────────────────────────
    DARK_BLUE   = colors.HexColor('#0D1B2A')   # Fondo encabezado
    ACCENT_BLUE = colors.HexColor('#1A73E8')   # Líneas / resaltados
    SILVER      = colors.HexColor('#B0BEC5')   # Líneas suaves
    LIGHT_GRAY  = colors.HexColor('#F4F6F8')   # Fondo filas alternas
    WHITE       = colors.white
    TEXT_DARK   = colors.HexColor('#212121')   # Texto principal
    TEXT_MUTED  = colors.HexColor('#546E7A')   # Texto secundario
    GREEN       = colors.HexColor('#1B5E20')   # Total resaltado
    GOLD        = colors.HexColor('#F4A900')   # Acento dorado

    # ── Estilos ───────────────────────────────────────────────────────
    styles = getSampleStyleSheet()

    def style(name, **kwargs):
        base = styles.get(name, styles['Normal'])
        return ParagraphStyle(name + '_custom', parent=base, **kwargs)

    s_empresa      = style('Normal', fontSize=18, fontName='Helvetica-Bold', textColor=WHITE, spaceAfter=2)
    s_empresa_sub  = style('Normal', fontSize=9,  fontName='Helvetica',      textColor=SILVER, leading=13)
    s_titulo_box   = style('Normal', fontSize=9,  fontName='Helvetica-Bold', textColor=ACCENT_BLUE, spaceBefore=2, spaceAfter=1)
    s_cliente_data = style('Normal', fontSize=9,  fontName='Helvetica',      textColor=TEXT_DARK, leading=14)
    s_th           = style('Normal', fontSize=8,  fontName='Helvetica-Bold', textColor=WHITE, alignment=TA_CENTER)
    s_cell         = style('Normal', fontSize=8,  fontName='Helvetica',      textColor=TEXT_DARK, leading=11)
    s_cell_center  = style('Normal', fontSize=8,  fontName='Helvetica',      textColor=TEXT_DARK, alignment=TA_CENTER, leading=11)
    s_cell_right   = style('Normal', fontSize=8,  fontName='Helvetica',      textColor=TEXT_DARK, alignment=TA_RIGHT,  leading=11)
    s_total_label  = style('Normal', fontSize=9,  fontName='Helvetica',      textColor=TEXT_DARK, alignment=TA_RIGHT)
    s_total_final  = style('Normal', fontSize=13, fontName='Helvetica-Bold', textColor=GREEN, alignment=TA_RIGHT)
    s_condicion    = style('Normal', fontSize=8,  fontName='Helvetica',      textColor=TEXT_DARK, leading=13)
    s_nota_legal   = style('Normal', fontSize=7,  fontName='Helvetica-Oblique', textColor=TEXT_MUTED, alignment=TA_CENTER)
    s_firma_label  = style('Normal', fontSize=8,  fontName='Helvetica-Bold', textColor=TEXT_DARK, alignment=TA_CENTER)
    s_firma_sub    = style('Normal', fontSize=8,  fontName='Helvetica',      textColor=TEXT_MUTED, alignment=TA_CENTER)
    s_section_hdr  = style('Normal', fontSize=9,  fontName='Helvetica-Bold', textColor=DARK_BLUE, spaceBefore=6, spaceAfter=3)

    story = []

    # ═══════════════════════════════════════════════════════════════════
    # SECCIÓN 1: ENCABEZADO
    # ═══════════════════════════════════════════════════════════════════
    empresa_nombre = empresa.nombrecomercial if empresa else 'EMPRESA S.A.C.'
    empresa_ruc    = f"RUC: {empresa.ruc}" if empresa else 'RUC: 00000000000'
    empresa_dir    = empresa.direccion if empresa else '-'
    empresa_tel    = f"Telf.: {empresa.telefono}" if (empresa and empresa.telefono) else ''
    empresa_email  = f"Email: {empresa.pagina}" if (empresa and empresa.pagina) else ''

    col_logo = Paragraph(
        f'<font color="white" size="28">&#9670;</font>',  # rombo decorativo si no hay logo externo
        ParagraphStyle('logo_icon', fontSize=28, textColor=GOLD, alignment=TA_LEFT)
    )
    # Si la empresa tiene logo en disco, intentamos cargarlo
    logo_img = None
    if empresa and empresa.logo:
        try:
            import os
            logo_path = empresa.logo
            if os.path.exists(logo_path):
                logo_img = Image(logo_path, width=3*cm, height=2*cm, kind='proportional')
        except Exception:
            pass

    empresa_info = [
        Paragraph(empresa_nombre, s_empresa),
        Paragraph(empresa_ruc, s_empresa_sub),
        Paragraph(empresa_dir, s_empresa_sub),
        Paragraph(empresa_tel, s_empresa_sub),
        Paragraph(empresa_email, s_empresa_sub),
    ]

    proforma_info = [
        Paragraph('<font color="#F4A900"><b>PROFORMA</b></font>',
                  ParagraphStyle('pf_num', fontSize=20, fontName='Helvetica-Bold',
                                 textColor=GOLD, alignment=TA_RIGHT)),
        Paragraph(f'<b>N°: {proforma.numero_proforma}</b>',
                  ParagraphStyle('pf_n', fontSize=11, fontName='Helvetica-Bold',
                                 textColor=WHITE, alignment=TA_RIGHT)),
        Paragraph(f'Fecha: {proforma.fecha_emision.strftime("%d/%m/%Y")}',
                  ParagraphStyle('pf_d', fontSize=9, fontName='Helvetica',
                                 textColor=SILVER, alignment=TA_RIGHT)),
    ]
    if proforma.fecha_vencimiento:
        proforma_info.append(
            Paragraph(f'Válida hasta: {proforma.fecha_vencimiento.strftime("%d/%m/%Y")}',
                      ParagraphStyle('pf_v', fontSize=9, fontName='Helvetica',
                                     textColor=SILVER, alignment=TA_RIGHT))
        )

    left_col  = logo_img if logo_img else col_logo
    info_table = Table(
        [[left_col, empresa_info, proforma_info]],
        colWidths=[3 * cm, 10 * cm, 5.5 * cm]
    )
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), DARK_BLUE),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (0, 0), 10),
        ('LEFTPADDING', (1, 0), (1, 0), 8),
        ('RIGHTPADDING', (-1, 0), (-1, 0), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('ROUNDEDCORNERS', [6, 6, 6, 6]),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 8))

    # ═══════════════════════════════════════════════════════════════════
    # SECCIÓN 2: DATOS DEL CLIENTE
    # ═══════════════════════════════════════════════════════════════════
    cliente = proforma.idcliente
    cliente_rows = [
        [Paragraph('<b>DATOS DEL CLIENTE</b>',
                   ParagraphStyle('cli_hdr', fontSize=9, fontName='Helvetica-Bold',
                                  textColor=ACCENT_BLUE)), ''],
        [Paragraph('<b>Razón Social / Nombre:</b>', s_cliente_data),
         Paragraph(cliente.razonsocial or '-', s_cliente_data)],
        [Paragraph('<b>DNI / RUC:</b>', s_cliente_data),
         Paragraph(cliente.numdoc or '-', s_cliente_data)],
        [Paragraph('<b>Dirección:</b>', s_cliente_data),
         Paragraph(cliente.direccion or '-', s_cliente_data)],
        [Paragraph('<b>Teléfono:</b>', s_cliente_data),
         Paragraph(cliente.telefono or '-', s_cliente_data)],
    ]
    cli_table = Table(cliente_rows, colWidths=[5 * cm, 13.5 * cm])
    cli_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), LIGHT_GRAY),
        ('SPAN', (0, 0), (-1, 0)),
        ('BOX', (0, 0), (-1, -1), 0.8, SILVER),
        ('INNERGRID', (0, 1), (-1, -1), 0.3, SILVER),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(cli_table)
    story.append(Spacer(1, 10))

    # ─── Separar items por tipo ──────────────────────────────────────
    vehiculos_det  = [d for d in detalles if d.tipo_item == 'vehiculo']
    repuestos_det  = [d for d in detalles if d.tipo_item == 'repuesto']

    # ═══════════════════════════════════════════════════════════════════
    # SECCIÓN 3a: TABLA DE VEHÍCULOS
    # ═══════════════════════════════════════════════════════════════════
    if vehiculos_det:
        story.append(Paragraph('VEHÍCULOS', s_section_hdr))
        veh_headers = ['Ítem', 'Nombre', 'Marca', 'Color', 'Cilindrada', 'Año', 'Cant.', 'Precio Unit.', 'Subtotal']
        veh_col_w   = [1*cm, 3.5*cm, 2.5*cm, 2*cm, 2*cm, 1.5*cm, 1.2*cm, 2.5*cm, 2.3*cm]
        veh_data    = [[Paragraph(h, s_th) for h in veh_headers]]

        for idx, det in enumerate(vehiculos_det, start=1):
            prod = det.id_vehiculo.idproducto if det.id_vehiculo else None
            fila = [
                Paragraph(str(idx), s_cell_center),
                Paragraph(prod.nomproducto if prod else '-', s_cell),
                Paragraph(str(prod.idmarca) if prod else '-', s_cell),
                Paragraph(str(prod.idcolor) if prod else '-', s_cell),
                Paragraph(str(prod.idcilindrada) if prod else '-', s_cell_center),
                Paragraph(str(det.id_vehiculo.anio or '-'), s_cell_center),
                Paragraph(str(det.cantidad), s_cell_center),
                Paragraph(f'S/ {det.precio_unitario:,.2f}', s_cell_right),
                Paragraph(f'S/ {det.subtotal:,.2f}', s_cell_right),
            ]
            veh_data.append(fila)

        veh_table = Table(veh_data, colWidths=veh_col_w, repeatRows=1)
        veh_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), DARK_BLUE),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
            ('BOX', (0, 0), (-1, -1), 0.8, SILVER),
            ('INNERGRID', (0, 0), (-1, -1), 0.3, SILVER),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(veh_table)
        story.append(Spacer(1, 8))

    # ═══════════════════════════════════════════════════════════════════
    # SECCIÓN 3b: TABLA DE REPUESTOS
    # ═══════════════════════════════════════════════════════════════════
    if repuestos_det:
        story.append(Paragraph('REPUESTOS & ACCESORIOS', s_section_hdr))
        rep_headers = ['Ítem', 'Nombre', 'Marca', 'Color', 'Cant.', 'Precio Unit.', 'Subtotal']
        rep_col_w   = [1*cm, 5*cm, 3*cm, 2.5*cm, 1.5*cm, 3*cm, 2.5*cm]
        rep_data    = [[Paragraph(h, s_th) for h in rep_headers]]

        for idx, det in enumerate(repuestos_det, start=1):
            rep = det.id_repuesto
            fila = [
                Paragraph(str(idx), s_cell_center),
                Paragraph(rep.nombre if rep else '-', s_cell),
                Paragraph(str(rep.idmarca) if rep else '-', s_cell),
                Paragraph(str(rep.idcolor) if rep else '-', s_cell),
                Paragraph(str(det.cantidad), s_cell_center),
                Paragraph(f'S/ {det.precio_unitario:,.2f}', s_cell_right),
                Paragraph(f'S/ {det.subtotal:,.2f}', s_cell_right),
            ]
            rep_data.append(fila)

        rep_table = Table(rep_data, colWidths=rep_col_w, repeatRows=1)
        rep_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), DARK_BLUE),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
            ('BOX', (0, 0), (-1, -1), 0.8, SILVER),
            ('INNERGRID', (0, 0), (-1, -1), 0.3, SILVER),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(rep_table)
        story.append(Spacer(1, 8))

    # ═══════════════════════════════════════════════════════════════════
    # SECCIÓN 4: RESUMEN ECONÓMICO
    # ═══════════════════════════════════════════════════════════════════
    blank   = Paragraph('', styles['Normal'])
    summary = [
        [blank,
         Paragraph('Subtotal:', s_total_label),
         Paragraph(f'S/ {proforma.subtotal:,.2f}', s_total_label)],
        [blank,
         Paragraph('IGV (18%):', s_total_label),
         Paragraph(f'S/ {proforma.igv:,.2f}', s_total_label)],
        [blank,
         Paragraph('Descuento:', s_total_label),
         Paragraph(f'S/ {proforma.descuento:,.2f}', s_total_label)],
        [blank,
         Paragraph('<b>TOTAL:</b>', s_total_final),
         Paragraph(f'<b>S/ {proforma.total:,.2f}</b>', s_total_final)],
    ]
    sum_table = Table(summary, colWidths=[9 * cm, 5 * cm, 4.5 * cm])
    sum_table.setStyle(TableStyle([
        ('BACKGROUND', (1, 0), (2, 2), LIGHT_GRAY),
        ('BACKGROUND', (1, 3), (2, 3), colors.HexColor('#E8F5E9')),
        ('BOX', (1, 0), (2, 3), 1, ACCENT_BLUE),
        ('INNERGRID', (1, 0), (2, 3), 0.3, SILVER),
        ('LINEABOVE', (1, 3), (2, 3), 1.5, GREEN),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (1, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (1, 0), (-1, -1), 5),
        ('LEFTPADDING', (1, 0), (-1, -1), 8),
        ('RIGHTPADDING', (-1, 0), (-1, -1), 8),
    ]))
    story.append(sum_table)
    story.append(Spacer(1, 12))

    # ═══════════════════════════════════════════════════════════════════
    # SECCIÓN 5: CONDICIONES COMERCIALES
    # ═══════════════════════════════════════════════════════════════════
    story.append(HRFlowable(width='100%', thickness=0.5, color=SILVER))
    story.append(Spacer(1, 6))

    cond_data = [
        [Paragraph('<b>CONDICIONES COMERCIALES</b>',
                   ParagraphStyle('cc_hdr', fontSize=9, fontName='Helvetica-Bold',
                                  textColor=ACCENT_BLUE)), '', ''],
        [Paragraph(f'<b>Forma de pago:</b> {proforma.forma_pago}', s_condicion),
         Paragraph(f'<b>Tiempo de entrega:</b> {proforma.tiempo_entrega}', s_condicion),
         Paragraph(f'<b>Garantía:</b> {proforma.garantia}', s_condicion)],
    ]
    cond_table = Table(cond_data, colWidths=[6.1 * cm, 6.2 * cm, 6.2 * cm])
    cond_table.setStyle(TableStyle([
        ('SPAN', (0, 0), (-1, 0)),
        ('BACKGROUND', (0, 0), (-1, 0), LIGHT_GRAY),
        ('BOX', (0, 0), (-1, -1), 0.8, SILVER),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(cond_table)

    if proforma.observaciones:
        story.append(Spacer(1, 4))
        story.append(Paragraph(f'<b>Observaciones:</b> {proforma.observaciones}', s_condicion))

    story.append(Spacer(1, 6))
    story.append(Paragraph(
        '⚠  Este documento es una PROFORMA (cotización) y NO constituye comprobante de pago. '
        'Los precios son referenciales y válidos hasta la fecha indicada.',
        s_nota_legal
    ))
    story.append(Spacer(1, 16))

    # ═══════════════════════════════════════════════════════════════════
    # SECCIÓN 6: ÁREA DE FIRMA
    # ═══════════════════════════════════════════════════════════════════
    asesor = proforma.idusuario
    asesor_nombre = asesor.nombrecompleto if asesor else '___________________________'

    firma_data = [
        ['', ''],
        [Paragraph('_________________________', s_firma_label),
         Paragraph('_________________________', s_firma_label)],
        [Paragraph(asesor_nombre, s_firma_label),
         Paragraph('Sello de la Empresa', s_firma_label)],
        [Paragraph('Asesor Comercial', s_firma_sub),
         Paragraph(empresa_nombre, s_firma_sub)],
    ]
    firma_table = Table(firma_data, colWidths=[9.25 * cm, 9.25 * cm])
    firma_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('LINEBELOW', (0, 1), (0, 1), 0.8, DARK_BLUE),
        ('LINEBELOW', (1, 1), (1, 1), 0.8, DARK_BLUE),
        ('BOX', (0, 0), (-1, -1), 0.5, SILVER),
        ('ROWBACKGROUNDS', (0, 0), (-1, 0), [LIGHT_GRAY]),
    ]))
    story.append(firma_table)

    # ── Generar PDF ───────────────────────────────────────────────────
    doc.build(story)
    buffer.seek(0)

    response = FileResponse(
        buffer,
        content_type='application/pdf',
        as_attachment=False,
    )
    response['Content-Disposition'] = (
        f'inline; filename="Proforma_{proforma.numero_proforma}.pdf"'
    )
    return response


def eliminar_proforma(request, idproforma):
    """Anula (eliminación lógica) de una proforma."""
    if request.method == 'POST':
        proforma = get_object_or_404(Proforma, idproforma=idproforma)
        proforma.estado = 3  # Anulada
        proforma.save()
        return JsonResponse({'ok': True, 'message': 'Proforma anulada correctamente.'})
    return JsonResponse({'ok': False, 'error': 'Método no permitido.'}, status=405)
