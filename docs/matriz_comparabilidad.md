# Matriz de compatibilidad contable

Dos cifras se pueden comparar o restar solo si coinciden universo, base contable, cobertura de partidas y período.

| Fuente / medida | Universo | Base | Cubre | No cubre | Período |
|---|---|---|---|---|---|
| PA `credito_*` | Administración Nacional | presupuestado / vigente / comprometido / **devengado** / pagado | Gasto corriente + capital (econ. 21, 22), con intereses | Amortización de deuda, aplicaciones financieras, gastos figurativos | Ejercicio; anual o mensual (impacto) |
| PA `recurso_*` | Administración Nacional | inicial / vigente / **percibido** | Recursos corrientes + capital (econ. 11, 12) | Fuentes financieras (endeudamiento, uso de activos) | Ídem |
| PA `totales` | Administración Nacional | gasto devengado, recurso percibido | Totales y gasto primario | — | Anual; el ejercicio vigente es parcial |
| IMIG (Series de Tiempo 452.x) | **Sector Público Nacional** (AN + PAMI, fondos fiduciarios, otros entes; **empresas solo por su resultado operativo**; universidades como destino de transferencias) | **Caja**, metodología 2017: sin rentas del BCRA ni del FGS, intereses netos de los intra-sector público | Ingresos y gastos primarios por concepto | Rentas BCRA/FGS, intereses intra-SP | Mensual |
| Cuenta de Inversión, Cuadro 35 (CGN) | **SPNF** por subsector: AN (3 partes), universidades, empresas, fondos fiduciarios, entes, con columna de eliminaciones | Devengado (gastos) / percibido (recursos); transferencias intra-SPNF devengadas de ambos lados | AIF completa, incluidas fuentes y aplicaciones financieras | No consolida compraventa de bienes y servicios ni tributos entre subsectores; 2 fondos fiduciarios sin datos en 2025 | Anual, cierre |
| Boletín Fiscal ONP (4º trim.) | Cuadro 1: AN. Cuadros 4-5: SPN base caja (AN y “INSSJyP, fondos fiduciarios y otros”) | AN: recaudado/devengado, **provisorio**. SPN: caja, metodología 2017 | Publica por separado rentas BCRA, rentas FGS e intereses intra-SP | — | Trimestral acumulado |
| Recaudación (172.x, MECON/ARCA) | Recaudación tributaria **nacional, bruta** | Caja (ingreso al fisco) | Incluye lo que después se coparticipa a provincias | No es ingreso presupuestario de la AN | Mensual |
| IPC (148.3) | Precios al consumidor, total país | Índice dic-2016 = 100 | — | Antes de dic-2016 | Mensual |

## Combinaciones permitidas y prohibidas

| Operación | ¿Válida? | Condición / motivo |
|---|---|---|
| PA recursos percibidos − PA gasto devengado (mismo ejercicio) | ✅ con rótulo | Es la convención de la cuenta AIF de la AN. Se rotula "base mixta" y no es caja |
| PA devengado vs PA pagado | ✅ con rótulo | Mismo universo. La diferencia es gasto **del ejercicio** devengado e impago a la fecha de corte del archivo. **No** es el saldo de deuda flotante: ese stock incluye obligaciones de ejercicios anteriores, que se pagan fuera del crédito del ejercicio (nota `deuda_exigible_no_es_flotante`) |
| PA mensual: presupuestado/vigente por mes | ❌ | Se imputan íntegros al mes 1 (stock). Solo devengado/pagado/comprometido son flujos mensuales |
| PA resultado vs IMIG resultado | ✅ **solo con el puente** (`/api/bridge`) | Distinto universo y base. 2025: 21.433.030,27 M$ (AN) → 11.769.218,70 M$ (SPN caja), descompuesto en revisión de corte, residual de base, rentas BCRA, rentas FGS e institucional (ver inventario §6) |
| Cuenta de Inversión SPNF vs IMIG (ingresos o gastos totales) | ❌ | Las empresas entran brutas en la CGN y netas en el IMIG; universidades son subsector en una y transferencia en el otro. Solo los resultados son comparables, y con puente |
| Boletín 4T (AN) vs cierre (PA detalle / Cuenta de Inversión) | ⚠ | Son cortes distintos del mismo universo: la diferencia es revisión. Se usa el cierre y el corte provisorio solo dentro del puente |
| Recaudación bruta vs PA ingresos impositivos | ❌ | 2025: recaudación 183.109.216,18 M$ vs ingresos impositivos AN 73.020.949,95 M$. La recaudación incluye coparticipación a provincias y seguridad social con otro tratamiento |
| Suma AN + provincias (V3) | ❌ sin consolidar | Las transferencias de Nación a provincias ya están como gasto de la AN (econ. 21723100 corrientes, 22223100 de capital): sumarlas como gasto provincial las cuenta dos veces |
| Ingresos AN "Rentas de la propiedad" | ⚠ | Incluyen flujos intra-sector público. 2025 (cuantificado, Boletín 4T): 11.976.386,7 M$ del BCRA (utilidades del ejercicio 2024) y 986.977,3 M$ del FGS y otros, sobre 16.390.348,9 M$ de rentas de la AN. En 2026 son 30,96 billones (21% de los recursos): sin Boletín 4T 2026 todavía no se puede separar |
| PA totales 2025 vs PA detalle 2025 | ⚠ resuelto | Discrepan. El detalle coincide con la Cuenta de Inversión 2025 (cierre oficial): **se usa el detalle**; la fila de totales es un corte anterior y se muestra como discrepancia, sin corregirla |
| Real vs nominal | ✅ | Deflactor: IPC promedio de 12 meses. Si al año le falta algún mes, no hay valor real (no se extrapola) |
| Ejercicio en curso vs años cerrados | ❌ | Es un acumulado parcial (p. ej. al 16-oct-2026). Solo se compara con el mismo período del año anterior, y eso requiere datos mensuales (MVP) |

## Riesgos de doble conteo identificados
1. **Transferencias intra-AN (contribuciones figurativas):** no aparecen en el archivo de crédito (no hay inciso 9). El conector corta la carga si aparece un código económico fuera de 21/22 (gastos) u 11/12 (recursos).
2. **Transferencias a fondos fiduciarios y empresas públicas** (econ. 21722300 fondos fiduciarios y otros entes del SPNF; 21722100 y 22222100 empresas públicas no financieras): son gasto de la AN. Si en V2 se suma el SPNF, deben eliminarse contra los ingresos de esos entes.
3. **Transferencias a provincias y municipios** (econ. 21723100, 21723400, 22223100, 22223400): son gasto final para la AN e ingreso para la provincia. Se resuelve en la consolidación de V3.
4. **Intereses intra-sector público:** en 2025 la AN pagó 979.916,8 M$ y el resto del SPN 7.060,5 M$ a otros entes públicos, y el FGS y otros cobraron 986.977,3 M$: las dos caras coinciden (control del puente). El IMIG los excluye de ambos lados; la AN y la Cuenta de Inversión los mantienen.
5. **Compraventa y tributos entre subsectores:** la Cuenta de Inversión no los elimina (cita verificada). Los ingresos y gastos **totales** del SPNF de la CGN los cuentan dos veces; los resultados no se ven afectados.
6. **Cuadro 35, celdas K52:K53:** el total SPNF de las transferencias de capital a provincias y a otros figura como `#REF!` en el archivo oficial. No se reconstruye.
