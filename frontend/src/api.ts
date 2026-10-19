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
