export type Prov = {
  dataset_id: string; nombre?: string; organismo?: string; url?: string; universo?: string
  unidad?: string; metodologia?: string; sha256?: string | null; archivo_crudo?: string | null
  fecha_publicacion_fuente?: string | null; fecha_descarga?: string | null
  ultima_verificacion?: string | null; estado: string; desactualizado?: boolean
  ultimo_intento?: { status: string; error: string | null; started_at: string } | null
  observaciones?: number; licencia?: string; granularidad?: string
}
export type Card = {
  etiqueta: string; valor_millones: string | null; estado: string; unidad: string; etapa: string
  periodo: string; universo: string | null; base: string | null; formula: string | null
  advertencias: string[]; procedencia: Prov[]
}
export type Rec = {
  comparacion: string; total_calculado_centavos: string | null; total_publicado_centavos: string | null
  diferencia_centavos: string | null; tolerancia_centavos: number; conclusion: string; checked_at: string
}
export type Summary = { ejercicio: number; universo: string; cards: Card[]; conciliacion: Rec[] }
export type Item = { code: string; label: string; valor_millones: string; participacion: string | null }
export type Breakdown = {
  estado: string; items: Item[]; total_millones?: string; periodo?: string; unidad?: string
  nota?: string; etapa?: string; n_categorias?: number; procedencia: Prov[]
}
export type Point = { ejercicio: number; nominal_millones: string | null; real_millones: string | null; parcial: boolean; ultima_actualizacion: string }
export type Annual = {
  estado: string; unidad_nominal?: string; unidad_real?: string | null; deflactor?: string
  ejercicio_vigente_parcial?: number; series: Record<string, Point[]>; procedencia: Prov[]
}

export async function get<T>(path: string, params: Record<string, string | number | undefined> = {}): Promise<T> {
  const q = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) if (v !== undefined) q.set(k, String(v))
  const r = await fetch(`${path}${q.size ? '?' + q : ''}`)
  if (!r.ok) {
    let msg = `${r.status} ${r.statusText}`
    try { msg = (await r.json()).detail ?? msg } catch { /* respuesta sin JSON */ }
    throw new Error(msg)
  }
  return r.json()
}

const nf2 = new Intl.NumberFormat('es-AR', { maximumFractionDigits: 2, minimumFractionDigits: 2 })
const nf0 = new Intl.NumberFormat('es-AR', { maximumFractionDigits: 0 })

/** millones (string decimal exacto) -> texto legible. Null => "sin datos", nunca 0. */
export function fmtMillones(v: string | null | undefined): string {
  if (v === null || v === undefined) return 'sin datos'
  const n = Number(v)
  if (Math.abs(n) >= 1e6) return `$ ${nf2.format(n / 1e6)} billones`
  if (Math.abs(n) >= 1e3) return `$ ${nf2.format(n / 1e3)} miles de millones`
  return `$ ${nf2.format(n)} millones`
}
export const fmtExacto = (v: string | null | undefined) =>
  v === null || v === undefined ? 'sin datos' : `${nf2.format(Number(v))} M$`
/** centavos como texto exacto -> millones con 8 decimales, sin pasar por float */
export function fmtCentavos(c: string | null): string {
  if (c === null) return 'sin datos'
  const neg = c.startsWith('-'), d = (neg ? c.slice(1) : c).padStart(9, '0')
  const ent = d.slice(0, -8).replace(/\B(?=(\d{3})+(?!\d))/g, '.')
  return `${neg ? '−' : ''}${ent},${d.slice(-8)} M$`
}
export const fmtPct = (p: string | null) => (p === null ? '—' : `${nf2.format(Number(p) * 100)} %`)
export const fmtInt = (n: number) => nf0.format(n)

export type BalLine = {
  etiqueta: string; valor_millones: string | null; estado: string; anterior_millones: string | null
  var_nominal_pct: string | null; var_real_pct: string | null; nota?: string | null
  flujo?: string; detalle?: BalLine[]; columna?: string
  real_millones?: string | null; anterior_real_millones?: string | null; grupo?: string
}
export type Balance = {
  estado: string; ejercicio: number; periodo?: string; comparado_con?: string | null; universo?: string
  base?: string; unidad?: string; unidad_real?: string | null; parcial?: boolean; meses?: string[]
  cards: BalLine[]; grupos: BalLine[]; procedencia: Prov[]
}
export type Paso = {
  tipo: string; categoria: string; concepto: string; fuente: string; notas: string[]
  universo: string | null; base: string | null; valor_millones: string | null; acumulado_millones: string | null; rotulo: string
  advertencia?: string
}
export type Control = { control: string; estado: string; diferencia_millones: string | null; tolerancia_millones?: string; nota?: string | null }
export type RentaFila = { fuente: string; universo: string; base: string; valor_millones: string | null; estado: string; nota: string | null }
export type Bridge = {
  estado: string; ejercicio: number; motivo?: string; unidad?: string; faltan?: string[]
  resultado_primario?: Paso[]; resultado_financiero?: Paso[]; controles?: Control[]
  tipos?: Record<string, string>; comparacion_rentas?: RentaFila[]; procedencia: Prov[]
  partida_es_cierre?: boolean; deflactor?: Deflactor | null
}
export type Deflactor = { base: number; factor: string; unidad_real: string; metodo: string }
export type HistRes = { partida_millones: string | null; llegada_millones: string | null; componentes: Record<string, string | null> }
export type HistFila = {
  ejercicio: number; estado: string; faltan?: string[]; partida_es_cierre?: boolean; deflactor?: Deflactor | null
  ingresos_imig_millones?: string | null
  controles_discrepan?: number; controles_total?: number
  resultado_primario?: HistRes; resultado_financiero?: HistRes
}
export type Historico = { unidad: string; componentes: Record<string, string>; ejercicios: HistFila[] }
export type FilaCI = {
  subsector: string; nombre: string; ingresos_totales: string | null; gastos_totales: string | null
  intereses: string | null; rentas_propiedad: string | null; resultado_primario: string | null
  resultado_financiero: string | null; contribuciones_figurativas: string | null; gastos_figurativos: string | null
}
export type CuentaInversion = {
  estado: string; ejercicio: number; universo?: string; base?: string; unidad?: string; filas?: FilaCI[]
  identidades?: Record<string, number>; celdas_con_error?: { celda: string; concepto: string; subsector: string; importe_original: string }[]
  notas?: string[]; advertencia?: string; procedencia: Prov[]
}
export type Nota = {
  nota_id: string; tema: string; aplica_a: string; vigencia_desde: string | null; vigencia_hasta: string | null
  resumen: string; cita_textual: string | null; fuente_dataset_id: string | null; fuente_url: string
  ubicacion: string | null; estado_verificacion: string; verificado_en: string
}
export const fmtVar = (p: string | null) =>
  p === null ? '—' : `${Number(p) > 0 ? '+' : ''}${nf2.format(Number(p))} %`

/** millones (número) -> "$ 11,8 billones" con un decimal: para titulares; el exacto va en tablas y tooltips. */
export function fmtCorto(n: number | null): string {
  if (n === null || Number.isNaN(n)) return 'sin datos'
  const a = Math.abs(n), sg = n < 0 ? '−' : ''
  const f = (x: number) => new Intl.NumberFormat('es-AR', { maximumFractionDigits: 1, minimumFractionDigits: 1 }).format(x)
  if (a >= 1e6) return `${sg}$ ${f(a / 1e6)} billones`
  if (a >= 1e3) return `${sg}$ ${f(a / 1e3)} mil millones`
  return `${sg}$ ${f(a)} millones`
}
