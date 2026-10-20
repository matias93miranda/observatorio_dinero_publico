import { useEffect, useRef, useState } from 'react'
import ReactECharts from 'echarts-for-react'
import { fmtCorto, type Balance, type BalLine, type Historico } from './api'
import { useApi, ErrorBox, useDark, chartColors, useReducedMotion, FONT } from './comun'
import { G } from './glosario'
import { GRUPO, explicaLinea } from './explicaciones'

/** "de cada $100": proporción redondeada; lo que no llega a 1 se dice así, nunca como 0. */
function deCada100(v: number, total: number): string {
  const x = (v / total) * 100
  return x > 0 && x < 0.5 ? 'menos de 1' : String(Math.round(x))
}

/** Texto legible sobre un color de serie (claro u oscuro según la luminancia del fondo). */
function tinta(hex: string): string {
  const [r, g, b] = [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16) / 255)
  return 0.2126 * r + 0.7152 * g + 0.0722 * b > 0.45 ? '#0b0b0b' : '#ffffff'
}

type Cat = { key: string; nombre: string; corto: string; que: string; valor: number; color: string; detalle: BalLine[] }

/** Categorías como partes de 100: una barra (en orden fijo, para que el color siga a la categoría)
 * y tarjetas ordenadas por tamaño. Tocar una abre su explicación. */
function Mapa({ cats, sel, onSel, verbo }: { cats: Cat[]; sel: string | null; onSel: (k: string | null) => void; verbo: string }) {
  const total = cats.reduce((t, c) => t + c.valor, 0)
  const porTam = [...cats].sort((a, b) => b.valor - a.valor)
  return (
    <>
      <div className="mapa-barra" role="list">
        {cats.map(c => {
          const p = (c.valor / total) * 100
          return (
            <button key={c.key} role="listitem" className={sel && sel !== c.key ? 'atenuada' : ''}
              style={{ flexBasis: `${p}%`, background: c.color, color: tinta(c.color) }}
              onClick={() => onSel(sel === c.key ? null : c.key)} title={`${c.corto}: ${deCada100(c.valor, total)} de cada $100`}>
              {p >= 8 && <span>{deCada100(c.valor, total)}</span>}
            </button>)
        })}
      </div>
      <div className="mapa-cards">
        {porTam.map(c => (
          <button key={c.key} className={'mapa-card' + (sel === c.key ? ' elegida' : sel ? ' atenuada' : '')}
            style={{ borderTopColor: c.color }} onClick={() => onSel(sel === c.key ? null : c.key)} aria-expanded={sel === c.key}>
            <span className="mapa-num">{deCada100(c.valor, total)}</span>
            <span className="mapa-de">de cada $100 {verbo}</span>
            <span className="mapa-nombre"><i style={{ background: c.color }} />{c.corto}</span>
          </button>))}
      </div>
    </>
  )
}

function Detalle({ c, total, periodo, frase, onClose }: { c: Cat; total: number; periodo: string; frase: string; onClose: () => void }) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => { ref.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' }) }, [c.key])
  const sub = c.detalle.filter(d => d.valor_millones !== null && Number(d.valor_millones) !== 0)
  const max = Math.max(...sub.map(d => Number(d.valor_millones)), 1)
  return (
    <div className="detalle-cat" ref={ref} style={{ borderLeftColor: c.color }}>
      <div className="detalle-cab">
        <h3><i style={{ background: c.color }} />{c.corto}</h3>
        <button className="link" onClick={onClose}>cerrar ✕</button>
      </div>
      <p className="detalle-que">{c.que}</p>
      <p className="detalle-frase">{frase.replace('{n}', deCada100(c.valor, total))}</p>
      {sub.length > 1 && <>
        <h4>¿Cómo se reparte?</h4>
        <p className="note">De cada $100 de "{c.corto.toLowerCase()}":</p>
        <ul className="sub-lista">
          {[...sub].sort((a, b) => Number(b.valor_millones) - Number(a.valor_millones)).map(d => {
            const v = Number(d.valor_millones), ex = explicaLinea(d.columna, d.etiqueta)
            return (
              <li key={d.etiqueta}>
                <div className="sub-num">{deCada100(v, c.valor)}</div>
                <div className="sub-cuerpo">
                  <div className="sub-nombre">{d.etiqueta}</div>
                  <span className="sub-barra" style={{ width: `${Math.max((v / max) * 100, 1)}%`, background: c.color }} />
                  {ex && <div className="sub-ex">{ex}</div>}
                </div>
              </li>)
          })}
        </ul>
      </>}
      <p className="note">Para tener una idea del tamaño: en {periodo} fueron {fmtCorto(c.valor)} en total.
        {' '}"De cada $100" está redondeado: la suma puede no dar exactamente 100.</p>
    </div>
  )
}

