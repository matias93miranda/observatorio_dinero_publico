import { useEffect, useState } from 'react'
import ReactECharts from 'echarts-for-react'
import { fmtCorto, fmtExacto, type Bridge, type Historico, type Paso } from './api'
import { useApi, ErrorBox, ProvList, NotasRef, useNotas, useDark, chartColors, useReducedMotion, FONT } from './comun'
import { G } from './glosario'

/** Explicación en lenguaje llano de cada paso, por rótulo corto (ver puente.ROTULOS en el backend). */
const EXPLICA: Record<string, React.ReactNode> = {
  'AN cierre': <>Partimos del resultado de la <G t="an" /> en el Presupuesto: lo que cobró (<G t="percibido" />) menos lo que
    gastó (<G t="devengado" />). Este es el cierre: coincide con la Cuenta de Inversión de la Contaduría General.</>,
  'AN (PA)': <>Partimos del resultado de la <G t="an" /> según el detalle de Presupuesto Abierto: lo que cobró
    (<G t="percibido" />) menos lo que gastó (<G t="devengado" />). Para este año no está cargada la Cuenta de Inversión,
    así que no se afirma que sea el cierre definitivo.</>,
  'Revisión de corte': <>El Boletín Fiscal se publica con datos provisorios y Presupuesto Abierto es un corte posterior.
    Esta barra es la <b>revisión entre dos publicaciones</b>: no es un ingreso ni un gasto nuevo.</>,
  'AN provisorio': <>El mismo resultado de la Administración Nacional, según el corte provisorio del Boletín Fiscal.</>,
  'Base caja (residual)': <>El resultado oficial se mide en <G t="caja" />: cuenta el dinero cuando entra o sale de verdad,
    no cuando se reconoce la deuda. Esta diferencia (y otras de registro) <b>no se puede abrir</b> con lo que se publica:
    por eso se muestra como residual, sin repartirla.</>,
  'AN caja': <>El resultado de la Administración Nacional medido en caja, todavía con todas las rentas.</>,
  '− Rentas BCRA': <>Las <G t="rentas" /> que transfiere el <G t="bcra" /> (por ejemplo, sus utilidades) se restan: desde
    2017 la metodología oficial no las cuenta como ingreso del resultado.</>,
  '− Rentas FGS': <>El <G t="fgs" /> cobra intereses de bonos del propio Estado. Es un pago entre organismos públicos
    (<G t="intra" />), así que también se resta.</>,
  '+ Intereses intra-SP': <>Por la misma razón, los intereses que el Tesoro le paga a otros organismos públicos no se cuentan
    como gasto: se suman de vuelta.</>,
  'AN caja s/rentas': <>El resultado de la Administración Nacional con la metodología oficial: en caja y sin esas rentas.</>,
  '+ Resto SPN': <>El resultado oficial abarca más que la Administración Nacional: suma PAMI, fondos fiduciarios, otros
    entes y el resultado operativo de las empresas públicas (el <G t="spn" />).</>,
  'SPN caja (IMIG)': <>Llegada: el resultado oficial del Sector Público Nacional que publica la Secretaría de Hacienda
    (<G t="imig" />). Se controla contra la suma de los 12 informes mensuales (ver controles).</>,
}

const TIPO_CORTO: Record<string, string> = {
  punto_calculado: 'calculado de los archivos', punto_publicado: 'cifra publicada', punto_derivado: 'suma de publicadas',
  ajuste_publicado: 'ajuste publicado', diferencia_derivada: 'revisión entre cortes', residual: 'residual sin abrir',
}

