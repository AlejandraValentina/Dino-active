## Context
La ficha existente es la única fuente de diámetro D, carrera S, biela L y
compresión C. La pestaña nueva no duplica campos ni cambia archivos JSON v2.

## Decisions
- Un cilindro de geometría común; N no interviene en volúmenes instantáneos.
- r=S/2; mecanismo sin descentrado y no degenerado: L > r. L <= r impide
  cinemática (en L=r hay singularidad); puede guardarse la ficha con esos datos
  positivos para corregirla después. No modifica la validación de persistencia.
- θ=0° es PMS de referencia; ángulo positivo horario en el esquema. PMS a
  0/360/720°, PMI a 180/540°. 2T abarca 0–360°, 4T 0–720°, con segunda revolución
  diferenciada. No se asignan eventos de combustión ni válvulas.
- Posición desde PMS, positiva hacia el cigüeñal, en mm:
  x = r(1-cos θ) + L - sqrt(L²-r² sin² θ).
  Se evalúa la forma estable equivalente
  x = r(1-cos θ) + r*(r/L)*sin²θ/(1+sqrt(1-(r/L)² sin²θ)).
- Vd=π D² S/4000 cm³; Vc=Vd/(C-1); V(θ)=Vc+π D² x(θ)/4000.
  Vmin=Vc, Vmax=Vc+Vd. Posición depende de S/L; cámara y extremos de D/S/C;
  curva de volumen requiere además L compatible. Diámetro ausente no impide
  posición ni esquema; compresión ausente no impide posición. Datos inválidos,
  ausentes o resultados fuera de rango retiran únicamente resultados afectados.
- Curvas muestreadas cada grado, incluida frontera; cálculo directo sin tiempo,
  integradores ni solver. Selector de ángulo entero solo para inspección, no
  persistente ni animado. Esquema a escala uniforme de S/L, sin representar
  espesor, holguras ni dimensiones de fabricación. Misma función que las curvas.
- Dos widgets de dibujo especializados con QPainter: curvas y mecanismo, sin
  biblioteca general. Pestaña con desplazamiento para ventanas pequeñas/escaladas.
- Distinguir límites de cálculo en coma flotante de entradas inválidas: no
  corregir datos ni alterar su guardado cuando un resultado excede el rango.

## Risks / Trade-offs
El esquema no es CAD ni verifica interferencias o resistencia. Los resultados
geométricos no certifican física del motor. Las pruebas visibles y capturas no
completan retrospectivamente el recorrido manual histórico pendiente.
