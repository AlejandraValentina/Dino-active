# Dino Commercial Product V1 — hoja de ruta

Fecha: 2026-11-10. Base técnica: `main` con C05 integrado; baseline
funcional congelada `DINO_COMMERCIAL_READINESS_V1` (rc7 TRIAL) y candidato
técnico `9298cb66` (rc12 no-trial) aceptado para el alcance C05.

## 1. Objetivo y definición de “comercial”

El objetivo es una aplicación de escritorio **distribuible, soportable,
recuperable y auditable**, con flujos 2T y 4T completos. “Comercial” no
significa validación científica: la precisión, calibración y capacidad
predictiva son gates separados y dependen de datos medidos.

La V1 comercial debe poder instalarse, activarse/actualizarse según el modelo
elegido, abrir y recuperar proyectos sin pérdida, ejecutar los flujos
soportados, exportar resultados trazables, diagnosticarse ante fallos y
declarar con precisión qué está validado y qué no.

## 2. Estado de partida

| Elemento | Estado |
|---|---|
| Desktop 2T | Flujo funcional TRIAL, historial, comparación, curvas, cancelación/checkpoint |
| Desktop 4T nativo | API, A/B estricto, cancelación, exportaciones, trazabilidad |
| 4T 0D referencia | Curva RPM, persistencia, reapertura, estados parcial/obsoleto |
| Aseguramiento | C01/C03, C02/C04, C05; recepción terminal y cierre de workers |
| Windows | Candidato `9298cb66` PASS para el alcance C05; sin publicación |
| Validación | Experimental `NOT_PERFORMED`; calibración `NOT_PERFORMED`; predictiva `NOT_CLAIMED` |

## 3. Fases y dependencias

| Fase | Depende de | Objetivo observable |
|---|---|---|
| CP0 — hardening comercial | C05 | Identidad de producto, licencias/EULA, about, diagnóstico, proyectos recientes, autosave/recuperación, cierre seguro, política de update |
| CP1 — completitud de flujo | CP0 | Undo/redo, bundles de proyecto 2T/4T, PDF, plantillas/onboarding, batch/cola, mejoras de comparación e importación legacy |
| CP2 — operación comercial | CP1 | Instalador/portable, update, licenciamiento/activación, privacidad/telemetría opt-in, soporte, firma/checksums, release notes |
| CP3 — datos y validación | CP0 + datos | Paquetes D2/D4, calibración, VAL2/VAL4, PRED2/PRED4, incertidumbre. **Data-gated** |
| CP4 — aceptación comercial | CP2 + alcance CP3 | UAT, estabilidad/performance, seguridad, licencias, distribución y aceptación del dueño |

## 4. CP0 — hardening comercial (primera implementación)

### CP0-PRODUCT-INFO
- Diálogo “Acerca de Dino” con versión, commit/build, esquema de proyectos,
  estado científico, licencias de terceros y contacto de soporte.
- Debe estar disponible en 2T y 4T sin depender de documentación externa.

### CP0-DIAGNOSTICS
- Exportar un ZIP de diagnóstico con identidad de build, versión, sistema,
  configuración no sensible, proyecto actual (si el usuario lo incluye) y
  últimos logs. Sin credenciales, sin telemetría automática.
- El ZIP debe ser legible por soporte y no modificar el proyecto.

### CP0-RECENT-PROJECTS
- Lista de proyectos recientes 2T/4T en `QSettings`, con apertura directa,
  poda de entradas inexistentes y límite acotado.
- No debe mezclar proyectos 2T y 4T en un mismo flujo.

### CP0-AUTOSAVE-RECOVERY
- Autosave periódico sólo cuando el proyecto está sucio, fuera del repositorio,
  bajo la raíz de artefactos.
- Al iniciar, ofrecer recuperación de un borrador; nunca sobrescribir el
  archivo original sin confirmación.
- Limpiar el borrador al guardar correctamente o al descartar.

### CP0-CLOSE-SAFE
- Cierre con ejecución activa: cancelar, esperar y no destruir widgets con
  callbacks pendientes. Sin workers huérfanos.
- Reutilizar la evidencia C05; no relajar los checks.

