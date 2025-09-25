#from flask import Flask, render_template, request, redirect, url_for, flash, Response, jsonify
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import psycopg2
from psycopg2 import extras
from datetime import datetime
import os
import pandas as pd
from urllib.parse import urlparse
import io
from sklearn.linear_model import LinearRegression
from collections import OrderedDict
import numpy as np

# Inicializar la aplicación Flask
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'una_clave_secreta_muy_larga_y_compleja')

# Inicializar la tabla al iniciar la aplicación

print("=== INICIANDO APLICACIÓN ===")
print(f"Python version: {os.sys.version}")
print(f"Variables de entorno: {list(os.environ.keys())}")
print(f"DATABASE_URL: {os.environ.get('DATABASE_URL', 'NO CONFIGURADA')}")

def entrenar_modelos():
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                # Obtener datos históricos de mortalidad
                cursor.execute('''
                    SELECT 
                        TO_CHAR(TO_DATE(fecha_muerte, 'YYYY-MM-DD'), 'YYYY-MM') AS mes,
                        SUM(muertos_hembras + muertos_machos) AS total_muertes
                    FROM muertes_destetados
                    WHERE fecha_muerte IS NOT NULL
                    GROUP BY mes
                    ORDER BY mes
                ''')
                mortalidad_data = cursor.fetchall()

                # Obtener datos históricos de nacimientos
                cursor.execute('''
                    SELECT 
                        TO_CHAR(TO_DATE(fecha_nacimiento, 'YYYY-MM-DD'), 'YYYY-MM') AS mes,
                        SUM(nacidos) AS total_nacidos
                    FROM partos
                    WHERE fecha_nacimiento IS NOT NULL
                    GROUP BY mes
                    ORDER BY mes
                ''')
                nacimientos_data = cursor.fetchall()

                # Obtener datos históricos de ganancias
                cursor.execute('''
                    SELECT 
                        TO_CHAR(TO_DATE(fecha_venta, 'YYYY-MM-DD'), 'YYYY-MM') AS mes,
                        SUM(costo_venta) AS total_ganancias
                    FROM ventas_destetados
                    WHERE fecha_venta IS NOT NULL
                    GROUP BY mes
                    ORDER BY mes
                ''')
                ganancias_data = cursor.fetchall()

        # Verificar que hay suficientes datos para entrenar
        if len(mortalidad_data) < 2:
            print("⚠️  No hay suficientes datos de mortalidad para entrenar el modelo")
            modelo_mortalidad = None
        else:
            # Convertir a DataFrames de Pandas
            df_mortalidad = pd.DataFrame(mortalidad_data, columns=['mes', 'total_muertes'])
            df_mortalidad['mes_num'] = (pd.to_datetime(df_mortalidad['mes']) - pd.to_datetime(df_mortalidad['mes'].min())).dt.days / 30
            X_mortalidad = df_mortalidad[['mes_num']]
            y_mortalidad = df_mortalidad['total_muertes']
            modelo_mortalidad = LinearRegression()
            modelo_mortalidad.fit(X_mortalidad, y_mortalidad)

        if len(nacimientos_data) < 2:
            print("⚠️  No hay suficientes datos de nacimientos para entrenar el modelo")
            modelo_nacimientos = None
        else:
            df_nacimientos = pd.DataFrame(nacimientos_data, columns=['mes', 'total_nacidos'])
            df_nacimientos['mes_num'] = (pd.to_datetime(df_nacimientos['mes']) - pd.to_datetime(df_nacimientos['mes'].min())).dt.days / 30
            X_nacimientos = df_nacimientos[['mes_num']]
            y_nacimientos = df_nacimientos['total_nacidos']
            modelo_nacimientos = LinearRegression()
            modelo_nacimientos.fit(X_nacimientos, y_nacimientos)

        if len(ganancias_data) < 2:
            print("⚠️  No hay suficientes datos de ganancias para entrenar el modelo")
            modelo_ganancias = None
        else:
            df_ganancias = pd.DataFrame(ganancias_data, columns=['mes', 'total_ganancias'])
            df_ganancias['mes_num'] = (pd.to_datetime(df_ganancias['mes']) - pd.to_datetime(df_ganancias['mes'].min())).dt.days / 30
            X_ganancias = df_ganancias[['mes_num']]
            y_ganancias = df_ganancias['total_ganancias']
            modelo_ganancias = LinearRegression()
            modelo_ganancias.fit(X_ganancias, y_ganancias)

        return modelo_mortalidad, modelo_nacimientos, modelo_ganancias

    except Exception as e:
        print(f"Error al entrenar los modelos: {str(e)}")
        return None, None, None
    
