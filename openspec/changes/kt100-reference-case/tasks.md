# Tareas — KT100 Reference Case V1

- [x] Verificar baseline local/remoto, árbol previo limpio, hash P9 inicial y
      revisar fuentes de la variante sin mezclar KT100S/SE/SD/SEC.
- [x] Crear inventario de fuentes y manifest documental con estados de
      provenance para documentados, derivados, unknowns y supuestos sintéticos.
- [x] Implementar derivaciones geométricas independientes y validación del
      manifest, sin confundir datos del fixture con especificación Yamaha.
- [x] Generar `KT100_MODEL_FIXTURE_V1` determinístico para el modelo 0D
      existente; su alcance y límites quedan identificados en configuración.
- [x] Agregar pruebas de provenance, derivación, generación, completitud,
      ejecución geométrica y guardas de claims/P9.
- [x] Ejecutar pruebas focales y regresiones de adaptativo/proyecto/P9; validar
      OpenSpec en modo estricto.
- [x] Ejecutar la malla fija 5000/7000/9000/11000/13000 con profile B;
      preservar convergencia, no convergencia, balances y replay exacto.
- [x] Ejecutar sensibilidad preregistrada ±5 % en biela y escape; descriptiva,
      sin ajuste de parámetros.
- [ ] Verificar restart y gates de especie/entrega/short-circuit de la
      topología completa. El camino 0D no los soporta; el preflight híbrido
      previo terminó en estado inválido. No modificar física para forzar PASS.
- [x] Documentar fuentes, límites, resultados y claims permitidos.
- [x] Autorrevisión puntual y revisión independiente del provenance, alcance
      del modelo y artifacts; se corrigieron los desajustes de presiones y
      fracciones frescas antes de la aprobación final.
- [x] Registrar commit local sin push.
- [x] Confirmar el hash preregistrado de la especificación P9 y que no hay
      archivos versionados por LFS en este cambio.

Estado: `KT100_REFERENCE_CASE_V1_READY`; fixture ejecutable y determinista en
el camino 0D, pero no `KT100_MODEL_FIXTURE_V1_VERIFIED` por gates no soportados.
P9 permanece congelado; validación experimental `NOT_PERFORMED`.

## Continuación V2 autorizada

- [x] Confirmar baseline `290502abbcaaa1f844f2fe40b7d8bb5b634c5496`, árbol
      limpio, rama `main`, `origin/main`, y preservar los artifacts V1.
- [x] Inspeccionar productor/auditor P8, P5-C/P6/P7, periodicidad E13 y
      contrato P9 antes de preparar geometría o ejecutar campaña.
- [x] Reproducir el armado de la geometría KT100 dentro del adaptador P5-C/P6;
      validar las cuatro especies y registrar el resultado acotado.
- [x] Determinar que el error histórico `invalid species state` no se reproduce
      con la inicialización actual; conservar el artifact original sin alterarlo.
- [x] Registrar el hard stop contractual P8/P7/E13 y validar OpenSpec estricto;
      no cambiar código/contratos P4–P9, no crear fixture V2 parcial y no lanzar
      la campaña.
- [x] Ejecutar regresiones focales P5-C/P6/P7/P8: 56 pruebas aprobaron; el
      diagnóstico reproducible de inicialización quedó en
      `results/kt100-hybrid-model-fixture-v2-20261001/bounded-preflight.json`.
- [x] Ejecutar regresiones KT100 V1 y guardas P9: 36 pruebas aprobaron; V1
      mantiene su estado/documentación y P9 conserva su hash preregistrado.
- [x] Ejecutar `git diff --check`, `git lfs fsck` y verificar que el hash
      congelado del spec P9 no cambia.
- [x] Revisión independiente puntual del diff y fundamento del blocker: sin
      defectos concretos; se añadió la diferencia de anchors P8/V2 al registro.
- [ ] Crear y validar un fixture V2 ejecutable cuando el productor/auditor
      congelado pueda aceptar su identidad/topología y P7 periódico sin alterar
      contratos P4–P8.
- [ ] Ejecutar puntos, E13, evidencia primaria, restart/replay, sensibilidad y
      comparación V1/V2 únicamente después de resolver el hard stop autorizado.

Estado de continuación: `KT100_HYBRID_V2_STACK_CONTRACT_BLOCKER`.
`KT100_HYBRID_MODEL_FIXTURE_V2_VERIFIED` NO otorgado. Los resultados V1 siguen
siendo 0D y no convergen a 5000 rpm; no se sustituyen por resultados híbridos.
P9 queda sin cambios y V1 permanece intacto.
