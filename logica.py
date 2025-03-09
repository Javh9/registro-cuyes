from datetime import datetime, timedelta
import sqlite3

class CuyesManagerLogic:
    def __init__(self, db_name="cuyes.db"):
        self.db_name = db_name
        self.conn = sqlite3.connect(self.db_name)
        self.cursor = self.conn.cursor()
        self._crear_tablas()

    def _crear_tablas(self):
        """Crea las tablas necesarias en la base de datos si no existen."""
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS galpones_pozas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                galpon TEXT NOT NULL,
                poza TEXT NOT NULL,
                hembras INTEGER,
                machos INTEGER,
                numero_parto INTEGER,
                nacidos INTEGER,
                muertos_bebes INTEGER,
                muertos_reproductores INTEGER,
                tiempo_reproductores INTEGER,
                fecha_ingreso_reproductores TEXT,
                fecha_descarte TEXT,
                fecha_nacimiento TEXT,
                destetados_hembras INTEGER,
                destetados_machos INTEGER,
                muertos_destetados_hembras INTEGER,
                muertos_destetados_machos INTEGER
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS ventas_destetados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hembras_vendidas INTEGER,
                machos_vendidos INTEGER,
                costo_venta REAL,
                futuros_reproductores_hembras INTEGER,
                futuros_reproductores_machos INTEGER,
                fecha_venta TEXT
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS ventas_descarte (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                galpon TEXT,
                poza TEXT,
                cuyes_vendidos INTEGER,
                costo_venta REAL,
                fecha_venta TEXT
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS gastos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                descripcion TEXT,
                monto REAL,
                tipo TEXT
            )
        ''')

        self.conn.commit()

    def ingresar_datos(self, galpon, poza, hembras, machos, numero_parto, nacidos, muertos_bebes, muertos_reproductores, tiempo_reproductores):
        """Ingresa datos de cuyes reproductores y nacimientos."""
        try:
            fecha_ingreso_reproductores = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            fecha_descarte = (datetime.now() + timedelta(days=tiempo_reproductores * 30)).strftime('%Y-%m-%d %H:%M:%S')
            fecha_nacimiento = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            self.cursor.execute('''
                INSERT INTO galpones_pozas (
                    galpon, poza, hembras, machos, numero_parto, nacidos, muertos_bebes, muertos_reproductores,
                    tiempo_reproductores, fecha_ingreso_reproductores, fecha_descarte, fecha_nacimiento,
                    destetados_hembras, destetados_machos, muertos_destetados_hembras, muertos_destetados_machos
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0, 0)
            ''', (galpon, poza, hembras, machos, numero_parto, nacidos, muertos_bebes, muertos_reproductores,
                  tiempo_reproductores, fecha_ingreso_reproductores, fecha_descarte, fecha_nacimiento))

            self.conn.commit()
            return True, "Datos ingresados correctamente."
        except Exception as e:
            return False, f"Error al ingresar datos: {e}"

    def registrar_destete(self, galpon, poza, destetados_hembras, destetados_machos):
        """Registra el destete de cuyes."""
        try:
            self.cursor.execute('''
                SELECT nacidos, muertos_bebes FROM galpones_pozas
                WHERE galpon = ? AND poza = ?
            ''', (galpon, poza))
            resultado = self.cursor.fetchone()

            if resultado:
                nacidos, muertos_bebes = resultado
                nacidos_vivos = nacidos - muertos_bebes
                total_destetados = destetados_hembras + destetados_machos

                if total_destetados > nacidos_vivos:
                    return False, "No hay suficientes cuyes nacidos vivos para destetar."

                self.cursor.execute('''
                    UPDATE galpones_pozas
                    SET destetados_hembras = destetados_hembras + ?,
                        destetados_machos = destetados_machos + ?,
                        nacidos = 0
                    WHERE galpon = ? AND poza = ?
                ''', (destetados_hembras, destetados_machos, galpon, poza))

                self.conn.commit()
                return True, "Destete registrado correctamente."
            else:
                return False, "Galpón o poza no encontrados."
        except Exception as e:
            return False, f"Error al registrar destete: {e}"

    def registrar_muertes_destetados(self, galpon, poza, muertos_hembras, muertos_machos):
        """Registra muertes de cuyes destetados."""
        try:
            self.cursor.execute('''
                SELECT destetados_hembras, destetados_machos FROM galpones_pozas
                WHERE galpon = ? AND poza = ?
            ''', (galpon, poza))
            resultado = self.cursor.fetchone()

            if resultado:
                destetados_hembras, destetados_machos = resultado
                if muertos_hembras > destetados_hembras or muertos_machos > destetados_machos:
                    return False, "No hay suficientes cuyes destetados para registrar las muertes."

                self.cursor.execute('''
                    UPDATE galpones_pozas
                    SET muertos_destetados_hembras = muertos_destetados_hembras + ?,
                        muertos_destetados_machos = muertos_destetados_machos + ?
                    WHERE galpon = ? AND poza = ?
                ''', (muertos_hembras, muertos_machos, galpon, poza))

                self.conn.commit()
                return True, "Muertes de cuyes destetados registradas correctamente."
            else:
                return False, "Galpón o poza no encontrados."
        except Exception as e:
            return False, f"Error al registrar muertes: {e}"

    def registrar_ventas_destetados(self, hembras_vendidas, machos_vendidos, costo_venta, futuros_hembras, futuros_machos):
        """Registra ventas de cuyes destetados."""
        try:
            self.cursor.execute('''
                INSERT INTO ventas_destetados (
                    hembras_vendidas, machos_vendidos, costo_venta,
                    futuros_reproductores_hembras, futuros_reproductores_machos, fecha_venta
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (hembras_vendidas, machos_vendidos, costo_venta,
                  futuros_hembras, futuros_machos, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

            self.conn.commit()
            return True, "Venta de cuyes destetados registrada correctamente."
        except Exception as e:
            return False, f"Error al registrar venta: {e}"

    def registrar_ventas_descarte(self, galpon, poza, cuyes_vendidos, costo_venta):
        """Registra ventas de cuyes de descarte."""
        try:
            self.cursor.execute('''
                INSERT INTO ventas_descarte (
                    galpon, poza, cuyes_vendidos, costo_venta, fecha_venta
                ) VALUES (?, ?, ?, ?, ?)
            ''', (galpon, poza, cuyes_vendidos, costo_venta, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

            self.conn.commit()
            return True, "Venta de cuyes de descarte registrada correctamente."
        except Exception as e:
            return False, f"Error al registrar venta de descarte: {e}"

    def registrar_gastos(self, descripcion, monto, tipo):
        """Registra gastos."""
        try:
            self.cursor.execute('''
                INSERT INTO gastos (descripcion, monto, tipo) VALUES (?, ?, ?)
            ''', (descripcion, monto, tipo))

            self.conn.commit()
            return True, "Gasto registrado correctamente."
        except Exception as e:
            return False, f"Error al registrar gasto: {e}"

    def obtener_datos_analisis(self):
        """Obtiene datos para análisis."""
        self.cursor.execute('''
            SELECT galpon, poza, 
                   MAX(numero_parto) AS numero_parto,
                   SUM(hembras) AS hembras,
                   SUM(machos) AS machos,
                   SUM(nacidos) AS nacidos,
                   SUM(muertos_bebes) AS muertos_bebes,
                   SUM(muertos_reproductores) AS muertos_reproductores,
                   SUM(tiempo_reproductores) AS tiempo_reproductores,
                   MIN(fecha_ingreso_reproductores) AS fecha_ingreso_reproductores,
                   MIN(fecha_descarte) AS fecha_descarte,
                   MIN(fecha_nacimiento) AS fecha_nacimiento,
                   SUM(destetados_hembras) AS destetados_hembras,
                   SUM(destetados_machos) AS destetados_machos,
                   SUM(muertos_destetados_hembras) AS muertos_destetados_hembras,
                   SUM(muertos_destetados_machos) AS muertos_destetados_machos
            FROM galpones_pozas
            GROUP BY galpon, poza
        ''')
        return self.cursor.fetchall()

    def actualizar_balance(self):
        """Calcula y devuelve el balance."""
        self.cursor.execute('SELECT SUM(costo_venta) FROM ventas_destetados')
        total_ventas_destetados = self.cursor.fetchone()[0] or 0

        self.cursor.execute('SELECT SUM(costo_venta) FROM ventas_descarte')
        total_ventas_descarte = self.cursor.fetchone()[0] or 0

        self.cursor.execute('SELECT SUM(monto) FROM gastos')
        total_gastos = self.cursor.fetchone()[0] or 0

        balance = (total_ventas_destetados + total_ventas_descarte) - total_gastos
        return total_ventas_destetados, total_ventas_descarte, total_gastos, balance

    def cerrar_conexion(self):
        """Cierra la conexión a la base de datos."""
        self.conn.close()