# Función para obtener la conexión a la base de datos CORREGIDA
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
def init_ventas_table():
    """Crear la tabla ventas si no existe"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS ventas (
                        id SERIAL PRIMARY KEY,
                        tipo_venta VARCHAR(20) NOT NULL CHECK (tipo_venta IN ('destetados', 'descarte')),
                        galpon VARCHAR(50),
                        poza VARCHAR(50),
                        hembras_vendidas INTEGER DEFAULT 0,
                        machos_vendidos INTEGER DEFAULT 0,
                        costo_total DECIMAL(10, 2) NOT NULL,
                        fecha_venta TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        mover_engorde BOOLEAN DEFAULT FALSE,
                        engorde_galpon VARCHAR(50),
                        engorde_poza VARCHAR(50),
                        fecha_movimiento DATE,
                        dias_engorde INTEGER,
                        observaciones TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                conn.commit()
                app.logger.info("Tabla ventas verificada/creada correctamente")
    except Exception as e:
        app.logger.error("Error al crear tabla ventas", exc_info=e)
init_ventas_table()
# Función para validar valores positivos
def validate_positive_values(**kwargs):
    for key, value in kwargs.items():
        if value < 0:
            raise ValueError(f"{key} no puede ser negativo")

# Función para crear o actualizar las tablas en la base de datos
def crear_o_actualizar_tablas():
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
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

            # === NUEVAS TABLAS PARA NOTIFICACIONES ===
            # Crear tabla de notificaciones si no existe
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS notificaciones (
                    id SERIAL PRIMARY KEY,
                    tipo VARCHAR(50) NOT NULL,
                    titulo VARCHAR(200) NOT NULL,
                    mensaje TEXT NOT NULL,
                    prioridad VARCHAR(20) CHECK (prioridad IN ('baja', 'media', 'alta', 'urgente')),
                    leida BOOLEAN DEFAULT FALSE,
                    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    fecha_vencimiento TIMESTAMP,
                    relacion_id INTEGER,
                    relacion_tipo VARCHAR(50)
                )
            ''')

            # Crear tabla de configuraciones de alertas si no existe
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS configuraciones_alertas (
                    id SERIAL PRIMARY KEY,
                    tipo_alerta VARCHAR(50) UNIQUE NOT NULL,
                    dias_antes INTEGER DEFAULT 0,
                    activa BOOLEAN DEFAULT TRUE,
                    parametros JSONB
                )
            ''')

            # Insertar configuraciones predeterminadas si no existen
            cursor.execute('''
                INSERT INTO configuraciones_alertas (tipo_alerta, dias_antes, parametros) 
                VALUES 
                    ('destete', 15, '{"dias_min": 15, "dias_max": 20}'),
                    ('descarte', 360, '{"meses_min": 12}'),
                    ('vacunacion', 0, '{"intervalo_dias": 90}'),
                    ('control_peso', 30, '{}'),
                    ('parto_proximo', 70, '{"dias_gestacion": 70}')
                ON CONFLICT (tipo_alerta) DO NOTHING
            ''')

            conn.commit()
# Llamar a la función para crear o actualizar las tablas al iniciar la aplicación
try:
    crear_o_actualizar_tablas()
    print("✅ Aplicación iniciada correctamente")
except Exception as e:
    print(f"⚠️  Error al inicializar tablas: {e}")

# Agregar estas funciones después de las funciones existentes
def generar_notificaciones_destetes():
    """Detectar cuyes listos para destete (15-20 días)"""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                # Buscar partos con crías entre 15 y 20 días
                cursor.execute('''
                    SELECT p.id, p.galpon, p.poza, p.nacidos, p.fecha_nacimiento,
                           EXTRACT(DAYS FROM (CURRENT_DATE - TO_DATE(p.fecha_nacimiento, 'YYYY-MM-DD'))) as dias
                    FROM partos p
                    LEFT JOIN destetes d ON p.galpon = d.galpon AND p.poza = d.poza
                    WHERE d.id IS NULL 
                    AND EXTRACT(DAYS FROM (CURRENT_DATE - TO_DATE(p.fecha_nacimiento, 'YYYY-MM-DD'))) BETWEEN 15 AND 20
                ''')
                partos_pendientes = cursor.fetchall()
                
                notificaciones = []
                for parto in partos_pendientes:
                    # Verificar si ya existe notificación para este parto
                    cursor.execute('''
                        SELECT id FROM notificaciones 
                        WHERE relacion_id = %s AND relacion_tipo = 'destete' AND leida = FALSE
                    ''', (parto['id'],))
                    existe = cursor.fetchone()
                    
                    if not existe:
                        notificaciones.append({
                            'tipo': 'destete',
                            'titulo': f'Destete Pendiente - Galpón {parto["galpon"]} Poza {parto["poza"]}',
                            'mensaje': f'{parto["nacidos"]} cuyes tienen {parto["dias"]} días. ¡Es tiempo de destetar!',
                            'prioridad': 'alta' if parto['dias'] > 25 else 'media',
                            'relacion_id': parto['id'],
                            'relacion_tipo': 'destete'
                        })
                
                return notificaciones
    except Exception as e:
        print(f"Error generando notificaciones de destete: {e}")
        return []

def generar_notificaciones_descarte():
    """Detectar reproductores para descarte (> 12 meses)"""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                cursor.execute('''
                    SELECT id, galpon, poza, hembras, machos, fecha_ingreso,
                           EXTRACT(MONTHS FROM (CURRENT_DATE - TO_DATE(fecha_ingreso, 'YYYY-MM-DD'))) as meses
                    FROM reproductores 
                    WHERE EXTRACT(MONTHS FROM (CURRENT_DATE - TO_DATE(fecha_ingreso, 'YYYY-MM-DD'))) >= 12
                ''')
                reproductores_descarte = cursor.fetchall()
                
                notificaciones = []
                for repro in reproductores_descarte:
                    cursor.execute('''
                        SELECT id FROM notificaciones 
                        WHERE relacion_id = %s AND relacion_tipo = 'descarte' AND leida = FALSE
                    ''', (repro['id'],))
                    existe = cursor.fetchone()
                    
                    if not existe:
                        notificaciones.append({
                            'tipo': 'descarte',
                            'titulo': f'Descarte Programado - Galpón {repro["galpon"]} Poza {repro["poza"]}',
                            'mensaje': f'Reproductores con {repro["meses"]} meses. Considerar descarte.',
                            'prioridad': 'media',
                            'relacion_id': repro['id'],
                            'relacion_tipo': 'descarte'
                        })
                
                return notificaciones
    except Exception as e:
        print(f"Error generando notificaciones de descarte: {e}")
        return []

def generar_notificaciones_salud():
    """Alertas de salud basadas en mortalidad"""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                # Mortalidad alta en últimos 7 días
                cursor.execute('''
                    SELECT galpon, poza, SUM(muertos_hembras + muertos_machos) as total_muertes
                    FROM muertes_destetados 
                    WHERE TO_DATE(fecha_muerte, 'YYYY-MM-DD') >= CURRENT_DATE - INTERVAL '7 days'
                    GROUP BY galpon, poza 
                    HAVING SUM(muertos_hembras + muertos_machos) > 3
                ''')
                mortalidad_alta = cursor.fetchall()
                
                notificaciones = []
                for registro in mortalidad_alta:
                    notificaciones.append({
                        'tipo': 'salud',
                        'titulo': f'Alerta de Salud - Galpón {registro["galpon"]} Poza {registro["poza"]}',
                        'mensaje': f'Alta mortalidad: {registro["total_muertes"]} muertes en 7 días.',
                        'prioridad': 'urgente',
                        'relacion_id': None,
                        'relacion_tipo': 'salud'
                    })
                
                return notificaciones
    except Exception as e:
        print(f"Error generando notificaciones de salud: {e}")
        return []

def guardar_notificaciones(notificaciones):
    """Guardar notificaciones en la base de datos"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                for notif in notificaciones:
                    cursor.execute('''
                        INSERT INTO notificaciones (tipo, titulo, mensaje, prioridad, relacion_id, relacion_tipo)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    ''', (notif['tipo'], notif['titulo'], notif['mensaje'], 
                          notif['prioridad'], notif['relacion_id'], notif['relacion_tipo']))
                conn.commit()
    except Exception as e:
        print(f"Error guardando notificaciones: {e}")

# Función principal para generar todas las notificaciones
def generar_todas_las_notificaciones():
    notificaciones = []
    notificaciones.extend(generar_notificaciones_destetes())
    notificaciones.extend(generar_notificaciones_descarte())
    notificaciones.extend(generar_notificaciones_salud())
    
    if notificaciones:
        guardar_notificaciones(notificaciones)
        print(f"✅ Generadas {len(notificaciones)} notificaciones")
    
    return notificaciones
# Ruta principal