/** Cascada animada: los pasos posteriores a `k` quedan como sombra; el paso `k` se resalta. */
function Waterfall({ pasos, k, factor, onPick }: { pasos: Paso[]; k: number; factor: number; onPick: (i: number) => void }) {
  const dark = useDark(), C = chartColors(dark), quieto = useReducedMotion()
  const B = 1e6 / factor  // M$ -> billones (con factor real)
  let prev = 0
  const data = pasos.map((p, i) => {
    const acc = Number(p.acumulado_millones) / B, v = Number(p.valor_millones) / B
    const level = p.tipo.startsWith('punto')
    const y0 = level ? 0 : prev, y1 = level ? v : acc
    prev = acc
    return { value: [i, y0, y1], kind: level ? 'level' : v >= 0 ? 'up' : 'down' }
  })
  const fmt = (x: number) => x.toLocaleString('es-AR', { maximumFractionDigits: 2 })
  const option = {
    animation: !quieto, textStyle: { fontFamily: FONT }, animationDurationUpdate: 450,
    grid: { left: 52, right: 12, top: 36, bottom: 92 },
    tooltip: {
      trigger: 'item', confine: true,
      formatter: (x: { dataIndex: number }) => {
        const p = pasos[x.dataIndex]
        return `<b>${p.concepto}</b><br/>${fmtExacto(p.valor_millones)} (pesos corrientes)<br/><i>Clic para ir a este paso</i>`
      },
    },
    xAxis: {
      type: 'category', data: pasos.map(p => p.rotulo), axisTick: { show: false },
      axisLine: { lineStyle: { color: C.grid } },
      axisLabel: { interval: 0, rotate: 35, fontSize: 11,
        color: (_: string, i: number) => (i === k ? C.ink : C.muted), fontWeight: (_: string, i: number) => (i === k ? 'bold' : 'normal') },
    },
    yAxis: { type: 'value', name: 'billones de $', nameTextStyle: { color: C.muted },
      axisLabel: { color: C.muted }, splitLine: { lineStyle: { color: C.grid } } },
    series: [{
      type: 'custom', data, cursor: 'pointer',
      renderItem: (_: unknown, api: { value: (d: number) => number; coord: (v: number[]) => number[]; size: (v: number[]) => number[] }) => {
        const i = api.value(0), a = api.coord([i, api.value(1)]), b = api.coord([i, api.value(2)])
        const w = api.size([1, 0])[0] * 0.62
        const top = Math.min(a[1], b[1]), h = Math.max(Math.abs(a[1] - b[1]), 2)
        const futuro = i > k, actual = i === k
        return {
          type: 'rect', shape: { x: a[0] - w / 2, y: top, width: w, height: h, r: 4 },
          style: { fill: C[data[i].kind as 'up' | 'down' | 'level'], opacity: futuro ? 0.12 : 1,
            stroke: actual ? C.ink : C.surface, lineWidth: 2 },
          transition: ['shape', 'style'],
        }
      },
    }, {
      type: 'scatter', symbolSize: 0, silent: true,
      data: data.map((d, i) => (i <= k && (d.kind === 'level' || i === k)) ? [i, d.value[2]] : [i, NaN]),
      label: { show: true, position: 'top', color: C.ink, fontSize: 11,
        formatter: (x: { value: number[]; dataIndex: number }) => Number.isNaN(x.value[1]) ? ''
          : data[x.dataIndex].kind === 'level' ? fmt(x.value[1]) : `${data[x.dataIndex].kind === 'up' ? '+' : '−'}${fmt(Math.abs(x.value[1] - x.value[0]))}` },
    }],
  }
  return <ReactECharts option={option} style={{ height: 400 }} onEvents={{ click: (e: { dataIndex: number }) => onPick(e.dataIndex) }} />
}

