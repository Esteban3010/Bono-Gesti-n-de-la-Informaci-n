from datetime import date, datetime
import os

from flask import Flask, render_template, request
import oracledb

app = Flask(__name__)


def conectar():
    return oracledb.connect(
        user=os.getenv("ORACLE_USER", "GRUPOBD01"),
        password=os.getenv("ORACLE_PASSWORD", "GRUPOBD01"),
        dsn=os.getenv("ORACLE_DSN", "127.0.0.1:1521/FREEPDB1"),
    )


def consultar(cursor, sql, parametros):
    cursor.execute(sql, parametros)
    columnas = [col[0].lower() for col in cursor.description]
    return [dict(zip(columnas, fila)) for fila in cursor.fetchall()]


def fecha_legible(valor, incluir_hora=False):
    if valor is None:
        return None
    if isinstance(valor, (date, datetime)):
        formato = "%d/%m/%Y %H:%M" if incluir_hora else "%d/%m/%Y"
        return valor.strftime(formato)
    return str(valor)


def calcular_edad(nacimiento):
    if not isinstance(nacimiento, (date, datetime)):
        return "No disponible"
    hoy = date.today()
    meses = (hoy.year - nacimiento.year) * 12 + hoy.month - nacimiento.month
    if hoy.day < nacimiento.day:
        meses -= 1
    if meses < 0:
        return "No disponible"
    anios, meses_restantes = divmod(meses, 12)
    if anios == 0:
        return f"{meses} meses"
    return f"{anios} {'año' if anios == 1 else 'años'}" + (
        f" y {meses_restantes} {'mes' if meses_restantes == 1 else 'meses'}"
        if meses_restantes else ""
    )


@app.template_filter("cop")
def formato_cop(valor):
    if valor is None:
        return "No registrado"
    return "$" + f"{valor:,.0f}".replace(",", ".") + " COP"


SQL_MASCOTA = """
    SELECT m.id_mascota, m.nombre, m.sexo, m.fecha_nacimiento,
           m.esterilizado, m.alergias, m.condiciones_medicas,
           r.nombre AS raza, e.nombre AS especie
    FROM MASCOTA m
    JOIN RAZA r ON r.id_raza = m.id_raza
    JOIN ESPECIE e ON e.id_especie = r.id_especie
    WHERE m.id_mascota = :id
"""

SQL_PROPIETARIOS = """
    SELECT p.id_propietario, p.nombre, p.tipo_doc, p.no_documento,
           p.telefono, p.correo, p.direccion,
           ca.nombre AS contacto_nombre,
           ca.relacion AS contacto_relacion,
           ca.telefono AS contacto_telefono
    FROM TIENE t
    JOIN PROPIETARIO p ON p.id_propietario = t.id_propietario
    LEFT JOIN CONTACTO_AUXILIAR ca
           ON ca.id_propietario = p.id_propietario
    WHERE t.id_mascota = :id
    ORDER BY p.nombre
"""

SQL_ATENCIONES = """
    SELECT a.id_atencion, a.fecha, a.estado_cita, a.peso,
           a.evaluacion, a.plan_de_manejo, a.valor_cobrado,
           s.nombre AS servicio, ts.nombre AS tipo_servicio,
           sd.direccion AS sede,
           COALESCE(ev.nombre, ep.nombre) AS profesional,
           c.motivo, c.diagnostico, c.tratamiento,
           ci.nombre AS cirugia_nombre,
           ci.estado_post AS cirugia_estado,
           h.estado AS hospital_estado, h.jaula AS hospital_jaula,
           h.hora_ingreso, h.hora_alta, h.informacion_alta,
           sp.descrp_esp AS peluqueria_detalle,
           sp.no_jaula AS peluqueria_jaula
    FROM ATENCION_SERVICIO a
    JOIN SERVICIO s ON s.id_servicio = a.id_servicio
    JOIN TIPO_SERVICIO ts ON ts.id_tipo_servicio = s.id_tipo_servicio
    JOIN SEDE sd ON sd.id_sede = a.id_sede
    LEFT JOIN EMPLEADO ev ON ev.id_empleado = a.id_veterinario_agenda
    LEFT JOIN EMPLEADO ep ON ep.id_empleado = a.id_peluquero_agenda
    LEFT JOIN CONSULTA c ON c.id_atencion = a.id_atencion
    LEFT JOIN CIRUGIA ci ON ci.id_atencion = a.id_atencion
    LEFT JOIN HOSPITALIZACION h ON h.id_atencion = a.id_atencion
    LEFT JOIN SERVICIO_PELUQUERIA sp ON sp.id_atencion = a.id_atencion
    WHERE a.id_mascota = :id
    ORDER BY a.fecha DESC, a.id_atencion DESC
"""

