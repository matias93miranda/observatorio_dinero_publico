# Fase 0 — Inventario de fuentes (verificado 2026-10-19)

Todas las pruebas se hicieron el 2026-10-19 desde Linux con `curl` y con los conectores de este repo.
"Probado" = descargado, parseado y cargado. "Accesible" = la página responde HTTP 200, pero sin conector.

## 1. Presupuesto Abierto: datos abiertos (conectado)

| Ítem | Hallazgo |
|---|---|
| Página | https://www.presupuestoabierto.gob.ar/sici/datos-abiertos (HTTP 200; el listado se arma por JS) |
| Catálogo legible por máquina | `https://www.presupuestoabierto.gob.ar/sici/rest-api/catalog/site` (JSON, 757 distribuciones, ejercicios 1995–2026). Lo encontré en `dist/js/busqueda-recursos-datasets.*.js`; **no está documentado como API pública** y puede cambiar |
| Archivos | `https://dgsiaf-repo.mecon.gob.ar/repository/pa/datasets/{año}/...zip` (CSV UTF-8 con BOM, coma decimal, sin separador de miles) |
| Licencia | CC BY 4.0 (indicada en la página) |
| Token | **No hace falta** para las descargas. La API PAC (https://www.presupuestoabierto.gob.ar/sici/api-pac) pide registro y no se usa |
| Actualización | Ejercicio vigente: `R/P1D` (diaria). El 2026-10-19 los archivos 2026 decían "Última actualización … 16 Octubre 2026". Ejercicio 2025 cerrado: "05 Julio 2026" |
| Unidad | **Millones de pesos corrientes**, hasta 8 decimales (= centavos). Inferido: `totales-de-presupuesto.csv` 2007 devengado = 142.421,08473426 y `serie_pib_anual.csv` (en pesos) = 142.421.084.734,26 |
| Universo | Columna `subsector_desc` = "Administración Nacional" en el 100% de las filas (2025 y 2026). Carácter: Adm. Central, Org. Descentralizados, Inst. de Seguridad Social |

### Datasets cargados

| dataset_id | Archivo | Filas (2026-10-19) | Medidas |
|---|---|---|---|
| `pa_credito_anual_2026` | 2026/credito-anual-2026.zip (2,8 MB zip / 79 MB csv) | 85.384 | presupuestado, vigente, comprometido, devengado, pagado |
| `pa_credito_anual_2025` | 2025/credito-anual-2025.zip | 113.217 | ídem |
| `pa_recursos_anual_2026` | 2026/recursos-anual-2026.zip | 459 | inicial, vigente, ingresado/percibido |
| `pa_recursos_anual_2025` | 2025/recursos-anual-2025.zip | 562 | ídem |
| `pa_totales` | totales-de-presupuesto.zip | 20 (2007–2026) | 9 totales publicados |

### Disponibles y verificados, sin conectar todavía
- `credito-mensual-{año}.zip` (2026: 337.410 filas, 312 MB csv) y `credito-diario`. **Trampa verificada:** presupuestado y vigente se imputan íntegros al mes 1 (son stock, no flujo); los meses 2–12 tienen 0 en esas columnas. Comprometido, devengado y pagado sí son flujos mensuales. La suma de los meses coincide exactamente con el archivo anual.
- `recursos-mensual-{año}.zip` (misma estructura). Mayo 2026 muestra 37,6 billones percibidos, casi 3 veces un mes típico. No investigué la causa.
- Clasificadores (`d-*.zip`), mapeo jurisdiccional, ejecución física, proyecto de ley, `serie_pib_anual.csv`, `serie_finfun_anual.csv` (en pesos, no en millones).

### Composición verificada (archivo anual 2026)
- Gasto: el clasificador económico solo tiene códigos 21x (corrientes) y 22x (capital). **No incluye aplicaciones financieras** (amortización de deuda) **ni gastos figurativos** (no aparece el inciso 9). Por eso no hay doble conteo de contribuciones figurativas dentro de la AN.
- Recursos: solo 11x (corrientes) y 12x (capital). **No incluye fuentes financieras** (endeudamiento).
- Gasto primario = gasto total − Σ económico `2131*` (intereses y primas). Verificado al centavo: 117.476.799,88051809 − 12.860.075,27082612 = 104.616.724,60969197 = `gasto_primario_devengado` publicado.

## 2. API Series de Tiempo (conectada)

| Ítem | Hallazgo |
|---|---|
| Endpoint | `https://apis.datos.gob.ar/series/api/series/?ids=…&format=csv` y `/search/` (sin token) |
| Formato | CSV con punto decimal. Los valores traen artefactos de float (`5102.599999999999`): se guarda el texto tal cual |
| Celdas vacías | Existen (p. ej. resultado primario antes de 2016). Se cargan como NULL |

| Serie | id | Cobertura | Fuente original |
|---|---|---|---|
| IPC Nivel General Nacional, base dic-2016 | `148.3_INIVELNAL_DICI_M_26` | 2016-12 → 2026-08 | INDEC |
| IMIG Resultado primario (mensual) | `452.3_RESULTADO_RIO_0_M_18_54` | 2016-01 → 2026-08 | Secretaría de Hacienda (SPNF, base caja) |
| Recaudación tributaria total (mensual) | `172.3_TL_RECAION_M_0_0_17` | 1997-01 → 2026-09 | Secretaría de Hacienda / DNIAF (la descripción en el catálogo dice "Anuales", pero la serie es mensual) |

## 3. Fuentes accesibles, no conectadas

| Fuente | Estado 2026-10-19 | Formato | Motivo para dejarla pendiente |
|---|---|---|---|
| Recaudación MECON (https://www.argentina.gob.ar/economia/ingresospublicos/dniaf/recaudacion) | HTTP 200 | XLSX mensual (`2026-recadudacion-septiembre.xlsx`, `2026_10.xlsx`) | Planilla con formato de presentación; el total mensual ya llega por Series de Tiempo |
| ARCA estudios (https://arca.gob.ar/institucional/estudios/) | HTTP 200 | XLS/XLSX/ZIP/PDF (`serie2026.xls`, `Estadisticas-Tributarias-2025.zip`, informes PDF) | Detalle por impuesto: V2 |
| OPC (https://opc.gob.ar/ejecucion-presupuestaria-2/) | HTTP 200 | Informes HTML/PDF mensuales (hasta septiembre 2026) | Análisis en prosa, sin datos tabulares. Útil como referencia manual para conciliar |
| Presupuesto Abierto API PAC | HTTP 200 (página) | REST con token | No hace falta mientras las descargas abiertas alcancen |

## 4. Conciliación (resultado real, 2026-10-19)

- **2026:** las 9 medidas de `totales-de-presupuesto.csv` coinciden **exactamente** (diferencia 0 centavos) con la suma de líneas de `credito-anual-2026` y `recursos-anual-2026`.
- **2025: DISCREPA.** Los archivos detallados suman más que la fila 2025 de totales:
  - devengado: +656.183,78 M$ (detalle 123.533.955,01 vs totales 122.877.771,23)
  - vigente: +44.845,29 M$
  - recurso percibido: +1.275.439,72 M$ (detalle 134.812.992,32 vs totales 133.537.552,60)
  - presupuestado e inicial: coinciden.
  - **El detalle coincide al centavo con `serie_pib_anual.csv`** (gasto 123.533.955.013.701,51 $ e ingreso 134.812.992.323.521,43 $). Las dos publicaciones oficiales difieren entre sí. Hipótesis sin verificar: la fila 2025 de totales es un corte anterior al cierre. La app muestra la discrepancia y no la corrige.
