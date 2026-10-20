import { useEffect, useState } from 'react'
import ReactECharts from 'echarts-for-react'
import Recorrido from './Recorrido'
import BridgeView from './Puente'
import { useApi, ErrorBox, ProvList, useNotas, NotasRef, Metodologia } from './comun'
import {
  fmtMillones, fmtExacto, fmtCentavos, fmtPct, fmtInt,
  type Summary, type Breakdown, type Annual, type Prov, type Card, type Balance, type BalLine, fmtVar,
  type CuentaInversion, type Rec, type FilaCI,
} from './api'

type Tab = 'recorrido' | 'inicio' | 'puente' | 'cuenta' | 'destinos' | 'evolucion' | 'fuentes'
const TABS: [Tab, string][] = [
  ['recorrido', 'Recorrido guiado'], ['inicio', 'Resumen'], ['puente', 'Puente Presupuesto → oficial'], ['cuenta', 'Cuenta de Inversión'],
  ['destinos', 'Destinos'], ['evolucion', 'Evolución'], ['fuentes', 'Fuentes y metodología'],
]
const CON_EJERCICIO: Tab[] = ['recorrido', 'inicio', 'puente', 'cuenta', 'destinos']

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

function BalCard({ c, cmp }: { c: BalLine; cmp: string | null | undefined }) {
  const neg = c.valor_millones !== null && c.valor_millones.startsWith('-')
  return (
    <div className="card">
      <div className="card-label">{c.etiqueta}</div>
      <div className={'card-value' + (c.valor_millones === null ? ' nodata' : neg ? ' neg' : '')}>{fmtMillones(c.valor_millones)}</div>
      <div className="card-meta">Exacto: {fmtExacto(c.valor_millones)}</div>
      {cmp && <div className="card-meta">vs {cmp}: {fmtMillones(c.anterior_millones)}</div>}
      {cmp && <div className="card-meta">Var. nominal {fmtVar(c.var_nominal_pct)} · <b>var. real {fmtVar(c.var_real_pct)}</b></div>}
      {c.nota && <div className="card-meta">{c.nota}</div>}
    </div>
  )
}

function BalanceView({ ej }: { ej: number }) {
  const { data, err } = useApi<Balance>('/api/balance', { ejercicio: ej })
  if (err) return <ErrorBox err={err} />
  if (!data) return <p>Cargando…</p>
  if (data.estado !== 'ok') return <p className="nodata">Sin datos del IMIG para {ej}.</p>
  return (
    <>
      <p className="scope">Universo: <b>{data.universo}</b> · base <b>{data.base}</b> · {data.periodo}.
        Fuente: IMIG, Secretaría de Hacienda. Es el resultado fiscal oficial.
        {data.parcial && ' Año en curso: se compara contra los mismos meses del año anterior.'}</p>
      <div className="cards">{data.cards.map(c => <BalCard key={c.etiqueta} c={c} cmp={data.comparado_con} />)}</div>
      <details>
        <summary>Composición por grupo ({data.periodo})</summary>
        <div className="tablewrap"><table>
          <thead><tr><th>Concepto</th><th>Importe</th><th>{data.comparado_con ?? 'Anterior'}</th><th>Var. nominal</th><th>Var. real</th></tr></thead>
          <tbody>{data.grupos.flatMap(g => [
            <tr key={g.etiqueta} className="grp"><td><b>{g.etiqueta}</b> <span className="muted">({g.flujo})</span></td>
              <td className="num">{fmtExacto(g.valor_millones)}</td><td className="num">{fmtExacto(g.anterior_millones)}</td>
              <td className="num">{fmtVar(g.var_nominal_pct)}</td><td className="num">{fmtVar(g.var_real_pct)}</td></tr>,
            ...(g.detalle ?? []).map(d => (
              <tr key={g.etiqueta + d.columna}><td className="indent">{d.etiqueta}</td>
                <td className="num">{fmtExacto(d.valor_millones)}</td><td className="num">{fmtExacto(d.anterior_millones)}</td>
                <td className="num">{fmtVar(d.var_nominal_pct)}</td><td className="num">{fmtVar(d.var_real_pct)}</td></tr>)),
          ])}</tbody>
        </table></div>
        <p className="note">Real: {data.unidad_real}.</p>
      </details>
      <details><summary>Procedencia</summary><ProvList prov={data.procedencia} /></details>
    </>
  )
}

