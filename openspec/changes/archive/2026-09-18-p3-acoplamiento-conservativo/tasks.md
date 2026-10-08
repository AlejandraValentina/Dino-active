## P3 — registro inicial histórico (sustituido por R1; no marcar P3A reservoir como PASS)
- [x] Registrar aceptación humanaP2 y congelar hashes del núcleo/contratos.
- [x] Leer contrato de interfazP1 y definir energía/signos.
- [x] Implementar interfaz aislada y reproducir preflight con dev_orchestrator.
- [ ] P3A reservoir/tubo completo PASS.
- [ ] P3B volumen constante, C01–C07/C09–C12 PASS.
- [ ] P3C volumen variable C08 PASS.
- [ ] Adaptador mínimo a estados0D existentes, sólo tras gates sintéticos.
- [x] RegresionesP0/P2, OpenSpec y revisión independiente del preflight bloqueado (no acredita integración completa).
- [ ] P3_PASS_0D_1D_COUPLING_VERIFIED; aceptación humana posterior, sinP4.


## Resultado — P3_BLOCKED_BACKFLOW / SCIENTIFIC_CHANGE_REQUIRED

42 evaluaciones de la frontera reservoir congelada, ambas orientaciones.
A p_pipe=p0=100kPa,T0=300K, T_pipe301K y velocidad normal−1e−9m/s:
No consistent reservoir inflow branch. A299K el flujo tiende a−0.037563294kg/s
para área.01m², pero en reposo es0. Límite analítico demuestra salto/ausencia de raíz;
no es ruido de integración. Ver results/p3-coupling-20260918/analysis.md.

Implementado solo estado m/U/F/V y flujo Euler único con incrementos opuestos;
energía entalpía total, donor según signo e impulso separado. No integrador
acoplado ni conexión productiva. No cambiar BC/P1 para pasar sin decisión científica.
C04 BLOCKED; C01–C03/C05–C12 NOT_RUN como gates dinámicos. Pruebas puntuales
de equilibrio/energía/especie no sustituyen C01–C12. P3A no acreditado, P3B/P3C
no iniciados, volumen variable y adaptador pendientes. P4 no iniciado.

74 pruebas PASS en23.983s; P2 T01–T12/58finales y FIRST_ORDER/R4 offline PASS;
siete regresiones P0 offline PASS. Núcleo/contratos congelados exactos.
Preflight+regresiones11.750s, cero integraciones nuevas. No campaña >300s.
AceptaciónP2 registrada en3a19e41; no aceptaciónP3. Sin push ni archivo.
El borrado ajeno redme.txt permanece intacto.

Revisión independiente /root/p3_review confirma STOP,27hashes y42evaluaciones;
6sinrama. Ningún hallazgo adicional en interfaz preparatoria. Dictamen en
results/p3-coupling-20260918/independent-review.json. Autorrevisión separada
de alcance/documentos/hashes. OpenSpec estricto P3 y P2 PASS.

## P3-R1 — orden38a85593
- [x] C00/C00B, curvas, forward/reverse, energía/especie y revisión independiente.
- [x] P3B C01–C07 tras R1 PASS.
- [x] P3C C08–C12 tras P3B PASS.
- [x] Adaptador0D y cierre sólo tras todos los gates.

## Resultado vigente P3-R1
**P3_PASS_0D_1D_COUPLING_VERIFIED / WAITING_HUMAN_APPROVAL**.
Cierre técnico, no aceptación humana. Revisión independiente /root/p3_review
por gates R1, P3B, P3C y adaptador/regresiones; sin hallazgos abiertos.
Autorrevisión separada: alcance, signos, documentación, hashes e índice Git.
Núcleo/contratosP2 y producción0D/UI/JSON intactos. Borrado ajeno redme.txt conservado.

- [x] Adaptador de m/U/F para layouts2T/4T, sin conexión de puertos ni campaña de motor.
- [x] 83 pruebas PASS en27.627s, incluido source adiabático aislado con cara sellada simulada.
- [x] P2 T01–T12/58 finales y FIRST_ORDER/R4 reevaluados offline PASS, sin nuevas integracionesP2.
- [x] Siete regresiones históricasP0 offline PASS y27 hashes de núcleo/contratos exactos.
- [x] Revisión independiente final PASS; dictamen separado del hook nativo no conectado.
- [x] Aceptación humanaP3 por orden cec0f5b3; archivo autorizado. P4 se realiza en cambio separado.

R1:6 contactos térmicos en reposo con flujosm/E/F exactamente0;66 muestras de
velocidad y4 casos de diferencia de presión,76HLLC/0HLLE. Las36 series de
magnitudes disminuyen estrictamente; ratio final/inicial9.99656e-5..1.00034474e-4.
Prueba de vectorfallback con mock; no afirmar activaciónHLLE física en estos casos.
Energía conserva TODO el flujo Euler; cinética entrante se incorpora a U bajo
mezcla estancada. Momentum/impulso es reacción registrada, sin estado ni trabajo
axial0D adicional. Especie es el componente completo de Riemann, sin donor manual.

P3B:8 casos completos, C01–C07 PASS con ambos métodos. Reversión natural:
FIRST_ORDER2 cruces (primero .001719620266s); MUSCL3 (primero .001718139823s).
Mayor residuo normalizado global2.000353008e-15. Ledgers incluyen todos los
stages aceptados y cuentas de RHS/HLLC también los intentos rechazados.

