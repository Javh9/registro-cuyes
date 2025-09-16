from flask import Flask, render_template, request, redirect, url_for, flash, Response
import psycopg2
from psycopg2 import extras
from datetime import datetime
import os
import pandas as pd
from urllib.parse import urlparse
import io
from sklearn.linear_model import LinearRegression
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

        # Convertir a DataFrames de Pandas
        df_mortalidad = pd.DataFrame(mortalidad_data, columns=['mes', 'total_muertes'])
        df_nacimientos = pd.DataFrame(nacimientos_data, columns=['mes', 'total_nacidos'])
        df_ganancias = pd.DataFrame(ganancias_data, columns=['mes', 'total_ganancias'])

        # Convertir fechas a formato numérico (meses desde el inicio)
        df_mortalidad['mes_num'] = (pd.to_datetime(df_mortalidad['mes']) - pd.to_datetime(df_mortalidad['mes'].min())).dt.days / 30
        df_nacimientos['mes_num'] = (pd.to_datetime(df_nacimientos['mes']) - pd.to_datetime(df_nacimientos['mes'].min())).dt.days / 30
        df_ganancias['mes_num'] = (pd.to_datetime(df_ganancias['mes']) - pd.to_datetime(df_ganancias['mes'].min())).dt.days / 30

        # Entrenar modelo de mortalidad
        X_mortalidad = df_mortalidad[['mes_num']]
        y_mortalidad = df_mortalidad['total_muertes']
        modelo_mortalidad = LinearRegression()
        modelo_mortalidad.fit(X_mortalidad, y_mortalidad)

        # Entrenar modelo de nacimientos
        X_nacimientos = df_nacimientos[['mes_num']]
        y_nacimientos = df_nacimientos['total_nacidos']
        modelo_nacimientos = LinearRegression()
        modelo_nacimientos.fit(X_nacimientos, y_nacimientos)

        # Entrenar modelo de ganancias
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

            conn.commit()

# Llamar a la función para crear o actualizar las tablas al iniciar la aplicación
try:
    crear_o_actualizar_tablas()
    print("✅ Aplicación iniciada correctamente")
except Exception as e:
    print(f"⚠️  Error al inicializar tablas: {e}")

# Ruta principal
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sistema de Registro de Cuyes</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #4e73df;
            --success: #1cc88a;
            --info: #36b9cc;
            --warning: #f6c23e;
            --danger: #e74a3b;
            --secondary: #858796;
            --light: #f8f9fc;
            --dark: #5a5c69;
        }
        
        body {
            background-color: #f8f9fc;
            font-family: 'Nunito', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            padding-top: 0;
        }
        
        .navbar-custom {
            background: linear-gradient(90deg, var(--primary) 0%, #224abe 100%);
            box-shadow: 0 0.15rem 1.75rem 0 rgba(58, 59, 69, 0.15);
        }
        
        .sidebar {
            min-height: calc(100vh - 70px);
            background: white;
            box-shadow: 0 0 15px rgba(0, 0, 0, 0.1);
            position: sticky;
            top: 70px;
        }
        
        .sidebar .nav-item {
            margin-bottom: 0.25rem;
        }
        
        .sidebar .nav-link {
            color: var(--dark);
            padding: 1rem;
            border-left: 4px solid transparent;
        }
        
        .sidebar .nav-link:hover {
            color: var(--primary);
            background-color: rgba(78, 115, 223, 0.1);
            border-left-color: var(--primary);
        }
        
        .sidebar .nav-link.active {
            font-weight: bold;
            color: var(--primary);
            background-color: rgba(78, 115, 223, 0.15);
            border-left-color: var(--primary);
        }
        
        .sidebar .nav-link i {
            margin-right: 0.5rem;
            width: 20px;
            text-align: center;
        }
        
        .topbar {
            height: 70px;
            box-shadow: 0 0.15rem 1.75rem 0 rgba(58, 59, 69, 0.15);
            background-color: white;
            position: sticky;
            top: 0;
            z-index: 1000;
        }
        
        .card {
            border: none;
            border-radius: 0.5rem;
            box-shadow: 0 0.15rem 1.75rem 0 rgba(58, 59, 69, 0.1);
            margin-bottom: 1.5rem;
            transition: transform 0.2s;
        }
        
        .card:hover {
            transform: translateY(-5px);
        }
        
        .card-header {
            background-color: #f8f9fc;
            border-bottom: 1px solid #e3e6f0;
            font-weight: bold;
            color: var(--dark);
            padding: 1rem 1.5rem;
        }
        
        .btn-primary {
            background-color: var(--primary);
            border-color: var(--primary);
            border-radius: 0.35rem;
            padding: 0.5rem 1rem;
            font-weight: 600;
        }
        
        .btn-primary:hover {
            background-color: #2e59d9;
            border-color: #2e59d9;
            transform: translateY(-2px);
            box-shadow: 0 0.15rem 0.75rem 0 rgba(58, 59, 69, 0.2);
        }
        
        .stat-card {
            border-left: 4px solid;
            transition: transform 0.2s;
        }
        
        .stat-card:hover {
            transform: translateY(-5px);
        }
        
        .stat-card.primary { border-left-color: var(--primary); }
        .stat-card.success { border-left-color: var(--success); }
        .stat-card.info { border-left-color: var(--info); }
        .stat-card.warning { border-left-color: var(--warning); }
        
        .page-title {
            color: var(--dark);
            margin-bottom: 1.5rem;
            font-weight: 700;
        }
        
        .table th {
            border-top: none;
            font-weight: 600;
            color: var(--dark);
            background-color: #f8f9fc;
        }
        
        .badge-status {
            padding: 0.5em 0.8em;
            border-radius: 0.35rem;
            font-weight: 600;
        }
        
        .galpon-card {
            transition: all 0.3s ease;
        }
        
        .galpon-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15);
        }
        
        .poza-item {
            border-left: 3px solid var(--primary);
            padding-left: 10px;
            margin-bottom: 10px;
            transition: all 0.2s ease;
        }
        
        .poza-item:hover {
            background-color: rgba(78, 115, 223, 0.05);
        }
        
        .dashboard-stats {
            margin-bottom: 2rem;
        }
        
        .main-content {
            padding: 2rem 0;
        }
        
        .footer {
            background-color: white;
            padding: 1.5rem;
            margin-top: 2rem;
            border-top: 1px solid #e3e6f0;
        }
        
        @media (max-width: 768px) {
            .sidebar {
                min-height: auto;
                position: static;
            }
            
            .topbar {
                position: static;
            }
        }
    </style>
