## Implementación
- [x] Comprobar repositorio y referencia confirmada; preservar eliminación ajena de redme.txt.
- [x] Componentes/paleta compartidos y shell accesible.
- [x] Resumen, cuatro archivos como copia y preparación real.
- [x] Simulación/contexto/estados/gráficos y ocho vistas coherentes.
## Comprobación
- [x] Suite pertinente y OpenSpec estricto.
- [x] Windows visible 100/125/150 %, anchos representativos y capturas inspeccionadas.
- [x] Revisión independiente puntual y correcciones.
- [x] Commit fuente, rc5 preservando rc1–4; recorrido EXE, dos puntos y cancelación.
- [x] Comparación exacta con resultados preservados y documentación.
- [x] Registrar commit de evidencia final.
## Pendientes
Aceptación manual final no atribuida; no archivar ni iniciar validación experimental.

## Evidencia de fuente (17/09/2026)
- Base e30356a2b3034f88e48e4aaa2d8b81d769a4dfae main; única modificación
  previa: eliminación ajena de redme.txt, preservada fuera del commit.
- Suite: 258 pruebas OK, 69,976 s; build/windows/cae-tests.log.
- Revisión independiente /root/review_rc2_hardening, solo lectura: encontró
  NameError en Detalles por bloque duplicado. Corregido; ocho pruebas CAE OK
  incluyen Detalles sin worker. 12 workspaces y 17 externos OK después de ajustes.
  La invocación inicial por módulos de dos suites falló por rutas de importación;
  se ejecutaron correctamente mediante unittest discover, sin cambios de producto.
- Validación: openspec validate implementacion-ui-cae-final --strict --no-interactive.
- Autorrevisión: capturas de Windows nativo bajo E:/MotorSim distribucion/UI CAE rc5.
  Se inspeccionaron Resumen 2T/4T, vacío, Simulación con histórico, motores,
  Geometría, Resultados, comparación y externos/curvas. Contexto lateral amplio,
  colapsado debajo en compacto; teclado y ausencia de scroll global en pruebas.
- Correcciones visuales: selector truncado, acción primaria sin fondo por cascada,
  altura de tabla y propagación de mínimos de panel. El capturador ahora espera
  eventos de layout antes de grabar, evitando capturas transitorias solapadas.
- Capturas no son aceptación manual ni ejecución nueva de los históricos R2.
  QWidget.grab sobre ventana Windows real. Monitor físico 1440×900: tamaño
  solicitado 1920×1080 limitado a 1920×881 lógicos; 1366×768 al125 % a1366×705;
  900×650 al150 % a900×587. Full HD físico permanece por verificar.

## Candidata final y recorrido de paquete
Fuente final 8cbd0bfe580e4221f0f1d496bb9f0429827e3d73, sobre implementación
5ee49e21ca37f909b3e2c3cd40347d90ce0981ec. Corrección adicional: aviso stale
junto al estado, visible aunque el contexto esté colapsado. Ocho pruebas CAE
aprobadas de nuevo en2,022s. Revisor independiente confirmó Detalles y resolución
frozen de Ejemplos; prueba focalizada0,246s. Sin otra revisión general.

Construcción .venv-build/Scripts/python.exe packaging/build_windows.py en
E:/dino/build-cae-final, checkout limpio; fuente principal conserva D redme.txt.
Windows10 x64 19045, Python3.11.0, PySide6 6.11.2, PyInstaller6.22.3.
Primera construcción 5ee49e21 conservada en su checkout, no candidata final;
no se ejecutaron puntos con ella. La candidata final no sobrescribe paquetes.
ZIP dist/MotorSim-0.1.0-rc5-windows-x64-8cbd0bfe.zip:43.420.101bytes;
carpeta104.918.005bytes; SHA256
f3159c9dd91ddf64e7b02901a9488e6eea60f4c9346eed768bbf2e4f835c9d18.
EXE E:/MotorSim distribucion/Candidata CAE 0.1.0-rc5/MotorSim/MotorSim.exe.
162 archivos coinciden exactamente con el ZIP después del recorrido.
MotorSimWorker.exe y los cuatro Ejemplos presentes; sin Python externo.

Automatización visible tests/verify_distribution_windows.py sobre EXE extraído,
cwd distinto y PATH sistema: cae-examples100%, cae-points100%, uxcancel150%,
uxanalysis150%, uxeditor125%, uxseries125%. Todas aprobadas. Guardar/Nuevo/reabrir
Unicode, cuatro JSON cargados como copia sin ruta y originales intactos,
ciclo contextual/entradas, navegación conservando worker, cancelación cooperativa,
resultados, punto histórico, comparación/CSV e importación/contraste/exportación.
Las etapas históricas del harness conservan prefijos rc3 en ciertos nombres de
captura; sus JSON identifican el EXE rc5 y el factor real (incluido125%).
No equivalen a aceptación manual ni a evidencia histórica de versiones anteriores.

Dos puntos reales B100/3000 (únicos de esta entrega):
- 2T: convergido10ciclos;13,516s;W_C16,49050751206088J;pmax1331530,846070603Pa;
  mayor balance independiente0,0004459656622212729%.
- 4T: convergido7ciclos;14,594s;W_C50,52602475854359J;pmax2618462,4643861516Pa;
  mayor balance independiente0,00007683375214576464%.
- Cancelación cooperativa0,187s; sin proceso hijo restante ni ciclo aceptado.
Comparación EXACTA: todos los campos científicos de result y todas las muestras
cycles/partial, incluidas trayectorias/balances/controlador/contadores. Se excluyen
seconds, memoria pico, run_id y tiempos del manifest por no ser deterministas.
Referencia2T: rc4 20260916-132839-df87fe068f;4T:R2/gui-sweep/point-02.
Evidencia exact-comparison.json conserva rutas y lista de claves comprobadas.
Consumo28,297s; acumulado de distribución140,438/300s, sin reiniciar presupuesto.

Evidencia externa completa: E:/MotorSim distribucion/Comprobación CAE rc5.
Copias versionadas: results/ui-cae-rc5-20260917 (integridad, referencias,
registros de etapas y tres capturas representativas). Capturas fuente finales
settled-100-1920, settled-125-1366 y source-8cbd0bf-150 en UI CAE rc5, además de
las anteriores conservadas. Se inspeccionaron alineación, unidades, desplazamiento,
contexto, estados y curvas; automatización Windows real, no offscreen ni aceptación.

## Por verificar — cierre de usuaria
Aceptación manual final; monitor físico1920×1080; equipo sin Python/offline aislado.
No se archiva ni se inicia validación experimental. Commits locales, sin publicar.