P3C:11 casos completos (2 volumen variable +9 acústicos). C08 trabajo-pdV
recalculado desde presiones de stage/derivada analítica. Residuos energía
3.46e-17/1.98e-16. C09 referencia causal derivada del modeloR1:
tau=2V/(aA), dpch/dt=(2pi-pch)/tau, pr=pch/2. Coeficiente reflejado medido,
no impuesto. A N160/CFL.4, pico/ε=.0730709467 vs referencia .0733048136.
Colas gaussianas: inicial1.388794386e-11Pa, pared5.319643583e-13Pa.
Máximo error acústico normalizado .0016572813 < .025. Las18 secuencias C10
disminuyen estrictamente. Las3 parejasCFL reducen sensibilidadN40→N160.
C12: admisibilidad por etapa, máximo residuo stage2.18e-16 y global1.57e-15.
Todas las integraciones completadas individuales<300s; máximo10.250s.

| CFL | L1 presión N40 | N80 | N160 |
|---|---:|---:|---:|
| 0.2 | 0.00163615583 | 0.000497261568 | 0.000122393775 |
| 0.4 | 0.00164312713 | 0.000504096718 | 0.000124923706 |
| 0.6 | 0.00165309005 | 0.000517533656 | 0.000145274428 |

| Pareja CFL | Sensibilidad N40 | N80 | N160 |
|---|---:|---:|---:|
| 0.2/0.4 | 7.05567236e-05 | 3.16786794e-05 | 1.0049787e-05 |
| 0.2/0.6 | 0.000176594682 | 8.0077134e-05 | 5.17431658e-05 |
| 0.4/0.6 | 0.000106291421 | 4.84096417e-05 | 4.23753518e-05 |

| Caso | Tiempo (s) | RHS | HLLC | Rechazos |
|---|---:|---:|---:|---:|
| equilibrium_FIRST_ORDER | 0.328 | 256 | 15616 | 0 |
| blowdown_FIRST_ORDER | 0.062 | 55 | 3355 | 0 |
| filling_FIRST_ORDER | 0.062 | 55 | 3355 | 0 |
| reversal_FIRST_ORDER | 1.063 | 709 | 43249 | 0 |
| equilibrium_MUSCL_SSPRK2 | 0.969 | 512 | 31232 | 0 |
| blowdown_MUSCL_SSPRK2 | 0.344 | 221 | 13481 | 55 |
| filling_MUSCL_SSPRK2 | 0.344 | 211 | 12871 | 51 |
| reversal_MUSCL_SSPRK2 | 4.078 | 2270 | 138470 | 426 |
| variable_FIRST_ORDER | 1.344 | 697 | 56457 | 0 |
| variable_MUSCL_SSPRK2 | 6.797 | 2963 | 240003 | 785 |
| acoustic_N40_CFL0.2 | 0.672 | 562 | 23042 | 76 |
| acoustic_N80_CFL0.2 | 2.578 | 1089 | 88209 | 135 |
| acoustic_N160_CFL0.2 | 10.250 | 2167 | 348887 | 265 |
| acoustic_N40_CFL0.4 | 0.328 | 286 | 11726 | 40 |
| acoustic_N80_CFL0.4 | 1.328 | 566 | 45846 | 78 |
| acoustic_N160_CFL0.4 | 5.360 | 1136 | 182896 | 158 |
| acoustic_N40_CFL0.6 | 0.250 | 203 | 8323 | 33 |
| acoustic_N80_CFL0.6 | 0.938 | 394 | 31914 | 60 |
| acoustic_N160_CFL0.6 | 3.797 | 785 | 126385 | 119 |

Un fallo de infraestructura conservado: primerC09 integradoN40/CFL.2 no llegó
a guardarse por falta de convergencia de cuadratura relativa de referencia final
cerca de momento nulo. Se corrigió sólo evaluador, GL4 compuesto8/16 con escala
absoluta; inicialización/solver/criterios intactos. Repetido sólo ese resultado
perdido; C08 se reutiliza por hashes, otros8 acústicos se ejecutan por primera vez.
No ocultar esa ejecución perdida ni contar reutilizaciónC08 como nueva campaña.

Evidencia: results/p3-r1-20260918/{r1,p3b,p3c-infrastructure,p3c,closure}.
Cada run conserva gate nativo BLOCKED (review_not_approved), excepto el fallo
inicial FAILED_INFRASTRUCTURE. Decisión final derivada de pruebas y revisiones
reales, no del stub; ver decision.json e independent-review.json.
Curvas revisadas visualmente: flux-continuity.png/svg y finite-verification.png/svg.
Son gráficos de evidencia sintética; no captura de UI ni validación experimental.
Comandos ejecutados desde raíz: python de .venv, `-m dev_orchestrator.runners.run_phase`
con fases P3_R1/P3B/P3C/P3_CLOSE y
`--dependency P2=docs/gasdynamic/p2_accepted_dependency.json`.
No repetir campañas para consultar evidencia. Integración automática OpenSpec
sigue omitida; sin cambios globales. Commits locales, sin publicación.

OpenSpec: `openspec validate p3-acoplamiento-conservativo --strict --no-interactive` PASS.
AtributosGit locales preservan bytes de los cinco archivosP3 revisados al
reabrir checkoutWindows; sin cambios de configuración global. Gráficas PNG/SVG
y artefactos tienen inventarioSHA256; no incluyen datos privados ni entorno.

## Aceptación posterior
P3_HUMAN_ACCEPTED por la usuaria, orden cec0f5b3. Baseline ec6ec55 congelado.
Se autoriza archivar. Casillas históricas reservoir no se marcan falsamente:
fueron sustituidas por R1, cuyo cierre técnico y aceptación están acreditados.
