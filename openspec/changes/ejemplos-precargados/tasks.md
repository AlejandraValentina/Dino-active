## Implementación
### Continuación: JSON físicos (16/09/2026)
- [x] Generar cuatro proyectos v6 desde definiciones canónicas en examples/projects.
- [x] Generador determinista y empaquetado que copia/verifica los cuatro originales.
- [x] Validación, igualdad completa con referencias, diferencia única, round-trip y ejecutabilidad sin solver: 10 pruebas pertinentes aprobadas en 2,681 s.
- [x] Apertura real 2T/4T, geometría, configuración, conductos, listo y Guardar como sin alterar originales.
- [x] Revisión puntual, OpenSpec, documentación, commit y paquete identificado.

El estado y evidencia anteriores siguientes se conservan como históricos.
Continuación: Windows automatizado con EXE rc4 d6c4e19b, Archivo/Abrir para
los dos JSON físicos del repositorio; geometría, lumbreras/válvulas y conductos,
Listo para simular y Comprobar entradas aprobados. Guardar como crea copias
equivalentes y conserva los bytes originales. Sin worker. Seis capturas en
`E:\MotorSim distribucion\JSON físicos repositorio`, inspección visual del principal;
no aceptación manual de la usuaria. Revisión independiente puntual de
review_rc2_hardening sin defectos identificados; dos pruebas de datos aprobadas
sin escribir en el repositorio ni ejecutar solver. OpenSpec estricto aprobado.
Pruebas finales pertinentes: 11 aprobadas en 31,498 s; incluye preservación de
archivos ajenos y rechazo de una definición inválida antes de cualquier escritura.

Fuente de esta continuación: `8d6f41dc08f113e3c60503420b7a798b2d9721c4`.
Después del commit apareció una eliminación ajena de `redme.txt` en la copia
principal. El primer intento de build se detuvo por árbol no limpio; sin modificar
ni registrar esa eliminación. Construcción final desde worktree limpio aislado
`E:\dino\build-json-8d6f41d`, reutilizando .venv-build mediante junction, sin instalar
dependencias. Log `build/windows/physical-examples-build-isolated.log` en la copia
principal. Python3.11.0/PySide6 6.11.2/PyInstaller6.22.3, sin física/solver nuevos.
ZIP copiado a `dist/MotorSim-0.1.0-rc4-windows-x64-8d6f41dc.zip`, 43.408.653 bytes;
SHA256 `cb4a68fe7322f04b9cf804515a4f2ea05dab8dea84fbf94dcd8af8eaf05a8c6d`.
Extracción `E:\MotorSim distribucion\Candidata JSON físicos rc4\MotorSim`;
los cuatro JSON bajo Ejemplos coinciden byte por byte con repositorio y ZIP.
Paquetes anteriores conservados. Build.json identifica fuente limpia, no trial.

Recorrido final con `tests/verify_distribution_windows.py --stage physical-examples
--scale 1 --exe "E:\MotorSim distribucion\Candidata JSON físicos rc4\MotorSim\MotorSim.exe"
--work "E:\MotorSim distribucion\JSON físicos paquete"`: aprobado. Archivo/Abrir
2T/4T desde el paquete, geometría, configuración y conductos, Listo para simular,
Comprobar entradas y Guardar como; copias iguales, bytes originales intactos.
EXE con PATH de sistema y cwd externo, archivos autónomos sin rutas absolutas
en JSON. No se eliminó/renombró el repositorio para comprobarlo. Cero workers.
Registro `physical-examples-evidence.json` y seis capturas reales en esa carpeta;
inspección visual del principal de configuración/estado, separada de las pruebas
automáticas y de aceptación manual pendiente. OpenSpec estricto vuelto a aprobar.
Commit posterior registra esta evidencia; sin publicar ni archivar.
- [x] Comprobar main limpio, rc3 y referencias canónicas; preservar evidencia.
- [x] Definición común de cuatro ejemplos e identificación sintética.
- [x] Menú de carga protegida, proyecto editable sin ruta, origen de simulación real.
- [x] Integrar los cuatro JSON en empaquetado rc4 sin cambiar formatos.
## Comprobaciones
- [x] Pruebas de campos, variantes, dirty/ruta, guardado y cancelaciones.
- [x] Entradas 2T/4T y comparación por fixtures/históricos sin integrar.
- [x] OpenSpec estricto y revisión puntual.
- [x] Commit limpio y candidata rc4; recorrido/captura real del EXE.
- [x] README/ayuda y registro final de evidencia, sin publicar ni archivar.
## Pendientes
Aceptación manual final y pendientes históricos de distribución/validación
experimental conservados; no se cierran mediante ejemplos sintéticos.

