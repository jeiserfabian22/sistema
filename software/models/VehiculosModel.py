from django.db import models

from software.models.ProductoModel import Producto
from software.models.estadoproductoModel import EstadoProducto


class Vehiculo(models.Model):
    id_vehiculo = models.AutoField(primary_key=True,  db_column='id_vehiculo')
    idproducto = models.ForeignKey(Producto, on_delete=models.DO_NOTHING, db_column='idproducto', related_name='vehiculos')
    idestadoproducto = models.ForeignKey(EstadoProducto, on_delete=models.DO_NOTHING, db_column='idestadoproducto', related_name='vehiculos')
    imperfecciones = models.TextField(blank=True)
    placas = models.TextField(blank=True)
    serie_chasis = models.CharField(max_length=50)
    serie_motor = models.CharField(max_length=50)
    anio = models.PositiveIntegerField(null=True, blank=True)
    estado = models.IntegerField(db_column='estado')


    class Meta:
        managed = True 
        db_table = 'vehiculos'


        