@app.route("/")
def index():
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # -----------------------
        # Totales generales
        # -----------------------
        # Total reproductores (sum actual de hembras+machos)
        try:
            cur.execute("SELECT COALESCE(SUM(hembras + machos), 0) FROM reproductores;")
            total_reproductores = cur.fetchone()[0] or 0
        except Exception as e:
            print("Error total_reproductores:", e)
            total_reproductores = 0

        # Total destetados
        try:
            cur.execute("SELECT COALESCE(SUM(destetados_hembras + destetados_machos), 0) FROM destetes;")
            total_destetados = cur.fetchone()[0] or 0
        except Exception as e:
            print("Error total_destetados:", e)
            total_destetados = 0

        # Total nacidos
        total_nacidos = 0
        try:
            cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'partos');")
            if cur.fetchone()[0]:
                cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'partos';")
                parto_cols = [r[0] for r in cur.fetchall()]

                if 'nacidos' in parto_cols:
                    cur.execute("SELECT COALESCE(SUM(nacidos),0) FROM partos;")
                elif 'nacidos_hembras' in parto_cols and 'nacidos_machos' in parto_cols:
                    cur.execute("SELECT COALESCE(SUM(nacidos_hembras + nacidos_machos),0) FROM partos;")
                elif 'crias_nacidas_hembras' in parto_cols and 'crias_nacidas_machos' in parto_cols:
                    cur.execute("SELECT COALESCE(SUM(crias_nacidas_hembras + crias_nacidas_machos),0) FROM partos;")
                else:
                    columna_nacidos = None
                    for c in parto_cols:
                        if any(k in c.lower() for k in ('nac', 'cria', 'bebe', 'parto')) and not c.lower().startswith('fecha'):
                            columna_nacidos = c
                            break
                    if columna_nacidos:
                        cur.execute(f"SELECT COALESCE(SUM({columna_nacidos}),0) FROM partos;")
                    else:
                        cur.execute("SELECT COUNT(*) FROM partos;")
                total_nacidos = cur.fetchone()[0] or 0
        except Exception as e:
            print("Error total_nacidos:", e)
            conn.rollback()
            total_nacidos = 0

        # Nacidos actuales
        nacidos_actuales = total_nacidos - total_destetados

        # Total muertos
        total_muertos = 0
        try:
            muertos_partos = 0
            cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'partos');")
            if cur.fetchone()[0]:
                cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'partos';")
                parto_cols = [r[0] for r in cur.fetchall()]
                if 'muertos_bebes' in parto_cols or 'muertos_reproductores' in parto_cols:
                    expr = []
                    if 'muertos_bebes' in parto_cols:
                        expr.append('COALESCE(SUM(muertos_bebes),0)')
                    if 'muertos_reproductores' in parto_cols:
                        expr.append('COALESCE(SUM(muertos_reproductores),0)')
                    if expr:
                        cur.execute("SELECT " + " + ".join(expr) + " FROM partos;")
                        muertos_partos = cur.fetchone()[0] or 0
            muertos_dest = 0
            cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'muertes_destetados');")
            if cur.fetchone()[0]:
                cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'muertes_destetados';")
                md_cols = [r[0] for r in cur.fetchall()]
                if 'muertos_hembras' in md_cols and 'muertos_machos' in md_cols:
                    cur.execute("SELECT COALESCE(SUM(muertos_hembras + muertos_machos),0) FROM muertes_destetados;")
                    muertos_dest = cur.fetchone()[0] or 0
            total_muertos = (muertos_partos or 0) + (muertos_dest or 0)
        except Exception as e:
            print("Error total_muertos:", e)
            conn.rollback()
            total_muertos = 0

        # -----------------------
        # Datos por galpón / poza
        # -----------------------
        reproductores_data, nacidos_data, destetados_data, muertos_data = {}, {}, {}, {}

        # Reproductores
        try:
            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'reproductores';")
            repro_cols = [r[0] for r in cur.fetchall()]
            posibles_fecha = ['fecha_ingreso', 'fecha_registro', 'created_at', 'tiempo_reproductores', 'fecha', 'fecha_creacion']
            fecha_col = next((c for c in posibles_fecha if c in repro_cols), None)

            if fecha_col:
                cur.execute(f"""
                    SELECT r.galpon, r.poza, (r.hembras + r.machos) as cantidad
                    FROM reproductores r
                    JOIN (
                        SELECT galpon, poza, MAX({fecha_col}) as ultima_fecha
                        FROM reproductores
                        GROUP BY galpon, poza
                    ) ult
                    ON r.galpon = ult.galpon
                    AND r.poza = ult.poza
                    AND r.{fecha_col} = ult.ultima_fecha
                    ORDER BY r.galpon, r.poza;
                """)
            else:
                cur.execute("""
                    SELECT r.galpon, r.poza, (r.hembras + r.machos) as cantidad
                    FROM reproductores r
                    JOIN (
                        SELECT galpon, poza, MAX(id) as maxid
                        FROM reproductores
                        GROUP BY galpon, poza
                    ) ult
                    ON r.galpon = ult.galpon
                    AND r.poza = ult.poza
                    AND r.id = ult.maxid
                    ORDER BY r.galpon, r.poza;
                """)
            for row in cur.fetchall():
                galpon, poza, cantidad = str(row[0]), str(row[1]), int(row[2] or 0)
                reproductores_data.setdefault(galpon, {})[poza] = cantidad
        except Exception as e:
            print("Error reproductores_data:", e)
            conn.rollback()

        # Nacidos
        try:
            cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'partos');")
            if cur.fetchone()[0]:
                cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'partos';")
                parto_cols = [r[0] for r in cur.fetchall()]
                if 'nacidos' in parto_cols:
                    cur.execute("SELECT galpon, poza, COALESCE(SUM(nacidos),0) FROM partos GROUP BY galpon, poza ORDER BY galpon, poza;")
                elif 'nacidos_hembras' in parto_cols and 'nacidos_machos' in parto_cols:
                    cur.execute("SELECT galpon, poza, COALESCE(SUM(nacidos_hembras + nacidos_machos),0) FROM partos GROUP BY galpon, poza ORDER BY galpon, poza;")
                elif 'crias_nacidas_hembras' in parto_cols and 'crias_nacidas_machos' in parto_cols:
                    cur.execute("SELECT galpon, poza, COALESCE(SUM(crias_nacidas_hembras + crias_nacidas_machos),0) FROM partos GROUP BY galpon, poza ORDER BY galpon, poza;")
                else:
                    columna_nacidos = None
                    for c in parto_cols:
                        if any(k in c.lower() for k in ('nac', 'cria', 'bebe', 'parto')) and not c.lower().startswith('fecha'):
                            columna_nacidos = c
                            break
                    if columna_nacidos:
                        cur.execute(f"SELECT galpon, poza, COALESCE(SUM({columna_nacidos}),0) FROM partos GROUP BY galpon, poza ORDER BY galpon, poza;")
                    else:
                        cur.execute("SELECT galpon, poza, COUNT(*) FROM partos GROUP BY galpon, poza ORDER BY galpon, poza;")
                for r in cur.fetchall():
                    galpon, poza, cantidad = str(r[0]), str(r[1]), int(r[2] or 0)
                    nacidos_data.setdefault(galpon, {})[poza] = cantidad
        except Exception as e:
            print("Error nacidos_data:", e)
            conn.rollback()

        # Destetados
        try:
            cur.execute("""
                SELECT galpon, poza, COALESCE(SUM(destetados_hembras + destetados_machos),0)
                FROM destetes GROUP BY galpon, poza ORDER BY galpon, poza;
            """)
            for r in cur.fetchall():
                galpon, poza, cantidad = str(r[0]), str(r[1]), int(r[2] or 0)
                destetados_data.setdefault(galpon, {})[poza] = cantidad
        except Exception as e:
            print("Error destetados_data:", e)
            conn.rollback()

        # Muertos
        try:
            cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'partos');")
            if cur.fetchone()[0]:
                cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'partos';")
                parto_cols = [r[0] for r in cur.fetchall()]
                if 'muertos_bebes' in parto_cols or 'muertos_reproductores' in parto_cols:
                    expr = []
                    if 'muertos_bebes' in parto_cols:
                        expr.append('COALESCE(SUM(muertos_bebes),0)')
                    if 'muertos_reproductores' in parto_cols:
                        expr.append('COALESCE(SUM(muertos_reproductores),0)')
                    if expr:
                        cur.execute("SELECT galpon, poza, " + " + ".join(expr) + " FROM partos GROUP BY galpon, poza ORDER BY galpon, poza;")
                        for r in cur.fetchall():
                            galpon, poza, cantidad = str(r[0]), str(r[1]), int(r[2] or 0)
                            muertos_data.setdefault(galpon, {})[poza] = muertos_data.get(galpon, {}).get(poza, 0) + cantidad

            cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'muertes_destetados');")
            if cur.fetchone()[0]:
                cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'muertes_destetados';")
                md_cols = [r[0] for r in cur.fetchall()]
                if 'muertos_hembras' in md_cols and 'muertos_machos' in md_cols:
                    cur.execute("SELECT galpon, poza, COALESCE(SUM(muertos_hembras + muertos_machos),0) FROM muertes_destetados GROUP BY galpon, poza ORDER BY galpon, poza;")
                    for r in cur.fetchall():
                        galpon, poza, cantidad = str(r[0]), str(r[1]), int(r[2] or 0)
                        muertos_data.setdefault(galpon, {})[poza] = muertos_data.get(galpon, {}).get(poza, 0) + cantidad
        except Exception as e:
            print("Error muertos_data:", e)
            conn.rollback()

        # -----------------------
        # Combinar y ORDENAR
        # -----------------------
        datos_galpones = OrderedDict()
        total_reproductores_por_galpon, total_nacidos_por_galpon, total_destetados_por_galpon = {}, {}, {}

        fuentes = [reproductores_data, nacidos_data, destetados_data, muertos_data]
        all_galpones = set()
        for src in fuentes:
            all_galpones.update(src.keys())

        for galpon in sorted(all_galpones, key=lambda x: int(x) if x.isdigit() else x):
            datos_galpones[galpon] = OrderedDict()
            total_reproductores_por_galpon[galpon] = 0
            total_nacidos_por_galpon[galpon] = 0
            total_destetados_por_galpon[galpon] = 0

            pozas = set()
            for src in fuentes:
                pozas.update(src.get(galpon, {}).keys())

            for poza in sorted(pozas, key=lambda x: int(x) if x.isdigit() else x):
                r = reproductores_data.get(galpon, {}).get(poza, 0)
                n = nacidos_data.get(galpon, {}).get(poza, 0)
                d = destetados_data.get(galpon, {}).get(poza, 0)
                m = muertos_data.get(galpon, {}).get(poza, 0)

                datos_galpones[galpon][poza] = {
                    'reproductores': r,
                    'nacidos': n,
                    'destetados': d,
                    'nacidos_vigentes': max(0, n - d - m),
                    'muertos': m
                }

                total_reproductores_por_galpon[galpon] += r
                total_nacidos_por_galpon[galpon] += n
                total_destetados_por_galpon[galpon] += d

        cur.close()
        conn.close()

        # Logs
        print("=== RESUMEN GENERAL ===")
        print("Total Reproductores:", total_reproductores)
        print("Total Nacidos:", total_nacidos)
        print("Nacidos actuales:", nacidos_actuales)
        print("Total Destetados:", total_destetados)
        print("Total Muertos:", total_muertos)
        print("Datos por Galpón:", datos_galpones)

        return render_template(
            "index.html",
            total_reproductores=total_reproductores,
            total_nacidos=total_nacidos,
            nacidos_actuales=nacidos_actuales,
            total_destetados=total_destetados,
            total_muertos=total_muertos,
            datos_galpones=datos_galpones,
            total_reproductores_por_galpon=total_reproductores_por_galpon,
            total_nacidos_por_galpon=total_nacidos_por_galpon,
            total_destetados_por_galpon=total_destetados_por_galpon
        )

    except Exception as e:
        print("Error general en la función index:", e)
        return render_template(
            "index.html",
            total_reproductores=0,
            total_nacidos=0,
            nacidos_actuales=0,
            total_destetados=0,
            total_muertos=0,
            datos_galpones={},
            total_reproductores_por_galpon={},
            total_nacidos_por_galpon={},
            total_destetados_por_galpon={}
        )


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
            # Obtener valores únicos de galpón y poza
            cursor.execute('SELECT DISTINCT galpon, poza FROM reproductores')
            galpones_pozas = cursor.fetchall()

            # Obtener valores únicos de galpón
            cursor.execute('SELECT DISTINCT galpon FROM reproductores')
            galpones_unicos = [row['galpon'] for row in cursor.fetchall()]

            # Obtener valores únicos de poza
            cursor.execute('SELECT DISTINCT poza FROM reproductores')
            pozas_unicas = [row['poza'] for row in cursor.fetchall()]

    if request.method == 'POST':
        action = request.form.get('action')  # Obtener la acción (registrar o buscar)
        galpon = request.form['galpon']
        poza = request.form['poza']

        if action == 'registrar':
            try:
                numero_parto = int(request.form['numero_parto'])
                nacidos = int(request.form['nacidos'])
                muertos_bebes = int(request.form['muertos_bebes'])
                muertos_reproductores = int(request.form['muertos_reproductores'])

                with get_db_connection() as conn:
                    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                        # Verificar si el parto ya existe
                        cursor.execute('''
                            SELECT id FROM partos
                            WHERE galpon = %s AND poza = %s AND numero_parto = %s
                        ''', (galpon, poza, numero_parto))
                        parto_existente = cursor.fetchone()

                        if parto_existente:
                            # Si el parto ya existe, actualizar los valores
                            cursor.execute('''
                                UPDATE partos
                                SET nacidos = nacidos + %s,
                                    muertos_bebes = muertos_bebes + %s,
                                    muertos_reproductores = muertos_reproductores + %s
                                WHERE id = %s
                            ''', (nacidos, muertos_bebes, muertos_reproductores, parto_existente['id']))
                        else:
                            # Si el parto no existe, insertar un nuevo registro
                            cursor.execute('''
                                INSERT INTO partos (
                                    galpon, poza, numero_parto, nacidos, muertos_bebes, muertos_reproductores, fecha_nacimiento
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                            ''', (galpon, poza, numero_parto, nacidos, muertos_bebes, muertos_reproductores, datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')))

                        conn.commit()
                        flash('Parto registrado correctamente.', 'success')
                        return redirect(url_for('registrar_partos'))
            except ValueError as e:
                flash(f'Error en los datos ingresados: {str(e)}', 'danger')
            except psycopg2.Error as e:
                flash(f'Error en la base de datos: {str(e)}', 'danger')
            except Exception as e:
                flash(f'Ocurrió un error inesperado: {str(e)}', 'danger')

        elif action == 'buscar':
            try:
                with get_db_connection() as conn:
                    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                        # Buscar partos existentes
                        cursor.execute('''
                            SELECT * FROM partos
                            WHERE galpon = %s AND poza = %s
                        ''', (galpon, poza))
                        partos = cursor.fetchall()

                        if partos:
                            return render_template('buscar_partos.html', partos=partos)
                        else:
                            flash('No se encontraron partos para el galpón y poza seleccionados.', 'warning')
            except Exception as e:
                flash(f'Ocurrió un error inesperado: {str(e)}', 'danger')

    return render_template(
        'registrar_partos.html',
        galpones_pozas=galpones_pozas,
        galpones_unicos=galpones_unicos,
        pozas_unicas=pozas_unicas
    )

# Ruta para buscar partos
@app.route('/buscar_partos', methods=['GET'])
def buscar_partos():
    galpon = request.args.get('galpon')
    poza = request.args.get('poza')

    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            cursor.execute('''
                SELECT * FROM partos
                WHERE galpon = %s AND poza = %s
            ''', (galpon, poza))
            partos = cursor.fetchall()

    return render_template('buscar_partos.html', partos=partos)

# Ruta para editar partos
@app.route('/editar_parto/<int:id>', methods=['GET', 'POST'])
def editar_parto(id):
    print(f"Editando parto con ID: {id}")  # Depuración
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            if request.method == 'POST':
                try:
                    galpon = request.form['galpon']
                    poza = request.form['poza']
                    numero_parto = int(request.form['numero_parto'])
                    nacidos = int(request.form['nacidos'])
                    muertos_bebes = int(request.form['muertos_bebes'])
                    muertos_reproductores = int(request.form['muertos_reproductores'])

                    validate_positive_values(numero_parto=numero_parto, nacidos=nacidos, muertos_bebes=muertos_bebes, muertos_reproductores=muertos_reproductores)

                    cursor.execute('''
                        UPDATE partos
                        SET galpon = %s, poza = %s, numero_parto = %s, nacidos = %s, muertos_bebes = %s, muertos_reproductores = %s
                        WHERE id = %s
                    ''', (galpon, poza, numero_parto, nacidos, muertos_bebes, muertos_reproductores, id))

                    conn.commit()
                    flash('Parto actualizado correctamente.', 'success')
                    return redirect(url_for('index'))
                except ValueError as e:
                    flash(f'Error en los datos ingresados: {str(e)}', 'danger')
                except psycopg2.Error as e:
                    flash(f'Error en la base de datos: {str(e)}', 'danger')
                except Exception as e:
                    flash(f'Ocurrió un error inesperado: {str(e)}', 'danger')

            cursor.execute('SELECT * FROM partos WHERE id = %s', (id,))
            parto = cursor.fetchone()
            print(f"Parto encontrado: {parto}")  # Depuración

    if parto is None:
        flash('Parto no encontrado.', 'danger')
        return redirect(url_for('index'))

    return render_template('editar_parto.html', parto=parto)

# Ruta para registrar destete
# Ruta para registrar destete (versión robusta)
# Ruta para registrar destete (versión robusta y con debug)
@app.route('/registrar_destete', methods=['GET', 'POST'])
def registrar_destete():
    galpones_unicos = []
    pozas_unicas = []
    destetados_hoy = 0
    destetados_mes = 0
    total_destetados = 0

    # Obtener galpones/pozas y estadísticas (GET parte)
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                # Galpones y pozas
                cursor.execute("SELECT DISTINCT galpon FROM reproductores ORDER BY galpon")
                galpones_unicos = [r['galpon'] for r in cursor.fetchall()]

                cursor.execute("SELECT DISTINCT poza FROM reproductores ORDER BY poza")
                pozas_unicas = [r['poza'] for r in cursor.fetchall()]

                # Total acumulado (simple)
                cursor.execute("""
                    SELECT COALESCE(SUM(destetados_hembras + destetados_machos), 0) AS suma
                    FROM destetes
                """)
                total_destetados = int(cursor.fetchone()['suma'] or 0)

                # --- Destetados HOY (robusto para distintos formatos) ---
                cursor.execute("""
                    SELECT COALESCE(SUM(destetados_hembras + destetados_machos), 0) AS suma
                    FROM destetes
                    WHERE (
                        -- Formato ISO al inicio:  YYYY-MM-DD or YYYY-MM-DD HH:MM:SS[.fff]
                        (substring(trim(fecha_destete) from '(\d{4}-\d{2}-\d{2})') IS NOT NULL
                         AND substring(trim(fecha_destete) from '(\d{4}-\d{2}-\d{2})')::date = CURRENT_DATE)
                        OR
                        -- Formato con barras al inicio: DD/MM/YYYY or DD/MM/YYYY HH:MM:SS
                        (substring(trim(fecha_destete) from '(\d{2}/\d{2}/\d{4})') IS NOT NULL
                         AND to_date(substring(trim(fecha_destete) from '(\d{2}/\d{2}/\d{4})'),'DD/MM/YYYY') = CURRENT_DATE)
                    )
                """)
                destetados_hoy = int(cursor.fetchone()['suma'] or 0)

                # --- Destetados MES (mismo enfoque, por mes actual) ---
                cursor.execute("""
                    SELECT COALESCE(SUM(destetados_hembras + destetados_machos), 0) AS suma
                    FROM destetes
                    WHERE (
                        (substring(trim(fecha_destete) from '(\d{4}-\d{2}-\d{2})') IS NOT NULL
                         AND date_trunc('month', substring(trim(fecha_destete) from '(\d{4}-\d{2}-\d{2})')::date) = date_trunc('month', CURRENT_DATE))
                        OR
                        (substring(trim(fecha_destete) from '(\d{2}/\d{2}/\d{4})') IS NOT NULL
                         AND date_trunc('month', to_date(substring(trim(fecha_destete) from '(\d{2}/\d{2}/\d{4})'),'DD/MM/YYYY')) = date_trunc('month', CURRENT_DATE))
                    )
                """)
                destetados_mes = int(cursor.fetchone()['suma'] or 0)

        app.logger.debug(f"[destetes] hoy={destetados_hoy} mes={destetados_mes} total={total_destetados}")

    except Exception as e:
        app.logger.error("Error al leer estadísticas de destetes", exc_info=e)
        flash('Advertencia: error al calcular estadísticas (revisa logs).', 'warning')
        # Si falla, las listas ya están inicializadas con valores vacíos

    # Manejo POST (inserción)
    if request.method == 'POST':
        try:
            galpon = request.form['galpon']
            poza = request.form['poza']
            destetados_hembras = int(request.form['destetados_hembras'])
            destetados_machos = int(request.form['destetados_machos'])

            if destetados_hembras < 0 or destetados_machos < 0:
                flash('Los valores no pueden ser negativos.', 'danger')
                return redirect(url_for('registrar_destete'))

            if destetados_hembras == 0 and destetados_machos == 0:
                flash('Debe ingresar al menos un animal destetado.', 'danger')
                return redirect(url_for('registrar_destete'))

            fecha_str = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        INSERT INTO destetes (galpon, poza, destetados_hembras, destetados_machos, fecha_destete)
                        VALUES (%s, %s, %s, %s, %s)
                    ''', (galpon, poza, destetados_hembras, destetados_machos, fecha_str))
                conn.commit()

            flash('Destete registrado correctamente.', 'success')
            return redirect(url_for('registrar_destete'))

        except ValueError:
            flash('Por favor ingrese valores numéricos válidos.', 'danger')
        except Exception as e:
            app.logger.error("Error al insertar destete", exc_info=e)
            flash('Error al registrar el destete. Revisa los logs.', 'danger')
            return redirect(url_for('registrar_destete'))

    # Renderizar template con las variables calculadas
    return render_template('registrar_destete.html',
                           galpones_unicos=galpones_unicos,
                           pozas_unicas=pozas_unicas,
                           destetados_hoy=destetados_hoy,
                           destetados_mes=destetados_mes,
                           total_destetados=total_destetados)

@app.route('/registrar_muertes_destetados', methods=['GET', 'POST'])
def registrar_muertes_destetados():
    if request.method == 'POST':
        try:
            galpon = request.form['galpon']
            poza = request.form['poza']
            muertos_hembras = int(request.form['muertos_hembras'])
            muertos_machos = int(request.form['muertos_machos'])

            # Validar valores positivos
            if muertos_hembras < 0 or muertos_machos < 0:
                flash('Los valores no pueden ser negativos.', 'danger')
                return redirect(url_for('registrar_muertes_destetados'))

            # Insertar en la base de datos
            conn = get_db_connection()
            if conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        INSERT INTO muertes_destetados (galpon, poza, muertos_hembras, muertos_machos, fecha_muerte)
                        VALUES (%s, %s, %s, %s, NOW())
                    ''', (galpon, poza, muertos_hembras, muertos_machos))
                    conn.commit()
                conn.close()
                
                flash('Muertes registradas correctamente.', 'success')
                return redirect(url_for('registrar_muertes_destetados'))
            else:
                flash('Error de conexión a la base de datos.', 'danger')

        except ValueError:
            flash('Por favor ingrese valores numéricos válidos.', 'danger')
        except Exception as e:
            print(f"Error al registrar muertes: {str(e)}")
            flash('Error al registrar las muertes. Intente nuevamente.', 'danger')

    return render_template('registrar_muertes_destetados.html')
# Ruta unificada para ventas (REEMPLAZA las dos rutas anteriores)
# Asegúrate de tener estos imports
@app.route('/ventas', methods=['GET', 'POST'])
def ventas():
    galpones_pozas = []
    ventas_destetados_hoy = 0
    ventas_destetados_mes = 0
    total_ventas_destetados = 0
    ventas_descarte_mes = 0
    ingresos_totales = 0

    # --- GET: Obtener galpones/pozas y estadísticas ---
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                # Galpones y pozas
                cur.execute("SELECT DISTINCT galpon, poza FROM reproductores ORDER BY galpon, poza")
                galpones_pozas = cur.fetchall()

                # Verificar si la tabla ventas existe consultando el catálogo del sistema
                cur.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public'
                        AND table_name = 'ventas'
                    );
                """)
                tabla_existe = cur.fetchone()[0]
                
                if not tabla_existe:
                    # Si la tabla no existe, inicializarla
                    init_ventas_table()
                    flash('Tabla de ventas inicializada correctamente.', 'info')
                else:
                    # Verificar si hay datos
                    cur.execute("SELECT COUNT(*) FROM ventas")
                    hay_datos = cur.fetchone()[0] > 0
                    
                    if hay_datos:
                        # Total acumulado de ventas de destetados
                        cur.execute("""
                            SELECT COALESCE(SUM(hembras_vendidas + machos_vendidos),0) AS total
                            FROM ventas
                            WHERE tipo_venta='destetados'
                        """)
                        total_ventas_destetados = int(cur.fetchone()['total'] or 0)

                        # Ventas de destetados hoy
                        cur.execute("""
                            SELECT COALESCE(SUM(hembras_vendidas + machos_vendidos),0) AS total
                            FROM ventas
                            WHERE tipo_venta='destetados'
                            AND fecha_venta::date = CURRENT_DATE
                        """)
                        ventas_destetados_hoy = int(cur.fetchone()['total'] or 0)

                        # Ventas de destetados este mes
                        cur.execute("""
                            SELECT COALESCE(SUM(hembras_vendidas + machos_vendidos),0) AS total
                            FROM ventas
                            WHERE tipo_venta='destetados'
                            AND date_trunc('month', fecha_venta) = date_trunc('month', CURRENT_DATE)
                        """)
                        ventas_destetados_mes = int(cur.fetchone()['total'] or 0)
                        
                        # Ventas de descarte este mes
                        cur.execute("""
                            SELECT COALESCE(SUM(hembras_vendidas + machos_vendidos),0) AS total
                            FROM ventas
                            WHERE tipo_venta='descarte'
                            AND date_trunc('month', fecha_venta) = date_trunc('month', CURRENT_DATE)
                        """)
                        ventas_descarte_mes = int(cur.fetchone()['total'] or 0)
                        
                        # Ingresos totales (suma de todas las ventas)
                        cur.execute("""
                            SELECT COALESCE(SUM(costo_total),0) AS total
                            FROM ventas
                        """)
                        ingresos_totales = float(cur.fetchone()['total'] or 0)

        app.logger.debug(f"[ventas] hoy={ventas_destetados_hoy} mes={ventas_destetados_mes} total={total_ventas_destetados}")

    except Exception as e:
        app.logger.error("Error al leer estadísticas de ventas", exc_info=e)
        flash('Advertencia: error al calcular estadísticas de ventas (revisa logs).', 'warning')

    # --- POST: Registrar venta ---
    if request.method == 'POST':
        try:
            tipo_venta = request.form['tipo_venta']
            costo_venta = float(request.form['costo_venta'])
            fecha_venta = request.form.get('fecha_venta', datetime.utcnow().date())

            if tipo_venta == 'destetados':
                hembras_vendidas = int(request.form['hembras_vendidas'])
                machos_vendidos = int(request.form['machos_vendidos'])

                if hembras_vendidas < 0 or machos_vendidos < 0 or costo_venta <= 0:
                    flash('Valores de venta no válidos.', 'danger')
                    return redirect(url_for('ventas'))

                if hembras_vendidas == 0 and machos_vendidos == 0:
                    flash('Debe registrar al menos un cuy vendido.', 'danger')
                    return redirect(url_for('ventas'))

                with get_db_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            INSERT INTO ventas (tipo_venta, hembras_vendidas, machos_vendidos, costo_total, fecha_venta)
                            VALUES (%s, %s, %s, %s, %s)
                        """, (tipo_venta, hembras_vendidas, machos_vendidos, costo_venta, fecha_venta))
                    conn.commit()

                flash('Venta de destetados registrada correctamente.', 'success')

            elif tipo_venta == 'descarte':
                origen_galpon = request.form['origen_galpon']
                origen_poza = request.form['origen_poza']
                cuyes_vendidos = int(request.form['cuyes_vendidos'])
                mover_engorde = 'mover_engorde' in request.form
                
                # Campos opcionales para engorde
                engorde_galpon = request.form.get('engorde_galpon', '')
                engorde_poza = request.form.get('engorde_poza', '')
                fecha_movimiento = request.form.get('fecha_movimiento', None)
                dias_engorde = request.form.get('dias_engorde', 0)
                observaciones = request.form.get('observaciones', '')

                if cuyes_vendidos <= 0 or costo_venta <= 0:
                    flash('Valores de venta no válidos.', 'danger')
                    return redirect(url_for('ventas'))

                if not origen_galpon or not origen_poza:
                    flash('Debe especificar el galpón y poza de origen.', 'danger')
                    return redirect(url_for('ventas'))
                
                # Validar campos de engorde si se seleccionó esa opción
                if mover_engorde:
                    if not engorde_galpon or not engorde_poza:
                        flash('Debe especificar el galpón y poza de engorde.', 'danger')
                        return redirect(url_for('ventas'))
                    if not fecha_movimiento:
                        flash('Debe especificar la fecha de movimiento a engorde.', 'danger')
                        return redirect(url_for('ventas'))

                with get_db_connection() as conn:
                    with conn.cursor() as cur:
                        # Insertar la venta con los nuevos campos
                        cur.execute("""
                            INSERT INTO ventas (
                                tipo_venta, galpon, poza, hembras_vendidas, machos_vendidos, 
                                costo_total, fecha_venta, mover_engorde, engorde_galpon, 
                                engorde_poza, fecha_movimiento, dias_engorde, observaciones
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            tipo_venta, origen_galpon, origen_poza, 0, cuyes_vendidos, 
                            costo_venta, fecha_venta, mover_engorde, engorde_galpon, 
                            engorde_poza, fecha_movimiento, dias_engorde, observaciones
                        ))
                    conn.commit()

                flash('Venta de descarte registrada correctamente.', 'success')

            else:
                flash('Tipo de venta desconocido.', 'danger')

            return redirect(url_for('ventas'))

        except ValueError:
            flash('Por favor ingrese valores numéricos válidos.', 'danger')
        except Exception as e:
            app.logger.error("Error al registrar venta", exc_info=e)
            flash('Error al registrar la venta. Revisa los logs.', 'danger')
            return redirect(url_for('ventas'))

    return render_template('ventas_unificado.html',
                           galpones_pozas=galpones_pozas,
                           ventas_destetados_hoy=ventas_destetados_hoy,
                           ventas_destetados_mes=ventas_destetados_mes,
                           total_ventas_destetados=total_ventas_destetados,
                           ventas_descarte_mes=ventas_descarte_mes,
                           ingresos_totales=ingresos_totales)
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
# Ruta para ver análisis de datos - CORREGIDA
@app.route('/analisis_datos')
def analisis_datos():
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                # Obtener datos de reproductores
                cursor.execute('SELECT * FROM reproductores ORDER BY galpon, poza')
                reproductores = cursor.fetchall()

                # Obtener datos de partos
                cursor.execute('SELECT * FROM partos ORDER BY galpon, poza, fecha_nacimiento')
                partos = cursor.fetchall()

                # Obtener datos de destetes
                cursor.execute('SELECT * FROM destetes ORDER BY galpon, poza, fecha_destete')
                destetes = cursor.fetchall()

                # Obtener datos de muertes de destetados
                cursor.execute('SELECT * FROM muertes_destetados ORDER BY galpon, poza, fecha_muerte')
                muertes_destetados = cursor.fetchall()

                # Obtener datos de ventas de destetados
                cursor.execute('SELECT * FROM ventas_destetados ORDER BY galpon, poza, fecha_venta')
                ventas_destetados = cursor.fetchall()

                # Obtener datos de ventas de descarte
                cursor.execute('SELECT * FROM ventas_descarte ORDER BY galpon, poza, fecha_venta')
                ventas_descarte = cursor.fetchall()

                # Obtener datos de gastos
                cursor.execute('SELECT * FROM gastos ORDER BY fecha_gasto DESC')
                gastos = cursor.fetchall()

        # Pasar los datos organizados por tabla
        return render_template('analisis_datos.html', 
                             reproductores=reproductores,
                             partos=partos,
                             destetes=destetes,
                             muertes_destetados=muertes_destetados,
                             ventas_destetados=ventas_destetados,
                             ventas_descarte=ventas_descarte,
                             gastos=gastos)

    except Exception as e:
        print(f"Error en análisis de datos: {e}")
        flash(f'Ocurrió un error al cargar los datos: {str(e)}', 'danger')
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
                # 1. Mortalidad por mes y poza/galpón (incluyendo todas las fuentes)
                cursor.execute('''
                    SELECT 
                        TO_CHAR(TO_DATE(fecha_muerte, 'YYYY-MM-DD'), 'YYYY-MM') AS mes,
                        galpon,
                        poza,
                        SUM(muertos_hembras + muertos_machos) AS total_muertes
                    FROM muertes_destetados
                    WHERE fecha_muerte IS NOT NULL
                    GROUP BY mes, galpon, poza

                    UNION ALL

                    SELECT 
                        TO_CHAR(TO_DATE(fecha_nacimiento, 'YYYY-MM-DD'), 'YYYY-MM') AS mes,
                        galpon,
                        poza,
                        SUM(muertos_bebes + muertos_reproductores) AS total_muertes
                    FROM partos
                    WHERE fecha_nacimiento IS NOT NULL
                    GROUP BY mes, galpon, poza
                ''')
                mortalidad_por_mes = cursor.fetchall()

                # 2. Nacimientos por mes y poza/galpón
                cursor.execute('''
                    SELECT 
                        TO_CHAR(TO_DATE(fecha_nacimiento, 'YYYY-MM-DD'), 'YYYY-MM') AS mes,
                        galpon,
                        poza,
                        SUM(nacidos) AS total_nacidos
                    FROM partos
                    WHERE fecha_nacimiento IS NOT NULL
                    GROUP BY mes, galpon, poza
                    ORDER BY mes, galpon, poza
                ''')
                nacimientos_por_mes = cursor.fetchall()

                # 3. Costos и ganancias por mes
                cursor.execute('''
                    SELECT 
                        TO_CHAR(TO_DATE(fecha_gasto, 'YYYY-MM-DD'), 'YYYY-MM') AS mes,
                        SUM(monto) AS total_gastos
                    FROM gastos
                    WHERE fecha_gasto IS NOT NULL
                    GROUP BY mes
                    ORDER BY mes
                ''')
                gastos_por_mes = cursor.fetchall()

                cursor.execute('''
                    SELECT 
                        TO_CHAR(TO_DATE(fecha_venta, 'YYYY-MM-DD'), 'YYYY-MM') AS mes,
                        SUM(costo_venta) AS total_ventas
                    FROM ventas_destetados
                    WHERE fecha_venta IS NOT NULL
                    GROUP BY mes
                    ORDER BY mes
                ''')
                ventas_destetados_por_mes = cursor.fetchall()

                cursor.execute('''
                    SELECT 
                        TO_CHAR(TO_DATE(fecha_venta, 'YYYY-MM-DD'), 'YYYY-MM') AS mes,
                        SUM(costo_venta) AS total_ventas
                    FROM ventas_descarte
                    WHERE fecha_venta IS NOT NULL
                    GROUP BY mes
                    ORDER BY mes
                ''')
                ventas_descarte_por_mes = cursor.fetchall()

                # 4. Proyección de crecimiento (usando Pandas)
                cursor.execute('''
                    SELECT 
                        TO_CHAR(TO_DATE(fecha_nacimiento, 'YYYY-MM-DD'), 'YYYY-MM') AS mes,
                        SUM(nacidos) AS total_nacidos
                    FROM partos
                    WHERE fecha_nacimiento IS NOT NULL
                    GROUP BY mes
                    ORDER BY mes
                ''')
                proyeccion_nacimientos = cursor.fetchall()

                cursor.execute('''
                    SELECT 
                        TO_CHAR(TO_DATE(fecha_venta, 'YYYY-MM-DD'), 'YYYY-MM') AS mes,
                        SUM(costo_venta) AS total_ventas
                    FROM ventas_destetados
                    WHERE fecha_venta IS NOT NULL
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

# Ruta para health check
@app.route('/health')
def health_check():
    """Endpoint para monitoreo de salud (HEAD request compatible)"""
    try:
        # Verifica conexión a la base de datos
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")  # Consulta ligera
        
        # Respuesta mínima en texto plano
        return "Application and database: OK", 200, {'Content-Type': 'text/plain'}
    
    except Exception as e:
        return f"Database connection failed: {str(e)}", 500

# Ruta para predicciones
@app.route('/predicciones', methods=['GET', 'POST'])
def predicciones():
    if request.method == 'POST':
        try:
            # Obtener el número de meses a predecir desde el formulario
            meses_a_predecir = int(request.form['meses_a_predecir'])

            # Entrenar los modelos
            modelo_mortalidad, modelo_nacimientos, modelo_ganancias = entrenar_modelos()

            # Verificar si los modelos se entrenaron correctamente
            modelos_entrenados = 0
            if modelo_mortalidad is not None:
                modelos_entrenados += 1
            if modelo_nacimientos is not None:
                modelos_entrenados += 1
            if modelo_ganancias is not None:
                modelos_entrenados += 1

            if modelos_entrenados == 0:
                flash('No hay suficientes datos históricos para generar predicciones. Se necesitan al menos 2 meses de datos.', 'warning')
                return redirect(url_for('predicciones'))

            # Crear fechas futuras para la predicción
            ultima_fecha = pd.to_datetime('now')  # Fecha actual
            fechas_futuras = pd.date_range(start=ultima_fecha, periods=meses_a_predecir, freq='M')
            
            predicciones = []
            for i, fecha in enumerate(fechas_futuras):
                mes_num = i + 1  # Meses futuros desde el presente
                
                prediccion = {
                    'mes': fecha.strftime('%Y-%m'),
                    'prediccion_mortalidad': 0,
                    'prediccion_nacimientos': 0,
                    'prediccion_ganancias': 0
                }
                
                # Realizar predicciones solo si los modelos están disponibles
                if modelo_mortalidad is not None:
                    try:
                        prediccion['prediccion_mortalidad'] = max(0, float(modelo_mortalidad.predict([[mes_num]])[0]))
                    except:
                        prediccion['prediccion_mortalidad'] = 0
                
                if modelo_nacimientos is not None:
                    try:
                        prediccion['prediccion_nacimientos'] = max(0, float(modelo_nacimientos.predict([[mes_num]])[0]))
                    except:
                        prediccion['prediccion_nacimientos'] = 0
                
                if modelo_ganancias is not None:
                    try:
                        prediccion['prediccion_ganancias'] = max(0, float(modelo_ganancias.predict([[mes_num]])[0]))
                    except:
                        prediccion['prediccion_ganancias'] = 0
                
                predicciones.append(prediccion)

            # Informar al usuario sobre los modelos que se pudieron entrenar
            mensaje_modelos = []
            if modelo_nacimientos is not None:
                mensaje_modelos.append("nacimientos")
            if modelo_mortalidad is not None:
                mensaje_modelos.append("mortalidad")
            if modelo_ganancias is not None:
                mensaje_modelos.append("ganancias")
            
            if mensaje_modelos:
                flash(f'Predicciones generadas usando datos de: {", ".join(mensaje_modelos)}', 'success')
            else:
                flash('No se pudieron generar predicciones por falta de datos históricos.', 'warning')

            return render_template('predicciones.html', predicciones=predicciones)

        except Exception as e:
            flash(f'Ocurrió un error al realizar las predicciones: {str(e)}', 'danger')
            return redirect(url_for('predicciones'))

    # Para GET requests, simplemente mostrar el formulario
    return render_template('predicciones.html')

# Agregar estas rutas después de las rutas existentes en app.py

@app.route('/api/notificaciones')
def obtener_notificaciones():
    """Obtener notificaciones no leídas"""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                cursor.execute('''
                    SELECT * FROM notificaciones 
                    WHERE leida = FALSE 
                    ORDER BY 
                        CASE prioridad 
                            WHEN 'urgente' THEN 1
                            WHEN 'alta' THEN 2
                            WHEN 'media' THEN 3
                            ELSE 4
                        END,
                    fecha_creacion DESC
                    LIMIT 20
                ''')
                notificaciones = cursor.fetchall()
                return jsonify([dict(notif) for notif in notificaciones])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/notificaciones/<int:notificacion_id>/leer', methods=['POST'])
def marcar_notificacion_leida(notificacion_id):
    """Marcar notificación como leída"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    UPDATE notificaciones SET leida = TRUE WHERE id = %s
                ''', (notificacion_id,))
                conn.commit()
                return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/notificaciones/leer-todas', methods=['POST'])
def marcar_todas_leidas():
    """Marcar todas las notificaciones como leídas"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('UPDATE notificaciones SET leida = TRUE')
                conn.commit()
                return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/notificaciones/generar', methods=['POST'])
def generar_notificaciones():
    """Forzar generación de notificaciones"""
    try:
        notificaciones = generar_todas_las_notificaciones()
        return jsonify({
            'success': True,
            'generadas': len(notificaciones),
            'notificaciones': notificaciones
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)