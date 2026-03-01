

from django.http import JsonResponse
from software.models.detalletipousuarioxmodulosModel import Detalletipousuarioxmodulos
from software.models.empresaModel import Empresa
from software.models.sucursalesModel import Sucursales
from software.models.cajaModel import Caja
from software.models.almacenesModel import Almacenes
from software.models.UsuarioModel import Usuario
from software.models.AperturaCierreCajaModel import AperturaCierreCaja


def modulos_sidebar(request):
    """
    Context processor para agregar módulos organizados a todas las plantillas
    """
    id_tipousuario = request.session.get('idtipousuario')
    
    if not id_tipousuario:
        return {'modulos_organizados': {}}
    
    try:
        # Obtener permisos del usuario
        permisos = Detalletipousuarioxmodulos.objects.filter(
            idtipousuario=id_tipousuario
        ).select_related('idmodulo', 'idmodulo__idmodulo_padre')
        
        # Organizar módulos en estructura jerárquica
        modulos_organizados = {}
        
        for permiso in permisos:
            modulo = permiso.idmodulo
            
            # Si el módulo tiene padre
            if modulo.idmodulo_padre:
                padre = modulo.idmodulo_padre
                padre_nombre = padre.nombremodulo
                
                if padre_nombre not in modulos_organizados:
                    modulos_organizados[padre_nombre] = {
                        'padre': padre,
                        'hijos': []
                    }
                modulos_organizados[padre_nombre]['hijos'].append(modulo)
            else:
                # Es módulo padre o independiente
                if modulo.nombremodulo not in modulos_organizados:
                    modulos_organizados[modulo.nombremodulo] = {
                        'padre': modulo,
                        'hijos': []
                    }
        
        # Ordenar hijos por orden
        for nombre, grupo in modulos_organizados.items():
            grupo['hijos'].sort(key=lambda x: x.orden if x.orden is not None else 0)

        # Ordenar el diccionario principal por el orden del padre
        modulos_organizados = dict(sorted(
            modulos_organizados.items(),
            key=lambda item: item[1]['padre'].orden if item[1]['padre'].orden is not None else 0
        ))
        
        return {'modulos_organizados': modulos_organizados}
    
    except Exception as e:
        print(f"Error en context processor: {e}")
        return {'modulos_organizados': {}}
    

def empresa_context(request):
    """
    Agrega información de empresa, sucursal, caja, almacén y apertura actual
    """
    empresa = None
    sucursal = None
    caja = None
    almacen = None
    apertura_actual = None
    tiene_caja_abierta = False
    
    if request.session.get('idusuario'):
        try:
            # Obtener empresa
            idempresa = request.session.get('idempresa')
            if idempresa:
                empresa = Empresa.objects.get(idempresa=idempresa)
            
            # Obtener sucursal
            id_sucursal = request.session.get('id_sucursal')
            if id_sucursal:
                sucursal = Sucursales.objects.get(id_sucursal=id_sucursal)
            
            # Obtener caja desde la sesión
            id_caja = request.session.get('id_caja')
            if id_caja:
                caja = Caja.objects.get(id_caja=id_caja)
            
            # Obtener almacén desde la sesión
            id_almacen = request.session.get('id_almacen')
            if id_almacen:
                almacen = Almacenes.objects.get(id_almacen=id_almacen)
            
            # Obtener apertura de la caja seleccionada
            idusuario = request.session.get('idusuario')
            
            if id_caja:
                apertura_actual = AperturaCierreCaja.objects.filter(
                    idusuario_id=idusuario,
                    id_caja_id=id_caja,
                    estado__in=['abierta', 'reabierta']
                ).select_related('id_caja').first()
            else:
                apertura_actual = None

            tiene_caja_abierta = apertura_actual is not None
                
        except Exception as e:
            print(f"❌ Error en context_processor: {e}")
    
    return {
        'empresa': empresa,
        'sucursal': sucursal,
        'caja': caja,
        'almacen': almacen,
        'apertura_actual': apertura_actual,
        'tiene_caja_abierta': tiene_caja_abierta,
    }


def cambiar_contexto(request):
    """
    Permite cambiar sucursal, caja y almacén (para todos los usuarios)
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    idusuario = request.session.get('idusuario')
    es_admin = request.session.get('es_admin', False)
    
    if not idusuario:
        return JsonResponse({'error': 'No autenticado'}, status=401)
    
    # Aceptar datos JSON o POST normales
    import json
    try:
        data = json.loads(request.body)
        id_sucursal = data.get('id_sucursal')
        id_caja = data.get('id_caja')
        id_almacen = data.get('id_almacen')
    except:
        id_sucursal = request.POST.get('id_sucursal')
        id_caja = request.POST.get('id_caja')
        id_almacen = request.POST.get('id_almacen')
    
    try:
        usuario = Usuario.objects.get(idusuario=idusuario)
        
        # Actualizar sucursal
        if id_sucursal:
            if es_admin:
                # Admin puede cambiar a cualquier sucursal de su empresa
                sucursal = Sucursales.objects.get(
                    id_sucursal=id_sucursal,
                    idempresa=usuario.idempresa
                )
            else:
                # Usuario normal: verificar que sea su sucursal
                if usuario.id_sucursal and usuario.id_sucursal.id_sucursal == int(id_sucursal):
                    sucursal = usuario.id_sucursal
                else:
                    return JsonResponse({
                        'ok': False,
                        'error': 'No tienes permiso para cambiar a esta sucursal'
                    }, status=403)
            
            request.session['id_sucursal'] = sucursal.id_sucursal
            print(f"✅ Sucursal cambiada a: {sucursal.nombre_sucursal}")
        
        # Actualizar caja (sin aperturar)
        if id_caja:
            caja = Caja.objects.get(id_caja=id_caja)
            request.session['id_caja'] = caja.id_caja
            print(f"✅ Caja seleccionada: {caja.nombre_caja}")
        else:
            request.session.pop('id_caja', None)
        
        # Actualizar almacén
        if id_almacen:
            almacen = Almacenes.objects.get(id_almacen=id_almacen)
            request.session['id_almacen'] = almacen.id_almacen
            print(f"✅ Almacén seleccionado: {almacen.nombre_almacen}")
        else:
            request.session.pop('id_almacen', None)
        
        return JsonResponse({
            'ok': True,
            'success': True,
            'mensaje': 'Configuración actualizada correctamente',
            'contexto': {
                'id_sucursal': request.session.get('id_sucursal'),
                'id_caja': request.session.get('id_caja'),
                'id_almacen': request.session.get('id_almacen')
            }
        })
        
    except (Sucursales.DoesNotExist, Caja.DoesNotExist, Almacenes.DoesNotExist):
        return JsonResponse({
            'ok': False,
            'error': 'Registro no encontrado'
        }, status=404)
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'ok': False,
            'error': 'Error al cambiar contexto'
        }, status=500)