function Historia({ hist, res, real, ej, onEj }: {
  hist: Historico; res: 'resultado_primario' | 'resultado_financiero'; real: boolean; ej: number; onEj: (y: number) => void
}) {
  const dark = useDark(), C = chartColors(dark), quieto = useReducedMotion()
  const filas = hist.ejercicios.filter(f => f.estado === 'ok' && (!real || f.deflactor))
  const claves = Object.keys(hist.componentes).filter(c => filas.some(f => f[res]!.componentes[c] !== null))
  const colores = C.series
  const val = (v: string | null | undefined, f: (typeof filas)[number]) =>
    v == null ? null : Number(v) * (real ? Number(f.deflactor!.factor) : 1) / 1e6
  const nf = new Intl.NumberFormat('es-AR', { maximumFractionDigits: 2, minimumFractionDigits: 2 })
  const unidad = real && filas[0]?.deflactor ? `billones de pesos promedio de ${filas[0].deflactor.base}` : 'billones de pesos corrientes'
  return (
    <>
      <h3>Nueve años de puente: qué explica la diferencia cada año</h3>
      <p className="note">Cada barra apila los pasos que llevan del resultado de la Administración Nacional al oficial
        ({unidad}). Arriba de cero suman, abajo restan; el rombo es la diferencia total. Tocá un año para verlo en la cascada.</p>
      <ReactECharts style={{ height: 380 }} onEvents={{ click: (e: { dataIndex: number }) => onEj(filas[e.dataIndex].ejercicio) }}
        option={{
          animation: !quieto, textStyle: { fontFamily: FONT },
          legend: { top: 0, textStyle: { color: C.ink }, type: 'scroll' },
          grid: { left: 52, right: 12, top: 40, bottom: 28 },
          tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, confine: true,
            valueFormatter: (v: number | null) => (v == null ? 'sin datos' : `${nf.format(v)} billones`) },
          xAxis: { type: 'category', data: filas.map(f => String(f.ejercicio)), axisTick: { show: false },
            axisLabel: { color: (s: string) => (Number(s) === ej ? C.ink : C.muted), fontWeight: (s: string) => (Number(s) === ej ? 'bold' : 'normal') },
            axisLine: { lineStyle: { color: C.grid } } },
          yAxis: { type: 'value', axisLabel: { color: C.muted }, splitLine: { lineStyle: { color: C.grid } } },
          series: [
            ...claves.map((c, i) => ({
              name: hist.componentes[c], type: 'bar', stack: 'p', stackStrategy: 'samesign', barMaxWidth: 34, cursor: 'pointer',
              itemStyle: { color: colores[i], borderColor: C.surface, borderWidth: 1 },
              emphasis: { focus: 'series' },
              data: filas.map(f => ({ value: val(f[res]!.componentes[c], f), itemStyle: { opacity: f.ejercicio === ej ? 1 : 0.6 } })),
            })),
            { name: 'Diferencia total', type: 'scatter', symbol: 'diamond', symbolSize: 12, z: 5,
              itemStyle: { color: C.ink, borderColor: C.surface, borderWidth: 2 },
              data: filas.map(f => {
                const a = val(f[res]!.llegada_millones, f), b = val(f[res]!.partida_millones, f)
                return a === null || b === null ? null : a - b
              }) },
          ],
        }} />
      <details>
        <summary>Ver la tabla ({unidad})</summary>
        <div className="tablewrap"><table>
          <thead><tr><th>Ejercicio</th><th>Partida AN</th>{claves.map(c => <th key={c}>{hist.componentes[c]}</th>)}<th>Oficial (IMIG)</th></tr></thead>
          <tbody>{filas.map(f => (
            <tr key={f.ejercicio} className={f.ejercicio === ej ? 'grp' : ''}>
              <td>{f.ejercicio}{!f.partida_es_cierre && <span className="muted"> *</span>}</td>
              <td className="num">{nf.format(val(f[res]!.partida_millones, f) ?? NaN)}</td>
              {claves.map(c => { const v = val(f[res]!.componentes[c], f); return <td key={c} className="num">{v === null ? '—' : nf.format(v)}</td> })}
              <td className="num"><b>{nf.format(val(f[res]!.llegada_millones, f) ?? NaN)}</b></td>
            </tr>))}
          </tbody>
        </table></div>
        <p className="note">* Partida = detalle de Presupuesto Abierto, sin Cuenta de Inversión que confirme el cierre.
          {real && ' Pesos constantes: mismo factor de IPC promedio anual para todos los pasos de un año (aproximación).'}
          {' '}Cifras exactas en pesos corrientes: en la tabla del puente de cada año.</p>
      </details>
    </>
  )
}

