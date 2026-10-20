-- Esquema local del Observatorio del Dinero Público Argentino.
-- Versión 2 (v1 + tablas al final). Cualquier cambio incompatible incrementa schema_version y agrega una migración.
--
-- Convenciones:
--  * Importes monetarios: INTEGER en centavos (exacto). Nunca REAL.
--  * Ausencia de dato = fila ausente o NULL. Nunca 0 como sustituto.
--  * Cada observación apunta al ingestion_run y al raw_artifact del que salió.

CREATE TABLE IF NOT EXISTS schema_version (
    version     INTEGER NOT NULL,
    applied_at  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS source (
    source_id           TEXT PRIMARY KEY,          -- p.ej. 'presupuesto_abierto'
    organismo           TEXT NOT NULL,
    base_url            TEXT NOT NULL,
    licencia            TEXT,
    frecuencia_publicada TEXT,
    notas               TEXT
);

CREATE TABLE IF NOT EXISTS dataset (
    dataset_id          TEXT PRIMARY KEY,          -- p.ej. 'pa_credito_anual_2026'
    source_id           TEXT NOT NULL REFERENCES source(source_id),
    nombre              TEXT NOT NULL,
    url                 TEXT NOT NULL,
    universo            TEXT NOT NULL,             -- p.ej. 'Administración Nacional'
    nivel_gobierno      TEXT NOT NULL,             -- 'nacional' | 'provincial' | 'municipal'
    cobertura_temporal  TEXT,
    granularidad        TEXT,
    unidad              TEXT NOT NULL,             -- unidad del archivo original
    metodologia         TEXT
);

CREATE TABLE IF NOT EXISTS ingestion_run (
    run_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    dataset_id          TEXT NOT NULL REFERENCES dataset(dataset_id),
    started_at          TEXT NOT NULL,
    finished_at         TEXT,
    status              TEXT NOT NULL CHECK (status IN ('running','ok','failed','unchanged')),
    url                 TEXT NOT NULL,
    sha256              TEXT,
    fecha_publicacion   TEXT,                      -- según la fuente, texto literal
    rows_loaded         INTEGER,
    error               TEXT
);

CREATE TABLE IF NOT EXISTS raw_artifact (
    artifact_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id              INTEGER NOT NULL REFERENCES ingestion_run(run_id),
    path                TEXT NOT NULL,             -- relativo a data/raw
    size_bytes          INTEGER NOT NULL,
    sha256              TEXT NOT NULL,
    formato             TEXT NOT NULL,
    downloaded_at       TEXT NOT NULL
);

-- Organismos (jerarquía institucional del clasificador presupuestario).
CREATE TABLE IF NOT EXISTS dimension_entity (
    entity_id           TEXT PRIMARY KEY,          -- 'AN/servicio/312'
    nombre              TEXT NOT NULL,
    nivel_gobierno      TEXT NOT NULL,
    tipo_institucional  TEXT NOT NULL,             -- carácter: Adm. Central, Org. Descentralizados, ...
    jurisdiccion_id     TEXT,
    jurisdiccion_desc   TEXT,
    ejercicio           INTEGER NOT NULL           -- vigencia: el clasificador cambia por ejercicio
);

-- Clasificadores oficiales (finalidad-función, objeto, económico, programa, rubro de recurso, ...).
CREATE TABLE IF NOT EXISTS dimension_category (
    clasificador        TEXT NOT NULL,             -- 'finalidad_funcion', 'inciso', 'economico', 'programa', 'recurso_tipo', ...
    code                TEXT NOT NULL,
    label               TEXT NOT NULL,
    parent_code         TEXT,
    ejercicio           INTEGER NOT NULL,
    PRIMARY KEY (clasificador, code, ejercicio)
);

-- Observación fiscal: una línea del archivo original x una medida (etapa contable).
CREATE TABLE IF NOT EXISTS fiscal_observation (
    obs_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    dataset_id          TEXT NOT NULL REFERENCES dataset(dataset_id),
    run_id              INTEGER NOT NULL REFERENCES ingestion_run(run_id),
    source_line         INTEGER NOT NULL,          -- número de línea en el CSV original (1 = encabezado)
    ejercicio           INTEGER NOT NULL,
    periodo             TEXT NOT NULL,             -- 'YYYY' (anual) o 'YYYY-MM' (mensual)
    flujo               TEXT NOT NULL CHECK (flujo IN ('gasto','recurso')),
    etapa               TEXT NOT NULL CHECK (etapa IN (
                            'presupuestado','vigente','comprometido','devengado','pagado',
                            'recurso_inicial','recurso_vigente','percibido')),
    entity_id           TEXT NOT NULL REFERENCES dimension_entity(entity_id),
    finalidad_funcion   TEXT,                      -- 'f.fn'
    programa            TEXT,                      -- 'jur.servicio.programa'
    inciso              TEXT,
    economico           TEXT,                      -- clasificador económico 8 dígitos
    fuente_financiamiento TEXT,
    ubicacion_geografica TEXT,
    recurso_tipo        TEXT,
    recurso_clase       TEXT,
    moneda              TEXT NOT NULL DEFAULT 'ARS',
    importe_centavos    INTEGER NOT NULL,          -- exacto; original en millones de pesos con 8 decimales
    importe_original    TEXT NOT NULL              -- texto literal del archivo, sin tocar
);
CREATE INDEX IF NOT EXISTS ix_obs_ds_etapa ON fiscal_observation(dataset_id, etapa);
CREATE INDEX IF NOT EXISTS ix_obs_periodo ON fiscal_observation(ejercicio, periodo, flujo, etapa);

-- Totales publicados por la fuente (para conciliar contra la suma de líneas).
CREATE TABLE IF NOT EXISTS published_total (
    dataset_id          TEXT NOT NULL REFERENCES dataset(dataset_id),
    run_id              INTEGER NOT NULL REFERENCES ingestion_run(run_id),
    ejercicio           INTEGER NOT NULL,
    medida              TEXT NOT NULL,             -- nombre de columna original
    importe_centavos    INTEGER,                   -- NULL si la celda viene vacía
    importe_original    TEXT,
    ultima_actualizacion TEXT,
    PRIMARY KEY (dataset_id, ejercicio, medida)
);

-- Series de tiempo (IPC, IMIG, recaudación): valores no necesariamente monetarios.
CREATE TABLE IF NOT EXISTS series_observation (
    series_id           TEXT NOT NULL,
    dataset_id          TEXT NOT NULL REFERENCES dataset(dataset_id),
    run_id              INTEGER NOT NULL REFERENCES ingestion_run(run_id),
    periodo             TEXT NOT NULL,             -- 'YYYY-MM'
    valor_original      TEXT,                      -- NULL = la fuente no publica valor
    unidad              TEXT NOT NULL,
    PRIMARY KEY (series_id, periodo)
);

-- Transferencias verificadas (V2). Vacía hasta tener evidencia pagador->receptor.
CREATE TABLE IF NOT EXISTS transfer (
    transfer_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    originador_entity_id TEXT,
    receptor            TEXT,
    periodo             TEXT,
    importe_centavos    INTEGER,
    etapa               TEXT,
    evidencia           TEXT,                      -- URL/documento que prueba el flujo
    relacion_comprobada INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS reconciliation (
    rec_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id              INTEGER REFERENCES ingestion_run(run_id),
    comparacion         TEXT NOT NULL,
    total_calculado_centavos INTEGER,
    total_publicado_centavos INTEGER,
    diferencia_centavos INTEGER,
    tolerancia_centavos INTEGER NOT NULL,
    conclusion          TEXT NOT NULL CHECK (conclusion IN ('coincide','discrepa','sin_dato')),
    checked_at          TEXT NOT NULL
);

-- ===== Versión 2 =====

-- Celdas de cuadros contables publicados en planilla (p.ej. Cuenta de Inversión, Cuadro 35).
-- Una fila = una celda del archivo oficial. No se corrige nada: un error de fórmula del archivo
-- (#REF!) queda con estado 'error_formula' e importe NULL; una celda vacía, 'vacia' y NULL.
CREATE TABLE IF NOT EXISTS aif_observation (
    dataset_id          TEXT NOT NULL REFERENCES dataset(dataset_id),
    run_id              INTEGER NOT NULL REFERENCES ingestion_run(run_id),
    ejercicio           INTEGER NOT NULL,
    cuadro              TEXT NOT NULL,
    celda               TEXT NOT NULL,             -- coordenada en la planilla, p.ej. 'K52'
    concepto_id         TEXT NOT NULL,             -- clave estable, p.ej. 'I.rentas_propiedad'
    concepto            TEXT NOT NULL,             -- rótulo literal del archivo
    subsector           TEXT NOT NULL,             -- columna institucional, p.ej. 'total_an'
    universo            TEXT NOT NULL,
    base_contable       TEXT NOT NULL,
    importe_centavos    INTEGER,
    importe_original    TEXT,                      -- repr del valor almacenado en el archivo
    estado              TEXT NOT NULL CHECK (estado IN ('ok','vacia','error_formula')),
    PRIMARY KEY (dataset_id, celda)
);

-- Cifras extraídas de publicaciones en PDF (p.ej. Boletín Fiscal de la ONP). El conector las
-- lee del texto del PDF crudo por rótulo de fila; si el rótulo no aparece, la carga falla.
CREATE TABLE IF NOT EXISTS published_figure (
    dataset_id          TEXT NOT NULL REFERENCES dataset(dataset_id),
    run_id              INTEGER NOT NULL REFERENCES ingestion_run(run_id),
    figure_id           TEXT NOT NULL,
    ejercicio           INTEGER NOT NULL,
    periodo             TEXT NOT NULL,
    universo            TEXT NOT NULL,
    base_contable       TEXT NOT NULL,
    concepto            TEXT NOT NULL,
    valor_texto         TEXT NOT NULL,             -- tal como está impreso, p.ej. '11.976.386,7'
    importe_centavos    INTEGER NOT NULL,
    unidad              TEXT NOT NULL,
    pagina              INTEGER NOT NULL,          -- página del PDF (1 = primera)
    cuadro              TEXT,
    linea_texto         TEXT NOT NULL,             -- línea completa de la que se extrajo
    PRIMARY KEY (dataset_id, figure_id)
);

-- Criterios contables y cambios metodológicos, con cita textual y ubicación en la fuente.
CREATE TABLE IF NOT EXISTS metodologia_nota (
    nota_id             TEXT PRIMARY KEY,
    tema                TEXT NOT NULL,
    aplica_a            TEXT NOT NULL,             -- fuentes/indicadores afectados
    vigencia_desde      TEXT,
    vigencia_hasta      TEXT,
    resumen             TEXT NOT NULL,
    cita_textual        TEXT,
    fuente_dataset_id   TEXT,                      -- crudo donde se verifica la cita
    fuente_url          TEXT NOT NULL,
    ubicacion           TEXT,                      -- página / cuadro / sección
    estado_verificacion TEXT NOT NULL CHECK (estado_verificacion IN
                            ('verificada_en_crudo','no_encontrada_en_crudo','crudo_no_disponible',
                             'hallazgo_reproducible')),  -- hallazgo: sin cita, con procedimiento
    verificado_en       TEXT
);
