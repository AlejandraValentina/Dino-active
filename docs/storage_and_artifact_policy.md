# Política de almacenamiento de Dino 2T

Estado: operativa desde 2026-10-26. Alcance: paquetes Windows, temporales de
build y campañas/barridos RPM. No cambia el solver ni elimina datos existentes.

## Rutas

- `DINO_ARTIFACT_ROOT` define la raíz durable para campañas, resultados y
  paquetes. Si no se define, se usa `~/Dino-artifacts`, independiente de la
  letra de unidad asignada al perfil.
- `DINO_BUILD_WORK_ROOT` define el área temporal de PyInstaller. Si no se
  define, se usa `<directorio temporal del sistema>/Dino-build-work`.
- `packaging/build_windows.py --output-root ... --work-root ...` permite
  sobrescribir ambas rutas por invocación. El paquete va a
  `<DINO_ARTIFACT_ROOT>/Windows`; ya no se acumula por defecto en `repo/dist`.
- Un usuario puede ubicar `DINO_ARTIFACT_ROOT` y `DINO_BUILD_WORK_ROOT` en
  volúmenes distintos. No hay una ruta fija a C: o E:.

## Preflight y margen

`python scripts/agents/storage_preflight.py --require-gib PATH=GiB` informa el
espacio libre por volumen sin crear directorios. La reserva predeterminada es
2 GiB por volumen (`DINO_STORAGE_RESERVE_GIB` permite cambiarla).

- Un build reserva 1,5 GiB para la distribución extraída, ZIP y checksum, más
  1 GiB para el área temporal de PyInstaller y el margen de 2 GiB. Si ambos
  destinos comparten volumen, el preflight suma las estimaciones y añade una
  sola reserva para ese volumen.
- FULL_RPM_SWEEP usa 9 GiB como crecimiento estimado por campaña. Ese valor
  parte del mayor árbol observado (8,32 GiB) con redondeo conservador; el
  margen libre obligatorio de 2 GiB se añade aparte. El preflight conserva esa
  estimación completa también al reanudar: es deliberadamente conservador y no
  confía en que el tamaño parcial o manifest refleje todo el crecimiento que
  falta.
- Un preflight insuficiente o incapaz de localizar el volumen detiene el
  proceso antes de crear artefactos. No degrada precisión, horizonte ni
  checkpoint.
- Para revisar una campaña antes de autorizarla, por ejemplo:
  `python scripts/agents/storage_preflight.py --require-gib "$HOME/Dino-artifacts/engine-physics-v1/full-rpm-sweep-v1-impl2=9"`

## Retención y limpieza

No se purgan archivos automáticamente. Reglas de preservación:

- Preservar proyectos y configuraciones editables, referencias de resultados,
  evidencia científica primaria, resultados históricos y checkpoints que
  permitan reanudar o auditar una campaña.
- Preservar el ZIP y carpeta extraída del rc7 aceptado; sus commits, hash,
  pruebas y limitaciones están en el recibo de Commercial Readiness V1.
- `dist/` y los antiguos paquetes trial son reproducibles en principio, pero
  los metadatos de los árboles inspeccionados indican `source_dirty=true`.
  El hash de commit por sí solo no reconstruye el contenido de esos paquetes.
  No tratarlos como duplicados idénticos sin comparar hashes del paquete y
  metadatos completos.
- `build/` y los temporales PyInstaller son regenerables y no son evidencia
  científica. Pueden ser candidatos a limpieza tras revisar que no haya un
  proceso activo ni una investigación de build en curso.
- `.venv-build/` es regenerable desde Python 3.11.0 y
  `packaging/requirements-build.txt`, pero cuesta tiempo reconstruirlo y está
  ligado a la receta de build. Preservarlo como entorno de trabajo; no limpiarlo
  como si fuera caché descartable.
- El árbol de recuperación `C:/Dino-artifacts/recovery/...Windows` fue
  verificado byte-a-byte contra `E:/Dino-artifacts/Windows` el 2026-10-23.
  Es redundante, pero tiene función de copia de recuperación; no borrar sin una
  decisión explícita sobre qué copia queda como referencia.

## Inventario inicial: 2026-10-26

Los tamaños son bytes regulares bajo cada raíz, expresados en GiB decimales
binarios (2^30); son valores observados y no órdenes de borrado.

| Ruta | Tamaño | Clasificación | Candidato / riesgo |
|---|---:|---|---|
| `repo:dist` (volumen E:) | 6,159 GiB | 42 trial trees + 42 ZIPs + checksums; build products | Candidato para revisión. Los 42 árboles inspeccionados son `source_dirty=true`; recuperar 6,16 GiB podría requerir conservar algunos para reproducir auditorías históricas. |
| `repo:build` (volumen E:) | 0,832 GiB | intermediarios PyInstaller | Regenerable. Verificar que ningún build esté activo y autorizar antes de limpiar; no borrar ahora. |
| `repo:.venv-build` (volumen E:) | 0,680 GiB | entorno Python de build fijado | Regenerable pero necesario para empaquetar sin reinstalar dependencias. Preservar. |
| `external artifact root (E:)/Windows` | 7,296 GiB | paquetes extraídos y ZIPs históricos | Varios paquetes rc6/rc7 de ~1,1 GiB más ZIPs; `build.json` de los paquetes listados marca `source_dirty=true`. Candidato a deduplicación sólo tras comparar hashes y escoger referencias; preservar hasta autorización. |
| `external recovery copy (C:)/...Windows-20261023` | 7,296 GiB | copia verificada del árbol anterior | Candidato duplicado; riesgo de perder la única copia si se elimina el árbol E antes de validar otra copia. No borrar. |
| `external artifact root (C:)/Windows` | 2,752 GiB | paquete rc7 aceptado + paquete trial anterior y ZIPs | Preservar rc7 `fc275421` limpio (1,107 GiB extraído + 0,269 GiB ZIP); paquete anterior `eb143f67` es candidato una vez que el rc7 aceptado esté respaldado. |
| `external artifact root (E:)/engine-physics-v1` | 9,65 GiB | resultados de ingeniería y campañas | Preservar. Incluye el barrido de 8,32 GiB y resultados/checkpoints necesarios para auditoría o recuperación; no es caché de build. |
| `external artifact root (E:)/periodic-rpm-curves-v1-20261023` | 1,01 GiB | curvas/resultados históricos | Preservar; evidencia histórica. |

No se eliminaron archivos ni se trasladó información durante este cierre.
Proyectos, configuraciones, resultados científicos y checkpoints quedan fuera
de cualquier lote de limpieza automática.

El inventario detallado y la comprobación de espacio observada (E: rechaza
9 GiB + reserva; C: acepta 9 GiB + reserva; build de 2,5 GiB + reserva cabe en
E:) están en `results/storage-control/storage-inventory-2026-10-26.json`.
