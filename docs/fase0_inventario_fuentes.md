# Fase 0 — Inventario de fuentes (verificado 2026-10-19; ampliado tras la revisión externa)

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

## 1b. IMIG completo — balance fiscal oficial (conectado)

| Ítem | Hallazgo |
|---|---|
| Archivo | https://infra.datos.gob.ar/catalog/sspm/dataset/452/distribution/452.3/download/imig-mensual.csv (sin token) |
| Universo / base | Sector Público Nacional no Financiero, **caja**. Es el resultado fiscal oficial de la Secretaría de Hacienda |
| Cobertura | 2016-01 → 2026-08 (128 meses), 53 columnas: 16 de ingresos, 31 de gasto primario, 3 de resultado, 2 PIP (meta FMI 2016-19, no usadas) |
| Precisión | Mayormente 0,1 M$, algunos meses con más decimales y artefactos de float: se guarda el texto y para sumar se redondea a 1e-6 M$ (1 peso) |
| Identidades | Σ ingresos − Σ gasto primario = resultado primario, y resultado primario − intereses netos = resultado financiero: **desvío 0 M$ en los 128 meses** (verificado en cada carga; si no cierra, la carga falla) |
| 2025 | Ingresos 135.179.029,8 · gasto primario 123.409.811,1 · resultado primario 11.769.218,7 · intereses netos 10.315.399,6 · resultado financiero 1.453.819,1 (M$) |

Universo exacto (Boletín Fiscal, cuadros 4 y 5): AN + INSSJyP + fondos fiduciarios + otros entes; las **empresas públicas entran solo
por su resultado operativo** (superávit 1.633.598,7 / déficit 2.864.757,5 M$ en 2025) y las universidades como destino de transferencias.
Desde 2017 excluye rentas del BCRA y del FGS e intereses intra-sector público (cita verificada, nota `caja_spn_2017_rentas_intra_sp`).
El puente con Presupuesto Abierto está en la sección 6.

## 1c. Cuenta de Inversión 2025 — Contaduría General de la Nación (conectada)

| Ítem | Hallazgo |
|---|---|
| Página | https://www.argentina.gob.ar/economia/sechacienda/cgn/cuenta/2025 → Tomo I → "Gestión Financiera Consolidada del Sector Público Nacional" |
| Cuadro 35 | `https://www.argentina.gob.ar/sites/default/files/cuadro35-tomoi-2025.xlsx` (28 KB). Cuenta AIF del **SPNF** por nivel institucional: Adm. Central, Org. Descentralizados, Inst. Seguridad Social, Total AN, Universidades, Empresas, Fondos Fiduciarios, Entes Públicos, **Eliminación**, Total SPNF. En **pesos** |
| Metodología | `gestion-financiera-consolidada_aspectos_generales_y_metodologicos-tomoi-2025.pdf` (conectado como documento: las citas se verifican contra su texto) |
| Base | Devengado (gastos), recaudado/percibido (recursos); transferencias intra-SPNF devengadas de ambos lados para eliminarlas. No consolida compraventa ni tributos entre subsectores. Sin datos de 2 fondos fiduciarios |
| Precisión | El xlsx guarda dobles (~16 cifras): con 10^14 $ el último centavo no es exacto en el propio archivo. Se guarda el repr y la tolerancia de identidades es 10 centavos (máximo observado: 3) |
| Integridad | 182 identidades (filas = Σ subsectores − eliminaciones; I−II=III; VI=I+IV; VII=II+V; VIII=VI−VII; XI=VIII+IX−X; XIV=XII−XIII; XIV=−XI; figurativas eliminadas). **179 coinciden; 3 discrepan por 0,81 $** (XIV ≠ −XI en Adm. Central, Total AN y Total SPNF): es del original y se informa. Celdas **K52 y K53 = `#REF!`** en el original (total SPNF de transferencias de capital a provincias/otras): se guardan como error, sin valor |
| Cruce con PA | Columna Total AN = suma de `credito-anual-2025` y `recursos-anual-2025` (ingresos +0,03 $, gastos −0,01 $, intereses 0): **el detalle de Presupuesto Abierto es el cierre oficial** |
| SPNF 2025 | Ingresos 159.423.101,4 · gastos 146.926.684,8 · intereses 10.188.412,5 · resultado primario 22.684.829,2 · resultado financiero 12.496.416,7 M$ (devengado; **no** es el resultado oficial base caja) |
| Otros cuadros verificados, sin conectar | Cuadro 1 (AIF de la AN, `cuadro1-tomoi-2025.xlsx`), Cuadros 22 y 23 (gastos y contribuciones figurativas por entidad, `cuadro22/23-tomoi-2025.xlsx`), Tomo I y II completos en PDF, Separata I (ejecución presupuestaria) y **Separata II (deuda pública)**: `separataii-deuda-publica-cuenta_2025.pdf` (4,0 MB, 2026-07-01) |

