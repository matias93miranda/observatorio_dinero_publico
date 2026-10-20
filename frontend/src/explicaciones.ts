/** Explicaciones en lenguaje llano de cada categoría del IMIG (por clave de grupo o de columna).
 * Son textos didácticos: no contienen cifras ni afirmaciones que dependan de un año. Las cifras salen
 * siempre de la base; los criterios técnicos con cita oficial están en "Fuentes y metodología". */

export const GRUPO: Record<string, { corto: string; que: string }> = {
  // ingresos
  tributarios: { corto: 'Impuestos',
    que: 'Lo que pagamos en impuestos: al comprar (IVA), por lo que ganamos (Ganancias), al mover plata en el banco, al exportar o importar, al cargar combustible, entre otros.' },
  seguridad_social: { corto: 'Aportes jubilatorios',
    que: 'Los aportes que se descuentan del recibo de sueldo y las contribuciones que pagan los empleadores. Financian el sistema de seguridad social: jubilaciones, asignaciones, PAMI.' },
  rentas: { corto: 'Rentas',
    que: 'Intereses y ganancias que el Estado cobra por lo que posee, como las inversiones del FGS de la ANSES. Desde 2017 no se cuentan acá las utilidades del Banco Central ni los intereses que el Estado se paga a sí mismo.' },
  otros_ingresos: { corto: 'Otros ingresos',
    que: 'Ingresos que no son impuestos ni aportes: tasas, multas, cánones, transferencias recibidas y venta de bienes del Estado.' },
  // gastos
  prestaciones_sociales: { corto: 'Jubilaciones y ayuda social',
    que: 'Lo que el Estado paga directamente a las personas: jubilaciones y pensiones, asignaciones familiares y AUH, la atención de PAMI y otros programas sociales.' },
  subsidios_economicos: { corto: 'Subsidios',
    que: 'Plata que pone el Estado para que la luz, el gas y el transporte (colectivos, trenes) cuesten menos de lo que costarían.' },
  funcionamiento: { corto: 'Funcionamiento del Estado',
    que: 'Lo que cuesta que el Estado nacional funcione: los sueldos de sus empleados y las compras de bienes y servicios que necesita.' },
  transf_provincias: { corto: 'Envíos a provincias',
    que: 'Plata que la Nación envía a las provincias para gastos corrientes en educación, salud, seguridad social y otras áreas.' },
  otros_corrientes: { corto: 'Universidades y empresas públicas',
    que: 'Fondos para las universidades nacionales, lo que el Estado pone para cubrir las pérdidas operativas de empresas públicas y otros gastos.' },
  capital: { corto: 'Obras e inversión',
    que: 'Inversión en cosas que duran: obras de energía, transporte, educación, vivienda, agua y cloacas, hechas por la Nación o financiadas para que las hagan las provincias.' },
  intereses: { corto: 'Intereses de la deuda',
    que: 'Lo que se paga por la plata que el Estado tomó prestada. Se cuentan sin los intereses que el Estado se paga a sí mismo (por ejemplo, al FGS de la ANSES).' },
}

const LINEA: Record<string, string> = {
  iva_neto_reintegros: 'Impuesto que se paga en casi todas las compras de bienes y servicios ("neto de reintegros": descontadas las devoluciones).',
  ganancias: 'Impuesto sobre los ingresos de las personas y las utilidades de las empresas.',
  aportes_contribuciones_seguridad_social: 'Aportes de trabajadores y contribuciones de empleadores al sistema de seguridad social.',
  debitos_creditos: 'El llamado "impuesto al cheque": se cobra sobre los movimientos de las cuentas bancarias.',
  bienes_personales: 'Impuesto anual sobre el patrimonio de las personas (propiedades, ahorros, inversiones).',
  impuestos_internos: 'Impuestos sobre productos puntuales, como cigarrillos o bebidas alcohólicas.',
  combustibles: 'Impuestos sobre la nafta, el gasoil y otros combustibles.',
  derechos_exportacion: 'Las "retenciones": un porcentaje que se cobra al vender productos al exterior.',
  derechos_importacion: 'Aranceles que se cobran al traer productos del exterior.',
  resto_tributarios: 'Otros impuestos de menor peso.',
  fgs_cobradas_sector_privado_sector_publico_financiero: 'Intereses y ganancias que cobra el FGS por inversiones en empresas y bancos (no en el propio Estado).',
  resto_rentas_propiedad: 'Otras rentas (intereses, dividendos) que cobra el Estado.',
  ingresos_no_tributarios: 'Tasas, multas, cánones y otros cobros que no son impuestos.',
  transferencias_corrientes: 'Plata que el Estado recibe de otros sin dar nada a cambio.',
  resto_ingresos_corrientes: 'Otros ingresos corrientes menores.',
  ingresos_capital: 'Ingresos por vender bienes del Estado o recuperar préstamos.',
  jubilaciones_pensiones_contributivas: 'Jubilaciones y pensiones de quienes hicieron aportes durante su vida laboral.',
  asignacion_familiares_hijo: 'Asignaciones familiares por hijo y la Asignación Universal por Hijo (AUH).',
  pensiones_no_contributivas: 'Pensiones que no requieren aportes previos (por ejemplo, por invalidez).',
  prestaciones_inssjp: 'Atención médica y prestaciones de PAMI para jubilados y pensionados.',
  otros_programas: 'Otros programas sociales.',
  energia: 'Para que la electricidad y el gas cuesten menos.',
  transporte: 'Para colectivos, trenes y otros transportes.',
  otras_funciones: 'Subsidios a otros sectores.',
  salarios: 'Sueldos del personal del Estado nacional.',
  otros_gastos_funcionamiento: 'Compras de bienes y servicios para funcionar: insumos, alquileres, servicios.',
  otros_corrientes_transferencias_universidades: 'Fondos para el funcionamiento de las universidades nacionales.',
  otros_corrientes_deficit_operativo_empresas_publicas: 'Lo que pone el Estado para cubrir la diferencia entre lo que cobran y lo que gastan las empresas públicas en su operación.',
  otros_corrientes_resto: 'Otros gastos corrientes menores.',
  fondo_federal_solidario: 'Fondo que distribuía recursos a provincias y municipios para obras.',
}

/** Explicación de una línea; las series de transferencias y obras se describen por su área. */
export function explicaLinea(col: string | undefined, etiqueta: string): string | null {
  if (!col) return null
  if (LINEA[col]) return LINEA[col]
  const area = etiqueta.split(': ')[1]
  if (col.startsWith('transferencias_corrientes_provincias_') && area) return `Envíos a provincias para gastos corrientes en ${area}.`
  if (col.startsWith('capital_') && area) {
    const m = area.match(/^(.*) \((Nación|a provincias)\)$/)
    if (m) return m[2] === 'Nación' ? `Obras e inversión en ${m[1]} que hace directamente la Nación.`
      : `Plata para que las provincias hagan obras de ${m[1]}.`
  }
  return null
}