function Cuenta({ ing, gas, intr }: { ing: number; gas: number; intr: number }) {
  const C = chartColors(useDark())
  const sale = gas + intr, escala = Math.max(ing, sale)
  const r = ing - sale, w = (v: number) => `${(v / escala) * 100}%`
  const n = (v: number) => deCada100(v, ing)
  return (
    <div className="cuenta">
      <div className="cuenta-fila">
        <span className="cuenta-rot">Entró</span>
        <div className="cuenta-pista"><span style={{ width: w(ing), background: C.series[0], color: tinta(C.series[0]) }}>100</span></div>
      </div>
      <div className="cuenta-fila">
        <span className="cuenta-rot">Salió</span>
        <div className="cuenta-pista">
          <span style={{ width: w(gas), background: C.level, color: tinta(C.level) }}>{n(gas)}</span>
          <span style={{ width: w(intr), background: C.series[6], color: tinta(C.series[6]) }}>{n(intr)}</span>
        </div>
      </div>
      <div className="cuenta-ley">
        <span><i style={{ background: C.series[0] }} />Ingresos</span>
        <span><i style={{ background: C.level }} />Gastos (sin intereses)</span>
        <span><i style={{ background: C.series[6] }} />Intereses de la deuda</span>
      </div>
      <p className="cuenta-txt">De cada <b>$100</b> que entraron, <b>${n(gas)}</b> se fueron en gastos y <b>${n(intr)}</b> en
        intereses de la deuda. {r >= 0
          ? <>Sobraron <b>${n(r)}</b>.</>
          : <>Faltaron <b>${n(-r)}</b>, que se cubrieron pidiendo prestado u otras fuentes (<G t="financiero">déficit</G>).</>}</p>
    </div>
  )
}

function Historia({ hist, ej, onEj }: { hist: Historico; ej: number; onEj: (y: number) => void }) {
  const dark = useDark(), C = chartColors(dark), quieto = useReducedMotion()
  const filas = hist.ejercicios.filter(f => f.estado === 'ok' && f.ingresos_imig_millones)
  if (!filas.length) return null
  const rel = (v: string | null | undefined, ing: string) => (v == null ? null : Math.round((Number(v) / Number(ing)) * 1000) / 10)
  const serie = (k: 'resultado_primario' | 'resultado_financiero', i: number, nombre: string) => ({
    name: nombre, type: 'bar', barGap: '10%', barMaxWidth: 26, cursor: 'pointer',
    itemStyle: { color: C.series[i], borderRadius: 3 },
    data: filas.map(f => ({ value: rel(f[k]!.llegada_millones, f.ingresos_imig_millones!), itemStyle: { opacity: f.ejercicio === ej ? 1 : 0.45 } })),
  })
  return (
    <div className="comp">
      <h3>¿Sobró o faltó? Año por año <span className="muted">· por cada $100 que entraron · tocá un año</span></h3>
      <ReactECharts style={{ height: 300 }}
        onEvents={{ click: (e: { dataIndex: number }) => onEj(filas[e.dataIndex].ejercicio) }}
        option={{
          animation: !quieto, textStyle: { fontFamily: FONT },
          legend: { top: 0, textStyle: { color: C.ink } },
          grid: { left: 40, right: 12, top: 36, bottom: 28 },
          tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, valueFormatter: (v: number | null) =>
            v == null ? 'sin datos' : `${v > 0 ? 'sobraron' : 'faltaron'} $${Math.abs(v).toLocaleString('es-AR')} por cada $100` },
          xAxis: { type: 'category', data: filas.map(f => String(f.ejercicio)), axisTick: { show: false },
            axisLabel: { color: (s: string) => (Number(s) === ej ? C.ink : C.muted), fontWeight: (s: string) => (Number(s) === ej ? 'bold' : 'normal') },
            axisLine: { lineStyle: { color: C.grid } } },
          yAxis: { type: 'value', axisLabel: { color: C.muted, formatter: (v: number) => `$${v}` }, splitLine: { lineStyle: { color: C.grid } } },
          series: [serie('resultado_primario', 0, 'Antes de pagar intereses'), serie('resultado_financiero', 1, 'Después de pagar intereses')],
        }} />
      <p className="note">Arriba de cero: sobró. Abajo: faltó. Resultado <G t="primario">primario</G> y <G t="financiero">financiero</G>
        {' '}del Sector Público Nacional (IMIG) dividido por sus ingresos del mismo año: al ser una proporción, se puede comparar
        entre años sin ajustar por inflación.</p>
    </div>
  )
}

const PASOS = [
  ['¿De dónde sale la plata?', 'Ingresos'],
  ['¿En qué se gasta?', 'Gastos'],
  ['¿Alcanza?', 'Resultado'],
] as const