## 1d. Boletín Fiscal — Oficina Nacional de Presupuesto (conectado)

| Ítem | Hallazgo |
|---|---|
| Archivo | `https://www.mecon.gob.ar/onp/documentos/boletin/4totrim25/4totrim25.pdf` (125 p., creado 2026-04-01). Patrón `{n}{to/er/do}trim{aa}` verificado para 2017–2025, pero el conector solo usa boletines listados a mano |
| TLS | `www.mecon.gob.ar` no envía el certificado intermedio. Se agrega el intermedio Sectigo DV R36 que el propio servidor declara en AIA (`backend/observatorio/certs/`); **no** se desactiva la verificación |
| Extracción | 23 cifras por rótulo exacto de fila en las páginas 57 (cuadro 1), 61 (cuadro 4) y 62 (cuadro 5); cada página se valida por su encabezado. Si algo cambia, la carga falla |
| Contenido clave | AN base recaudado/devengado **provisoria** (resultado primario 20.299.426,4 vs 21.433.030,3 del cierre); SPN base caja abierto en AN y "INSSJyP, FF y otros"; **rentas del BCRA 11.976.386,7**, rentas del FGS y otros 986.977,3, intereses intra-SP 979.916,8 (AN) + 7.060,5 (resto) |

## 1e. Ejecución provincial, coparticipación, transferencias y deuda (verificadas, sin conectar)

Todas descargadas y abiertas el 2026-10-19 (HTTP 200 con User-Agent ASCII). Son planillas de presentación: cada conector necesitará
validar encabezados como el del Cuadro 35.

