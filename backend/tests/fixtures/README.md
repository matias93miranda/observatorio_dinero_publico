# Fixtures

- `credito-anual-2026-muestra.csv`: primeras 40 filas de datos más la línea 46917 (primera con clasificador económico 2131, intereses) de
  https://dgsiaf-repo.mecon.gob.ar/repository/pa/datasets/2026/credito-anual-2026.zip (descargado 2026-10-19), sin modificar.
- `recursos-anual-2026-muestra.csv`: primeras 30 filas de datos de `recursos-anual-2026.zip`, misma fecha, sin modificar.
- `totales-encabezado.csv`: solo el encabezado real de `totales-de-presupuesto.zip`. Los tests completan filas
  **sintéticas** (calculadas desde las muestras) para probar la lógica de conciliación; no son cifras oficiales.
- `serie-con-hueco.csv`: serie **sintética** con un período sin valor, para verificar que vacío ≠ 0.
