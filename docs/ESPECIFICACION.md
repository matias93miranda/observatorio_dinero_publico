# Observatorio del Dinero Público Argentino

Fecha: 2026-10-19
Estado: especificación inicial; no implica que se haya implementado ni conectado ninguna fuente.

## Objetivo
Construir una aplicación local accesible desde navegador que permita estudiar ingresos, gastos, balances y transferencias del sector público argentino con datos públicos, preservando procedencia y criterios contables.

## Principios innegociables
1. Nunca presentar flujos inferidos como pagos o transferencias verificados.
2. No mezclar niveles de gobierno ni universos institucionales sin identificar y consolidar.
3. Separar presupuestado, crédito vigente, compromiso, devengado, pagado, percibido y recaudado; verificar disponibilidad según fuente.
4. Separar resultado primario, financiero y operaciones de financiamiento; evitar doble conteo por transferencias entre entes.
5. Cada cifra debe mostrar fuente, enlace, período, unidad, fecha de consulta, cobertura, estado de validación y revisión de dato si corresponde.
6. Nunca convertir un 404 o un dataset faltante en valor cero. Sin datos significa sin datos.
7. Distinguir series nominales, reales y variaciones; documentar deflactor y año base.
8. Cualquier cálculo debe poder reconstruirse desde datos originales conservados sin modificaciones.

## Alcance por etapas
- MVP: Administración Pública Nacional; ejecución de gastos por finalidad, jurisdicción y programa; ingresos según disponibilidad y definición comparable; resultado fiscal según misma cobertura; series temporales; panel de procedencia.
- V2: Transferencias a provincias y destinatarios con identificadores confiables; conciliación entre fuentes; expansión a Sector Público Nacional no Financiero cuando haya cobertura y reglas claras.
- V3: Provincias, CABA y municipios por jurisdicción, con indicadores de completitud, conciliación y consolidación.
- V4: contrataciones, alertas, explicaciones interpretables y conectores adicionales.

## Fuentes candidatas verificadas al 2026-10-19
- Presupuesto Abierto, datos abiertos: https://www.presupuestoabierto.gob.ar/sici/datos-abiertos
- Presupuesto Abierto, API pública con registro para token: https://www.presupuestoabierto.gob.ar/sici/api-pac
- API Series de Tiempo: https://www.argentina.gob.ar/datos-abiertos/api-series-de-tiempo
- ARCA: https://arca.gob.ar/institucional/estudios/
- Recaudación Ministerio de Economía: https://www.argentina.gob.ar/economia/ingresospublicos/dniaf/recaudacion
- Oficina de Presupuesto del Congreso: https://opc.gob.ar/ejecucion-presupuestaria-2/
NOTA: probar accesibilidad, términos, esquemas, granularidad y última actualización durante la implementación. No asumir endpoints ni credenciales inexistentes.

## Arquitectura recomendada
- Frontend: React + TypeScript + Vite; Apache ECharts para Sankey, treemap, barras y series temporales.
- Backend: Python + FastAPI + Pydantic, Pandas para ETL y DuckDB opcional para transformaciones analíticas; SQLite como almacenamiento local inicial.
- Ingesta: conectores individuales por fuente con descarga, registro de checksum SHA-256, metadatos y conservación del archivo crudo.
- Validación: pytest y pruebas de reconciliación, totales, unidades, duplicados, cambios de esquema, cobertura, fechas y revisiones.
- Tareas de actualización: scheduler local con frecuencia configurable; reintentos y registro de errores. Nunca afirmar tiempo real si la fuente publica con retraso.
- Ejecución: Docker Compose opcional y scripts para Windows y Linux.

## Modelo de datos mínimo
- `source`: identificador, organismo, URL base, licencia, frecuencia publicada, notas.
- `dataset`: identificador, fuente, nombre, universo institucional, cobertura temporal, granularidad, metodología.
- `ingestion_run`: fuente, inicio/fin, estado, hash, URL exacta, fecha de publicación si existe, errores.
- `raw_artifact`: ruta local, tamaño, checksum, formato, fecha de descarga.
- `dimension_entity`: id, nombre, nivel de gobierno, tipo institucional, vigencia temporal, identificadores externos.
- `dimension_category`: id, clasificador oficial, código, etiqueta, padre, vigencia.
- `fiscal_observation`: id, dataset, período, entidad, categoría, tipo de medida, etapa contable, moneda, escala, importe decimal, versión, fuente original.
- `transfer`: originador, receptor, período, importe, etapa, evidencia, relación comprobada; NULL para campos ausentes.
- `reconciliation`: comparación, total calculado, total publicado, diferencia, tolerancia, conclusión.

