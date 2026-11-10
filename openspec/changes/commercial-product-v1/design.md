## Context
La base técnica integra C05 en `main` y conserva la baseline funcional
`DINO_COMMERCIAL_READINESS_V1` (rc7 TRIAL). El objetivo comercial exige
distribución, soporte, recuperación y operación, no una reescritura del solver.

## Decisions
### 1. Separación funcionalidad / validación
Una función comercial puede estar completa sin ser una validación científica.
Calibración, validación experimental y claims predictivos quedan en CP3/CP4 y
sólo avanzan con datos medidos. No se inventan parámetros ni se relajan
tolerancias para publicar.

### 2. Identidad de producto y soporte
“Acerca de Dino” muestra versión, build, commit, esquemas, estado científico,
licencias de terceros y contacto. El diagnóstico exporta un ZIP con identidad,
entorno, configuración no sensible, proyecto opcional y logs; no incluye
credenciales ni telemetría automática.

### 3. Recuperación fuera del repositorio
Autosave y recuperación viven bajo la raíz de artefactos, nunca dentro del
repositorio. El borrador no reemplaza el archivo del usuario: al recuperar se
abre como copia y se pide confirmación para guardar.

### 4. Recientes y portabilidad
La lista de recientes es por familia (2T/4T), acotada y con poda de entradas
inexistentes. Los bundles portables de CP1 deberán preservar hashes y no
promocionar históricos legacy.

### 5. Licenciamiento y distribución
El modelo de licencia/activación, el canal de actualización y la telemetría son
decisiones del dueño. CP0 deja el contrato, la UI de about/soporte y la política
de release; CP2 implementa el modelo elegido sin DRM improvisado.

## Alternatives considered
- **Publicar rc7 como comercial validada:** se descarta; es TRIAL funcional sin
  validación experimental.
- **Agregar telemetría por defecto:** se descarta por privacidad y por no ser
  necesaria para CP0.
- **Implementar undo/redo global antes de la recuperación:** se posterga a CP1;
  CP0 prioriza no perder datos.
- **Completar validación con supuestos sintéticos:** se descarta; CP3 es
  data-gated.

## Risks / Trade-offs
- Autosave agrega I/O y archivos de recuperación; se acotan y se limpian al
  guardar/descartar.
- Un instalador/actualizador introduce seguridad y soporte; CP2 requiere
  decisión y pruebas específicas.
- El producto puede venderse como herramienta TRIAL/engineering sin CP3, pero
  no como simulador validado.
- No se modifican P0–P9, ecuaciones, tolerancias ni evidencia histórica.

### 6. CP1 — orden y dependencias
La base es `main = 864f47f` con CP0 y la navegación unificada integrados.
CP1 se implementa en tres olas:
1. `CP1-UNDO-REDO`, `CP1-PDF-REPORT` y `CP1-TEMPLATES-ONBOARDING` (paralelas).
2. `CP1-PROJECT-BUNDLES` (depende de undo/redo para que el historial no
   interfiera con la exportación/importación).
3. `CP1-BATCH-QUEUE` y `CP1-COMPARISON-LEGACY-UX` (dependen de bundles para
   persistencia y procedencia de trabajos/resultados).

Cada componente exige pruebas funcionales, negativas, persistencia y
compatibilidad. La aceptación Windows de CP1 es separada de la aceptación en
fuente y no se infiere de una UI que sólo muestra la función.
