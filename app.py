from flask import Flask, render_template, request, redirect, url_for, flash
import psycopg2
from psycopg2 import extras
from datetime import datetime
import os
from urllib.parse import urlparse

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
    return render_template('index.html')

# Ruta para ingresar reproductores
@app.route('/ingresar_reproductores', methods=['GET', 'POST'])
def ingresar_reproductores():
    if request.method == 'POST':
        try:
            galpon = request.form['galpon']
            poza = request.form['poza']
            hembras = int(request.form['hembras'])
            machos = int(request.form['machos'])
            tiempo_reproductores = int(request.form['tiempo_reproductores'])

            validate_positive_values(hembras=hembras, machos=machos, tiempo_reproductores=tiempo_reproductores)

            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                    cursor.execute('''
                        SELECT id FROM reproductores
                        WHERE galpon = %s AND poza = %s
                    ''', (galpon, poza))
                    if cursor.fetchone():
                        flash('El galpón y la poza ya están registrados.', 'danger')
                        return redirect(url_for('ingresar_reproductores'))

                    cursor.execute('''
                        INSERT INTO reproductores (
                            galpon, poza, hembras, machos, tiempo_reproductores, fecha_ingreso
                        ) VALUES (%s, %s, %s, %s, %s, %s)
                    ''', (galpon, poza, hembras, machos, tiempo_reproductores, datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')))

                    conn.commit()
                    flash('Reproductores registrados correctamente.', 'success')
        except ValueError as e:
            flash(f'Error en los datos ingresados: {str(e)}', 'danger')
        except psycopg2.Error as e:
            flash(f'Error en la base de datos: {str(e)}', 'danger')
        except Exception as e:
            flash(f'Ocurrió un error inesperado: {str(e)}', 'danger')

        return redirect(url_for('index'))

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
        except ValueError as e:
            flash(f'Error en los datos ingresados: {str(e)}', 'danger')
        except psycopg2.Error as e:
            flash(f'Error en la base de datos: {str(e)}', 'danger')
        except Exception as e:
            flash(f'Ocurrió un error inesperado: {str(e)}', 'danger')

        return render_template('registrar_partos.html', galpones_pozas=galpones_pozas, galpon_seleccionado=galpon, poza_seleccionada=poza)

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
        except ValueError as e:
            flash(f'Error en los datos ingresados: {str(e)}', 'danger')
        except psycopg2.Error as e:
            flash(f'Error en la base de datos: {str(e)}', 'danger')
        except Exception as e:
            flash(f'Ocurrió un error inesperado: {str(e)}', 'danger')

        return render_template('registrar_destete.html', galpones_pozas=galpones_pozas, galpon_seleccionado=galpon, poza_seleccionada=poza)

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
        except ValueError as e:
            flash(f'Error en los datos ingresados: {str(e)}', 'danger')
        except psycopg2.Error as e:
            flash(f'Error en la base de datos: {str(e)}', 'danger')
        except Exception as e:
            flash(f'Ocurrió un error inesperado: {str(e)}', 'danger')

        return redirect(url_for('index'))

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
        except ValueError as e:
            flash(f'Error en los datos ingresados: {str(e)}', 'danger')
        except psycopg2.Error as e:
            flash(f'Error en la base de datos: {str(e)}', 'danger')
        except Exception as e:
            flash(f'Ocurrió un error inesperado: {str(e)}', 'danger')

        return redirect(url_for('index'))

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
        except ValueError as e:
            flash(f'Error en los datos ingresados: {str(e)}', 'danger')
        except psycopg2.Error as e:
            flash(f'Error en la base de datos: {str(e)}', 'danger')
        except Exception as e:
            flash(f'Ocurrió un error inesperado: {str(e)}', 'danger')

        return redirect(url_for('index'))

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
        except ValueError as e:
            flash(f'Error en los datos ingresados: {str(e)}', 'danger')
        except psycopg2.Error as e:
            flash(f'Error en la base de datos: {str(e)}', 'danger')
        except Exception as e:
            flash(f'Ocurrió un error inesperado: {str(e)}', 'danger')

        return redirect(url_for('index'))

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
        return redirect(url_for('index'))

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
        return redirect(url_for('index'))

# Ruta para ver resultados
@app.route('/resultados')
def resultados():
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
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

        return render_template('resultados.html', 
                             reproductores=reproductores,
                             partos=partos,
                             destetes=destetes,
                             muertes_destetados=muertes_destetados,
                             ventas_destetados=ventas_destetados,
                             ventas_descarte=ventas_descarte,
                             gastos=gastos)
    except Exception as e:
        flash(f'Ocurrió un error inesperado: {str(e)}', 'danger')
        return redirect(url_for('index'))

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
                except ValueError as e:
                    flash(f'Error en los datos ingresados: {str(e)}', 'danger')
                except psycopg2.Error as e:
                    flash(f'Error en la base de datos: {str(e)}', 'danger')
                except Exception as e:
                    flash(f'Ocurrió un error inesperado: {str(e)}', 'danger')

                return redirect(url_for('analisis_datos'))

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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)