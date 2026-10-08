## Context
Un cilindro de referencia, sin multiplicar áreas o volúmenes por N. Se reutiliza
piston_position de kinematics.py y GeometryPlot; no se rehace el editor.

## Decisions
- Lumbrera rectangular idealizada descubierta por el borde superior periférico
  del pistón. u se mide hacia abajo desde ese borde en PMS, no desde la cara del
  cilindro ni una cúpula. h en mm; w en mm desarrollado sobre la pared, no cuerda.
- A(θ)=w*max(0,min(h,x(θ)-u)), mm². PMS 0°, PMI 180°, rango 0–360°.
  Apertura se calcula por bisección de x(θ)=u en [0,180], 60 iteraciones acotadas
  (resolución angular muy inferior a 1e-9°). Cierre=360-apertura; duración=cierre-apertura.
  No se redondea a muestras; la curva es una muestra por grado solo para dibujo.
- Si u>=S: no hay apertura efectiva, ángulos ausentes, duración=0. Máximo efectivo
  w*max(0,min(h,S-u)), no siempre w*h. Se reutiliza requisito L>S/2 del mecanismo.
- Eventos dependen de S/L/u; áreas además h/w. Nombre y función identifican la fila,
  no alteran el cálculo. Ni diámetro, compresión, N ni volumen de cárter intervienen.
  Errores, ausencia e incompatibilidad se explican por resultado. Valores fuera
  del rango numérico no se presentan como datos ausentes ni se corrigen al guardar.
- Datos incompletos guardables: nombre vacío, función null sin elegir, dimensiones
  null. Función informada es escape o transfer. Números informados positivos finitos;
  coma/punto aceptados con el parser existente. Texto inválido permanece en el editor
  y bloquea guardado, incluso al cambiar de fila o temporalmente a 4T.
- Volumen libre de cárter en PMI: cm³, individual, sin conductos externos. Opcional,
  positivo finito; procedencia en observaciones existentes. No se deduce ni calcula.
- JSON plano v3 conserva claves v2 y añade ports (lista), crankcase_volume_bdc_cm3
  (número/null), two_stroke_reference (identificador fijo `rectangular-peripheral-tdc-developed-bdc-v1`).
  Cada port guarda name (texto), function (escape/transfer/null), top_mm, height_mm,
  width_mm (números/null). Todas estas claves se requieren en v3; referencia distinta
  se rechaza para no interpretar medidas bajo otra convención. Lectura v1/v2 deja
  lista vacía y volumen null; abrir no escribe. No se guardan curvas/eventos.
- La pestaña muestra lista y editor de la selección, botones Añadir/Eliminar,
  resultados y área con gráfico existente. En 4T se oculta editor/resultados y se
  retienen los datos en memoria y JSON. Seleccionar una fila no marca cambios;
  añadir/editar/eliminar sí. El tramo inicial no agregaba admisión; su ampliación se define abajo.

## Risks / Trade-offs
Aproximación rectangular; no es CAD, área efectiva de flujo, caudal o barrido.
La decisión de admisión queda resuelta por autorización de la usuaria. Pruebas,
inspección Windows y aceptación manual siguen siendo evidencias separadas.

## Ampliación autorizada: admisión por falda
- Sección separada Admisión: modalidad null (sin definir) o piston_port. No se
  asigna modalidad al abrir proyectos anteriores. Cuatro números opcionales
  positivos finitos: top_mm=u, height_mm=h, width_mm=w y skirt_mm=f, en mm.
- Ventana rectangular y borde inferior de falda recto. u hacia abajo desde el
  borde superior periférico del pistón en PMS; f distancia axial desde ese mismo
  borde hasta el borde inferior de falda en admisión, no biela/cúpula/bulón.
  w desarrollado, no cuerda. Un cilindro/cárter, sin multiplicar por N.
- x reutiliza piston_position. b=u+h, e=f+x; A=w*max(0,min(h,u+h-f-x)).
  Se exige L>S/2 y u>=S. d=u+h-f: d<=0 nunca abre; 0<d<S usa bisección
  compartida de 60 iteraciones para x(beta)=d; d>=S queda fuera del modelo por
  ausencia de intervalo de cierre alrededor de PMI, incluso con contacto en PMI.
- Cierre=beta, apertura=360-beta, duración=2beta; intervalo [apertura,360] unido
  a [0,cierre], sin contar PMS dos veces. Máximo=w*max(0,min(h,d)). Curva 0–360°.
  Eventos necesitan S/L/u/h/f; área además w; no diámetro, N, compresión ni cárter.
  Suma/resta de d usa Decimal desde los float validados para evitar cancelación
  y desbordamiento intermedio; resultados fuera de rango se retiran con causa.
- JSON v4 conserva referencia y claves v3 y añade intake con mode, top_mm,
  height_mm, width_mm, skirt_mm y reference: straight-skirt-peripheral-tdc-developed-v1.
  Todas las claves del objeto se requieren; números ausentes null. No guarda
  eventos/curvas. v1/v2/v3 inicializan Intake vacío y solo convierten al guardar.
- Borradores permanecen al cambiar modalidad, sección y 2T/4T, incluidos textos
  inválidos que bloquean guardar. Ayuda contextual/desplegable, unidades visibles,
  disposición apilada en ancho reducido y gráfico Qt existente.
- Contraste sintético independiente: S56/L100/u64/h10/w20/f42 -> 270°/90°/180°,
  máximo200 mm², A0=A360=200 y A90=A180=A270=0. No identifica motor experimental
  ni acredita rendimiento. No hay otras modalidades, conductos, caudal o presión.
