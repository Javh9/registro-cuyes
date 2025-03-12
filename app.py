from flask import Flask, render_template, request, redirect, url_for, flash, Response
import psycopg2
from psycopg2 import extras
from datetime import datetime
import os
import pandas as pd
from urllib.parse import urlparse
import io

# Inicializar la aplicación Flask
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'una_clave_secreta_muy_larga_y_compleja')

# Función para obtener la conexión a la base de datos
def get_db_connection():
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        raise ValueError("No se ha configurado DATABASE_URL")

    url = urlparse(database_url)
    conn = psycopg2.connect(
        dbname=url.path[1:],  # Eliminar el '/' inicial
        user=url.username,
        password=url.password,
        host=url.hostname,
        port=url.port
    )
    return conn

# Función para validar valores positivos
def validate_positive_values(**kwargs):
    for key, value in kwargs.items():
        if value < 0:
            raise ValueError(f"{key} no puede ser negativo")

# Función para crear o actualizar las tablas en la base de datos
def crear_o_actualizar_tablas():
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            # Crear tabla de reproductores si no existe
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS reproductores (
                    id SERIAL PRIMARY KEY,
                    galpon TEXT NOT NULL,
                    poza TEXT NOT NULL,
                    hembras INTEGER NOT NULL,
                    machos INTEGER NOT NULL,
                    tiempo_reproductores INTEGER NOT NULL,
                    fecha_ingreso TEXT NOT NULL
                )
            ''')

            # Crear tabla de partos si no existe
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS partos (
                    id SERIAL PRIMARY KEY,
                    galpon TEXT NOT NULL,
                    poza TEXT NOT NULL,
                    numero_parto INTEGER NOT NULL,
                    nacidos INTEGER NOT NULL,
                    muertos_bebes INTEGER NOT NULL,
                    muertos_reproductores INTEGER NOT NULL,
                    fecha_nacimiento TEXT NOT NULL
                )
            ''')

            # Crear tabla de destetes si no existe
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS destetes (
                    id SERIAL PRIMARY KEY,
                    galpon TEXT NOT NULL,
                    poza TEXT NOT NULL,
                    destetados_hembras INTEGER NOT NULL,
                    destetados_machos INTEGER NOT NULL,
                    fecha_destete TEXT NOT NULL
                )
            ''')

            # Crear tabla de muertes de destetados si no existe
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS muertes_destetados (
                    id SERIAL PRIMARY KEY,
                    galpon TEXT NOT NULL,
                    poza TEXT NOT NULL,
                    muertos_hembras INTEGER NOT NULL,
                    muertos_machos INTEGER NOT NULL,
                    fecha_muerte TEXT NOT NULL
                )
            ''')

            # Crear tabla de ventas de destetados si no existe
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ventas_destetados (
                    id SERIAL PRIMARY KEY,
                    galpon TEXT NOT NULL,
                    poza TEXT NOT NULL,
                    hembras_vendidas INTEGER NOT NULL,
                    machos_vendidos INTEGER NOT NULL,
                    costo_venta REAL NOT NULL,
                    fecha_venta TEXT NOT NULL
                )
            ''')

            # Crear tabla de ventas de descarte si no existe
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ventas_descarte (
                    id SERIAL PRIMARY KEY,
                    galpon TEXT NOT NULL,
                    poza TEXT NOT NULL,
                    cuyes_vendidos INTEGER NOT NULL,
                    costo_venta REAL NOT NULL,
                    fecha_venta TEXT NOT NULL
                )
            ''')

            # Crear tabla de gastos si no existe
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS gastos (
                    id SERIAL PRIMARY KEY,
                    descripcion TEXT NOT NULL,
                    monto REAL NOT NULL,
                    tipo TEXT NOT NULL,
                    fecha_gasto TEXT NOT NULL
                )
            ''')

            conn.commit()

# Llamar a la función para crear o actualizar las tablas al iniciar la aplicación
crear_o_actualizar_tablas()

# Ruta principal
@app.route('/')
def index():
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                # Obtener datos de reproductores por galpón y poza
                cursor.execute('''
                    SELECT galpon, poza, SUM(hembras + machos) AS total_reproductores
                    FROM reproductores
                    GROUP BY galpon, poza
                    ORDER BY galpon, CAST(poza AS INTEGER)
                ''')
                reproductores_por_poza = cursor.fetchall()

                # Obtener datos de nacidos y muertos por galpón y poza
                cursor.execute('''
                    SELECT p.galpon, p.poza, 
                           SUM(p.nacidos) AS total_nacidos,
                           COALESCE(SUM(m.muertos_hembras + m.muertos_machos), 0) AS total_muertos
                    FROM partos p
                    LEFT JOIN muertes_destetados m ON p.galpon = m.galpon AND p.poza = m.poza
                    GROUP BY p.galpon, p.poza
                    ORDER BY p.galpon, CAST(p.poza AS INTEGER)
                ''')
                nacidos_y_muertos_por_poza = cursor.fetchall()

        # Combinar los datos de reproductores, nacidos y muertos
        datos_galpones = {}
        total_reproductores_por_galpon = {}
        total_nacidos_por_galpon = {}
        total_muertos_por_galpon = {}

        for row in reproductores_por_poza:
            galpon = row['galpon']
            poza = row['poza']
            if galpon not in datos_galpones:
                datos_galpones[galpon] = {}
                total_reproductores_por_galpon[galpon] = 0
                total_nacidos_por_galpon[galpon] = 0
                total_muertos_por_galpon[galpon] = 0

            datos_galpones[galpon][poza] = {
                'reproductores': row['total_reproductores'],
                'nacidos': 0,
                'muertos': 0
            }
            total_reproductores_por_galpon[galpon] += row['total_reproductores']

        for row in nacidos_y_muertos_por_poza:
            galpon = row['galpon']
            poza = row['poza']
            if galpon in datos_galpones and poza in datos_galpones[galpon]:
                # Asegurarse de que los valores sean números válidos
                total_nacidos = int(row['total_nacidos']) if row['total_nacidos'] else 0
                total_muertos = int(row['total_muertos']) if row['total_muertos'] else 0

                datos_galpones[galpon][poza]['nacidos'] = total_nacidos - total_muertos
                datos_galpones[galpon][poza]['muertos'] = total_muertos
                total_nacidos_por_galpon[galpon] += (total_nacidos - total_muertos)
                total_muertos_por_galpon[galpon] += total_muertos

        return render_template(
            'index.html',
            datos_galpones=datos_galpones,
            total_reproductores_por_galpon=total_reproductores_por_galpon,
            total_nacidos_por_galpon=total_nacidos_por_galpon,
            total_muertos_por_galpon=total_muertos_por_galpon
        )
    except Exception as e:
        error_message = f'Ocurrió un error inesperado: {str(e)}'
        return render_template('error.html', error_message=error_message)
    
# Ruta para ingresar reproductores
@app.route('/ingresar_reproductores', methods=['GET', 'POST'])
def ingresar_reproductores():
    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            galpon = request.form['galpon']
            poza = request.form['poza']
            hembras = int(request.form['hembras'])
            machos = int(request.form['machos'])
            tiempo_reproductores = int(request.form['tiempo_reproductores'])

            # Validar que los valores sean positivos
            validate_positive_values(hembras=hembras, machos=machos, tiempo_reproductores=tiempo_reproductores)

            # Insertar datos en la base de datos
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                    cursor.execute('''
                        INSERT INTO reproductores (
                            galpon, poza, hembras, machos, tiempo_reproductores, fecha_ingreso
                        ) VALUES (%s, %s, %s, %s, %s, %s)
                    ''', (galpon, poza, hembras, machos, tiempo_reproductores, datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')))

                    conn.commit()
                    flash('Reproductores registrados correctamente.', 'success')
                    return redirect(url_for('index'))

        except ValueError as e:
            flash(f'Error en los datos ingresados: {str(e)}', 'danger')
        except psycopg2.Error as e:
            flash(f'Error en la base de datos: {str(e)}', 'danger')
        except Exception as e:
            flash(f'Ocurrió un error inesperado: {str(e)}', 'danger')

    return render_template('ingresar_reproductores.html')

# Ruta para registrar partos
@app.route('/registrar_partos', methods=['GET', 'POST'])
def registrar_partos():
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            cursor.execute('SELECT DISTINCT galpon, poza FROM reproductores')
            galpones_pozas = cursor.fetchall()

    if request.method == 'POST':
        try:
            galpon = request.form['galpon']
            poza = request.form['poza']
            numero_parto = int(request.form['numero_parto'])
            nacidos = int(request.form['nacidos'])
            muertos_bebes = int(request.form['muertos_bebes'])
            muertos_reproductores = int(request.form['muertos_reproductores'])

            validate_positive_values(numero_parto=numero_parto, nacidos=nacidos, muertos_bebes=muertos_bebes, muertos_reproductores=muertos_reproductores)

            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                    cursor.execute('''
                        SELECT id FROM reproductores
                        WHERE galpon = %s AND poza = %s
                    ''', (galpon, poza))
                    if not cursor.fetchone():
                        flash('El galpón y la poza no están registrados.', 'danger')
                        return render_template('registrar_partos.html', galpones_pozas=galpones_pozas, galpon_seleccionado=galpon, poza_seleccionada=poza)

                    cursor.execute('''
                        INSERT INTO partos (
                            galpon, poza, numero_parto, nacidos, muertos_bebes, muertos_reproductores, fecha_nacimiento
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ''', (galpon, poza, numero_parto, nacidos, muertos_bebes, muertos_reproductores, datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')))

                    conn.commit()
                    flash('Parto registrado correctamente.', 'success')
                    return redirect(url_for('index'))
        except ValueError as e:
            flash(f'Error en los datos ingresados: {str(e)}', 'danger')
        except psycopg2.Error as e:
            flash(f'Error en la base de datos: {str(e)}', 'danger')
        except Exception as e:
            flash(f'Ocurrió un error inesperado: {str(e)}', 'danger')

    return render_template('registrar_partos.html', galpones_pozas=galpones_pozas)

# Ruta para registrar destete
@app.route('/registrar_destete', methods=['GET', 'POST'])
def registrar_destete():
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            cursor.execute('SELECT DISTINCT galpon, poza FROM reproductores')
            galpones_pozas = cursor.fetchall()

    if request.method == 'POST':
        try:
            galpon = request.form['galpon']
            poza = request.form['poza']
            destetados_hembras = int(request.form['destetados_hembras'])
            destetados_machos = int(request.form['destetados_machos'])

            validate_positive_values(destetados_hembras=destetados_hembras, destetados_machos=destetados_machos)

            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                    cursor.execute('''
                        SELECT id FROM reproductores
                        WHERE galpon = %s AND poza = %s
                    ''', (galpon, poza))
                    if not cursor.fetchone():
                        flash('El galpón y la poza no están registrados.', 'danger')
                        return render_template('registrar_destete.html', galpones_pozas=galpones_pozas, galpon_seleccionado=galpon, poza_seleccionada=poza)

                    cursor.execute('''
                        INSERT INTO destetes (
                            galpon, poza, destetados_hembras, destetados_machos, fecha_destete
                        ) VALUES (%s, %s, %s, %s, %s)
                    ''', (galpon, poza, destetados_hembras, destetados_machos, datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')))

                    conn.commit()
                    flash('Destete registrado correctamente.', 'success')
                    return redirect(url_for('index'))
        except ValueError as e:
            flash(f'Error en los datos ingresados: {str(e)}', 'danger')
        except psycopg2.Error as e:
            flash(f'Error en la base de datos: {str(e)}', 'danger')
        except Exception as e:
            flash(f'Ocurrió un error inesperado: {str(e)}', 'danger')

    return render_template('registrar_destete.html', galpones_pozas=galpones_pozas)

# Ruta para registrar muertes de destetados
@app.route('/registrar_muertes_destetados', methods=['GET', 'POST'])
def registrar_muertes_destetados():
    if request.method == 'POST':
        try:
            galpon = request.form['galpon']
            poza = request.form['poza']
            muertos_hembras = int(request.form['muertos_hembras'])
            muertos_machos = int(request.form['muertos_machos'])

            validate_positive_values(muertos_hembras=muertos_hembras, muertos_machos=muertos_machos)

            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                    cursor.execute('''
                        SELECT id FROM reproductores
                        WHERE galpon = %s AND poza = %s
                    ''', (galpon, poza))
                    if not cursor.fetchone():
                        flash('El galpón y la poza no están registrados.', 'danger')
                        return redirect(url_for('registrar_muertes_destetados'))

                    cursor.execute('''
                        INSERT INTO muertes_destetados (
                            galpon, poza, muertos_hembras, muertos_machos, fecha_muerte
                        ) VALUES (%s, %s, %s, %s, %s)
                    ''', (galpon, poza, muertos_hembras, muertos_machos, datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')))

                    conn.commit()
                    flash('Muertes de destetados registradas correctamente.', 'success')
                    return redirect(url_for('index'))
        except ValueError as e:
            flash(f'Error en los datos ingresados: {str(e)}', 'danger')
        except psycopg2.Error as e:
            flash(f'Error en la base de datos: {str(e)}', 'danger')
        except Exception as e:
            flash(f'Ocurrió un error inesperado: {str(e)}', 'danger')

    return render_template('registrar_muertes_destetados.html')

# Ruta para registrar ventas de destetados
@app.route('/registrar_ventas_destetados', methods=['GET', 'POST'])
def registrar_ventas_destetados():
    if request.method == 'POST':
        try:
            galpon = request.form['galpon']
            poza = request.form['poza']
            hembras_vendidas = int(request.form['hembras_vendidas'])
            machos_vendidos = int(request.form['machos_vendidos'])
            costo_venta = float(request.form['costo_venta'])

            validate_positive_values(hembras_vendidas=hembras_vendidas, machos_vendidos=machos_vendidos, costo_venta=costo_venta)

            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                    cursor.execute('''
                        SELECT id FROM reproductores
                        WHERE galpon = %s AND poza = %s
                    ''', (galpon, poza))
                    if not cursor.fetchone():
                        flash('El galpón y la poza no están registrados.', 'danger')
                        return redirect(url_for('registrar_ventas_destetados'))

                    cursor.execute('''
                        INSERT INTO ventas_destetados (
                            galpon, poza, hembras_vendidas, machos_vendidos, costo_venta, fecha_venta
                        ) VALUES (%s, %s, %s, %s, %s, %s)
                    ''', (galpon, poza, hembras_vendidas, machos_vendidos, costo_venta, datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')))

                    conn.commit()
                    flash('Ventas de destetados registradas correctamente.', 'success')
                    return redirect(url_for('index'))
        except ValueError as e:
            flash(f'Error en los datos ingresados: {str(e)}', 'danger')
        except psycopg2.Error as e:
            flash(f'Error en la base de datos: {str(e)}', 'danger')
        except Exception as e:
            flash(f'Ocurrió un error inesperado: {str(e)}', 'danger')

    return render_template('registrar_ventas_destetados.html')

# Ruta para registrar ventas de descarte
@app.route('/registrar_ventas_descarte', methods=['GET', 'POST'])
def registrar_ventas_descarte():
    if request.method == 'POST':
        try:
            galpon = request.form['galpon']
            poza = request.form['poza']
            cuyes_vendidos = int(request.form['cuyes_vendidos'])
            costo_venta = float(request.form['costo_venta'])

            validate_positive_values(cuyes_vendidos=cuyes_vendidos, costo_venta=costo_venta)

            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                    cursor.execute('''
                        SELECT id FROM reproductores
                        WHERE galpon = %s AND poza = %s
                    ''', (galpon, poza))
                    if not cursor.fetchone():
                        flash('El galpón y la poza no están registrados.', 'danger')
                        return redirect(url_for('registrar_ventas_descarte'))

                    cursor.execute('''
                        INSERT INTO ventas_descarte (
                            galpon, poza, cuyes_vendidos, costo_venta, fecha_venta
                        ) VALUES (%s, %s, %s, %s, %s)
                    ''', (galpon, poza, cuyes_vendidos, costo_venta, datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')))

                    conn.commit()
                    flash('Ventas de descarte registradas correctamente.', 'success')
                    return redirect(url_for('index'))
        except ValueError as e:
            flash(f'Error en los datos ingresados: {str(e)}', 'danger')
        except psycopg2.Error as e:
            flash(f'Error en la base de datos: {str(e)}', 'danger')
        except Exception as e:
            flash(f'Ocurrió un error inesperado: {str(e)}', 'danger')

    return render_template('registrar_ventas_descarte.html')

# Ruta para registrar gastos
@app.route('/registrar_gastos', methods=['GET', 'POST'])
def registrar_gastos():
    if request.method == 'POST':
        try:
            descripcion = request.form['descripcion']
            monto = float(request.form['monto'])
            tipo = request.form['tipo']

            validate_positive_values(monto=monto)

            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                    cursor.execute('''
                        INSERT INTO gastos (
                            descripcion, monto, tipo, fecha_gasto
                        ) VALUES (%s, %s, %s, %s)
                    ''', (descripcion, monto, tipo, datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')))

                    conn.commit()
                    flash('Gasto registrado correctamente.', 'success')
                    return redirect(url_for('index'))
        except ValueError as e:
            flash(f'Error en los datos ingresados: {str(e)}', 'danger')
        except psycopg2.Error as e:
            flash(f'Error en la base de datos: {str(e)}', 'danger')
        except Exception as e:
            flash(f'Ocurrió un error inesperado: {str(e)}', 'danger')

    return render_template('registrar_gastos.html')

# Ruta para ver análisis de datos
@app.route('/analisis_datos')
def analisis_datos():
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                cursor.execute('''
                    SELECT 
                        r.id AS reproductor_id,
                        r.galpon AS galpon_reproductor,
                        r.poza AS poza_reproductor,
                        r.hembras AS hembras_reproductor,
                        r.machos AS machos_reproductor,
                        r.tiempo_reproductores,
                        r.fecha_ingreso,
                        p.id AS parto_id,
                        p.numero_parto,
                        p.nacidos,
                        p.muertos_bebes,
                        p.muertos_reproductores,
                        p.fecha_nacimiento,
                        d.id AS destete_id,
                        d.destetados_hembras,
                        d.destetados_machos,
                        d.fecha_destete,
                        m.id AS muerte_id,
                        m.muertos_hembras AS muertes_hembras,
                        m.muertos_machos AS muertes_machos,
                        m.fecha_muerte,
                        vd.id AS venta_destetado_id,
                        vd.hembras_vendidas,
                        vd.machos_vendidos,
                        vd.costo_venta AS costo_venta_destetados,
                        vd.fecha_venta AS fecha_venta_destetados,
                        vc.id AS venta_descarte_id,
                        vc.cuyes_vendidos,
                        vc.costo_venta AS costo_venta_descarte,
                        vc.fecha_venta AS fecha_venta_descarte
                    FROM reproductores r
                    LEFT JOIN partos p ON r.galpon = p.galpon AND r.poza = p.poza
                    LEFT JOIN destetes d ON r.galpon = d.galpon AND r.poza = d.poza
                    LEFT JOIN muertes_destetados m ON r.galpon = m.galpon AND r.poza = m.poza
                    LEFT JOIN ventas_destetados vd ON r.galpon = vd.galpon AND r.poza = vd.poza
                    LEFT JOIN ventas_descarte vc ON r.galpon = vc.galpon AND r.poza = vc.poza
                ''')
                datos = cursor.fetchall()

                cursor.execute('SELECT descripcion, monto, tipo, fecha_gasto FROM gastos')
                gastos = cursor.fetchall()

        return render_template('analisis_datos.html', datos=datos, gastos=gastos)
    except Exception as e:
        flash(f'Ocurrió un error inesperado: {str(e)}', 'danger')
        return render_template('error.html')

# Ruta para ver el balance
@app.route('/balance')
def balance():
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                cursor.execute('SELECT SUM(costo_venta) FROM ventas_destetados')
                total_ventas_destetados = cursor.fetchone()[0] or 0

                cursor.execute('SELECT SUM(costo_venta) FROM ventas_descarte')
                total_ventas_descarte = cursor.fetchone()[0] or 0

                cursor.execute('SELECT SUM(monto) FROM gastos')
                total_gastos = cursor.fetchone()[0] or 0

                balance = (total_ventas_destetados + total_ventas_descarte) - total_gastos

        return render_template('balance.html', 
                             total_ventas_destetados=total_ventas_destetados,
                             total_ventas_descarte=total_ventas_descarte,
                             total_gastos=total_gastos,
                             balance=balance)
    except Exception as e:
        flash(f'Ocurrió un error inesperado: {str(e)}', 'danger')
        return render_template('error.html')

# Ruta para ver resultados
@app.route('/resultados')
def resultados():
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                # Obtener todos los datos de las tablas
                cursor.execute('SELECT * FROM reproductores')
                reproductores = cursor.fetchall()

                cursor.execute('SELECT * FROM partos')
                partos = cursor.fetchall()

                cursor.execute('SELECT * FROM destetes')
                destetes = cursor.fetchall()

                cursor.execute('SELECT * FROM muertes_destetados')
                muertes_destetados = cursor.fetchall()

                cursor.execute('SELECT * FROM ventas_destetados')
                ventas_destetados = cursor.fetchall()

                cursor.execute('SELECT * FROM ventas_descarte')
                ventas_descarte = cursor.fetchall()

                cursor.execute('SELECT * FROM gastos')
                gastos = cursor.fetchall()

                # Análisis estadístico
                # 1. Mortalidad por mes y poza/galpón
                cursor.execute('''
                    SELECT 
                        DATE_TRUNC('month', TO_DATE(fecha_muerte, 'YYYY-MM-DD')) AS mes,
                        galpon,
                        poza,
                        SUM(muertos_hembras + muertos_machos) AS total_muertes
                    FROM muertes_destetados
                    GROUP BY mes, galpon, poza
                    ORDER BY mes, galpon, poza
                ''')
                mortalidad_por_mes = cursor.fetchall()

                # 2. Nacimientos por mes y poza/galpón
                cursor.execute('''
                    SELECT 
                        DATE_TRUNC('month', TO_DATE(fecha_nacimiento, 'YYYY-MM-DD')) AS mes,
                        galpon,
                        poza,
                        SUM(nacidos) AS total_nacidos
                    FROM partos
                    GROUP BY mes, galpon, poza
                    ORDER BY mes, galpon, poza
                ''')
                nacimientos_por_mes = cursor.fetchall()

                # 3. Costos y ganancias por mes
                cursor.execute('''
                    SELECT 
                        DATE_TRUNC('month', TO_DATE(fecha_gasto, 'YYYY-MM-DD')) AS mes,
                        SUM(monto) AS total_gastos
                    FROM gastos
                    GROUP BY mes
                    ORDER BY mes
                ''')
                gastos_por_mes = cursor.fetchall()

                cursor.execute('''
                    SELECT 
                        DATE_TRUNC('month', TO_DATE(fecha_venta, 'YYYY-MM-DD')) AS mes,
                        SUM(costo_venta) AS total_ventas
                    FROM ventas_destetados
                    GROUP BY mes
                    ORDER BY mes
                ''')
                ventas_destetados_por_mes = cursor.fetchall()

                cursor.execute('''
                    SELECT 
                        DATE_TRUNC('month', TO_DATE(fecha_venta, 'YYYY-MM-DD')) AS mes,
                        SUM(costo_venta) AS total_ventas
                    FROM ventas_descarte
                    GROUP BY mes
                    ORDER BY mes
                ''')
                ventas_descarte_por_mes = cursor.fetchall()

                # 4. Proyección de crecimiento (usando Pandas)
                cursor.execute('''
                    SELECT 
                        DATE_TRUNC('month', TO_DATE(fecha_nacimiento, 'YYYY-MM-DD')) AS mes,
                        SUM(nacidos) AS total_nacidos
                    FROM partos
                    GROUP BY mes
                    ORDER BY mes
                ''')
                proyeccion_nacimientos = cursor.fetchall()

                cursor.execute('''
                    SELECT 
                        DATE_TRUNC('month', TO_DATE(fecha_venta, 'YYYY-MM-DD')) AS mes,
                        SUM(costo_venta) AS total_ventas
                    FROM ventas_destetados
                    GROUP BY mes
                    ORDER BY mes
                ''')
                proyeccion_ventas = cursor.fetchall()

                # Convertir a DataFrame de Pandas para proyecciones
                df_nacimientos = pd.DataFrame(proyeccion_nacimientos, columns=['mes', 'total_nacidos'])
                df_ventas = pd.DataFrame(proyeccion_ventas, columns=['mes', 'total_ventas'])

                # Verificar y limpiar fechas
                df_nacimientos['mes'] = pd.to_datetime(df_nacimientos['mes'], errors='coerce')
                df_ventas['mes'] = pd.to_datetime(df_ventas['mes'], errors='coerce')

                # Eliminar filas con fechas NaT
                df_nacimientos = df_nacimientos.dropna(subset=['mes'])
                df_ventas = df_ventas.dropna(subset=['mes'])

                # Verificar que haya datos para proyección
                if df_nacimientos.empty or df_ventas.empty:
                    flash('No hay suficientes datos para realizar la proyección.', 'warning')
                    return redirect(url_for('index'))

                # Calcular proyección para los próximos 6 meses
                future_months = pd.date_range(start=df_nacimientos['mes'].max(), periods=6, freq='M')
                df_future = pd.DataFrame({'mes': future_months})

                # Proyección de nacimientos (regresión lineal)
                df_nacimientos.set_index('mes', inplace=True)
                df_nacimientos['proyeccion_nacidos'] = df_nacimientos['total_nacidos'].interpolate(method='linear')
                df_future['proyeccion_nacidos'] = df_nacimientos['proyeccion_nacidos'].iloc[-1]  # Extender la tendencia

                # Proyección de ventas (regresión lineal)
                df_ventas.set_index('mes', inplace=True)
                df_ventas['proyeccion_ventas'] = df_ventas['total_ventas'].interpolate(method='linear')
                df_future['proyeccion_ventas'] = df_ventas['proyeccion_ventas'].iloc[-1]  # Extender la tendencia

                # Convertir proyecciones a lista para la plantilla
                proyeccion_futura = df_future.reset_index(drop=True).to_dict('records')

        # Pasar todos los datos a la plantilla
        return render_template('resultados.html', 
                             reproductores=reproductores,
                             partos=partos,
                             destetes=destetes,
                             muertes_destetados=muertes_destetados,
                             ventas_destetados=ventas_destetados,
                             ventas_descarte=ventas_descarte,
                             gastos=gastos,
                             mortalidad_por_mes=mortalidad_por_mes,
                             nacimientos_por_mes=nacimientos_por_mes,
                             gastos_por_mes=gastos_por_mes,
                             ventas_destetados_por_mes=ventas_destetados_por_mes,
                             ventas_descarte_por_mes=ventas_descarte_por_mes,
                             proyeccion_nacimientos=proyeccion_nacimientos,
                             proyeccion_ventas=proyeccion_ventas,
                             proyeccion_futura=proyeccion_futura)
    except Exception as e:
        flash(f'Ocurrió un error inesperado: {str(e)}', 'danger')
        return render_template('error.html')

# Ruta para editar datos de reproductores
@app.route('/editar_reproductor/<int:id>', methods=['GET', 'POST'])
def editar_reproductor(id):
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            if request.method == 'POST':
                try:
                    galpon = request.form['galpon']
                    poza = request.form['poza']
                    hembras = int(request.form['hembras'])
                    machos = int(request.form['machos'])
                    tiempo_reproductores = int(request.form['tiempo_reproductores'])

                    validate_positive_values(hembras=hembras, machos=machos, tiempo_reproductores=tiempo_reproductores)

                    cursor.execute('''
                        UPDATE reproductores
                        SET galpon = %s, poza = %s, hembras = %s, machos = %s, tiempo_reproductores = %s
                        WHERE id = %s
                    ''', (galpon, poza, hembras, machos, tiempo_reproductores, id))

                    conn.commit()
                    flash('Reproductor actualizado correctamente.', 'success')
                    return redirect(url_for('analisis_datos'))
                except ValueError as e:
                    flash(f'Error en los datos ingresados: {str(e)}', 'danger')
                except psycopg2.Error as e:
                    flash(f'Error en la base de datos: {str(e)}', 'danger')
                except Exception as e:
                    flash(f'Ocurrió un error inesperado: {str(e)}', 'danger')

            cursor.execute('SELECT * FROM reproductores WHERE id = %s', (id,))
            reproductor = cursor.fetchone()

    if reproductor is None:
        flash('Reproductor no encontrado.', 'danger')
        return redirect(url_for('analisis_datos'))

    return render_template('editar_reproductor.html', reproductor=reproductor)

# Ruta para eliminar todos los datos
@app.route('/eliminar_todos_los_datos', methods=['POST'])
def eliminar_todos_los_datos():
    clave_ingresada = request.form.get('clave')
    CLAVE_AUTORIZACION = "0429"

    if clave_ingresada != CLAVE_AUTORIZACION:
        flash('Clave incorrecta. No se han eliminado los datos.', 'danger')
        return redirect(url_for('index'))

    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                cursor.execute('DELETE FROM reproductores')
                cursor.execute('DELETE FROM partos')
                cursor.execute('DELETE FROM destetes')
                cursor.execute('DELETE FROM muertes_destetados')
                cursor.execute('DELETE FROM ventas_destetados')
                cursor.execute('DELETE FROM ventas_descarte')
                cursor.execute('DELETE FROM gastos')

                conn.commit()
                flash('Todos los datos han sido eliminados correctamente.', 'success')
    except Exception as e:
        flash(f'Ocurrió un error inesperado: {str(e)}', 'danger')

    return redirect(url_for('index'))

# Ruta para Exportar a Excel
@app.route('/exportar_excel')
def exportar_excel():
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                # Obtener todos los datos de las tablas
                cursor.execute('SELECT * FROM reproductores')
                reproductores = cursor.fetchall()

                cursor.execute('SELECT * FROM partos')
                partos = cursor.fetchall()

                cursor.execute('SELECT * FROM destetes')
                destetes = cursor.fetchall()

                cursor.execute('SELECT * FROM muertes_destetados')
                muertes_destetados = cursor.fetchall()

                cursor.execute('SELECT * FROM ventas_destetados')
                ventas_destetados = cursor.fetchall()

                cursor.execute('SELECT * FROM ventas_descarte')
                ventas_descarte = cursor.fetchall()

                cursor.execute('SELECT * FROM gastos')
                gastos = cursor.fetchall()

                # Crear un DataFrame de Pandas
                df_reproductores = pd.DataFrame(reproductores)
                df_partos = pd.DataFrame(partos)
                df_destetes = pd.DataFrame(destetes)
                df_muertes = pd.DataFrame(muertes_destetados)
                df_ventas_destetados = pd.DataFrame(ventas_destetados)
                df_ventas_descarte = pd.DataFrame(ventas_descarte)
                df_gastos = pd.DataFrame(gastos)

                # Crear un archivo Excel en memoria
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_reproductores.to_excel(writer, sheet_name='Reproductores', index=False)
                    df_partos.to_excel(writer, sheet_name='Partos', index=False)
                    df_destetes.to_excel(writer, sheet_name='Destetes', index=False)
                    df_muertes.to_excel(writer, sheet_name='Muertes', index=False)
                    df_ventas_destetados.to_excel(writer, sheet_name='Ventas Destetados', index=False)
                    df_ventas_descarte.to_excel(writer, sheet_name='Ventas Descarte', index=False)
                    df_gastos.to_excel(writer, sheet_name='Gastos', index=False)

                output.seek(0)
                return Response(output, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                headers={"Content-Disposition": "attachment;filename=datos_granja.xlsx"})
    except Exception as e:
        flash(f'Ocurrió un error inesperado: {str(e)}', 'danger')
        return redirect(url_for('index'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)