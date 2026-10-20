import { useEffect, useState } from 'react'
import ReactECharts from 'echarts-for-react'
import {
  get, fmtMillones, fmtExacto, fmtCentavos, fmtPct, fmtInt,
  type Summary, type Breakdown, type Annual, type Prov, type Card, type Balance, type Bridge, type BalLine, fmtVar,
  type Paso, type CuentaInversion, type Nota, type Rec, type FilaCI,
} from './api'

type Tab = 'inicio' | 'puente' | 'cuenta' | 'destinos' | 'evolucion' | 'fuentes'
const TABS: [Tab, string][] = [
  ['inicio', 'Inicio'], ['puente', 'Puente AN → IMIG'], ['cuenta', 'Cuenta de Inversión'],
  ['destinos', 'Destinos'], ['evolucion', 'Evolución'], ['fuentes', 'Fuentes y metodología'],
]
const CON_EJERCICIO: Tab[] = ['inicio', 'puente', 'cuenta', 'destinos']

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

const VERIF: Record<string, [string, string]> = {
  verificada_en_crudo: ['ok', '✓ cita verificada en el archivo oficial descargado'],
  hallazgo_reproducible: ['muted', '◆ hallazgo propio, con procedimiento para reproducirlo'],
  no_encontrada_en_crudo: ['warn', '⚠ la cita no aparece en el archivo descargado'],
  crudo_no_disponible: ['warn', '⚠ sin archivo descargado para verificar la cita'],
}

