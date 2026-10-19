# Matriz de compatibilidad contable

Dos cifras se pueden comparar o restar solo si coinciden universo, base contable, cobertura de partidas y período.

| Fuente / medida | Universo | Base | Cubre | No cubre | Período |
|---|---|---|---|---|---|
| PA `credito_*` | Administración Nacional | presupuestado / vigente / comprometido / **devengado** / pagado | Gasto corriente + capital (econ. 21, 22), con intereses | Amortización de deuda, aplicaciones financieras, gastos figurativos | Ejercicio; anual o mensual (impacto) |
| PA `recurso_*` | Administración Nacional | inicial / vigente / **percibido** | Recursos corrientes + capital (econ. 11, 12) | Fuentes financieras (endeudamiento, uso de activos) | Ídem |
| PA `totales` | Administración Nacional | gasto devengado, recurso percibido | Totales y gasto primario | — | Anual; el ejercicio vigente es parcial |
| IMIG (Series de Tiempo 452.x) | **Sector Público Nacional no Financiero** (AN + empresas, fondos fiduciarios, PAMI, otros entes) | **Caja** | Ingresos y gastos primarios por concepto | — | Mensual |
| Recaudación (172.x, MECON/ARCA) | Recaudación tributaria **nacional, bruta** | Caja (ingreso al fisco) | Incluye lo que después se coparticipa a provincias | No es ingreso presupuestario de la AN | Mensual |
| IPC (148.3) | Precios al consumidor, total país | Índice dic-2016 = 100 | — | Antes de dic-2016 | Mensual |

## Combinaciones permitidas y prohibidas

| Operación | ¿Válida? | Condición / motivo |
|---|---|---|
| PA recursos percibidos − PA gasto devengado (mismo ejercicio) | ✅ con rótulo | Es la convención de la cuenta AIF de la AN. Se rotula "base mixta" y no es caja |
| PA devengado vs PA pagado | ✅ | Mismo universo; la diferencia es deuda flotante |
| PA mensual: presupuestado/vigente por mes | ❌ | Se imputan íntegros al mes 1 (stock). Solo devengado/pagado/comprometido son flujos mensuales |
| PA resultado vs IMIG resultado | ❌ sin puente | Distinto universo y distinta base. Ejemplo 2025: IMIG resultado primario 11.769.218,70 M$ (suma de 12 meses) vs PA (detalle) 21.433.030,27 M$. La brecha no es un error de ninguna de las dos |
| Recaudación bruta vs PA ingresos impositivos | ❌ | 2025: recaudación 183.109.216,18 M$ vs ingresos impositivos AN 73.020.949,95 M$. La recaudación incluye coparticipación a provincias y seguridad social con otro tratamiento |
| Suma AN + provincias (V3) | ❌ sin consolidar | Las transferencias de Nación a provincias ya están como gasto de la AN (econ. 21723100 corrientes, 22223100 de capital): sumarlas como gasto provincial las cuenta dos veces |
| Ingresos AN "Rentas de la propiedad" | ⚠ | Pueden incluir flujos intra-sector público (utilidades del BCRA, rentas del FGS). En 2026 son 30,96 billones (21% de los recursos). Hay que aclararlo antes de comparar con el IMIG |
| PA totales 2025 vs PA detalle 2025 | ⚠ | Discrepan (ver inventario). Hay que elegir una fuente y declararla |
| Real vs nominal | ✅ | Deflactor: IPC promedio de 12 meses. Si al año le falta algún mes, no hay valor real (no se extrapola) |
| Ejercicio en curso vs años cerrados | ❌ | Es un acumulado parcial (p. ej. al 16-oct-2026). Solo se compara con el mismo período del año anterior, y eso requiere datos mensuales (MVP) |

## Riesgos de doble conteo identificados
1. **Transferencias intra-AN (contribuciones figurativas):** no aparecen en el archivo de crédito (no hay inciso 9). El conector corta la carga si aparece un código económico fuera de 21/22 (gastos) u 11/12 (recursos).
2. **Transferencias a fondos fiduciarios y empresas públicas** (econ. 21722300 fondos fiduciarios y otros entes del SPNF; 21722100 y 22222100 empresas públicas no financieras): son gasto de la AN. Si en V2 se suma el SPNF, deben eliminarse contra los ingresos de esos entes.
3. **Transferencias a provincias y municipios** (econ. 21723100, 21723400, 22223100, 22223400): son gasto final para la AN e ingreso para la provincia. Se resuelve en la consolidación de V3.
4. **Intereses intra-sector público** (deuda con FGS/BCRA): están en el gasto de la AN y quizá en las rentas de otros entes. Se resuelve en la consolidación del SPNF (V2).