</head>
<body>
    <!-- Navbar -->
    <nav class="navbar navbar-expand-lg navbar-dark navbar-custom">
        <div class="container-fluid">
            <a class="navbar-brand" href="#">
                <i class="fas fa-paw me-2"></i>
                <span class="fw-bold">Registro de Cuyes</span>
            </a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarContent">
                <span class="navbar-toggler-icon"></span>
            </button>
            
            <div class="collapse navbar-collapse" id="navbarContent">
                <ul class="navbar-nav ms-auto mb-2 mb-lg-0">
                    <li class="nav-item dropdown">
                        <a class="nav-link dropdown-toggle" href="#" id="navbarDropdown" role="button" data-bs-toggle="dropdown">
                            <i class="fas fa-user-circle me-1"></i> Administrador
                        </a>
                        <ul class="dropdown-menu dropdown-menu-end">
                            <li><a class="dropdown-item" href="#"><i class="fas fa-user me-2"></i>Perfil</a></li>
                            <li><a class="dropdown-item" href="#"><i class="fas fa-cog me-2"></i>Configuración</a></li>
                            <li><hr class="dropdown-divider"></li>
                            <li><a class="dropdown-item" href="#"><i class="fas fa-sign-out-alt me-2"></i>Cerrar Sesión</a></li>
                        </ul>
                    </li>
                </ul>
            </div>
        </div>
    </nav>

    <div class="container-fluid">
        <div class="row">
            <!-- Sidebar -->
            <div class="col-md-3 col-lg-2 sidebar d-md-block">
                <div class="position-sticky pt-3">
                    <ul class="nav flex-column">
                        <li class="nav-item">
                            <a class="nav-link active" href="#">
                                <i class="fas fa-home"></i> Dashboard
                            </a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" href="/ingresar_reproductores">
                                <i class="fas fa-egg"></i> Reproductores
                            </a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" href="/registrar_partos">
                                <i class="fas fa-baby"></i> Partos
                            </a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" href="/registrar_destete">
                                <i class="fas fa-child"></i> Destetes
                            </a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" href="/registrar_muertes_destetados">
                                <i class="fas fa-skull"></i> Mortalidad
                            </a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" href="/ventas">
                                <i class="fas fa-money-bill-wave"></i> Ventas
                            </a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" href="/registrar_gastos">
                                <i class="fas fa-receipt"></i> Gastos
                            </a>
                        </li><a href="/ventas">
                        <li class="nav-item">
                            <a class="nav-link" href="/analisis_datos">
                                <i class="fas fa-chart-bar"></i> Análisis
                            </a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" href="/balance">
                                <i class="fas fa-calculator"></i> Balance
                            </a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" href="/resultados">
                                <i class="fas fa-chart-line"></i> Resultados
                            </a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" href="/predicciones">
                                <i class="fas fa-crystal-ball"></i> Predicciones
                            </a>
                        </li>
                    </ul>
                </div>
            </div>

            <!-- Main Content -->
            <main class="col-md-9 col-lg-10 ms-sm-auto px-md-4 main-content">
                <div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3">
                    <h1 class="h2 page-title">Dashboard - Resumen General</h1>
                    <div class="btn-toolbar mb-2 mb-md-0">
                        <div class="btn-group me-2">
                            <a href="/exportar_excel" class="btn btn-sm btn-outline-secondary">
                                <i class="fas fa-download me-1"></i> Exportar
                            </a>
                        </div>
                    </div>
                </div>

                <!-- Stats Cards -->
                <div class="row mb-4 dashboard-stats">
                    <div class="col-xl-3 col-md-6 mb-4">
                        <div class="card stat-card primary h-100">
                            <div class="card-body">
                                <div class="row align-items-center">
                                    <div class="col mr-2">
                                        <div class="text-xs font-weight-bold text-primary text-uppercase mb-1">
                                            Total Reproductores</div>
                                        <div class="h5 mb-0 font-weight-bold text-gray-800">
                                            {% set total_reproductores = [] %}
                                            {% for galpon in datos_galpones %}
                                                {% for poza in datos_galpones[galpon] %}
                                                    {% set _ = total_reproductores.append(datos_galpones[galpon][poza]['reproductores']) %}
                                                {% endfor %}
                                            {% endfor %}
                                            {{ total_reproductores|sum }}
                                        </div>
                                    </div>
                                    <div class="col-auto">
                                        <i class="fas fa-egg fa-2x text-gray-300"></i>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="col-xl-3 col-md-6 mb-4">
                        <div class="card stat-card success h-100">
                            <div class="card-body">
                                <div class="row align-items-center">
                                    <div class="col mr-2">
                                        <div class="text-xs font-weight-bold text-success text-uppercase mb-1">
                                            Nacidos Netos</div>
                                        <div class="h5 mb-0 font-weight-bold text-gray-800">
                                            {% set total_nacidos = [] %}
                                            {% for galpon in total_nacidos_por_galpon %}
                                                {% set _ = total_nacidos.append(total_nacidos_por_galpon[galpon]) %}
                                            {% endfor %}
                                            {{ total_nacidos|sum }}
                                        </div>
                                    </div>
                                    <div class="col-auto">
                                        <i class="fas fa-baby fa-2x text-gray-300"></i>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="col-xl-3 col-md-6 mb-4">
                        <div class="card stat-card warning h-100">
                            <div class="card-body">
                                <div class="row align-items-center">
                                    <div class="col mr-2">
                                        <div class="text-xs font-weight-bold text-warning text-uppercase mb-1">
                                            Destetados</div>
                                        <div class="h5 mb-0 font-weight-bold text-gray-800">
                                            {% set total_destetados = [] %}
                                            {% for galpon in datos_galpones %}
                                                {% for poza in datos_galpones[galpon] %}
                                                    {% set _ = total_destetados.append(datos_galpones[galpon][poza]['destetados']) %}
                                                {% endfor %}
                                            {% endfor %}
                                            {{ total_destetados|sum }}
                                        </div>
                                    </div>
                                    <div class="col-auto">
                                        <i class="fas fa-child fa-2x text-gray-300"></i>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="col-xl-3 col-md-6 mb-4">
                        <div class="card stat-card info h-100">
                            <div class="card-body">
                                <div class="row align-items-center">
                                    <div class="col mr-2">
                                        <div class="text-xs font-weight-bold text-info text-uppercase mb-1">
                                            Mortalidad</div>
                                        <div class="h5 mb-0 font-weight-bold text-gray-800">
                                            {% set total_muertos = [] %}
                                            {% for galpon in total_muertos_por_galpon %}
                                                {% set _ = total_muertos.append(total_muertos_por_galpon[galpon]) %}
                                            {% endfor %}
                                            {{ total_muertos|sum }}
                                        </div>
                                    </div>
                                    <div class="col-auto">
                                        <i class="fas fa-skull fa-2x text-gray-300"></i>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Resumen por Galpones -->
                <div class="row">
                    <div class="col-12">
                        <div class="card">
                            <div class="card-header py-3 d-flex justify-content-between align-items-center">
                                <h6 class="m-0 font-weight-bold text-primary">Resumen por Galpones y Pozas</h6>
                            </div>
                            <div class="card-body">
                                <div class="row">
                                    {% for galpon in datos_galpones %}
                                    <div class="col-md-6 col-lg-4 mb-4">
                                        <div class="card galpon-card h-100">
                                            <div class="card-header bg-primary text-white">
                                                <h6 class="m-0">Galpón {{ galpon }}</h6>
                                            </div>
                                            <div class="card-body">
                                                <div class="d-flex justify-content-between mb-3">
                                                    <span class="fw-bold">Reproductores:</span>
                                                    <span class="badge bg-primary">{{ total_reproductores_por_galpon[galpon] }}</span>
                                                </div>
                                                
                                                {% for poza in datos_galpones[galpon] %}
                                                <div class="poza-item mb-2">
                                                    <div class="d-flex justify-content-between">
                                                        <span class="fw-medium">Poza {{ poza }}:</span>
                                                    </div>
                                                    <div class="ms-3">
                                                        <small class="text-muted">Reproductores: {{ datos_galpones[galpon][poza]['reproductores'] }}</small><br>
                                                        <small class="text-muted">Nacidos: {{ datos_galpones[galpon][poza]['nacidos'] }}</small><br>
                                                        <small class="text-muted">Destetados: {{ datos_galpones[galpon][poza]['destetados'] }}</small><br>
                                                        <small class="text-danger">Muertos: {{ datos_galpones[galpon][poza]['muertos'] }}</small>
                                                    </div>
                                                </div>
                                                {% endfor %}
                                            </div>
                                        </div>
                                    </div>
                                    {% endfor %}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Acciones Rápidas -->
                <div class="row mt-4">
                    <div class="col-12">
                        <div class="card">
                            <div class="card-header py-3">
                                <h6 class="m-0 font-weight-bold text-primary">Acciones Rápidas</h6>
                            </div>
                            <div class="card-body">
                                <div class="row">
                                    <div class="col-md-3 col-6 mb-3">
                                        <a href="/ingresar_reproductores" class="btn btn-primary w-100">
                                            <i class="fas fa-plus-circle me-1"></i> Nuevos Reproductores
                                        </a>
                                    </div>
                                    <div class="col-md-3 col-6 mb-3">
                                        <a href="/registrar_partos" class="btn btn-success w-100">
                                            <i class="fas fa-baby me-1"></i> Registrar Parto
                                        </a>
                                    </div>
                                    <div class="col-md-3 col-6 mb-3">
                                        <a href="/registrar_destete" class="btn btn-info w-100">
                                            <i class="fas fa-child me-1"></i> Registrar Destete
                                        </a>
                                    </div>
                                    <div class="col-md-3 col-6 mb-3">
                                        <a href="/registrar_gastos" class="btn btn-warning w-100">
                                            <i class="fas fa-receipt me-1"></i> Registrar Gasto
                                        </a>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </main>
        </div>
    </div>

    <footer class="footer">
        <div class="container-fluid">
            <div class="d-flex justify-content-between align-items-center">
                <span>Sistema de Registro de Cuyes &copy; 2023</span>
                <span>v1.2.0</span>
            </div>
        </div>
    </footer>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            console.log('Sistema de registro de cuyes cargado');
            
            // Activar tooltips de Bootstrap
            var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
            var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
                return new bootstrap.Tooltip(tooltipTriggerEl)
            });
            
            // Animación para las tarjetas de estadísticas
            const statCards = document.querySelectorAll('.stat-card');
            statCards.forEach(card => {
                card.addEventListener('mouseenter', () => {
                    card.style.transform = 'translateY(-5px)';
                });
                card.addEventListener('mouseleave', () => {
                    card.style.transform = 'translateY(0)';
                });
            });
        });
    </script>