function CuentaInversionView({ ej }: { ej: number }) {
  const { data, err } = useApi<CuentaInversion>('/api/cuenta-inversion', { ejercicio: ej })
  const notas = useNotas()
  if (err) return <ErrorBox err={err} />
  if (!data) return <p>Cargando…</p>
  if (data.estado !== 'ok') return <p className="nodata">No hay Cuenta de Inversión cargada para {ej} (hoy solo 2025).</p>
  const cols: [keyof FilaCI, string][] = [
    ['ingresos_totales', 'Ingresos totales'], ['gastos_totales', 'Gastos totales'], ['intereses', 'Intereses'],
    ['resultado_primario', 'Resultado primario'], ['resultado_financiero', 'Resultado financiero'],
    ['rentas_propiedad', 'de los ingresos: rentas de la propiedad'],
  ]
  const ident = data.identidades ?? {}
  return (
    <>
      <h2>Cuenta Ahorro-Inversión-Financiamiento del SPNF · {ej} <span className="muted">(Cuenta de Inversión, Cuadro 35)</span></h2>
      <p className="scope">Universo: <b>{data.universo}</b> · Base: {data.base} · {data.unidad}.</p>
      <p className="warn">⚠ {data.advertencia}</p>
      <div className="tablewrap"><table>
        <thead><tr><th>Subsector</th>{cols.map(([, l]) => <th key={l}>{l}</th>)}</tr></thead>
        <tbody>{data.filas!.map(f => (
          <tr key={f.subsector} className={f.subsector.startsWith('total') ? 'grp' : ''}>
            <td className={['adm_central', 'org_descentralizados', 'inst_seguridad_social'].includes(f.subsector) ? 'indent' : ''}>
              {f.subsector.startsWith('total') ? <b>{f.nombre}</b> : f.nombre}</td>
            {cols.map(([k]) => {
              const v = f[k]
              return <td key={k} className="num">{v === null ? '—' : fmtExacto(v)}</td>
            })}
          </tr>))}
        </tbody>
      </table></div>
      <p className="note">Resultado primario = resultado financiero + intereses. La fila de eliminaciones resta las
        transferencias y contribuciones figurativas entre subsectores (no cambia ningún resultado). "—" = celda vacía en el original.</p>
      <h3>Integridad del archivo oficial</h3>
      <p className={ident.discrepa ? 'warn' : 'ok'}>
        {ident.coincide ?? 0} identidades contables y de consolidación coinciden
        {ident.discrepa ? `; ${ident.discrepa} discrepan (se informan, no se corrigen)` : ''}.</p>
      <ConciliacionPrefijo prefix={`ci35:${ej}:`} soloMalas />
      {!!data.celdas_con_error?.length && (
        <p className="warn">⚠ Celdas con error de fórmula en el archivo publicado (se guardan sin valor):{' '}
          {data.celdas_con_error.map(c => `${c.celda} (${c.concepto.replace(/^[.\s-]+/, '')}, ${c.subsector}: ${c.importe_original})`).join(' · ')}</p>)}
      <h3>Criterios de la fuente</h3>
      <NotasRef ids={data.notas ?? []} notas={notas} />
      <details><summary>Procedencia</summary><ProvList prov={data.procedencia} /></details>
    </>
  )
}

function ConciliacionPrefijo({ prefix, soloMalas = false }: { prefix: string; soloMalas?: boolean }) {
  const { data } = useApi<Rec[]>('/api/reconciliation', { prefix })
  const rows = (data ?? []).filter(r => !soloMalas || r.conclusion !== 'coincide')
  if (!rows.length) return null
  return <RecTable recs={rows.map(r => ({ ...r, comparacion: r.comparacion.slice(prefix.length) }))} />
}

function CruceCI({ ej }: { ej: number }) {
  const { data } = useApi<Rec[]>('/api/reconciliation', { prefix: `cruce:${ej}:` })
  if (!data?.length) return null
  const ok = data.every(r => r.conclusion === 'coincide')
  return (
    <>
      <h3>Cruce con la Cuenta de Inversión (cierre oficial)</h3>
      <p className={ok ? 'ok' : 'warn'}>{ok
        ? '✓ El detalle de Presupuesto Abierto coincide con la Cuenta de Inversión: es el cierre. Si la fila de totales difiere, es un corte anterior.'
        : '⚠ El detalle de Presupuesto Abierto no coincide con la Cuenta de Inversión.'}</p>
      <RecTable recs={data.map(r => ({ ...r, comparacion: r.comparacion.slice(`cruce:${ej}:`.length) }))} />
    </>
  )
}