## Fórmulas y advertencias
- Resultado financiero = ingresos totales - gastos totales, solo cuando ambos pertenezcan al mismo universo y base contable.
- Resultado primario = ingresos totales - gastos primarios, siguiendo metodología oficial documentada.
- Participación de categoría = importe categoría / total comparable.
- Variación nominal porcentual = 100 * (valor_t / valor_(t-1) - 1), si denominador válido.
- Variación real = (1 + variación nominal) / (1 + inflación comparable) - 1.
- Moneda y escala explícitas en todo cálculo; importes almacenados como decimal y no float binario.
- No confundir gasto devengado con caja pagada, recaudación bruta con ingreso presupuestario, ni presupuesto aprobado con ejecutado.

## Interfaz
1. Inicio: tarjetas de ingresos y gastos comparables, resultado fiscal y cobertura/última actualización.
2. Flujo: Sankey solo para transferencias verificadas o taxonomías jerárquicas rotuladas como descomposición y no como pagos rastreados.
3. Destinos: treemap y barras por función, jurisdicción y programa.
4. Evolución: líneas mensuales/anuales, nominal/real, filtros y comparaciones.
5. Fuentes: tabla con origen, accesibilidad, períodos disponibles, fecha de publicación, integridad y vínculos a originales.
6. Explorador: descargar datos normalizados y consultar observaciones originales.

## API local propuesta (no endpoints oficiales)
- GET /api/health
- GET /api/sources
- GET /api/datasets
- GET /api/coverage
- GET /api/summary?period=YYYY-MM&scope=...
- GET /api/expenditures?period=...&classification=...
- GET /api/revenues?period=...
- GET /api/transfers?period=...
- GET /api/timeseries?metric=...&from=...&to=...
- GET /api/observations/{id}/provenance
- POST /api/admin/sync (acceso local protegido, sin token incrustado en frontend)

## Entregables de fase 0
- Inventario de datasets reales, URLs comprobadas, formato, rango temporal, actualización y cobertura.
- Matriz de compatibilidad contable y advertencias de doble conteo.
- Modelo SQL versionado y ejemplos de registros basados en datos reales.
- Proyecto base reproducible, pruebas automatizadas y README de instalación.
- Un dashboard mínimo, claramente etiquetado como datos reales o de demostración.

## Entregables de fase 1 / MVP
- Al menos una fuente oficial de gasto y una de ingresos efectivamente ingeridas.
- Descarga reproducible de originales, validación de agregados y trazabilidad por indicador.
- Panel de resumen, gráfico de composición, evolución y explorador.
- Documentación de definiciones y pruebas; errores legibles en interfaz.

## Criterios de aceptación
- La aplicación funciona sin internet usando la última copia local e indica antigüedad del dato.
- Un usuario puede llegar desde cualquier cifra hasta el recurso primario y su metodología.
- Los totales coinciden con los publicados dentro de una tolerancia justificada; discrepancias visibles.
- No hay doble conteo en una consolidación y cada agregado explicita universo, base y período.
- Se distinguen valores faltantes de ceros, revisiones y estimaciones.
- Los tests cubren categorías, sumas, fechas, moneda, mapeos de organismos y archivos faltantes.

## Prompt para Claude Code
Actuá como arquitecto de datos fiscales, ingeniero full stack y revisor de contabilidad pública argentina. Implementá incrementalmente el Observatorio del Dinero Público Argentino según esta especificación. Primero inspeccioná el repositorio existente, identificá stack y restricciones y evitá reemplazar código o archivos de otros proyectos. Si el directorio no contiene una app, iniciá un repositorio nuevo. Entregá primero fase 0: verificá y documentá datasets oficiales, granularidad, cobertura temporal, esquemas, restricciones de API y método contable; elaborá matriz de comparabilidad; creá esquema de datos, conectores de ingesta, pruebas de trazabilidad y una interfaz inicial. Después implementá un MVP con datos reales, sin fingir conexiones ni cifras. Solicitá el token de Presupuesto Abierto solo si realmente es necesario; si no existe, usá descargas oficiales mientras preservás trazabilidad. No inventes endpoints ni archivos. Conservá crudos, usa importes decimales exactos, diferencia devengado/pagado, ingresos presupuestarios/recaudación, y resultados primario/financiero. No mezcles Nación/provincias/municipios. Cada cifra tiene fuente, período, unidad, universo, etapa contable y última actualización. Un Sankey de clasificación no debe rotularse como transferencia efectiva; los flujos comprobados requieren evidencia entre pagador y receptor. Configurá actualización bajo demanda y pruebas de conciliación; si una fuente no responde, guardá el último dato, mostrale la fecha al usuario y no reemplaces fallos por ceros. Documentá cómo ejecutar en Windows y Linux. Hacé cambios pequeños y testeados, con commits claros si el repositorio está bajo Git. Al finalizar, describí qué se implementó, cuáles fuentes se probaron y qué puntos quedaron pendientes con evidencia verificable.
