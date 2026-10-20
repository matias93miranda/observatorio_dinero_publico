# Fixtures

- `credito-anual-2026-muestra.csv`: primeras 40 filas de datos más la línea 46917 (primera con clasificador económico 2131, intereses) de
  https://dgsiaf-repo.mecon.gob.ar/repository/pa/datasets/2026/credito-anual-2026.zip (descargado 2026-10-19), sin modificar.
- `recursos-anual-2026-muestra.csv`: primeras 30 filas de datos de `recursos-anual-2026.zip`, misma fecha, sin modificar.
- `totales-encabezado.csv`: solo el encabezado real de `totales-de-presupuesto.zip`. Los tests completan filas
  **sintéticas** (calculadas desde las muestras) para probar la lógica de conciliación; no son cifras oficiales.
- `serie-con-hueco.csv`: serie **sintética** con un período sin valor, para verificar que vacío ≠ 0.
- `imig-muestra.csv`: encabezado + filas 2024-01..03 y 2025-01..03 de
  https://infra.datos.gob.ar/catalog/sspm/dataset/452/distribution/452.3/download/imig-mensual.csv (2026-10-19), sin modificar.
- `cuadro35-tomoi-2025.xlsx`: Cuenta de Inversión 2025, Tomo I, Cuadro 35 (CGN), de
  https://www.argentina.gob.ar/sites/default/files/cuadro35-tomoi-2025.xlsx (2026-10-19), sin modificar
  (SHA-256 `1061985877d0f1cf51c9974d557f6081486aaef8118c1700b5b81a11b3937234`).
- `boletin-4t2025-paginas.pdf`: Boletín Fiscal 4º trimestre 2025 (ONP) con las páginas 5, 6, 33, 57, 61 y 62 originales
  y las demás reemplazadas por páginas en blanco (para conservar la numeración), de
  https://www.mecon.gob.ar/onp/documentos/boletin/4totrim25/4totrim25.pdf (2026-10-19).
- `cgn-metodologia-spnf-2025.pdf`: Gestión Financiera Consolidada, aspectos generales y metodológicos, Cuenta de Inversión
  2025, de https://www.argentina.gob.ar/sites/default/files/gestion-financiera-consolidada_aspectos_generales_y_metodologicos-tomoi-2025.pdf, sin modificar.
- En `test_cuenta_inversion_puente.py`, `insert_pa_sintetico` arma 4 líneas **sintéticas** de Presupuesto Abierto con los
  totales del Cuadro 35 (para no versionar 113 mil filas); `IMIG_2025` son los valores reales de resultado primario y
  financiero de `imig-mensual.csv`.