### CP0-RELEASE-POLICY
- Documentar versionado, canal de actualización, política de licencias/EULA,
  requisitos de build y checklist de candidato.
- La licencia/activación concreta es una decisión del dueño; CP0 deja el
  contrato y el lugar de integración, no inventa precios ni DRM.

### CP0-REGRESSION
- Tests offscreen de about/diagnóstico/recientes/autosave.
- Suites C05 y empaquetado; candidato Windows antes de aceptar CP0.

## 5. CP1 — completitud de flujo

- **Undo/redo** por contexto (2T, 4T 0D y 4T nativo) con límites y limpieza al
  guardar/cambiar de proyecto.
- **Bundles de proyecto** 2T/4T: proyecto + resultados + configuración +
  trazas, rutas portables y verificación de hashes; importación sin
  promocionar históricos legacy.
- **PDF** de informe técnico además de HTML/CSV.
- **Plantillas/onboarding**: proyecto inicial, ejemplos, guía breve y
  verificación de primeros pasos.
- **Batch/cola**: ejecutar varios puntos/curvas con presupuesto, cancelación y
  reanudación.
- **Comparación**: pares exactos, contexto, exclusiones y exportación.
- **Importación legacy**: explicar clasificación y límites sin promoción
  automática.

## 6. CP2 — operación comercial

- Instalador/portable firmado o con checksums; desinstalación limpia.
- Actualización: comprobación manual/opt-in, notas de versión, rollback.
- Licenciamiento/activación: modelo, claves, expiración, modo TRIAL y
  recuperación; decisión del dueño.
- Privacidad: sin telemetría por defecto; opt-in explícito y documento.
- Soporte: diagnóstico, contacto, SLA y base de conocimiento.
- Release notes y política de compatibilidad de proyectos/resultados.

## 7. CP3 — datos y validación (data-gated)

No se puede cerrar con software ni con supuestos inventados.

- **D2:** Cahoon MK.1 / X30 con volumen libre de cárter, ángulo de referencia,
  fronteras e inclusiones; MT110S como referencia complementaria.
- **D4:** geometría medida, alzadas/tiempos, Cd directo/inverso y convención de
  área, condiciones, presión/par/flujo y combustión.
- **VAL2/VAL4:** protocolo preregistrado, holdout, incertidumbre de medición,
  numérica, de parámetros y de forma del modelo.
- **PRED2/PRED4:** claims absolutos y de diferencia de diseño, con covarianza
  y dominio explícito.

Sin CP3, el producto puede ser comercial como **herramienta de ingeniería
TRIAL/auditable**, pero no como simulador validado o predictivo.

## 8. CP4 — aceptación comercial

- UAT con usuarios representativos y casos de uso documentados.
- Estabilidad: sesiones largas, crash-free, recuperación y cierre.
- Performance: presupuestos medidos, sin degradar precisión/CFL/tolerancias.
- Seguridad y privacidad: dependencias, licencias, datos del usuario.
- Distribución: instalador/paquete, hashes, licencias, soporte.
- Aceptación del dueño y decisión explícita de publicación.

## 9. Criterios de cierre

La V1 comercial se declara sólo cuando CP0, CP1, CP2 y CP4 están cerrados y
CP3 está cerrado para cada claim incluido. Si no hay datos medidos, la
publicación debe declararse como TRIAL/engineering y no puede incluir claims
de validación o predictivos.

## 10. Riesgos y decisiones abiertas

- Modelo de licenciamiento/activación y canal de distribución (dueño).
- Telemetría: por defecto no; cualquier opt-in requiere documento y control.
- Datos medidos insuficientes para 4T y para el cárter X30.
- Coste de soporte de históricos legacy y bundles portables.
- No se modifican ecuaciones, tolerancias, contratos P0–P9 ni evidencia
  histórica para “hacer pasar” una función comercial.

## 11. Orden de implementación

1. CP0 completo y aceptado en Windows.
2. CP1 undo/redo + bundles + PDF.
3. CP2 licenciamiento/instalador/update según decisión del dueño.
4. CP3 en paralelo cuando lleguen datos; no bloquear CP0–CP2.
5. CP4 aceptación comercial.

El plan machine-readable está en
`results/commercial-product-v1/plan.json`; la cola operativa en
`program-status.json`.
