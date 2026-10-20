# Observatorio del Dinero Público Argentino

Proyecto independiente (no es un sitio del Estado). Aplicación (FastAPI + SQLite + React/ECharts) para estudiar ingresos, gastos y resultados del
sector público argentino a partir de datos oficiales. Cada cifra conserva su procedencia: archivo crudo, SHA-256,
URL, fecha de publicación de la fuente, universo, unidad y etapa contable.

**Estado: fase 0 + revisión de comparabilidad (2026-10-19).** **Balance oficial:** IMIG (Sector Público Nacional, base caja,
2016–hoy), con comparación interanual nominal y real. **Detalle:** Presupuesto Abierto (Administración Nacional, 2017–2026).
**Cierre consolidado:** Cuenta de Inversión 2025 de la CGN (Cuadro 35, SPNF por subsector, devengado). **Puente cuantificado**
AN → IMIG 2017–2025 con los Boletines Fiscales 4T de la ONP. **Recorrido guiado** para público general ("de cada $100"). Notas metodológicas con cita verificada. Referencias: IPC y recaudación. Ver `docs/fase0_inventario_fuentes.md` y
`docs/matriz_comparabilidad.md`. La especificación original está en `docs/ESPECIFICACION.md`.

## Versión publicada

**https://matias93miranda.github.io/observatorio_dinero_publico/**: sitio estático, sin servidor. El workflow
`.github/workflows/publicar.yml` lo regenera cada lunes (y con el botón *Run workflow* en la pestaña Actions):
descarga las fuentes oficiales, corre todas las pruebas con datos reales, exporta las respuestas de la API a JSON
(`python -m observatorio.export_static`) y publica. Si una descarga o un control falla, no publica y queda online la
versión anterior. Para generarlo a mano: `scripts/run_linux.sh sync`, después `export_static` y
`VITE_STATIC=1 npx vite build --base=/observatorio_dinero_publico/`.

## Requisitos
- Python ≥ 3.11 y Node ≥ 18 (probado con Python 3.13.2 y Node 24.16 en Linux).
- Internet solo para sincronizar. Después funciona offline con la última copia local.

## Instalación y uso

Linux / macOS:
```bash
scripts/run_linux.sh setup     # venv + dependencias + build del frontend
scripts/run_linux.sh sync      # descarga fuentes oficiales (~30 s; ~7 MB de zips por corrida, base SQLite ~190 MB)
scripts/run_linux.sh test      # pytest
scripts/run_linux.sh serve     # http://127.0.0.1:8000
scripts/run_linux.sh dev       # backend con --reload + Vite en http://localhost:5173
```

Windows (PowerShell):
```powershell
.\scripts\run_windows.ps1 setup
.\scripts\run_windows.ps1 sync
.\scripts\run_windows.ps1 serve
```
(El script de Windows no se probó en Windows: está escrito pero sin verificar.)

CLI: `cd backend && python -m observatorio.cli {init|sync [--ejercicios 2024 2025 2026] [--force]|reconcile AÑO|status}`.

La actualización es **bajo demanda** (`sync`). Para programarla, usar cron o el Programador de tareas.
`POST /api/admin/sync` solo funciona si se define `ODP_ADMIN_TOKEN` y se envía el header `X-Admin-Token`.
El token nunca va en el frontend.

## Reglas que implementa el código
| Regla | Dónde |
|---|---|
| Importes exactos: enteros en **centavos**; el texto original se guarda aparte | `money.py`, `fiscal_observation.importe_original` |
| Vacío ≠ 0: una celda vacía hace fallar la carga o queda NULL; un 404 marca la corrida `failed` | `money.parse_decimal`, `ingest/base.py` |
| Una corrida fallida no borra los datos previos y la UI la marca como desactualizada | `run_ingestion` (transacción), `metrics.provenance` |
| El crudo se guarda tal cual, con SHA-256; no se duplica si no cambió | `data/raw/<fuente>/<dataset>/` |
| No se mezclan universos: falla si `subsector_desc` ≠ Administración Nacional | `presupuesto_abierto._check_universe` |
| Doble conteo: falla si aparecen partidas fuera de 21/22 (gasto) u 11/12 (recursos) | `_check_composicion` |
| Conciliación contra totales publicados, con tolerancia 0 | `sync.reconcile`, pestaña Inicio |
| Real: IPC promedio de 12 meses; sin año completo no hay valor real | `metrics.annual_series` |
| Descomposición ≠ transferencia: los treemaps se rotulan así y `/api/transfers` queda vacío hasta tener evidencia | `metrics.breakdown`, `api.transfers` |
| Errores del archivo oficial (`#REF!`) quedan como error, sin valor; las identidades que no cierran se informan sin corregir | `ingest/cuenta_inversion.py`, tabla `reconciliation` (`ci35:*`) |
| Cifras de PDF: se extraen por rótulo de fila y página validada, nunca se tipean | `ingest/boletin_fiscal.py` |
| Puente: cada paso es publicado, diferencia de publicados o **residual** rotulado; los controles comparan cifras publicadas por separado | `puente.py` |
| Citas metodológicas verificadas contra el crudo descargado | `metodologia.py` |
| TLS siempre verificado; intermedios faltantes se agregan documentados | `ingest/base.py`, `observatorio/certs/` |

## Definiciones
- **Balance oficial (IMIG)**: resultado primario = ingresos totales − gasto primario; resultado financiero = primario − intereses netos. Base caja, SPNF. Real: cada mes deflactado por su IPC.
- **Gasto total**: gasto corriente + capital devengado de la AN (sin amortización de deuda ni gastos figurativos).
- **Gasto primario**: gasto total − intereses y primas (clasificador económico `2131*`).
- **Resultado primario** = recursos percibidos − gasto primario devengado. **Resultado financiero** = recursos percibidos − gasto total devengado.
  Base mixta (convención de la cuenta AIF): no es base caja y no se compara con el IMIG.
- **Devengado − pagado** (Presupuesto Abierto): gasto del ejercicio devengado e impago a la fecha de corte del archivo. **No** es el
  saldo de deuda flotante (que incluye obligaciones de ejercicios anteriores) ni ahorro.
- **Puente AN → IMIG**: ver `docs/fase0_inventario_fuentes.md` §6.
- **Variación nominal** = 100·(vₜ/vₜ₋₁ − 1); **variación real** = (1+nominal)/(1+inflación) − 1 (`metrics.pct_change`, `real_change`).

## API local (no oficial)
`GET /api/health · /api/sources · /api/datasets · /api/coverage · /api/ejercicios ·
/api/balance?ejercicio= · /api/bridge?ejercicio= (puente AN → IMIG) · /api/cuenta-inversion?ejercicio= (CGN, Cuadro 35) · /api/metodologia · /api/reconciliation?prefix= · /api/summary?ejercicio= · /api/expenditures?ejercicio=&classification=finalidad|funcion|jurisdiccion|inciso|programa|economico&etapa= ·
/api/revenues?ejercicio=&classification=tipo|clase · /api/transfers · /api/timeseries?metric=totales_anuales|<id_serie>&from=&to= ·
/api/observations/{id}/provenance` · `POST /api/admin/sync`.

Los centavos salen como **texto** en JSON: superan 2^53 y JavaScript los redondearía.
