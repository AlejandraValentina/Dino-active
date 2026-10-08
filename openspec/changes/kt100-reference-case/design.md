# Diseño

La referencia selecciona el KT100SP descrito en la publicación oficial Yamaha
de 1998 para el contexto doméstico japonés FP2. La fuente no fija año de serie
ni RPM de operación. Los datos no disponibles permanecen `UNKNOWN`; el fixture
los completa con supuestos sintéticos separados y justificados.

La ejecución usa exclusivamente el camino de aplicación existente: modelo 0D
de cuatro volúmenes y RK4 adaptativo perfil B, con regularización exterior fija
de 100 Pa ya utilizada por el producto. La convergencia disponible es el
contrato nativo de periodo 1 de la aplicación. No equivale al detector E13-R1
de sensores 1D y no detecta periodo 2. No se cambia solver, tolerancia, umbral,
ni configuración después de observar resultados.

El preflight previo de la topología híbrida completa P5-C/P6/P7 terminó con
estado de especie inválido. No se altera esa física en esta entrega. El modelo
0D no representa propagación de ondas en conductos, cuatro especies, entrega
separada de aire fresco, cortocircuito fresco ni restart. La campaña 0D es una
exploración útil y reproducible, pero no puede acreditar esos gates ni se
presenta como sustituto de la calificación E13.

Se ejecuta la malla exploratoria fija 5000/7000/9000/11000/13000 rpm, elegida
antes de inspeccionar resultados. No se encontró un régimen específico para
KT100SP, por lo que no se llama rango operativo Yamaha. Cada punto se repite
desde el mismo estado inicial para comprobar determinismo; esa repetición no es
restart. Una sensibilidad descriptiva, congelada antes de ejecutarse, perturba
±5 % longitud de biela y longitud de escape en el punto medio geométrico de la
malla. No hay calibración contra potencia externa.

P9 v1.0 y sus claims permanecen congelados e intactos.

## Continuación V2 — diagnóstico y límite contractual

La orden V2 mantiene los cinco puntos exploratorios de V1 y requiere el stack
completo, evidencia primaria, E13, restart y replay. El armado puntual con la
geometría de `fixture_case(5000)` y `P6IntegratedSystem` produjo un estado P6
admisible y `species_sum_error = 1.73e-18`; por tanto, el antiguo artefacto
`kt100-reference-v1-20261001-smoke/anchor-5000.json` no identifica una falla
reproducible en la inicialización P6 actual.

No se generó una configuración V2 ejecutable ni se lanzó una campaña. P8
construye siempre `SyntheticCase()`/`S2T-0D-01`, fija dos duct cells y su
auditoría rechaza otra identidad de mecánica, otra ventana P7 y anchors distintos:
P8 fija 2500/5000/8000/11000/15000 rpm, mientras V2 solicita
5000/7000/9000/11000/13000 rpm. P6/P7 captura un único evento absoluto
350–390° y no crea automáticamente el evento del ciclo siguiente. El
productor/auditor P8 tampoco genera historiales de ciclos repetidos para el
detector E13. Cumplir juntos P7 no vacuo, convergencia E13 por ciclos y auditoría
primaria de P8 requeriría extender la semántica/contrato de esos componentes;
esta entrega prohíbe cambios en contratos P4–P8. Este es el hard stop
`KT100_HYBRID_V2_STACK_CONTRACT_BLOCKER`.

La geometría documental y todos los límites/salidas de V1 permanecen intactos.
No se escogieron nuevas dimensiones, mallas, estados ni valores de combustión,
ni se creó un fixture parcial que pudiera confundirse con V2 verificado. El
estado 5000 rpm V1 continúa siendo `NO_CONVERGENCE / 8 consecutive rejects`.
