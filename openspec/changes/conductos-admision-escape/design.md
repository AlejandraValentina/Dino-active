## Context
Un recorrido por sistema del cilindro de referencia 2T. Se reutilizan parser numérico,
guardado seguro, widgets Qt y estilo actuales; no se rehacen las pestañas existentes.

## Decisions
- Segment: name opcional; length_mm, start_diameter_mm, end_diameter_mm positivos
  finitos o null. Diámetros interiores (no radios), variación lineal. Tipo derivado
  por igualdad D1=D2: tubo; en otro caso troncocónico, expansión o contracción.
- Admisión ordenada entrada exterior → ventana al cárter; escape salida del cilindro
  → extremo exterior. x axial acumulado en mm y contornos ±D/2. Un cilindro, sin N.
- A1=pi*D1²/4, A2=pi*D2²/4; V=pi*L*(D1²+D1*D2+D2²)/12000 cm³. Decimal con
  precisión 50 para cálculo y totales, evitando desbordamiento/subdesbordamiento
  float; entradas se guardan sin redondear. Resultados redondeados solo al mostrar.
- Cada resultado valida sus entradas. Totales requieren todas sus contribuciones,
  no sumas parciales; lista vacía Sin tramos. Longitud no depende de diámetros.
- Unión continua exige igualdad numérica exacta D2 anterior=D1 siguiente; sin
  ajuste automático ni tolerancia oculta. Datos ausentes/erróneos dejan unión sin
  verificar. Discontinuidades se indican con números de tramos y en el perfil,
  sin adaptadores; no bloquean áreas ni suma de volúmenes de piezas calculables.
- Perfil completo requiere todas las dimensiones; si faltan o son inválidas se
  retira con causa. Polígonos separados por pieza, unión señalada, selección azul.
  Escala igual en ambos ejes, unidades y sentido visibles; no CAD de fabricación.
  Rango no representable se informa sin alterar datos ni totales.
- Borradores de texto por recorrido conservados al seleccionar/reordenar/cambiar
  vista o 2T/4T; invalidación bloquea guardar aun en sección oculta. Solo mutaciones
  marcan pendiente. Un único editor alterna recorridos; apilado al reducir ancho.
- JSON v5 conserva v4 y añade ducts: intake/exhaust listas, reference fijo
  ordered-circular-inner-axial-linear-2t-v1. Cada fila requiere name, length_mm,
  start_diameter_mm y end_diameter_mm. v1–v4 inicializan listas vacías sin escribir
  al abrir. No se guardan tipo derivado, resultados ni perfil.

## Risks / Trade-offs
No transición lumbrera/conducto, volumen añadido al cárter, ramificaciones, curvas,
espesores, silenciadores o flujo. Los casos sintéticos no acreditan predicción.
Comprobación automatizada/visual y aceptación manual se mantienen separadas.
