import { useEffect, useState } from 'react'
import { get, ESTATICO, type Prov, type Nota } from './api'

export function useApi<T>(path: string, params: Record<string, string | number | undefined>) {
  const [data, setData] = useState<T | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const key = path + JSON.stringify(params)
  useEffect(() => {
    let alive = true
    setErr(null)
    get<T>(path, params).then(d => alive && setData(d)).catch(e => alive && setErr(String(e.message ?? e)))
    return () => { alive = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key])
  return { data, err }
}

export function ErrorBox({ err }: { err: string }) {
  return <div className="error">{ESTATICO ? `No se pudo cargar: ${err}.`
    : `No se pudo consultar la API local: ${err}. ¿Está corriendo el backend?`}</div>
}

export function ProvList({ prov }: { prov: Prov[] }) {
  return (
    <ul className="prov">
      {prov.map(p => (
        <li key={p.dataset_id}>
          <b>{p.nombre ?? p.dataset_id}</b> — {p.organismo}<br />
          <a href={p.url} target="_blank" rel="noreferrer">{p.url}</a><br />
          Universo: {p.universo} · Unidad: {p.unidad} · Publicación: {p.fecha_publicacion_fuente ?? 's/d'} ·
          Descarga: {p.fecha_descarga ?? 's/d'}<br />
          Crudo: <code>{p.archivo_crudo ?? 's/d'}</code> · SHA-256: <code>{p.sha256?.slice(0, 16) ?? 's/d'}…</code>
          {p.desactualizado && <div className="warn">El último intento de actualización falló: se muestra la copia anterior.</div>}
        </li>
      ))}
    </ul>
  )
}

const VERIF: Record<string, [string, string]> = {
  verificada_en_crudo: ['ok', '✓ cita verificada en el archivo oficial descargado'],
  hallazgo_reproducible: ['muted', '◆ hallazgo propio, con procedimiento para reproducirlo'],
  no_encontrada_en_crudo: ['warn', '⚠ la cita no aparece en el archivo descargado'],
  crudo_no_disponible: ['warn', '⚠ sin archivo descargado para verificar la cita'],
}

export function NotaView({ n }: { n: Nota }) {
  const [cls, txt] = VERIF[n.estado_verificacion] ?? ['warn', n.estado_verificacion]
  return (
    <details className="nota" id={'nota-' + n.nota_id}>
      <summary><b>{n.tema}</b>{(n.vigencia_desde || n.vigencia_hasta) &&
        <span className="muted"> · {n.vigencia_desde ?? '…'}{n.vigencia_hasta !== n.vigencia_desde && `–${n.vigencia_hasta ?? 'vigente'}`}</span>}</summary>
      <p>{n.resumen}</p>
      <p className="note">Aplica a: {n.aplica_a}</p>
      {n.cita_textual && <blockquote>“{n.cita_textual}”</blockquote>}
      <p className="note"><a href={n.fuente_url} target="_blank" rel="noreferrer">{n.ubicacion ?? n.fuente_url}</a>
        {' '}· <span className={cls}>{txt}</span></p>
    </details>
  )
}

export function useNotas() {
  return useApi<Nota[]>('/api/metodologia', {}).data ?? []
}

export function NotasRef({ ids, notas }: { ids: string[]; notas: Nota[] }) {
  const sel = notas.filter(n => ids.includes(n.nota_id))
  if (!sel.length) return null
  return <>{sel.map(n => <NotaView key={n.nota_id} n={n} />)}</>
}

export function Metodologia() {
  const notas = useNotas()
  if (!notas.length) return <p className="nodata">Sin notas cargadas: ejecutá la sincronización.</p>
  return <>{notas.map(n => <NotaView key={n.nota_id} n={n} />)}</>
}

export function useDark() {
  const q = '(prefers-color-scheme: dark)'
  const [d, setD] = useState(() => window.matchMedia(q).matches)
  useEffect(() => {
    const m = window.matchMedia(q), h = () => setD(m.matches)
    m.addEventListener('change', h)
    return () => m.removeEventListener('change', h)
  }, [])
  return d
}

/** Misma tipografía que la página (el canvas de ECharts no hereda la del CSS). */
export const FONT = 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif'

/** Paleta categórica validada (light/dark), en orden fijo; ver skill dataviz. */
export const SERIES_LIGHT = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#6250d6']
export const SERIES_DARK = ['#3987e5', '#d95926', '#199e70', '#c98500', '#d55181', '#008300', '#9085e9']
export function chartColors(dark: boolean) {
  return dark
    ? { up: '#3987e5', down: '#e66767', level: '#a9a8a2', ink: '#e8e8e6', muted: '#a2a5a8', grid: '#3a3a3a', surface: '#212121', series: SERIES_DARK }
    : { up: '#2a78d6', down: '#e34948', level: '#5c5b57', ink: '#1d1d1b', muted: '#5f6368', grid: '#e6e6e1', surface: '#ffffff', series: SERIES_LIGHT }
}

export function useReducedMotion() {
  const q = '(prefers-reduced-motion: reduce)'
  return useState(() => window.matchMedia(q).matches)[0]
}