</body>
</html>
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

            if modelo_mortalidad is None or modelo_nacimientos is None or modelo_ganancias is None:
                flash('Error al entrenar los modelos predictivos.', 'danger')
                return redirect(url_for('predicciones'))

            # Crear fechas futuras para la predicción
            ultima_fecha = pd.to_datetime('now')  # Fecha actual
            fechas_futuras = pd.date_range(start=ultima_fecha, periods=meses_a_predecir, freq='M')
            meses_futuros = (fechas_futuras - fechas_futuras.min()).days / 30

            # Realizar predicciones
            predicciones_mortalidad = modelo_mortalidad.predict(meses_futuros.reshape(-1, 1))
            predicciones_nacimientos = modelo_nacimientos.predict(meses_futuros.reshape(-1, 1))
            predicciones_ganancias = modelo_ganancias.predict(meses_futuros.reshape(-1, 1))

            # Crear un DataFrame con las predicciones
            df_predicciones = pd.DataFrame({
                'mes': fechas_futuras.strftime('%Y-%m'),
                'prediccion_mortalidad': predicciones_mortalidad,
                'prediccion_nacimientos': predicciones_nacimientos,
                'prediccion_ganancias': predicciones_ganancias
            })

            # Convertir el DataFrame a una lista de diccionarios para la plantilla
            predicciones = df_predicciones.to_dict('records')

            return render_template('predicciones.html', predicciones=predicciones)

        except Exception as e:
            flash(f'Ocurrió un error al realizar las predicciones: {str(e)}', 'danger')
            return redirect(url_for('predicciones'))

    return render_template('predicciones.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)