function Inicio({ ej }: { ej: number }) {
  const { data, err } = useApi<Summary>('/api/summary', { ejercicio: ej })
  const bad = data?.conciliacion.filter(r => r.conclusion !== 'coincide') ?? []
  const hasAN = data?.cards.some(c => c.estado === 'ok')
  return (
    <>
      <h2>Balance fiscal oficial</h2>
      <BalanceView ej={ej} />
      <p className="note">¿Por qué este resultado difiere del de la Administración Nacional de más abajo? Ver la pestaña
        {' '}<a href={`#puente/${ej}`}>Puente AN → IMIG</a>: cada diferencia está cuantificada con cifras oficiales.</p>
      <h2>Detalle presupuestario de la Administración Nacional</h2>
      {err && <ErrorBox err={err} />}
      {data && !hasAN && <p className="nodata">No hay ejecución presupuestaria cargada para {ej}.</p>}
      {data && hasAN && (
        <>
          <p className="scope">Universo: <b>{data.universo}</b> (sin empresas públicas, fondos fiduciarios fuera del
            presupuesto, PAMI, provincias ni municipios). Recursos percibidos y gastos devengados: <b>no</b> es el
            resultado oficial y no se compara directamente con el balance de arriba.</p>
          <div className="cards">{data.cards.map(c => <CardView key={c.etiqueta} c={c} />)}</div>
          <h3>Conciliación contra totales publicados</h3>
          {bad.length === 0
            ? <p className="ok">Las 9 medidas coinciden exactamente con <code>totales-de-presupuesto.csv</code>.</p>
            : <p className="warn">{bad.length} de {data.conciliacion.length} comparaciones no coinciden o no tienen dato. Ver detalle.</p>}
          <RecTable recs={data.conciliacion} />
          <CruceCI ej={ej} />
        </>)}
    </>
  )
}

function RecTable({ recs }: { recs: Summary['conciliacion'] }) {
  return (
    <div className="tablewrap"><table>
      <thead><tr><th>Comparación</th><th>Calculado</th><th>Publicado</th><th>Diferencia</th><th>Resultado</th></tr></thead>
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
    <>
    <h2>Criterios contables y cambios metodológicos</h2>
    <Metodologia />
    <h2>Datasets cargados</h2>
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
    </>
  )
}

export default function App() {
  // #pestaña o #pestaña/ejercicio (enlace compartible)
  const fromHash = () => {
    const [t, y] = window.location.hash.slice(1).split('/')
    return { tab: TABS.find(([k]) => k === t)?.[0] ?? 'recorrido', ej: y && /^\d{4}$/.test(y) ? Number(y) : null }
  }
  const [tab, setTabState] = useState<Tab>(() => fromHash().tab)
  const [ej, setEjState] = useState<number | null>(() => fromHash().ej)
  const setTab = (t: Tab) => { window.location.hash = CON_EJERCICIO.includes(t) && ej ? `${t}/${ej}` : t; setTabState(t) }
  const setEj = (y: number) => { window.location.hash = `${tab}/${y}`; setEjState(y) }
  useEffect(() => {
    const h = () => { const f = fromHash(); setTabState(f.tab); if (f.ej) setEjState(f.ej) }
    window.addEventListener('hashchange', h)
    return () => window.removeEventListener('hashchange', h)
  }, [])
  const { data: ejs } = useApi<number[]>('/api/ejercicios', {})
  const ejercicio = ej ?? ejs?.[0] ?? null
  return (
    <div className="app">
      <header>
        <h1>Observatorio del Dinero Público Argentino</h1>
        <p className="badge">Datos reales · copia local · fase 0</p>
      </header>
      <nav>
        {TABS.map(([t, l]) => <button key={t} className={t === tab ? 'active' : ''} onClick={() => setTab(t)}>{l}</button>)}
        {CON_EJERCICIO.includes(tab) && ejs && (
          <select value={ejercicio ?? ''} onChange={e => setEj(Number(e.target.value))}>
            {ejs.map(y => <option key={y} value={y}>Ejercicio {y}</option>)}
          </select>)}
      </nav>
      <main>
        {tab === 'evolucion' ? <Evolucion /> : tab === 'fuentes' ? <Fuentes />
          : ejercicio === null ? <p className="nodata">No hay datos cargados. Ejecutá la sincronización (ver README).</p>
          : tab === 'recorrido' ? <Recorrido ej={ejercicio} onEj={setEj} />
          : tab === 'inicio' ? <Inicio ej={ejercicio} /> : tab === 'puente' ? <BridgeView ej={ejercicio} onEj={setEj} />
          : tab === 'cuenta' ? <CuentaInversionView ej={ejercicio} /> : <Destinos ej={ejercicio} />}
      </main>
      <footer>Cifras en pesos corrientes salvo indicación. Cada valor enlaza a su archivo oficial.
        Las descomposiciones por clasificador no son pagos rastreados a destinatarios.</footer>
    </div>
  )
}
