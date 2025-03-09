-- Tabla para almacenar los reproductores
CREATE TABLE IF NOT EXISTS reproductores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    galpon TEXT NOT NULL,
    poza TEXT NOT NULL,
    hembras INTEGER NOT NULL,
    machos INTEGER NOT NULL,
    tiempo_reproductores INTEGER NOT NULL,
    fecha_ingreso TEXT NOT NULL
);

-- Tabla para almacenar los partos
CREATE TABLE IF NOT EXISTS partos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    galpon TEXT NOT NULL,
    poza TEXT NOT NULL,
    numero_parto INTEGER NOT NULL,
    nacidos INTEGER NOT NULL,
    muertos_bebes INTEGER NOT NULL,
    muertos_reproductores INTEGER NOT NULL,
    fecha_nacimiento TEXT NOT NULL
);