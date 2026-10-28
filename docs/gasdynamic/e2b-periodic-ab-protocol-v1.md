# E2B — comparación periódica A/B MUSCL V2

2026-10-28. Activación expresa del dueño. Congelar este protocolo antes de
integrar; no cambiar solver, física, CFL, detector, umbrales ni rc7.

## Viabilidad y resolución elegida

Se usan **44 celdas totales, 31 de escape**, configuración ya ensayada en E2A,
con MUSCL_PRIMITIVE_SPECIES_BOUNDARY_CANDIDATE_V2 y tobera V2 experimental.
El archivo A44 coincide campo por campo con el del caso independiente que
alcanzó PERIOD_1 en ciclo30, streak3, verificado posteriormente desde primarias.
Ese historial sólo fundamenta coste y planificación: no se reanuda ni se
reutiliza para declarar un nuevo resultado con otra identidad de código.

Tiempos E2A: A44 13,228 s/ciclo, B44 13,409; extensión de la misma configuración
A44 ≈13,952 s/ciclo. Se planifica **15 s/ciclo**. A tiene referencia30; B no
tiene un conteo medido con esta ley. 30–60 ciclos para B es un intervalo de
planificación por geometría próxima, **no una predicción estadística ni garantía**.
Estimación nominal A/B: 90 ciclos×15=1350 s. Límite de100 ciclos por variante:
3000 s estimados, más1500 de auditorías,250 de tests y650 de otros costes/
reserva = **5400 s**. El ejecutor limita integración a1600 s por variante,
auditorías a1500 s compartidos y conserva margen global para cierre.

No se selecciona88 como campaña nueva: tarda≈34–36 s/ciclo en E2A y existe
historial88 todavía no periódico, obtenido además mediante remallado, no un
arranque independiente equivalente. No hay fundamento para asegurar que A/B88
y sus auditorías entren en5400 s. No se transfiere el conteo30 de44 como
garantía para88. El44 se elige **exclusivamente para E2B exploratorio**;
no se afirma que resuelva la incertidumbre de potencia.

## Inputs y procedimiento

- Exactamente `results/e2-spatial-waves-v1/preparation/A44.json` y `B44.json`,
  hashes en `results/e2b-periodic-ab-v1/manifest.json`.
- A83/B103 mm;9000 RPM; misma física, condiciones iniciales en primitivas y
  proporciones de especies, adaptadas al volumen real de cada geometría.
  Ambos constructores comienzan a0° con detectores nuevos, sin warm start.
- Paso nominal0,5°, mismos eventos exactos y CFL0,4. La política de rechazo y
  subdivisión existente conserva admisibilidad; no se recortan flujos/especies.
- `PeriodicDetectorV2`, datos REFERENCE_PERIODIC_CONVERGENCE_V1, umbrales y
  streak3 originales, sin suprimir ningún observable. Período2 sigue habilitado.
- Guardar por ciclo checkpoint nativo, receta, detector, todos los resultados
  de comparación, trabajo, métricas y conservación. Probar restauración de
  checkpoint con la misma identidad. Ante tiempo agotado, conservar además
  terminal FAST y receta parcial ligados al último nativo.
- Cuando cada variante detecta periodicidad, detener su integración. Auditar
  las últimas4 primarias en período1 u8 en período2, mediante replay exacto
  de sus propias recetas, sin añadir ciclos físicos. Reconstruir el detector
  usando esas primarias y el prefijo histórico de la misma ejecución.
- Comparación final sólo cuando ambos detectores y sus auditorías concuerdan;
  no atribuir a periódicos resultados meramente estables en trabajo.

## Magnitudes

W_ind = −Δledger.cylinder_work_J; W_cc = −Δledger.crankcase_work_J;
W_pistón = W_ind+W_cc. Reutilizar el modelo mecánico del motor funcional,
FMEP85000 Pa, **SYNTHETIC_ASSUMPTION**, sin calibrarlo:
W_eje = W_pistón−FMEP×cilindrada. El bombeo del cárter no se resta dos veces.
Potencia2T=W×9000/60, torque=W/(2π), IMEP=W_ind/Vd, BMEP=W_eje/Vd.
La ley mecánica procede del fixture funcional y se congela por hash; no se
comparan potencias con curvas legacy para anunciar mejoras.

Registrar aire y combustible atrapados en el último cierre exacto de
lumbreras. Diferenciar el marcador residual inicial de gases no frescos
retenidos: (quemados+residuales)/masa de cilindro. No llamar oxígeno ni gas
químicamente identificado a estas etiquetas de composición.

Flujos por SSPRK2: integral con pesos1/2 de los flujos reales de las caras,
separando signo positivo/negativo, masa/energía/especies en escape y transfers.
Presión, fase y propagación: mismas cinco sondas físicas de10 mm y muestras
0,5° de E2A, comparadas por fase de ciclo. No identificar reflexión por un pico
o una correlación; conservar guardas de la hipótesis acústica.

En período2, conservar ambas ramas y promediar magnitudes integradas sobre
dos revoluciones; no presentarlas como un único ciclo PERIOD_1.

## Incertidumbre y clasificación inalterable

La diferencia entre variantes periódicas se distingue de su incertidumbre
numérica y de la validación experimental. Las envolventes transitorias P1
no cuantifican incertidumbre de potencia. No existe comparación periódica
A/B entre mallas equivalentes que la determine. En este alcance, si ambos
convergen, la clasificación admisible es **E2B_PERIÓDICO_EXPLORATORIO**.
No se deduce un error de potencia del test de periodicidad, de una presión
transitoria o de diferencias contra estados88 todavía transitorios.

- **E2B_PERIÓDICO_DISTINGUIBLE** exigiría periodicidad y respaldo numérico de
  la diferencia de potencia: no se obtiene relajando el alcance anterior.
- **E2B_NO_CONVERGIDO**: no se acredita periodicidad completa dentro de los
  límites congelados. No ampliar ciclos ni tiempo automáticamente.
- **E2B_NO_VIABLE**: estimación fundamentada previa supera5400 s; no lanzar.
- **E2B_DEFECTO**: inconsistencia reproducible, conservar reproductor.

## Recursos, parada y preservación

Máximo5400 s acumulados de verificación, integración, replay/auditoría y
análisis. Verificar viabilidad y almacenamiento antes de integrar. Pruebas
P4–P8 con raíz histórica explícita en el entorno hijo, sin trasladar archivos.
Estimar2 GiB de artefactos externos (checkpoints/recetas/primarias/spool),
16 MiB en repo y reserva adicional2 GiB por volumen. Artefactos bajo raíz
configurable; no codificar una dependencia deC:. No limpiar ni sobrescribir
históricos. Límite de100 ciclos/variante y1600 s de integración por variante.
Si deja de caber una auditoría completa, detener antes de admitirla.

No campañas de refinamiento, otras RPM, cambios físicos, Desktop ni etapa
posterior. SELF_REVIEW; conservar modelo numérico identificado y rc7. Al
entregar decisión y limitaciones, detenerse según el alcance del dueño.
