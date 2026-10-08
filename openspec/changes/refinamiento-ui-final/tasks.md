## Implementación
- [x] Comprobar main limpio5e6f474 y preservar rc3/rc4 previas.
- [x] Componentes visuales y navegación jerarquizada, encabezados y foco.
- [x] Resumen operativo y configuración geométrica/2T/4T contextual.
- [x] Simulación y resultados separados en paneles adaptables.
- [x] Comparar bilateral y externos secuencial con estados vacíos útiles.
## Comprobación
- [x] Suite/regresiones y OpenSpec estricto.
- [x] Inspección de ocho vistas en Windows100/125/150%, anchos representativos.
- [x] Revisión independiente puntual y correcciones afectadas.
- [x] Commit fuente limpio y nueva rc4; recorrido EXE con punto/cancelación e históricos.
- [x] README/ayuda/evidencia y commit final, sin publicar/archivar.
## Pendientes preservados
Aceptación manual final, escritorio físico1920×1080, equipo sin Python/offline
aislado y validación experimental separados de esta implementación.

## Evidencia obtenida en esta entrega (16/09/2026)
Automáticas: `.venv\Scripts\python.exe -m unittest discover -s tests`, 247
aprobadas en 36,169 s; log `build/windows/refinement-tests-approved.log`.
Conserva las 245 anteriores y añade estados vacíos/procedencia y columnas compactas.
Incluye navegación/ciclo, borradores, errores, cierre/cancelación, proceso activo,
consulta sin worker, ejemplos y persistencia. No son aceptación visual/manual.
`openspec validate refinamiento-ui-final --strict --no-interactive`: aprobado.

Windows visible automatizado: `tests/verify_workspaces_windows.py`, históricos R2
existentes y datos externos identificados sintéticos, sin nuevas integraciones.
Capturas reales `E:\MotorSim distribucion\Refinamiento UI`: `final-100-1366`,
`final-125-1366`, `compact-150-900`, `final-100-1920`. Ocho vistas inspeccionadas
en cada escala; 18 capturas por recorrido incluyendo vacíos y curvas desplazadas.
Se corrigieron botones sin texto, expansión vertical de Resumen, ancho mínimo
que impedía apilar, separación excesiva de derivados y procedencia sin resultado.
1920×1080 solicitado resulta 1920×881 Qt al 100 %; 1366×768 al 125 % resulta
1366×705 lógicos; 900×650 al 150 % resulta 900×587. El sistema limita la altura
al monitor físico 1440×900. Capturas QWidget.grab: Windows nativo, no offscreen,
pero no prueban una pantalla física 1920×1080. Desplazamiento vertical local
permite consultar el contenido; las tablas conservan su desplazamiento propio.

Revisión independiente: `/root/review_rc2_hardening`, solo lectura, sin defectos
concretos identificados; 12 pruebas workspaces aprobadas y dos capturas inspeccionadas.
Autorrevisión del principal: diff UI, todas las vistas/escala y separación de
estados. El ajuste posterior de altura de los motores se comprueba de forma focalizada.
Comprobación focalizada final: 12 pruebas aprobadas en 2,881 s y capturas renovadas
en `release-100-1366`, `release-125-1366`, `release-150-900`; motores inspeccionados
en las tres escalas. Se aprovecha la altura disponible sin aumentar el mínimo compacto.

## Paquete final y evidencia
Fuente: `d6c4e19b03692ba22301045ed2206da5081b5ac9`, main limpia al construir.
Comando: `.venv-build\Scripts\python.exe packaging/build_windows.py`.
Python3.11.0 / PySide6 6.11.2 / PyInstaller6.22.3 fijados, Windows10 x64 19045.
ZIP `dist/MotorSim-0.1.0-rc4-windows-x64-d6c4e19b.zip`: 43.407.420 bytes;
carpeta 104.904.421 bytes; SHA256
`e4dee7c4469e0d80b7b8ec57ae19d30de86b14851976b35da16fe711d90278c9`.
162 archivos extraídos comprobados idénticos al ZIP tras el recorrido; ejemplos
incluidos sin modificación. Hashes rc3 y rc4 anterior conservados, sin sobrescribir.
EXE: `E:\MotorSim distribucion\Candidata refinada á 0.1.0-rc4\MotorSim\MotorSim.exe`.

Automatización visible del paquete: `tests/verify_distribution_windows.py --exe`
con esa ruta y `--work "E:\MotorSim distribucion\Comprobación refinamiento rc4"`.
Etapas `uxeditor`, `uxpoint`, `uxcancel`, `uxanalysis`, `uxseries`, `examples`,
y `uxvisual --scale 1`, todas aprobadas. Las seis primeras al 150 %; consulta
visual final al 100 %, captura física del escritorio con marco nativo (1350×800).
Sin Python en PATH del EXE, cwd diferente, rutas Unicode y LOCALAPPDATA aislado.
No equivale a comprobar un equipo sin Python instalado ni aislamiento de red.

- Guardar/Nuevo/reabrir preserva Unicode y datos; navegación contextual 4T.
- Cuatro ejemplos: dirty/sin ruta, guardado fuera del paquete, Cancelar/Descartar,
  entradas efectivas8.2 y consulta de histórico sin cálculo.
- Un único punto 2T B100/3000 convergido: 13,703 s. Navegación conserva worker.
- Cancelación cooperativa: 0,281 s; sin hijo activo ni resultado aceptado.
- Resultados/barrido4T R2 previamente existentes, consulta del primer punto,
  comparación A/B y CSV, importación sintética y contraste/exportación: sin worker.
- Presupuesto previo98,157 s conservado en budget.json; añadido13,984 s;
  acumulado112,141 s/300 s. Sin campañas nuevas ni repetición del punto.

Evidencia de cada etapa `*-evidence.json` en la carpeta work, capturas
`rc4-Resumen-1.png`, `rc4-Geometría-1.png`, `rc4-Motor 2T-1.png`,
`rc4-Motor 4T-1.png`, `rc4-Simulación-1.png`, `rc4-Resultados-1.png`,
`rc4-Comparar-1.png`, `rc4-Datos externos-1.png`, `rc4-Contraste inferior-1.png`.
Todas inspeccionadas por el principal; contenido inferior accesible por scroll,
acciones/foco y procedencia visibles. Algunos nombres `rc3-*-150.png` proceden
del guion reutilizado: sus JSON identifican explícitamente este EXE rc4, no rc3.
La ampliación del guion para escala/captura final pertenece al commit de evidencia;
no modifica el código empaquetado. Capturas Qt multiescala y del EXE se distinguen
de pruebas offscreen y de aceptación manual, que permanece pendiente.

Por verificar: aceptación final de producto por la usuaria, escritorio físico
1920×1080 y equipo sin Python/offline aislado. Validación experimental no iniciada
ni atribuida a esta entrega. Cambio sin archivar; commits locales sin publicación.
