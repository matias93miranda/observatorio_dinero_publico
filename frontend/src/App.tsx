import { useEffect, useState } from 'react'
import ReactECharts from 'echarts-for-react'
import {
  get, fmtMillones, fmtExacto, fmtCentavos, fmtPct, fmtInt,
  type Summary, type Breakdown, type Annual, type Prov, type Card,
} from './api'

type Tab = 'inicio' | 'destinos' | 'evolucion' | 'fuentes'
const TABS: [Tab, string][] = [
  ['inicio', 'Inicio'], ['destinos', 'Destinos'], ['evolucion', 'Evolución'], ['fuentes', 'Fuentes'],
]

function useApi<T>(path: string, params: Record<string, string | number | undefined>) {
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

function ErrorBox({ err }: { err: string }) {
  return <div className="error">No se pudo consultar la API local: {err}. ¿Está corriendo el backend?</div>
}

function ProvList({ prov }: { prov: Prov[] }) {
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

function CardView({ c }: { c: Card }) {
  const [open, setOpen] = useState(false)
  const neg = c.valor_millones !== null && c.valor_millones.startsWith('-')
  return (
    <div className="card">
      <div className="card-label">{c.etiqueta}</div>
      <div className={'card-value' + (c.valor_millones === null ? ' nodata' : neg ? ' neg' : '')}>
        {fmtMillones(c.valor_millones)}
      </div>
      <div className="card-meta">Etapa: <b>{c.etapa}</b> · {c.periodo}</div>
      <div className="card-meta">Exacto: {fmtExacto(c.valor_millones)}</div>
      {c.formula && <div className="card-meta">Fórmula: {c.formula}</div>}
      <button className="link" onClick={() => setOpen(!open)}>{open ? 'Ocultar' : 'Ver'} procedencia</button>
      {open && (
        <div className="detail">
          {c.base && <p><b>Base contable:</b> {c.base}</p>}
          {c.advertencias.map((a, i) => <p key={i} className="warn">⚠ {a}</p>)}
          <ProvList prov={c.procedencia} />
        </div>
      )}
    </div>
  )
}

function Inicio({ ej }: { ej: number }) {
  const { data, err } = useApi<Summary>('/api/summary', { ejercicio: ej })
  if (err) return <ErrorBox err={err} />
  if (!data) return <p>Cargando…</p>
  const bad = data.conciliacion.filter(r => r.conclusion !== 'coincide')
  return (
    <>
      <p className="scope">Universo: <b>{data.universo}</b> (Sector Público Nacional no Financiero). No incluye
        empresas públicas, fondos fiduciarios fuera del presupuesto, PAMI, provincias ni municipios.</p>
      <div className="cards">{data.cards.map(c => <CardView key={c.etiqueta} c={c} />)}</div>
      <h3>Conciliación contra totales publicados</h3>
      {bad.length === 0
        ? <p className="ok">Las 9 medidas coinciden exactamente con <code>totales-de-presupuesto.csv</code>.</p>
        : <p className="warn">{bad.length} de {data.conciliacion.length} comparaciones no coinciden o no tienen dato. Ver detalle.</p>}
      <RecTable recs={data.conciliacion} />
    </>
  )
}

function RecTable({ recs }: { recs: Summary['conciliacion'] }) {
  return (
    <div className="tablewrap"><table>
      <thead><tr><th>Comparación</th><th>Suma de líneas</th><th>Publicado</th><th>Diferencia</th><th>Resultado</th></tr></thead>
      <tbody>{recs.map(r => (
        <tr key={r.comparacion}>
          <td>{r.comparacion}</td><td className="num">{fmtCentavos(r.total_calculado_centavos)}</td>
          <td className="num">{fmtCentavos(r.total_publicado_centavos)}</td>
          <td className="num">{fmtCentavos(r.diferencia_centavos)}</td>
          <td className={r.conclusion === 'coincide' ? 'ok' : 'warn'}>{r.conclusion}</td>
        </tr>))}
      </tbody>
    </table></div>
  )
}

const GASTO_CLS = [['finalidad', 'Finalidad'], ['funcion', 'Función'], ['jurisdiccion', 'Jurisdicción'],
  ['inciso', 'Objeto (inciso)'], ['programa', 'Programa']] as const
const ETAPAS = ['devengado', 'pagado', 'comprometido', 'vigente', 'presupuestado'] as const

function Destinos({ ej }: { ej: number }) {
  const [flujo, setFlujo] = useState<'gasto' | 'recurso'>('gasto')
  const [cls, setCls] = useState<string>('finalidad')
  const [etapa, setEtapa] = useState<string>('devengado')
  const path = flujo === 'gasto' ? '/api/expenditures' : '/api/revenues'
  const params = flujo === 'gasto'
    ? { ejercicio: ej, classification: cls, etapa, limit: 30 }
    : { ejercicio: ej, classification: cls === 'clase' ? 'clase' : 'tipo', etapa: 'percibido', limit: 30 }
  const { data, err } = useApi<Breakdown>(path, params)
  return (
    <>
      <div className="controls">
        <select value={flujo} onChange={e => { const f = e.target.value as 'gasto' | 'recurso'; setFlujo(f); setCls(f === 'gasto' ? 'finalidad' : 'tipo') }}>
          <option value="gasto">Gastos</option><option value="recurso">Recursos</option>
        </select>
        <select value={cls} onChange={e => setCls(e.target.value)}>
          {flujo === 'gasto'
            ? GASTO_CLS.map(([v, l]) => <option key={v} value={v}>{l}</option>)
            : [['tipo', 'Tipo de recurso'], ['clase', 'Clase']].map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
        {flujo === 'gasto' && (
          <select value={etapa} onChange={e => setEtapa(e.target.value)}>
            {ETAPAS.map(x => <option key={x}>{x}</option>)}
          </select>)}
      </div>
      {err && <ErrorBox err={err} />}
      {data && data.estado !== 'ok' && <p className="nodata">Sin datos para este ejercicio.</p>}
      {data && data.estado === 'ok' && (
        <>
          <p className="note">{data.nota} Etapa: <b>{data.etapa}</b> · {data.periodo} · Total {fmtMillones(data.total_millones)}
            {data.n_categorias! > data.items.length && ` · se muestran ${data.items.length} de ${data.n_categorias} categorías`}</p>
          <ReactECharts style={{ height: 420 }} option={{
            tooltip: { formatter: (p: { name: string; value: number }) => `${p.name}<br/>${fmtMillones(String(p.value))}` },
            series: [{
              type: 'treemap', roam: false, nodeClick: false, breadcrumb: { show: false },
              label: { formatter: '{b}' },
              data: data.items.map(i => ({ name: i.label, value: Number(i.valor_millones) })),
            }],
          }} />
          <div className="tablewrap"><table>
            <thead><tr><th>Código</th><th>Categoría</th><th>Importe</th><th>Participación</th></tr></thead>
            <tbody>{data.items.map(i => (
              <tr key={i.code}><td>{i.code}</td><td>{i.label}</td><td className="num">{fmtExacto(i.valor_millones)}</td>
                <td className="num">{fmtPct(i.participacion)}</td></tr>))}
            </tbody>
          </table></div>
          <details><summary>Procedencia</summary><ProvList prov={data.procedencia} /></details>
        </>)}
    </>
  )
}

const MEDIDAS: [string, string][] = [
  ['credito_devengado', 'Gasto total devengado'], ['gasto_primario_devengado', 'Gasto primario devengado'],
  ['recurso_ingresado_percibido', 'Recursos percibidos'],
]

function Evolucion() {
  const { data, err } = useApi<Annual>('/api/timeseries', { metric: 'totales_anuales' })
  const [modo, setModo] = useState<'nominal' | 'real'>('real')
  if (err) return <ErrorBox err={err} />
  if (!data) return <p>Cargando…</p>
  if (data.estado !== 'ok') return <p className="nodata">Sin datos.</p>
  const years = data.series.credito_devengado.map(p => p.ejercicio)
  const key = modo === 'nominal' ? 'nominal_millones' : 'real_millones'
  return (
    <>
      <div className="controls">
        <select value={modo} onChange={e => setModo(e.target.value as 'nominal' | 'real')}>
          <option value="real">Real ({data.unidad_real})</option>
          <option value="nominal">Nominal ({data.unidad_nominal})</option>
        </select>
      </div>
      <p className="note">
        Administración Nacional, totales anuales publicados por Presupuesto Abierto.
        {modo === 'real' && <> Deflactor: {data.deflactor}. Los años sin IPC completo quedan sin dato (no se extrapola).</>}
        {' '}El ejercicio {data.ejercicio_vigente_parcial} está en curso (acumulado parcial): no comparable con años cerrados.
      </p>
      <ReactECharts style={{ height: 420 }} option={{
        tooltip: { trigger: 'axis', valueFormatter: (v: number | null) => v === null || v === undefined ? 'sin datos' : fmtMillones(String(v)) },
        legend: { top: 0 },
        grid: { left: 70, right: 20, top: 40, bottom: 30 },
        xAxis: { type: 'category', data: years },
        yAxis: { type: 'value', axisLabel: { formatter: (v: number) => `${v / 1e6} bill.` } },
        series: MEDIDAS.map(([m, label]) => ({
          name: label, type: 'line', connectNulls: false,
          data: (data.series[m] ?? []).map(p => ({
            value: p[key] === null ? null : Number(p[key]),
            symbol: p.parcial ? 'emptyCircle' : 'circle', symbolSize: p.parcial ? 9 : 5,
          })),
        })),
      }} />
      <details><summary>Procedencia</summary><ProvList prov={data.procedencia} /></details>
    </>
  )
}

function Fuentes() {
  const { data, err } = useApi<Prov[]>('/api/coverage', {})
  if (err) return <ErrorBox err={err} />
  if (!data) return <p>Cargando…</p>
  return (
    <div className="tablewrap"><table>
      <thead><tr><th>Dataset</th><th>Universo</th><th>Unidad</th><th>Publicación fuente</th><th>Descarga</th><th>Obs.</th><th>Estado</th></tr></thead>
      <tbody>{data.map(p => (
        <tr key={p.dataset_id}>
          <td><a href={p.url} target="_blank" rel="noreferrer">{p.nombre}</a><br /><code>{p.dataset_id}</code></td>
          <td>{p.universo}</td><td>{p.unidad}</td><td>{p.fecha_publicacion_fuente ?? 's/d'}</td>
          <td>{p.fecha_descarga ?? 's/d'}</td><td className="num">{fmtInt(p.observaciones ?? 0)}</td>
          <td className={p.estado === 'ok' && !p.desactualizado ? 'ok' : 'warn'}>
            {p.estado}{p.desactualizado && ` (último intento falló: ${p.ultimo_intento?.error})`}</td>
        </tr>))}
      </tbody>
    </table></div>
  )
}

export default function App() {
  const fromHash = () => (TABS.find(([t]) => '#' + t === window.location.hash)?.[0] ?? 'inicio')
  const [tab, setTabState] = useState<Tab>(fromHash)
  const setTab = (t: Tab) => { window.location.hash = t; setTabState(t) }
  useEffect(() => {
    const h = () => setTabState(fromHash())
    window.addEventListener('hashchange', h)
    return () => window.removeEventListener('hashchange', h)
  }, [])
  const { data: ejs } = useApi<number[]>('/api/ejercicios', {})
  const [ej, setEj] = useState<number | null>(null)
  const ejercicio = ej ?? ejs?.[0] ?? null
  return (
    <div className="app">
      <header>
        <h1>Observatorio del Dinero Público Argentino</h1>
        <p className="badge">Datos reales · copia local · fase 0</p>
      </header>
      <nav>
        {TABS.map(([t, l]) => <button key={t} className={t === tab ? 'active' : ''} onClick={() => setTab(t)}>{l}</button>)}
        {(tab === 'inicio' || tab === 'destinos') && ejs && (
          <select value={ejercicio ?? ''} onChange={e => setEj(Number(e.target.value))}>
            {ejs.map(y => <option key={y} value={y}>Ejercicio {y}</option>)}
          </select>)}
      </nav>
      <main>
        {tab === 'evolucion' ? <Evolucion /> : tab === 'fuentes' ? <Fuentes />
          : ejercicio === null ? <p className="nodata">No hay datos cargados. Ejecutá la sincronización (ver README).</p>
          : tab === 'inicio' ? <Inicio ej={ejercicio} /> : <Destinos ej={ejercicio} />}
      </main>
      <footer>Cifras en pesos corrientes salvo indicación. Cada valor enlaza a su archivo oficial.
        Las descomposiciones por clasificador no son pagos rastreados a destinatarios.</footer>
    </div>
  )
}
