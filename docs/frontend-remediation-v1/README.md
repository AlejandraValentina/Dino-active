# Remediación del frontend de Dino — F0 + F1

Trabajo aislado en `feat/dino-frontend-remediation-v1`, desde `696b8fc`.
La aceptación de esta entrega cubre integridad y un incremento del recorrido de
usuario en fuente. No cierra los 23 hallazgos ni constituye aceptación del
instalador. El estado verificable está en
[`acceptance.json`](../../results/frontend-remediation-v1/acceptance.json).

- [Causas de los tres P0](p0-causes.md).
- [Arquitectura, alcance por hallazgo y fases siguientes](architecture-and-roadmap.md).
- [Verificación y límites de evidencia](verification.md).
- [Capturas](../../results/frontend-remediation-v1/captures/).
- [Registro de interacciones](../../results/frontend-remediation-v1/interaction-journal.jsonl).

Los tres P0 recibieron correcciones estructurales: resolución explícita de
borradores, cierre transitivo de artefactos portables y guardado con ruta
normalizada/fallo visible. F1 agrega contexto persistente, formularios físicos
nativos, navegación común, preparación con presupuestos, acceso al último
resultado 2T, preflight de comparación y revisión de contenido portable.

## Probar la fuente

Desde este worktree, con el entorno de dependencias de Dino activo:

```powershell
python -m motorsim.desktop
```

La evidencia de esta entrega usa Python 3.11 y PySide6 6.11.2 en Windows,
no el paquete rc7 anterior. Abrir ese paquete no muestra estos cambios.
El worktree de preparación C05 original permanece separado.

## Lo que sigue

Permanecen pendientes la cola general 2T/nativa, vinculación explícita de resultados
externos, selector de recuperación con previsualización, equivalencia de acciones
de variantes, diagrama coordinado, exploración gráfica avanzada, redistribución
completa en compacto y UAT de accesibilidad. La tabla de arquitectura detalla qué
se cubrió parcialmente y el criterio de salida de cada fase posterior.

La comparación de presentación usa un fixture sintético declarado. Las corridas
reales de este recorrido verifican integración de la aplicación; no validan
experimentalmente el motor ni demuestran capacidad predictiva.