export default function BridgeView({ ej, onEj }: { ej: number; onEj: (y: number) => void }) {
  const { data, err } = useApi<Bridge>('/api/bridge', { ejercicio: ej })
  const { data: hist } = useApi<Historico>('/api/bridge/historico', {})
  const notas = useNotas()
  const [res, setRes] = useState<'resultado_primario' | 'resultado_financiero'>('resultado_primario')
  // Pesos constantes por defecto: en corrientes, la inflación hace que el último año aplaste a los demás.
  const [real, setReal] = useState(true)
  const [k, setK] = useState(0)
  const [play, setPlay] = useState(false)
  const n = data?.[res]?.length ?? 0
  useEffect(() => {
    if (!play) return
    if (k >= n - 1) { setPlay(false); return }
    const t = setTimeout(() => setK(k + 1), 2400)
    return () => clearTimeout(t)
  }, [play, k, n])
  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement)?.tagName === 'INPUT' || (e.target as HTMLElement)?.tagName === 'SELECT') return
      if (e.key === 'ArrowRight') setK(x => Math.min(x + 1, n - 1))
      if (e.key === 'ArrowLeft') setK(x => Math.max(x - 1, 0))
    }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [n])

  const anios = (hist?.ejercicios ?? []).filter(f => f.estado === 'ok').map(f => f.ejercicio)
  const selector = anios.length > 0 && (
    <div className="anio-slider">
      <label htmlFor="anio">Ejercicio <b>{ej}</b></label>
      <input id="anio" type="range" min={anios[0]} max={anios[anios.length - 1]} step={1} list="anios"
        value={Math.min(Math.max(ej, anios[0]), anios[anios.length - 1])} onChange={e => onEj(Number(e.target.value))} />
      <datalist id="anios">{anios.map(y => <option key={y} value={y} />)}</datalist>
      <div className="anio-marcas">{anios.map(y =>
        <button key={y} className={y === ej ? 'activo' : ''} onClick={() => onEj(y)}>{String(y).slice(2)}</button>)}</div>
    </div>)

  if (err) return <ErrorBox err={err} />
  if (!data) return <p>Cargando…</p>
  if (data.estado !== 'ok') return (
    <>
      {selector}
      <p className="nodata">{data.motivo}</p>
      {data.faltan && <p className="note">Falta: {data.faltan.join(' · ')}.</p>}
    </>)
  const pasos = data[res]!
  const kk = Math.min(k, pasos.length - 1)
  const p = pasos[kk]
  const defl = data.deflactor
  const factor = real && defl ? Number(defl.factor) : 1
  const enReal = real && !!defl
  const malos = data.controles!.filter(c => c.estado !== 'coincide')
  const notaIds = [...new Set(pasos.flatMap(x => x.notas))]
  const v = Number(p.valor_millones) * factor
  const nivel = p.tipo.startsWith('punto')
  return (
    <>
      <h2>Del resultado del Presupuesto al resultado oficial · {ej}</h2>
      <p className="scope">Dos cifras oficiales distintas para "el resultado": la de la <G t="an" /> (Presupuesto) y la del
        {' '}<G t="spn" /> en <G t="caja" /> (<G t="imig" />). No es un error: miden universos y momentos distintos. El puente
        recorre cada diferencia con su fuente. Usá ◀ ▶ (o las flechas del teclado) o tocá una barra.</p>
      <div className="puente-controles">
        {selector}
        <div className="segmentado" role="group" aria-label="Resultado">
          <button className={res === 'resultado_primario' ? 'activo' : ''} onClick={() => setRes('resultado_primario')}>Primario</button>
          <button className={res === 'resultado_financiero' ? 'activo' : ''} onClick={() => setRes('resultado_financiero')}>Financiero</button>
        </div>
        <div className="segmentado" role="group" aria-label="Unidad">
          <button className={!enReal ? 'activo' : ''} onClick={() => setReal(false)}>Pesos corrientes</button>
          <button className={enReal ? 'activo' : ''} disabled={!defl} onClick={() => setReal(true)}
            title={defl ? defl.metodo : 'Sin IPC completo para este año'}>Pesos de {defl?.base ?? '—'}</button>
        </div>
      </div>
      <div className="puente-grid">
        <div className="puente-chart">
          <Waterfall pasos={pasos} k={kk} factor={factor} onPick={i => { setPlay(false); setK(i) }} />
          <div className="progreso" aria-hidden>{pasos.map((_, i) =>
            <span key={i} className={i < kk ? 'hecho' : i === kk ? 'activo' : ''} onClick={() => { setPlay(false); setK(i) }} />)}</div>
        </div>
        <aside className="explica" aria-live="polite">
          <div className="explica-paso">Paso {kk + 1} de {pasos.length} · <span className={p.tipo === 'residual' ? 'warn' : 'muted'}>{TIPO_CORTO[p.tipo] ?? p.tipo}</span></div>
          <h3>{p.rotulo}</h3>
          <div className={'explica-valor ' + (nivel ? '' : v >= 0 ? 'sube' : 'baja')}>
            {nivel ? fmtCorto(v) : `${v >= 0 ? '+' : ''}${fmtCorto(v)}`}
          </div>
          {enReal && <div className="muted explica-unidad">en pesos promedio de {defl!.base} (aprox.)</div>}
          <p>{EXPLICA[p.rotulo] ?? p.concepto}</p>
          <p className="note">Fuente: {p.fuente}{p.advertencia && <span className="warn"> · ⚠ {p.advertencia}</span>}</p>
          <div className="explica-botones">
            <button onClick={() => { setPlay(false); setK(Math.max(kk - 1, 0)) }} disabled={kk === 0} aria-label="Paso anterior">◀</button>
            <button className="primario" onClick={() => { if (kk >= pasos.length - 1) setK(0); setPlay(!play) }}>
              {play ? '⏸ Pausa' : kk >= pasos.length - 1 ? '↺ Repetir' : '▶ Reproducir'}</button>
            <button onClick={() => { setPlay(false); setK(Math.min(kk + 1, pasos.length - 1)) }} disabled={kk === pasos.length - 1} aria-label="Paso siguiente">▶</button>
            <button className="link" onClick={() => { setPlay(false); setK(pasos.length - 1) }}>ver todo</button>
          </div>
        </aside>
      </div>
      <p className="note">Gris: niveles (una cifra de una fuente). Azul: pasos que suman. Rojo: pasos que restan.
        {real && defl && ` Pesos de ${defl.base}: ${defl.metodo}`}</p>

      {hist && <Historia hist={hist} res={res} real={real} ej={ej} onEj={onEj} />}

      <details>
        <summary>Tabla del puente {ej} con cifras exactas (pesos corrientes)</summary>
        <div className="tablewrap"><table>
          <thead><tr><th>#</th><th>Paso</th><th>Tipo</th><th>Importe (M$)</th><th>Acumulado (M$)</th><th>Fuente</th></tr></thead>
          <tbody>{pasos.map((x, i) => (
            <tr key={i} className={x.tipo.startsWith('punto') ? 'grp' : ''}>
              <td>{i + 1}</td>
              <td>{x.concepto}<br /><span className="muted">{x.categoria}{x.universo && ` · ${x.universo}, ${x.base}`}</span>
                {x.advertencia && <div className="warn">⚠ {x.advertencia}</div>}</td>
              <td><span className={x.tipo === 'residual' ? 'warn' : 'muted'}>{data.tipos![x.tipo]}</span></td>
              <td className="num">{fmtExacto(x.valor_millones)}</td>
              <td className="num">{fmtExacto(x.acumulado_millones)}</td>
              <td>{x.fuente}</td>
            </tr>))}
          </tbody>
        </table></div>
      </details>

      <h3>Controles entre cifras publicadas por separado</h3>
      <p className={malos.length ? 'warn' : 'ok'}>{malos.length
        ? `⚠ ${malos.length} de ${data.controles!.length} controles no coinciden: se informan, sin ajustar cifras.`
        : `✓ Los ${data.controles!.length} controles coinciden dentro del redondeo de publicación.`}</p>
      <details open={malos.length > 0}>
        <summary>Ver controles</summary>
        <div className="tablewrap"><table>
          <thead><tr><th>Control</th><th>Diferencia (M$)</th><th>Resultado</th></tr></thead>
          <tbody>{data.controles!.map(c => (
            <tr key={c.control}><td>{c.control}{c.nota && <><br /><span className="muted">{c.nota}</span></>}</td>
              <td className="num">{c.diferencia_millones === null ? 'sin datos' : fmtExacto(c.diferencia_millones)}</td>
              <td className={c.estado === 'coincide' ? 'ok' : 'warn'}>{c.estado === 'coincide' ? '✓ coincide' : '⚠ ' + c.estado}</td></tr>))}
          </tbody>
        </table></div>
      </details>

      <details>
        <summary>Rentas de la propiedad según cada fuente</summary>
        <p className="note">Cinco cifras distintas para "rentas de la propiedad" {ej}: cada una corresponde a otro universo,
          otra base o otro corte. No se suman ni se restan entre sí fuera del puente.</p>
        <div className="tablewrap"><table>
          <thead><tr><th>Fuente</th><th>Universo</th><th>Base</th><th>Importe (M$)</th></tr></thead>
          <tbody>{data.comparacion_rentas!.map((r, i) => (
            <tr key={i}><td>{r.fuente}{r.nota && <><br /><span className="muted">{r.nota}</span></>}</td>
              <td>{r.universo}</td><td>{r.base}</td><td className="num">{fmtExacto(r.valor_millones)}</td></tr>))}
          </tbody>
        </table></div>
      </details>
      <h3>Criterios que explican los pasos</h3>
      <NotasRef ids={notaIds} notas={notas} />
      <details><summary>Procedencia</summary><ProvList prov={data.procedencia} /></details>
    </>
  )
}
