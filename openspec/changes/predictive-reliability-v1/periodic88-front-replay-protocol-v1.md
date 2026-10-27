# Diagnóstico acotado del frente88 y replay del ciclo39

2026-10-27. Sin nuevas extensiones. Fuente: ventana2 preregistrada `aa33c82`,
checkpoint38→39, configuración88 idéntica y receta aceptada/rechazada sellada
en `periodic88-window2-v1/manifest.json` antes del replay.

1. Con estados ya guardados31–39, localizar en coordenadas físicas las
   diferencias de composición, densidad y presión entre fases iguales.
   Informar L1/L2/Linf, centro y anchura de |delta Y| ponderados por volumen,
   inventarios y fracción de discrepancia situada en celdas de presión estable.
   La descomposición lineal delta rho = delta p/a² + resto es sólo un indicador
   acústico/contacto local, no una prueba exacta de un modo no lineal.
2. Reproducir UNA vez el ciclo39 existente. No calcular ciclo40. Presupuesto
   120s de replay, watchdog150s, estimación de escritura8MiB, reserva2GiB.
   Verificar dependencias, configuración y hashes; restauración nativa38.
   Cada rechazo y paso aceptado debe coincidir con la receta y el estado/ledger
   final debe ser exactamente39. Un desacuerdo detiene la interpretación.
3. Observar los dos stages reales SSPRK2 sin almacenar trayectorias extensas.
   Integrar flujos de masa, energía y cuatro especies de todos los extremos,
   separando signos por caudal de masa de cada stage (flujos ya incluyen área).
   Resolver balances por conducto y cámara con trabajo, calor de pared y fuentes
   químicas/P7 reales. No confundir entalpía transportada con energía interna.
4. Umbral de balance normalizado1e-12, coherente con controles previos; especies
   normalizadas por inventario total del subsistema y transporte, no por una
   especie casi nula; energía por inventario/transportes/fuentes. Registrar
   también residuos dimensionales. No tocar tolerancias del detector.
5. Inventario/caudal bruto es un diagnóstico de renovación, no una constante
   de relajación exponencial en presencia de recirculación. No inferir tiempo
   físico de purga de un frente sin flujos medidos. Distinguir fuente física,
   difusión numérica y desplazamiento; un replay no separa toda esa incertidumbre.

Salida: informe focal, manifest y tests del observador; L1/SELF_REVIEW, sin
promoción de solver ni claim experimental. Sólo después de esta evidencia se
decidirá si preparar otra ventana acotada. No hay avance automático de ciclos.