function NotaView({ n }: { n: Nota }) {
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

function useNotas() {
  return useApi<Nota[]>('/api/metodologia', {}).data ?? []
}

function NotasRef({ ids, notas }: { ids: string[]; notas: Nota[] }) {
  const sel = notas.filter(n => ids.includes(n.nota_id))
  if (!sel.length) return null
  return <>{sel.map(n => <NotaView key={n.nota_id} n={n} />)}</>
}

function Metodologia() {
  const notas = useNotas()
  if (!notas.length) return <p className="nodata">Sin notas cargadas: ejecutá la sincronización.</p>
  return <>{notas.map(n => <NotaView key={n.nota_id} n={n} />)}</>
}

function useDark() {
  const q = '(prefers-color-scheme: dark)'
  const [d, setD] = useState(() => window.matchMedia(q).matches)
  useEffect(() => {
    const m = window.matchMedia(q), h = () => setD(m.matches)
    m.addEventListener('change', h)
    return () => m.removeEventListener('change', h)
  }, [])
  return d
}

/** Cascada: los niveles (puntos) van desde 0; los pasos flotan entre el acumulado anterior y el nuevo. */
function Waterfall({ pasos }: { pasos: Paso[] }) {
  const dark = useDark()
  const C = dark
    ? { up: '#3987e5', down: '#e66767', level: '#a9a8a2', ink: '#e8e8e6', muted: '#a2a5a8', grid: '#3a3a3a', surface: '#212121' }
    : { up: '#2a78d6', down: '#e34948', level: '#5c5b57', ink: '#1d1d1b', muted: '#5f6368', grid: '#e6e6e1', surface: '#ffffff' }
  const B = 1e6  // M$ -> billones
  let prev = 0
  const data = pasos.map((p, i) => {
    const acc = Number(p.acumulado_millones) / B
    const v = Number(p.valor_millones) / B
    const level = p.tipo.startsWith('punto')
    const y0 = level ? 0 : prev, y1 = level ? v : acc
    prev = acc
    return { value: [i, y0, y1], kind: level ? 'level' : v >= 0 ? 'up' : 'down', paso: p }
  })
  const option = {
    animation: false,
    grid: { left: 56, right: 16, top: 40, bottom: 96 },
    tooltip: {
      trigger: 'item', confine: true,
      formatter: (x: { data: { paso: Paso } }) => {
        const p = x.data.paso
        return `<b>${p.concepto}</b><br/>${p.tipo.startsWith('punto') ? 'Nivel' : 'Paso'}: ${fmtExacto(p.valor_millones)}` +
          `<br/>Acumulado: ${fmtExacto(p.acumulado_millones)}<br/><span style="opacity:.75">${p.fuente}</span>`
      },
    },
    xAxis: {
      type: 'category', data: pasos.map(p => p.rotulo), axisTick: { show: false },
      axisLine: { lineStyle: { color: C.grid } },
      axisLabel: { color: C.muted, interval: 0, rotate: 35, fontSize: 11 },
    },
    yAxis: {
      type: 'value', name: 'billones de $', nameTextStyle: { color: C.muted },
      axisLabel: { color: C.muted }, splitLine: { lineStyle: { color: C.grid } },
    },
    series: [{
      type: 'custom', data,
      renderItem: (_: unknown, api: { value: (d: number) => number; coord: (v: number[]) => number[]; size: (v: number[]) => number[] }) => {
        const i = api.value(0), a = api.coord([i, api.value(1)]), b = api.coord([i, api.value(2)])
        const w = api.size([1, 0])[0] * 0.6
        const kind = data[i].kind
        const top = Math.min(a[1], b[1]), h = Math.max(Math.abs(a[1] - b[1]), 1)
        return {
          type: 'rect', shape: { x: a[0] - w / 2, y: top, width: w, height: h, r: 3 },
          style: { fill: C[kind as 'up' | 'down' | 'level'], stroke: C.surface, lineWidth: 2 },
        }
      },
      label: { show: false },
    }, {
      // rótulos de valor sólo en los niveles: los pasos se leen en la tabla
      type: 'scatter', symbolSize: 0, silent: true,
      data: data.map(d => d.kind === 'level' ? [d.value[0], d.value[2]] : [d.value[0], NaN]),
      label: {
        show: true, position: 'top', color: C.ink, fontSize: 11,
        formatter: (x: { value: number[] }) => Number.isNaN(x.value[1]) ? '' : x.value[1].toLocaleString('es-AR', { maximumFractionDigits: 2 }),
      },
    }],
  }
  return <ReactECharts option={option} style={{ height: 380 }} notMerge />
}

function BridgeView({ ej }: { ej: number }) {
  const { data, err } = useApi<Bridge>('/api/bridge', { ejercicio: ej })
  const notas = useNotas()
  const [res, setRes] = useState<'resultado_primario' | 'resultado_financiero'>('resultado_primario')
  if (err) return <ErrorBox err={err} />
  if (!data) return <p>Cargando…</p>
  if (data.estado !== 'ok') return (
    <>
      <p className="nodata">{data.motivo}</p>
      {data.faltan && <p className="note">Falta: {data.faltan.join(' · ')}.</p>}
    </>)
  const pasos = data[res]!
  const malos = data.controles!.filter(c => c.estado !== 'coincide')
  const notaIds = [...new Set(pasos.flatMap(p => p.notas))]
  return (
    <>
      <h2>Del resultado de la Administración Nacional al resultado oficial base caja · {ej}</h2>
      <p className="scope">Punto de partida: <b>Administración Nacional</b>, recursos percibidos y gastos devengados
        (Presupuesto Abierto, cierre). Punto de llegada: <b>Sector Público Nacional, base caja</b> (IMIG). Son universos
        y metodologías distintos; el puente muestra cada diferencia con su fuente.</p>
      <div className="controls">
        <select value={res} onChange={e => setRes(e.target.value as typeof res)}>
          <option value="resultado_primario">Resultado primario</option>
          <option value="resultado_financiero">Resultado financiero</option>
        </select>
      </div>
      <Waterfall pasos={pasos} />
      <p className="note">Gris: niveles (cifras de una fuente). Azul: pasos que suman. Rojo: pasos que restan.
        Valores en billones de pesos corrientes.</p>
      <div className="tablewrap"><table>
        <thead><tr><th>#</th><th>Paso</th><th>Tipo</th><th>Importe (M$)</th><th>Acumulado (M$)</th><th>Fuente</th></tr></thead>
        <tbody>{pasos.map((p, i) => (
          <tr key={i} className={p.tipo.startsWith('punto') ? 'grp' : ''}>
            <td>{i + 1}</td>
            <td>{p.concepto}<br /><span className="muted">{p.categoria}{p.universo && ` · ${p.universo}, ${p.base}`}</span>
              {p.advertencia && <div className="warn">⚠ {p.advertencia}</div>}</td>
            <td><span className={p.tipo === 'residual' ? 'warn' : 'muted'}>{data.tipos![p.tipo]}</span></td>
            <td className="num">{fmtExacto(p.valor_millones)}</td>
            <td className="num">{fmtExacto(p.acumulado_millones)}</td>
            <td>{p.fuente}</td>
          </tr>))}
        </tbody>
      </table></div>
      <h3>Controles entre cifras publicadas por separado</h3>
      <p className={malos.length ? 'warn' : 'ok'}>{malos.length
        ? `⚠ ${malos.length} control(es) no coinciden: el puente se muestra igual, sin ajustar cifras.`
        : `✓ Los ${data.controles!.length} controles coinciden dentro del redondeo de publicación.`}</p>
      <div className="tablewrap"><table>
        <thead><tr><th>Control</th><th>Diferencia (M$)</th><th>Resultado</th></tr></thead>
        <tbody>{data.controles!.map(c => (
          <tr key={c.control}><td>{c.control}{c.nota && <><br /><span className="muted">{c.nota}</span></>}</td>
            <td className="num">{c.diferencia_millones === null ? 'sin datos' : fmtExacto(c.diferencia_millones)}</td>
            <td className={c.estado === 'coincide' ? 'ok' : 'warn'}>{c.estado}</td></tr>))}
        </tbody>
      </table></div>
      <h3>Rentas de la propiedad según cada fuente</h3>
      <p className="note">Cinco cifras distintas para "rentas de la propiedad" 2025: cada una corresponde a otro universo,
        otra base o otro corte. No se suman ni se restan entre sí fuera del puente.</p>
      <div className="tablewrap"><table>
        <thead><tr><th>Fuente</th><th>Universo</th><th>Base</th><th>Importe (M$)</th></tr></thead>
        <tbody>{data.comparacion_rentas!.map((r, i) => (
          <tr key={i}><td>{r.fuente}{r.nota && <><br /><span className="muted">{r.nota}</span></>}</td>
            <td>{r.universo}</td><td>{r.base}</td><td className="num">{fmtExacto(r.valor_millones)}</td></tr>))}
        </tbody>
      </table></div>
      <h3>Criterios que explican los pasos</h3>
      <NotasRef ids={notaIds} notas={notas} />
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
    return { tab: TABS.find(([k]) => k === t)?.[0] ?? 'inicio', ej: y && /^\d{4}$/.test(y) ? Number(y) : null }
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
          : tab === 'inicio' ? <Inicio ej={ejercicio} /> : tab === 'puente' ? <BridgeView ej={ejercicio} />
          : tab === 'cuenta' ? <CuentaInversionView ej={ejercicio} /> : <Destinos ej={ejercicio} />}
      </main>
      <footer>Cifras en pesos corrientes salvo indicación. Cada valor enlaza a su archivo oficial.
        Las descomposiciones por clasificador no son pagos rastreados a destinatarios.</footer>
    </div>
  )
}
