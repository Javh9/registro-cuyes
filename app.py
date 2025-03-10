from flask import Flask, render_template, request, redirect, url_for, flash
import psycopg2  # Usar psycopg2 para PostgreSQL
from psycopg2 import extras  # Importar extras explícitamente
from datetime import datetime
import os
from urllib.parse import urlparse  # Para parsear la URL de Neon

# Inicializar la aplicación Flask
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'una_clave_secreta_muy_larga_y_compleja')

# Función para obtener la conexión a la base de datos
def get_db_connection():
    # Obtener la URL de la base de datos de la variable de entorno
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        raise ValueError("No se ha configurado DATABASE_URL")

    # Parsear la URL de la base de datos
    url = urlparse(database_url)
    
    conn = psycopg2.connect(
        dbname=url.path[1:],  # Eliminar el '/' inicial
        user=url.username,
        password=url.password,
        host=url.hostname,
        port=url.port
    )

    # Configurar el cursor para que los resultados sean diccionarios
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    return conn, cursor  # Retornar tanto la conexión como el cursor

# Función para crear o actualizar las tablas en la base de datos
def crear_o_actualizar_tablas():
    conn, cursor = get_db_connection()  # Obtener la conexión y el cursor

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
    conn.close()

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

            # Validar que los valores no sean negativos
            if any(value < 0 for value in [hembras, machos, tiempo_reproductores]):
                flash('Los valores no pueden ser negativos.', 'danger')
                return redirect(url_for('ingresar_reproductores'))

            conn, cursor = get_db_connection()

            # Verificar si el galpón y la poza ya están registrados
            cursor.execute('''
                SELECT id FROM reproductores
                WHERE galpon = %s AND poza = %s
            ''', (galpon, poza))
            if cursor.fetchone():
                flash('El galpón y la poza ya están registrados.', 'danger')
                return redirect(url_for('ingresar_reproductores'))

            # Insertar datos de los reproductores
            cursor.execute('''
                INSERT INTO reproductores (
                    galpon, poza, hembras, machos, tiempo_reproductores, fecha_ingreso
                ) VALUES (%s, %s, %s, %s, %s, %s)
            ''', (galpon, poza, hembras, machos, tiempo_reproductores, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

            conn.commit()
            flash('Reproductores registrados correctamente.', 'success')
        except ValueError as e:
            flash(f'Error en los datos ingresados: {str(e)}', 'danger')
        except psycopg2.Error as e:
            flash(f'Error en la base de datos: {str(e)}', 'danger')
        except Exception as e:
            flash(f'Ocurrió un error inesperado: {str(e)}', 'danger')
        finally:
            if 'conn' in locals():
                conn.close()

        return redirect(url_for('index'))

    return render_template('ingresar_reproductores.html')

# Ruta para registrar partos
@app.route('/registrar_partos', methods=['GET', 'POST'])
def registrar_partos():
    conn, cursor = get_db_connection()

    # Obtener los galpones y pozas registrados
    cursor.execute('SELECT DISTINCT galpon, poza FROM reproductores')
    galpones_pozas = cursor.fetchall()
    conn.close()

    # Inicializar variables para los valores seleccionados
    galpon_seleccionado = None
    poza_seleccionada = None

    if request.method == 'POST':
        try:
            galpon_seleccionado = request.form['galpon']
            poza_seleccionada = request.form['poza']
            numero_parto = int(request.form['numero_parto'])
            nacidos = int(request.form['nacidos'])
            muertos_bebes = int(request.form['muertos_bebes'])
            muertos_reproductores = int(request.form['muertos_reproductores'])

            # Validar que los valores no sean negativos
            if any(value < 0 for value in [numero_parto, nacidos, muertos_bebes, muertos_reproductores]):
                flash('Los valores no pueden ser negativos.', 'danger')
                return render_template('registrar_partos.html', galpones_pozas=galpones_pozas, galpon_seleccionado=galpon_seleccionado, poza_seleccionada=poza_seleccionada)

            conn, cursor = get_db_connection()

            # Verificar si el galpón y la poza están registrados
            cursor.execute('''
                SELECT id FROM reproductores
                WHERE galpon = %s AND poza = %s
            ''', (galpon_seleccionado, poza_seleccionada))
            if not cursor.fetchone():
                flash('El galpón y la poza no están registrados.', 'danger')
                return render_template('registrar_partos.html', galpones_pozas=galpones_pozas, galpon_seleccionado=galpon_seleccionado, poza_seleccionada=poza_seleccionada)

            # Insertar datos del parto
            cursor.execute('''
                INSERT INTO partos (
                    galpon, poza, numero_parto, nacidos, muertos_bebes, muertos_reproductores, fecha_nacimiento
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (galpon_seleccionado, poza_seleccionada, numero_parto, nacidos, muertos_bebes, muertos_reproductores, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

            conn.commit()
            flash('Parto registrado correctamente.', 'success')
        except Exception as e:
            flash(f'Ocurrió un error inesperado: {str(e)}', 'danger')
        finally:
            conn.close()

        # Mantener la ventana de registro abierta con los valores seleccionados
        return render_template('registrar_partos.html', galpones_pozas=galpones_pozas, galpon_seleccionado=galpon_seleccionado, poza_seleccionada=poza_seleccionada)

    # Mostrar el formulario de registro de partos
    return render_template('registrar_partos.html', galpones_pozas=galpones_pozas, galpon_seleccionado=galpon_seleccionado, poza_seleccionada=poza_seleccionada)

# Ruta para registrar destete
@app.route('/registrar_destete', methods=['GET', 'POST'])
def registrar_destete():
    # Obtener la conexión y el cursor
    conn, cursor = get_db_connection()

    # Obtener los galpones y pozas registrados
    cursor.execute('SELECT DISTINCT galpon, poza FROM reproductores')
    galpones_pozas = cursor.fetchall()
    conn.close()

    # Inicializar variables para los valores seleccionados
    galpon_seleccionado = None
    poza_seleccionada = None

    if request.method == 'POST':
        try:
            # Obtener los datos del formulario
            galpon_seleccionado = request.form['galpon']
            poza_seleccionada = request.form['poza']
            destetados_hembras = int(request.form['destetados_hembras'])
            destetados_machos = int(request.form['destetados_machos'])

            # Validar que los valores no sean negativos
            if destetados_hembras < 0 or destetados_machos < 0:
                flash('Los valores de destetados no pueden ser negativos.', 'danger')
                return render_template('registrar_destete.html', galpones_pozas=galpones_pozas, galpon_seleccionado=galpon_seleccionado, poza_seleccionada=poza_seleccionada)

            conn, cursor = get_db_connection()

            # Verificar si el galpón y la poza están registrados
            cursor.execute('''
                SELECT id FROM reproductores
                WHERE galpon = %s AND poza = %s
            ''', (galpon_seleccionado, poza_seleccionada))
            if not cursor.fetchone():
                flash('El galpón y la poza no están registrados.', 'danger')
                return render_template('registrar_destete.html', galpones_pozas=galpones_pozas, galpon_seleccionado=galpon_seleccionado, poza_seleccionada=poza_seleccionada)

            # Insertar datos del destete
            cursor.execute('''
                INSERT INTO destetes (
                    galpon, poza, destetados_hembras, destetados_machos, fecha_destete
                ) VALUES (%s, %s, %s, %s, %s)
            ''', (galpon_seleccionado, poza_seleccionada, destetados_hembras, destetados_machos, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

            conn.commit()
            flash('Destete registrado correctamente.', 'success')
        except Exception as e:
            flash(f'Ocurrió un error inesperado: {str(e)}', 'danger')
        finally:
            conn.close()

        # Mantener la ventana de registro abierta con los valores seleccionados
        return render_template('registrar_destete.html', galpones_pozas=galpones_pozas, galpon_seleccionado=galpon_seleccionado, poza_seleccionada=poza_seleccionada)

    # Mostrar el formulario de registro de destetes
    return render_template('registrar_destete.html', galpones_pozas=galpones_pozas, galpon_seleccionado=galpon_seleccionado, poza_seleccionada=poza_seleccionada)

# Ruta para registrar muertes de destetados
@app.route('/registrar_muertes_destetados', methods=['GET', 'POST'])
def registrar_muertes_destetados():
    if request.method == 'POST':
        try:
            galpon = request.form['galpon']
            poza = request.form['poza']
            muertos_hembras = int(request.form['muertos_hembras'])
            muertos_machos = int(request.form['muertos_machos'])

            # Validar que los valores no sean negativos
            if muertos_hembras < 0 or muertos_machos < 0:
                flash('Los valores de muertes no pueden ser negativos.', 'danger')
                return redirect(url_for('registrar_muertes_destetados'))

            conn = get_db_connection()
            cursor = conn.cursor()

            # Verificar si el galpón y la poza están registrados
            cursor.execute('''
                SELECT id FROM reproductores
                WHERE galpon = %s AND poza = %s
            ''', (galpon, poza))
            if not cursor.fetchone():
                flash('El galpón y la poza no están registrados.', 'danger')
                return redirect(url_for('registrar_muertes_destetados'))

            # Insertar datos de las muertes de destetados
            cursor.execute('''
                INSERT INTO muertes_destetados (
                    galpon, poza, muertos_hembras, muertos_machos, fecha_muerte
                ) VALUES (%s, %s, %s, %s, %s)
            ''', (galpon, poza, muertos_hembras, muertos_machos, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

            conn.commit()
            flash('Muertes de destetados registradas correctamente.', 'success')
        except Exception as e:
            flash(f'Ocurrió un error inesperado: {str(e)}', 'danger')
        finally:
            conn.close()

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

            # Validar que los valores no sean negativos
            if any(value < 0 for value in [hembras_vendidas, machos_vendidos, costo_venta]):
                flash('Los valores no pueden ser negativos.', 'danger')
                return redirect(url_for('registrar_ventas_destetados'))

            conn = get_db_connection()
            cursor = conn.cursor()

            # Verificar si el galpón y la poza están registrados
            cursor.execute('''
                SELECT id FROM reproductores
                WHERE galpon = %s AND poza = %s
            ''', (galpon, poza))
            if not cursor.fetchone():
                flash('El galpón y la poza no están registrados.', 'danger')
                return redirect(url_for('registrar_ventas_destetados'))

            # Insertar datos de las ventas de destetados
            cursor.execute('''
                INSERT INTO ventas_destetados (
                    galpon, poza, hembras_vendidas, machos_vendidos, costo_venta, fecha_venta
                ) VALUES (%s, %s, %s, %s, %s, %s)
            ''', (galpon, poza, hembras_vendidas, machos_vendidos, costo_venta, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

            conn.commit()
            flash('Ventas de destetados registradas correctamente.', 'success')
        except Exception as e:
            flash(f'Ocurrió un error inesperado: {str(e)}', 'danger')
        finally:
            conn.close()

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

            # Validar que los valores no sean negativos
            if cuyes_vendidos < 0 or costo_venta < 0:
                flash('Los valores no pueden ser negativos.', 'danger')
                return redirect(url_for('registrar_ventas_descarte'))

            conn = get_db_connection()
            cursor = conn.cursor()

            # Verificar si el galpón y la poza están registrados
            cursor.execute('''
                SELECT id FROM reproductores
                WHERE galpon = %s AND poza = %s
            ''', (galpon, poza))
            if not cursor.fetchone():
                flash('El galpón y la poza no están registrados.', 'danger')
                return redirect(url_for('registrar_ventas_descarte'))

            # Insertar datos de las ventas de descarte
            cursor.execute('''
                INSERT INTO ventas_descarte (
                    galpon, poza, cuyes_vendidos, costo_venta, fecha_venta
                ) VALUES (%s, %s, %s, %s, %s)
            ''', (galpon, poza, cuyes_vendidos, costo_venta, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

            conn.commit()
            flash('Ventas de descarte registradas correctamente.', 'success')
        except Exception as e:
            flash(f'Ocurrió un error inesperado: {str(e)}', 'danger')
        finally:
            conn.close()

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

            # Validar que el monto no sea negativo
            if monto < 0:
                flash('El monto no puede ser negativo.', 'danger')
                return redirect(url_for('registrar_gastos'))

            conn = get_db_connection()
            cursor = conn.cursor()

            # Insertar datos del gasto
            cursor.execute('''
                INSERT INTO gastos (
                    descripcion, monto, tipo, fecha_gasto
                ) VALUES (%s, %s, %s, %s)
            ''', (descripcion, monto, tipo, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

            conn.commit()
            flash('Gasto registrado correctamente.', 'success')
        except Exception as e:
            flash(f'Ocurrió un error inesperado: {str(e)}', 'danger')
        finally:
            conn.close()

        return redirect(url_for('index'))

    return render_template('registrar_gastos.html')

# Ruta para ver análisis de datos
@app.route('/analisis_datos')
def analisis_datos():
    try:
        conn, cursor = get_db_connection()  # Obtener la conexión y el cursor

        # Obtener datos de reproductores, partos, destetes, muertes y ventas
        cursor.execute('''
            SELECT r.id, r.galpon, r.poza, r.hembras, r.machos, r.tiempo_reproductores, r.fecha_ingreso,
                   p.numero_parto, p.nacidos, p.muertos_bebes, p.muertos_reproductores, p.fecha_nacimiento,
                   d.destetados_hembras, d.destetados_machos, d.fecha_destete,
                   m.muertos_hembras, m.muertos_machos, m.fecha_muerte,
                   vd.hembras_vendidas, vd.machos_vendidos, vd.costo_venta, vd.fecha_venta,
                   vc.cuyes_vendidos, vc.costo_venta, vc.fecha_venta
            FROM reproductores r
            LEFT JOIN partos p ON r.galpon = p.galpon AND r.poza = p.poza
            LEFT JOIN destetes d ON r.galpon = d.galpon AND r.poza = d.poza
            LEFT JOIN muertes_destetados m ON r.galpon = m.galpon AND r.poza = m.poza
            LEFT JOIN ventas_destetados vd ON r.galpon = vd.galpon AND r.poza = vd.poza
            LEFT JOIN ventas_descarte vc ON r.galpon = vc.galpon AND r.poza = vc.poza
        ''')
        datos = cursor.fetchall()  # Esto ahora devolverá diccionarios

        # Obtener los gastos por separado
        cursor.execute('SELECT descripcion, monto, tipo, fecha_gasto FROM gastos')
        gastos = cursor.fetchall()  # Esto también devolverá diccionarios

        conn.close()

        # Pasar los datos y los gastos al template
        return render_template('analisis_datos.html', datos=datos, gastos=gastos)
    except Exception as e:
        flash(f'Ocurrió un error inesperado: {str(e)}', 'danger')
        return redirect(url_for('index'))
    
# Ruta para ver el balance
@app.route('/balance')
def balance():
    try:
        conn, cursor = get_db_connection()  # Obtener la conexión y el cursor

        # Obtener total de ventas de destetados
        cursor.execute('SELECT SUM(costo_venta) FROM ventas_destetados')
        total_ventas_destetados = cursor.fetchone()[0] or 0

        # Obtener total de ventas de descarte
        cursor.execute('SELECT SUM(costo_venta) FROM ventas_descarte')
        total_ventas_descarte = cursor.fetchone()[0] or 0

        # Obtener total de gastos
        cursor.execute('SELECT SUM(monto) FROM gastos')
        total_gastos = cursor.fetchone()[0] or 0

        # Calcular el balance final
        balance = (total_ventas_destetados + total_ventas_descarte) - total_gastos

        conn.close()
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
        conn, cursor = get_db_connection()  # Obtener la conexión y el cursor

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

        conn.close()
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
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        try:
            # Obtener los datos del formulario
            galpon = request.form['galpon']
            poza = request.form['poza']
            hembras = int(request.form['hembras'])
            machos = int(request.form['machos'])
            tiempo_reproductores = int(request.form['tiempo_reproductores'])

            # Validar que los valores no sean negativos
            if any(value < 0 for value in [hembras, machos, tiempo_reproductores]):
                flash('Los valores no pueden ser negativos.', 'danger')
                return redirect(url_for('editar_reproductor', id=id))

            # Actualizar los datos en la base de datos
            cursor.execute('''
                UPDATE reproductores
                SET galpon = %s, poza = %s, hembras = %s, machos = %s, tiempo_reproductores = %s
                WHERE id = %s
            ''', (galpon, poza, hembras, machos, tiempo_reproductores, id))

            conn.commit()
            flash('Reproductor actualizado correctamente.', 'success')
        except Exception as e:
            flash(f'Ocurrió un error inesperado: {str(e)}', 'danger')
        finally:
            conn.close()

        return redirect(url_for('analisis_datos'))

    # Obtener los datos actuales del reproductor
    cursor.execute('SELECT * FROM reproductores WHERE id = %s', (id,))
    reproductor = cursor.fetchone()
    conn.close()

    if reproductor is None:
        flash('Reproductor no encontrado.', 'danger')
        return redirect(url_for('analisis_datos'))

    return render_template('editar_reproductor.html', reproductor=reproductor)

# Ruta para eliminar todos los datos
@app.route('/eliminar_todos_los_datos', methods=['POST'])
def eliminar_todos_los_datos():
    # Obtener la clave enviada por el usuario
    clave_ingresada = request.form.get('clave')

    # Clave de autorización (cámbiala por la que desees)
    CLAVE_AUTORIZACION = "0429"

    # Verificar si la clave es correcta
    if clave_ingresada != CLAVE_AUTORIZACION:
        flash('Clave incorrecta. No se han eliminado los datos.', 'danger')
        return redirect(url_for('index'))

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Eliminar todos los registros de cada tabla
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
    finally:
        conn.close()

    return redirect(url_for('index'))

if __name__ == '__main__':
    # Configuración para Heroku
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)