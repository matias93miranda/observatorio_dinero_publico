import type { ReactNode } from 'react'

/** Definiciones didácticas (lenguaje llano). Los criterios técnicos, con cita oficial verificada,
 * están en "Fuentes y metodología"; acá no se agrega ninguna cifra. */
export const GLOSARIO: Record<string, { termino: string; def: string }> = {
  devengado: { termino: 'Devengado', def: 'Momento en que el Estado reconoce que debe pagar algo (por ejemplo, porque ya recibió el bien o el servicio), aunque todavía no lo haya pagado.' },
  percibido: { termino: 'Percibido', def: 'Ingreso registrado cuando el dinero efectivamente entra a las cuentas del Estado.' },
  caja: { termino: 'Base caja', def: 'Cuenta ingresos y gastos cuando el dinero entra o sale de verdad. Es el criterio del resultado fiscal oficial (IMIG).' },
  primario: { termino: 'Resultado primario', def: 'Ingresos menos gastos, sin contar los intereses de la deuda. Dice si lo que se recauda alcanza para lo que se gasta antes de pagar la deuda.' },
  financiero: { termino: 'Resultado financiero', def: 'Resultado primario menos los intereses de la deuda. Si es negativo, la diferencia se financió (con deuda u otras fuentes).' },
  intereses: { termino: 'Intereses de la deuda', def: 'Lo que el Estado paga por el dinero que tomó prestado.' },
  an: { termino: 'Administración Nacional', def: 'Ministerios, organismos descentralizados e instituciones de seguridad social (como la ANSES). Es lo que cubre la ley de Presupuesto.' },
  spn: { termino: 'Sector Público Nacional no Financiero', def: 'La Administración Nacional más PAMI, fondos fiduciarios, otros entes y las empresas públicas (estas, solo por su resultado operativo). Es el universo del resultado oficial.' },
  imig: { termino: 'IMIG', def: 'Informe mensual de ingresos y gastos de la Secretaría de Hacienda: el resultado fiscal oficial del Sector Público Nacional, en base caja.' },
  rentas: { termino: 'Rentas de la propiedad', def: 'Intereses, dividendos y utilidades que cobra el Estado por lo que posee (por ejemplo, utilidades que transfiere el BCRA o intereses de bonos en manos del FGS).' },
  fgs: { termino: 'FGS', def: 'Fondo de Garantía de Sustentabilidad de la ANSES. Invierte reservas del sistema previsional, en buena parte en bonos del propio Estado.' },
  bcra: { termino: 'BCRA', def: 'Banco Central de la República Argentina. Cuando transfiere utilidades al Tesoro, aparecen como rentas de la propiedad.' },
  real: { termino: 'Pesos constantes', def: 'Montos ajustados por inflación (IPC del INDEC) para comparar años distintos con el mismo poder de compra.' },
  intra: { termino: 'Operaciones intra-sector público', def: 'Pagos entre organismos del mismo Estado (un bolsillo le paga a otro). En el resultado consolidado se cancelan.' },
}

/** Término con definición emergente: hover o foco (teclado / toque en pantallas táctiles). */
// Siglas y nombres propios: se muestran tal cual; el resto, en minúscula dentro de la frase.
const PROPIOS = new Set(['an', 'spn', 'imig', 'fgs', 'bcra'])

export function G({ t, children }: { t: keyof typeof GLOSARIO; children?: ReactNode }) {
  const g = GLOSARIO[t]
  const texto = PROPIOS.has(t) ? g.termino : g.termino.charAt(0).toLowerCase() + g.termino.slice(1)
  return (
    <span className="term" tabIndex={0} role="button" aria-label={`${g.termino}: ${g.def}`}>
      {children ?? texto}
      <span className="tip" role="tooltip"><b>{g.termino}.</b> {g.def}</span>
    </span>
  )
}