## Evidencia
Git inicial limpio en main, 343818a; remoto origin conservado, sin operaciones de red.
Suite completa: 245 pruebas aprobadas en 29,941 s (`build/windows/examples-suite.log`).
Después se actualizó la cabecera de preparación cuando el origen ya era Proyecto
actual: 7 pruebas específicas aprobadas en 6,426 s, incluidas entradas efectivas.
OpenSpec 1.3.1 estricto aprobado. Revisión independiente de solo lectura por
review_rc2_hardening, sin hallazgos concretos: 6 pruebas y proceso DiagnosticProcess
comprobaron conservación de ejecución activa al cargar otro ejemplo. Sin física.
El principal conserva la responsabilidad y probó además fallo/cancelación de guardado.
Comparación 2T/4T con fixtures explícitos: única diferencia geométrica compresión;
no constituye convergencia ni evidencia experimental.

## Paquete y Windows (16/09/2026)
Fuente limpia `4e7e559f61d7b19349e0eb37258340c78097451f`, main. rc4 construida
con la receta fijada, Python 3.11.0 / PySide6 6.11.2 / PyInstaller 6.22.3;
`build/windows/examples-build.log`. ZIP
`dist/MotorSim-0.1.0-rc4-windows-x64-4e7e559f.zip`, 43.396.571 bytes;
carpeta 104.894.037 bytes. SHA256
`17bcefc76b6275ca36c19068882cc026b878e8db55b7f5099f219ced305841a4`.
Extraído en `E:\MotorSim distribucion\Candidata final á 0.1.0-rc4\MotorSim`.
rc3 conserva su ZIP/hash `da355109e4126ab58e62b2016ab55b68e828622b69563ff0f52da9a7e7577ae2`.

Recorrido externo UIA/teclado con `tests/verify_distribution_windows.py --stage examples`,
EXE directo, ruta Unicode, cwd diferente y PATH de sistema, sin PYTHONPATH/VIRTUAL_ENV.
Windows 10 19045, QT_SCALE_FACTOR=1.5. La primera localización de menú por clic UIA
falló antes de cargar datos; se comprobó el menú real y se corrigió únicamente
el harness para usar Alt+A, E y flechas. No se cambió el EXE. Evidencia fallida
conservada y recorrido posterior aprobado; sin iteraciones físicas.

`E:\MotorSim distribucion\Comprobación final rc4\examples-evidence.json` registra
las cuatro opciones, carga 2T y Guardar como, carga 4T8.2 y comprobación de entradas,
navegación contextual, dirty/sin archivo, protección Cancelar/Descartar y guardado
4T referencia. Lectura explícita del histórico R2 copiado a Historico/, fuera del
repositorio, sin worker. Ningún resultado se presenta como recién calculado.
Captura `rc4-ejemplo-4t-150.png`, escritorio real del EXE, inspeccionada: identificación
sintética, compresión8.2, motor4T visible, cambios pendientes y sin archivo asociado.
`resources-evidence.json` acredita los cuatro JSON iguales a las definiciones
canónicas y a los bytes del ZIP tras el recorrido: ningún original sobrescrito.
No hubo nuevas integraciones. Automatización e inspección separadas de aceptación humana.
La documentación y el ajuste del harness se registran en un commit posterior al
fuente; no cambian el código empaquetado. Sin push/tag/release ni archivo OpenSpec.

- [ ] Aceptación manual final de la usuaria, expresamente pendiente.
