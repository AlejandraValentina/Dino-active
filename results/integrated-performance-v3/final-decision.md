# Performance V3 — decisión final de inicialización acelerada

**Decisión: KEEP EXPERIMENTAL.** Se conserva el warm start únicamente como candidato de investigación, deshabilitado para uso ordinario. El único método aceptado para producir puntos periódicos y curvas RPM sigue siendo la inicialización independiente. No se integra en Desktop ni en el coordinador RPM.

## Evidencia comparada

Se compararon exclusivamente los resultados ya existentes: A10000 independiente (`pc-08bbe6f9b9694ff3970bfeb02edf4283-10000`, ciclos 102–104) y A10000 warm (`perfv3-warm-A10000-from-A9000-20261026`, ciclos 13–15). Ambos observables terminales se guardaron al límite de ciclo, fase 0° CA; el ciclo completo cubre 360° CA. Las magnitudes de masa, energía y presión se compararon en kg, J y Pa; fracciones de especie y velocidad están normalizadas según `REFERENCE_PERIODIC_CONVERGENCE_V2`. Se aplicaron sus ecuaciones y umbrales existentes a los observables, sin alterar hashes ni invocar el comparador estricto entre identidades de inicialización distintas.

| Salida terminal | A10000 independiente | Warm A10000 | Diferencia warm vs histórico |
|---|---:|---:|---:|
| Trabajo indicado por ciclo | 32.92691 J | 32.84920 J | −0.2360% |
| Potencia de freno | 3523.70 W | 3511.25 W | −0.3534% |
| Torque de freno | 3.36489 Nm | 3.35300 Nm | −0.3534% |
| Aire atrapado | 28.92130 mg | 28.86337 mg | −0.2003% |
| Carga fresca atrapada | 32.47687 mg | 32.41545 mg | −0.1891% |
| AFR atrapado | 8.13409 | 8.12576 | −0.1024% |
| Calor químico / combustible quemado | 71.81510 J / 1.96485 mg | 71.66987 J / 1.96087 mg | −0.2022% |

Presión máxima del cilindro difiere −0.0163%; los extremos de presión del escape difieren entre +0.0211% y +0.0934%. Presión del cárter y el resto de extremos listados cambian menos de 0.014%. Estos escalares cercanos no demuestran equivalencia del campo espacial.

De 413 observables, **311 pasan y 102 fallan**. Los 102 se distribuyen así: 99 en el escape (22 masas de celda, 20 temperaturas, 20 fracciones de aire fresco, 20 de quemados y 17 de residuales) y 3 en el inventario global de especies. El mayor desvío es `exhaust[30].species.burned`: diferencia absoluta 0.03357 (3.357 puntos porcentuales) frente al límite 0.002 (0.2 pp), 16.79 veces el límite. En el escape, la masa de celda llega a 0.01866 normalizado frente a 0.002; temperatura llega a 0.01768 frente a 0.005. El inventario global de especie quemada se desvía 0.02031 frente a 0.002.

Las masas, energías, presiones, temperaturas y especies de cilindro/cárter y boost pasan sus umbrales; no hay fallos de energía total ni de presión/velocidad en celdas de escape. La transferencia inicial A9000 conservó masa, energía y especies con error relativo máximo menor que 5e−15. El piloto alcanzó periodicidad local observada en 15 ciclos (racha del detector de tres), con conservación por ciclo del orden 1e−15; el resultado es exploratorio no auditado. Frente al histórico: 89 ciclos menos (85.58%) y 654.05 s menos de workflow (91.39%).

## Interpretación y límite de la evidencia

- **A — residuo aún evolucionando:** plausible, especialmente por la distribución de especies del escape, pero no se midió su tendencia más allá del ciclo 15.
- **B — estado periódico físico distinto:** posible; la periodicidad local del piloto no prueba que su composición espacial coincida con el A10000 independiente. Los fallos extensos y grandes son una diferencia de estado material bajo las métricas existentes.
- **C — artefacto de fase/unidades/comparación:** no respaldado. Las fases coinciden en el límite de ciclo y se aplicaron las normalizaciones/unidades del contrato. Las identidades completas difieren por el estado inicial de forma legítima; por eso el comparador estricto no se hizo pasar por compatible.
- **D — insuficiencia:** no se puede decidir con estos dos terminales si el campo del escape aún converge o si permanece en otro estado periódico.

Por tanto, la cercanía de potencia/torque no basta para aceptar equivalencia; tampoco hay evidencia para llamar falsa a la diferencia espacial. La mejora temporal justifica conservar el mecanismo como experimental, pero no usarlo para curvas de producto.

## Única verificación posterior propuesta

Si se retoma con autorización, continuar el mismo run warm desde su checkpoint de ciclo 15 hasta un máximo total de 40 ciclos nuevos, con límite de 240 s, checkpoint completo y sin extensión automática. En cada límite de ciclo, comparar el mismo conjunto de observables contra A10000 histórico y registrar la tendencia de discrepancias del escape, además del detector vigente. Convergencia documentada hacia los umbrales respaldaría seguir evaluándolo; una meseta fuera de umbral o falta de tendencia al límite descartaría el warm start. Esta prueba no se ejecutó ni queda iniciada.

Se preservan baseline CRV1, checkpoints e históricos. No se modificaron solver, detector, resultados ni criterios.