export default function Recorrido({ ej, onEj }: { ej: number; onEj: (y: number) => void }) {
  // #recorrido/AAAA/N abre directamente el paso N (enlace compartible)
  const [paso, setPasoState] = useState(() => {
    const n = Number(window.location.hash.split('/')[2])
    return n >= 1 && n <= PASOS.length ? n - 1 : 0
  })
  const [sel, setSel] = useState<string | null>(null)
  const setPaso = (i: number) => {
    setPasoState(i); setSel(null)
    history.replaceState(null, '', `#recorrido/${ej}/${i + 1}`)
  }
  const { data, err } = useApi<Balance>('/api/balance', { ejercicio: ej })
  const { data: hist } = useApi<Historico>('/api/bridge/historico', {})
  const C = chartColors(useDark())
  if (err) return <ErrorBox err={err} />
  if (!data) return <p>Cargando…</p>
  if (data.estado !== 'ok') return <p className="nodata">Sin datos del IMIG para {ej}.</p>
  const card = (e: string) => data.cards.find(c => c.etiqueta === e)
  const val = (l: BalLine | undefined) => (l?.valor_millones == null ? null : Number(l.valor_millones))
  const ing = val(card('Ingresos totales')), gas = val(card('Gasto primario')), intr = val(card('Intereses netos'))
  const aCat = (g: BalLine, i: number): Cat => ({
    key: g.grupo!, nombre: g.etiqueta, corto: GRUPO[g.grupo!]?.corto ?? g.etiqueta, que: GRUPO[g.grupo!]?.que ?? '',
    valor: Number(g.valor_millones), color: C.series[i], detalle: g.detalle ?? [],
  })
  // Sin dato no es 0: una categoría sin valor publicado no se dibuja y se avisa.
  const conValor = (g: BalLine) => g.valor_millones !== null
  const ingCats = data.grupos.filter(g => g.flujo === 'ingreso').map(aCat).filter((_, i) => conValor(data.grupos.filter(g => g.flujo === 'ingreso')[i]))
  const gasGr = data.grupos.filter(g => g.flujo === 'gasto primario')
  const gasCats = [
    ...gasGr.map(aCat).filter((_, i) => conValor(gasGr[i])),
    ...(intr !== null ? [{ key: 'intereses', nombre: 'Intereses netos', corto: GRUPO.intereses.corto, que: GRUPO.intereses.que,
      valor: intr, color: C.series[6], detalle: [] }] : []),
  ]
  const faltan = data.grupos.filter(g => !conValor(g)).map(g => g.etiqueta)
  const cats = paso === 0 ? ingCats : gasCats
  const total = cats.reduce((t, c) => t + c.valor, 0)
  const elegida = cats.find(c => c.key === sel)
  return (
    <div className="tour">
      <p className="tour-intro">Las cuentas del <G t="spn">Estado nacional</G> en {data.periodo}, explicadas desde cero. Todo se
        muestra <b>de cada $100</b>, para que se entienda la proporción sin perderse en cifras gigantes. Tocá una categoría para
        saber qué es y cómo se reparte; las palabras subrayadas tienen su definición.</p>
      <ol className="stepper">
        {PASOS.map(([q, corto], i) => (
          <li key={q}>
            <button className={i === paso ? 'activo' : i < paso ? 'hecho' : ''} onClick={() => setPaso(i)} aria-current={i === paso}>
              <span className="num">{i + 1}</span><span className="q">{q}</span><span className="corto">{corto}</span>
            </button>
          </li>))}
      </ol>

      <section className="tour-body" key={paso}>
        {paso < 2 && <>
          <h2 className="pregunta">{paso === 0
            ? 'De cada $100 que recibe el Estado nacional…'
            : 'De cada $100 que gasta el Estado nacional…'}</h2>
          <Mapa cats={cats} sel={sel} onSel={setSel} verbo={paso === 0 ? 'que entran' : 'que se gastan'} />
          {elegida && <Detalle c={elegida} total={total} periodo={data.periodo!} onClose={() => setSel(null)}
            frase={paso === 0 ? 'De cada $100 que entran, {n} vienen de acá.' : 'De cada $100 que se gastan, {n} van acá.'} />}
          {!elegida && <p className="pista">👆 Tocá una categoría para ver qué es.</p>}
          {faltan.length > 0 && <p className="warn">⚠ Sin dato publicado para: {faltan.join(', ')} (no se dibuja; no es cero).</p>}
        </>}
        {paso === 2 && <>
          <h2 className="pregunta">¿Alcanzó lo que entró para lo que se gastó?</h2>
          {ing !== null && gas !== null && intr !== null
            ? <Cuenta ing={ing} gas={gas} intr={intr} />
            : <p className="nodata">Falta algún total publicado para hacer la cuenta.</p>}
          {hist && <Historia hist={hist} ej={ej} onEj={onEj} />}
          <a className="cta" href={`#puente/${ej}`}>¿Por qué el Presupuesto muestra otro resultado? Mirá el puente, paso a paso →</a>
        </>}
      </section>

      <div className="tour-nav">
        <button disabled={paso === 0} onClick={() => setPaso(paso - 1)}>← Anterior</button>
        <span className="muted">{paso + 1} de {PASOS.length}</span>
        {paso < PASOS.length - 1
          ? <button className="primario" onClick={() => setPaso(paso + 1)}>Siguiente →</button>
          : <a className="boton primario" href={`#puente/${ej}`}>Ver el puente →</a>}
      </div>
      <p className="note">Fuente: IMIG (Secretaría de Hacienda), Sector Público Nacional, <G t="caja">base caja</G>.
        Las cifras exactas y su procedencia están en la pestaña Resumen.</p>
    </div>
  )
}