| Fuente | URL verificada | Formato y contenido | Observaciones para el conector |
|---|---|---|---|
| Ejecución presupuestaria provincial, serie anual (DNAP / Coordinación Fiscal Provincial) | `https://www.argentina.gob.ar/sites/default/files/serie_aif-apnf-2025.xlsx` (desde https://www.argentina.gob.ar/economia/sechacienda/coordinacion-fiscal-provincial/ejecucion-presupuestaria-provincial/ejecuciones) | xlsx, una hoja por jurisdicción + "Consolidado"; cuenta AIF de la **Administración Pública No Financiera** provincial, 2005–2025, millones de pesos, "ejecución presupuestaria **provisoria**" | Universo provincial: **no** se suma a la Nación. 2025 consolidado: ingresos totales 131.129.866,1, resultado financiero −2.780.356,7 M$. Los ingresos tributarios "de origen nacional" (59.388.352,7) son coparticipación y otras leyes. *Inferido, sin verificar en norma:* no figuran como gasto de la AN porque la distribución automática ocurre antes de los recursos de la AN (2025: recaudación bruta 183,1 billones vs ingresos impositivos AN 73,0). Las transferencias **no automáticas** sí son gasto de la AN: al consolidar se duplicarían |
| Ejecución provincial trimestral | `ejecuciones_presupuestarias_apnf_{año}_-_trim_{n}.xls` (2016 → 2026 T-II) | xls (BIFF), una hoja, columnas = 24 jurisdicciones | Los nombres de archivo no siguen un patrón fijo (`_trim_ii_0`, `_trim._i`): listar desde la página |
| Coparticipación y otras leyes, mensual por provincia y régimen | `informacion_consolidada2025_5.xlsx`, `informacion_consolidada_2026_6.xlsx` (desde https://www.argentina.gob.ar/economia/sechacienda/asuntosprovinciales/ron) | xlsx, una hoja por mes + "CONS"; columnas por ley (24.049, 26.075, 23.966, 24.699…) | Los totales son **fórmulas** (`=SUM(...)`): leer valores cacheados y recalcular para validar |
| Coparticipación diaria | `internet_diario_{mes}{aa}_{n}.xls` mensuales y `montos_diarios_ano_{año}.zip` (2010–2024) | xls, una hoja por provincia, "Distribución de recursos nacionales", millones | Transferencia automática con evidencia pagador→receptor por régimen: candidata a `transfer` con `relacion_comprobada=1` (V2) |
| Deuda pública provincial (stock y servicios) | `stock_ii_trim_2026.xlsx`, `ev._de_servicios_-_consolidado_2026_-_trim._ii.xlsx` (desde .../coordinacion-fiscal-provincial/deuda-publica-provincial/ultima-informacion) | xlsx; stock por jurisdicción y acreedor (Gobierno Nacional, FFFIR, FFDP, bancos, títulos…), millones | La columna principal es "Total **sin deuda flotante**": no mezclar con deuda flotante ni con deuda nacional |
| Deuda de la Administración Central (Secretaría de Finanzas) | `deuda_publica_31-12-2025.xlsx` … `deuda_publica_30-06-2026_0.xlsx` (desde https://www.argentina.gob.ar/economia/finanzas/datos-trimestrales-de-la-deuda) | xlsx con índice y hojas A.1.x (por instrumento, plazo, moneda, legislación, tasa, vida promedio); base SIGADE en zip | Universo: **Administración Central** (no SPNF). Stock, no flujo: nunca se suma a resultados |
| Transferencias de la AN a provincias (no automáticas) | Presupuesto Abierto (ya conectado): económico 21723100/21723400 (corrientes) y 22223100/22223400 (capital), con ubicación geográfica | CSV | Es clasificación del gasto de la AN, **no** evidencia de recepción por la provincia. Sin cruce con la ejecución provincial no se registra como transferencia comprobada |

## 2. API Series de Tiempo (conectada)

| Ítem | Hallazgo |
|---|---|
| Endpoint | `https://apis.datos.gob.ar/series/api/series/?ids=…&format=csv` y `/search/` (sin token) |
| Formato | CSV con punto decimal. Los valores traen artefactos de float (`5102.599999999999`): se guarda el texto tal cual |
| Celdas vacías | Existen (p. ej. resultado primario antes de 2016). Se cargan como NULL |

| Serie | id | Cobertura | Fuente original |
|---|---|---|---|
| IPC Nivel General Nacional, base dic-2016 | `148.3_INIVELNAL_DICI_M_26` | 2016-12 → 2026-08 | INDEC |
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
- **2025: la fila de totales discrepa; el detalle es el cierre.** Los archivos detallados suman más que la fila 2025 de totales
  (devengado +656.183,78 M$, vigente +44.845,29 M$, percibido +1.275.439,72 M$), pero **coinciden con la Cuenta de Inversión 2025**
  (Cuadro 35, columna AN: ingresos 134.812.992,32 y gastos 123.533.955,01 M$) y con `serie_pib_anual.csv`. La fila de totales es un corte
  anterior al cierre. Se sigue mostrando la discrepancia (no se corrige) y la app usa el detalle.
- Hay un **tercer corte**: el Boletín Fiscal 4T-2025 (datos provisorios) da para la AN recursos 133.676.184,7, gastos 124.613.487,9 y
  resultado primario 20.299.426,4 M$.

## 5. Criterios contables y cambios metodológicos

Tabla `metodologia_nota` (endpoint `/api/metodologia`), cada nota con cita textual verificada contra el PDF crudo o marcada como
hallazgo con procedimiento. Las principales:

| Nota | Desde | Qué cambia |
|---|---|---|
| `caja_spn_2017_rentas_intra_sp` | 2017 | El resultado base caja (IMIG) excluye rentas del FGS por deuda intra-SPN y rentas del BCRA; intereses netos de los intra-SPN. La serie IMIG anterior a 2017 no es comparable sin ajuste |
| `an_metodologia_habitual` | — | AN, empresas, entes y fondos mantienen la exposición habitual (con todas las rentas) |
| `bcra_utilidades_2025` | 2025 | 11.976.386,7 M$ de utilidades del BCRA (ejercicio 2024) cobradas por la AN; 0,0 en 2024 |
| `deuda_exigible_no_es_flotante` | — | Devengado − pagado del ejercicio ≠ saldo de deuda flotante |
| `boletin_momentos_registro`, `cgn_momento_registro` | — | Momentos de registro por subsector y fuente |
| `cgn_no_consolida_compraventa`, `cgn_cobertura_incompleta_2025`, `ci35_ref_error_2025` | 2025 | Límites del consolidado de la CGN |
| `cortes_an_2025`, `universo_imig_vs_ci` | — | Hallazgos: tres cortes de la AN 2025; universos IMIG ≠ SPNF de la CGN |

Pendiente: no se encontró todavía una fuente oficial que documente el tratamiento de las rentas del BCRA **antes de 2017** ni los
cambios de cobertura del IMIG entre 2016 y hoy (p. ej. altas y bajas de fondos fiduciarios). No se infiere nada sobre esos años.

## 6. Puente cuantificado 2025: AN (Presupuesto Abierto) → SPN base caja (IMIG)

Implementado en `backend/observatorio/puente.py` (`/api/bridge?ejercicio=2025`, pestaña "Puente AN → IMIG"). Millones de pesos.

| # | Paso | Categoría | Importe | Acumulado | Tipo / fuente |
|---|---|---|---|---|---|
| 0 | Resultado primario AN, cierre | partida | | **21.433.030,3** | calculado, PA = Cuenta de Inversión |
| 1 | Revisión corte provisorio ↔ cierre | corte de publicación | −1.133.603,9 | 20.299.426,4 | diferencia de publicados (Boletín c.1 − PA) |
| 2 | Caja vs devengado y otras diferencias de registro | **base contable (residual)** | +553.705,6 | 20.853.132,0 | residual no descompuesto |
| 3 | Rentas del BCRA | rentas / criterio metodológico | −11.976.386,7 | 8.876.745,3 | publicado (Boletín c.5) |
| 4 | Rentas del FGS y otros | operaciones intra-sector público | −986.977,3 | 7.889.768,0 | publicado (c.5) = AN caja publicada |
| 5 | INSSJyP, fondos fiduciarios, otros entes, empresas (resultado operativo) | institucional | +3.879.450,7 | **11.769.218,7** | publicado (c.5) = IMIG |

Resultado financiero: mismo esquema, más +979.916,8 de intereses intra-SP excluidos del gasto; partida 11.279.037,3 → llegada 1.453.819,1.

Controles (todos coinciden con datos reales; si alguno no coincidiera, se muestra y no se ajusta): partida PA = Cuenta de Inversión;
llegada = suma de 12 meses del IMIG (primario y financiero); AN + resto = SPN en el Boletín; rentas netas + BCRA + FGS = rentas
devengadas de la AN (las rentas no tienen diferencia de base); intereses netos + intra-SP = intereses devengados (el residual de base es
el mismo en primario y financiero: 553.705,6); intereses intra-SP pagados = rentas cobradas por el FGS y otros.

Qué **no** está descompuesto: el residual de base (553.705,6 M$, 2,6 % del punto de partida) y la revisión entre cortes
(−1.133.603,9 M$). Las fuentes disponibles no los abren por concepto. La operación AN → resto del SPN (transferencias y figurativas)
es neutra para el consolidado: en la base caja se expone como figurativa (AN otorga 29.502.976,1 y recibe 21.816.667,1 M$).

### Puentes históricos 2017–2025 (resultado primario, millones de pesos corrientes)

Mismo método, con el Boletín Fiscal del 4º trimestre de cada año (páginas y variantes de rótulo registradas por año en
`ingest/boletin_fiscal.py`; verificadas 2026-10-20) y el detalle de Presupuesto Abierto de cada año. **Solo en 2025** la
partida está confirmada como cierre por la Cuenta de Inversión; en 2017–2024 se rotula "detalle de Presupuesto Abierto"
(nota `cortes_an_sin_ci`). Pesos corrientes: los años no se comparan entre sí sin deflactar.

| Ejercicio | Partida AN (PA) | Revisión de corte | Base caja (residual) | Rentas BCRA | Rentas FGS y otros | Resto SPN | **IMIG** |
|---|---|---|---|---|---|---|---|
| 2017 | −301.351,0 | −12.091,3 | 33.360,6 | −60.000,0 | −82.834,7 | 18.774,1 | **−404.142,3** |
| 2018 | −271.634,9 | 1,2 | 46.755,2 | 0,0 | −122.082,5 | 7.973,7 | **−338.987,3** |
| 2019 | 61.704,7 | 7.172,3 | 136.520,0 | −204.244,8 | −186.686,3 | 90.412,5 | **−95.121,6** |
| 2020 | −394.785,3 | 26.310,9 | 51.551,1 | −1.606.981,6 | −104.684,8 | 278.632,4 | **−1.749.957,3** |
| 2021 | −1.325.146,6 | 125.892,9 | 328.354,9 | −787.712,3 | −82.349,3 | 760.719,9 | **−980.240,5** |
| 2022 | −2.915.619,2 | 470.864,8 | 485.504,2 | 0,0 | −118.110,9 | 417.613,2 | **−1.659.747,9** |
| 2023 | −5.531.982,6 | −194.384,7 | 236.932,6 | −400.000,0 | −331.888,8 | 1.056.687,0 | **−5.164.636,5** |
| 2024 | 8.295.944,7 | −538.193,4 | 843.773,0 | 0,0 | −914.360,4 | 2.718.645,7 | **10.405.809,6** |
| 2025 | 21.433.030,3 | −1.133.603,9 | 553.705,6 | −11.976.386,7 | −986.977,3 | 3.879.450,7 | **11.769.218,7** |

Controles con datos reales (2026-10-20): en los nueve años la llegada coincide con la suma de 12 meses del IMIG (tolerancia
0,65 M$ por redondeo de 13 cifras) y las dos caras de la operación intra-sector público coinciden en la columna total del
cuadro 5. **Discrepan y se informan sin ajustar:** intereses netos de caja + intra-SP ≠ intereses devengados del cuadro 1 en
2017–2024 (de −39.178,5 a +303.462,7 M$; el residual de base del resultado financiero difiere del primario); rentas netas +
BCRA + FGS ≠ rentas devengadas en 2018 (−3.334,1 M$) y por ±0,4 M$ en 2017 y 2022 (redondeo del cuadro publicado). En 2022
las rentas devengadas de la AN incluyen las asociadas a emisiones primarias del Tesoro (nota `boletin_2022_rentas_emisiones_primarias`).
Corrección respecto de la versión anterior: el control intra-SP comparaba intereses AN + resto contra rentas FGS de la AN
sola; ahora compara las dos columnas totales (la nota (2) del cuadro 5 de 2017 lo confirma: 83.140,8 = 83.140,8).

Además, la fila de cada año de `totales-de-presupuesto.csv` **no coincide** con la suma del detalle anual en 2018–2024
(conciliaciones `AAAA:*: ... vs pa_totales`): es otro corte de publicación y se muestra como discrepancia.