SQL_VACUNAS = """
    SELECT v.nombre, v.descripcion, vac.dosis,
           vac.fecha_prox_dosis, a.fecha AS fecha_aplicacion,
           a.estado_cita
    FROM ATENCION_SERVICIO a
    JOIN VACUNACION vac ON vac.id_atencion = a.id_atencion
    JOIN VACUNA v ON v.id_atencion = vac.id_atencion
    WHERE a.id_mascota = :id
    ORDER BY a.fecha DESC
"""

SQL_EXAMENES = """
    SELECT o.id_orden, a.fecha,
           ex.tipo_examen
    FROM ATENCION_SERVICIO a
    JOIN ORDEN_MEDICA o ON o.id_atencion = a.id_atencion
    JOIN ENVIA en ON en.id_orden = o.id_orden
    JOIN EXAMEN_LABORATORIO ex ON ex.tipo_examen = en.tipo_examen
    WHERE a.id_mascota = :id
    ORDER BY a.fecha DESC, o.id_orden, ex.tipo_examen
"""


@app.route("/")
def inicio():
    id_texto = request.args.get("id", "").strip()
    mascota = None
    propietarios = []
    atenciones = []
    vacunas = []
    examenes = []
    error = None

    if id_texto:
        if not id_texto.isdecimal() or int(id_texto) < 1:
            error = "Ingresa un ID de mascota válido (número mayor que cero)."
        else:
            id_mascota = int(id_texto)
            parametros = {"id": id_mascota}
            try:
                with conectar() as conexion:
                    with conexion.cursor() as cursor:
                        filas = consultar(cursor, SQL_MASCOTA, parametros)
                        if filas:
                            mascota = filas[0]
                            propietarios = consultar(cursor, SQL_PROPIETARIOS, parametros)
                            atenciones = consultar(cursor, SQL_ATENCIONES, parametros)
                            vacunas = consultar(cursor, SQL_VACUNAS, parametros)
                            examenes = consultar(cursor, SQL_EXAMENES, parametros)

                if mascota is None:
                    error = f"No se encontró una mascota con el ID {id_mascota}."
                else:
                    mascota["edad"] = calcular_edad(mascota["fecha_nacimiento"])
                    mascota["nacimiento_texto"] = fecha_legible(mascota["fecha_nacimiento"])
                    mascota["sexo_texto"] = {"M": "Macho", "F": "Hembra", "O": "Otro"}.get(
                        mascota["sexo"], mascota["sexo"]
                    )
                    mascota["esterilizado_texto"] = (
                        "Sí" if mascota["esterilizado"] == 1 else "No"
                    )

                    for atencion in atenciones:
                        atencion["fecha_texto"] = fecha_legible(atencion["fecha"], True)
                        atencion["ingreso_texto"] = fecha_legible(atencion["hora_ingreso"], True)
                        atencion["alta_texto"] = fecha_legible(atencion["hora_alta"], True)
                    for vacuna in vacunas:
                        vacuna["aplicacion_texto"] = fecha_legible(vacuna["fecha_aplicacion"])
                        vacuna["proxima_texto"] = fecha_legible(vacuna["fecha_prox_dosis"])
                    for examen in examenes:
                        examen["fecha_texto"] = fecha_legible(examen["fecha"])

            except oracledb.Error:
                app.logger.exception("Error consultando la ficha de mascota en Oracle")
                error = "No se pudo consultar Oracle. Comprueba el túnel, la conexión y las tablas."

    return render_template(
        "index.html",
        id_buscado=id_texto,
        mascota=mascota,
        propietarios=propietarios,
        atenciones=atenciones,
        vacunas=vacunas,
        examenes=examenes,
        error=error,
    )


app.run(debug=False)
