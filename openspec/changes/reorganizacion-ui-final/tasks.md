## Implementación
- [x] Leer orden y comprobar Git limpio, preservar rc1/rc2 y evidencia.
- [x] Navegación por tareas, ciclo, título y barra de estado.
- [x] Resumen real con ejecutabilidad y accesos a errores.
- [x] Geometría/formulario adaptables; workspaces Motor2T/4T y contexto.
- [x] Simulación jerarquizada, resultados integrados y series.
- [x] Comparación/externos integrados con estados progresivos.
## Comprobación y entrega
- [x] Conservar cobertura y añadir regresión específica UI.
- [x] Suite completa, OpenSpec estricto y revisión independiente puntual.
- [x] Windows multiescala/ancho: capturas realmente inspeccionadas.
- [x] Commit fuente limpio, reconstrucción candidata, recorrido EXE.
- [x] README/hoja de ruta/evidencia y commit final; sin publicar ni archivar.
## Pendientes preservados
Parada rc1 clasificada F, equipo sin Python, offline aislado, aceptación manual y
validación experimental no se cierran mediante este rediseño.

## Evidencia actual (16/09/2026)

Suite final: 238 pruebas aprobadas en 69,542 s, Qt offscreen explícito;
`build/windows/ux-suite-final.log`. Una corrida anterior se detuvo sin resultado
por falta de finalización; la corrida diagnóstica terminó aprobada. No se atribuye
un fallo de aplicación sin evidencia. OpenSpec 1.3.1 estricto aprobado.
Capturas finales adicionales `100-final`, incluidas curvas completas de resultados
y externos, inspeccionadas después de las correcciones.

Revisión independiente de solo lectura por review_rc2_hardening, una pasada del
diff UX: tres hallazgos reproducidos y corregidos (atributos de diálogo en plot
externo; Escape ocultaba páginas embebidas; ejecutabilidad contaminada por borrador
del ciclo inactivo). Principal integró correcciones y pruebas focalizadas. También
se corrigieron enlaces de atención obsoletos y limpieza de resultados al abrir serie.
No se modificaron validadores científicos ni ejecución asíncrona.

Windows real automatizado con `tests/verify_workspaces_windows.py`; capturas/evidence.json
en `E:\MotorSim distribucion\UX final\100-1366`, `125-1366`, `100-1920`,
`100-900`, `150-900` y `150-final`. Se inspeccionaron Resumen, geometría,
ambos motores, simulación, resultados, barrido, comparación y externos/curvas.
Datos de prueba identificados y resultados históricos R2, sin nuevas integraciones.
100-1366 precede la corrección de enlaces; 150-final incluye correcciones de revisión.
1920 corresponde a ventana Qt de 1920×881 por límite del escritorio 1440×900,
capturada completa mediante QWidget.grab; no es captura de escritorio Full HD.
125 %: 1092×600 lógicos; 150 %: 900×520 lógicos. Foco/scroll local legibles;
sin scroll horizontal global. Navegación/geometría a 640×480 cubiertas por prueba UI.
No se atribuye aceptación manual de la usuaria. rc3 evita sobrescribir rc2 existente.

## Candidata y recorrido final del EXE

Fuente limpia `16097c43628fb523107aa8c661d7ea459db92432` en main, construcción
aprobada mediante `.venv-build/Scripts/python.exe packaging/build_windows.py`.
`dist/MotorSim-0.1.0-rc3-windows-x64-16097c43.zip`, 43.396.296 bytes,
carpeta 104.887.479 bytes. SHA256
`da355109e4126ab58e62b2016ab55b68e828622b69563ff0f52da9a7e7577ae2`.
Windows 10 19045 x64, Python 3.11.0, PySide6 6.11.2, PyInstaller 6.22.3.
Extraído en `E:\MotorSim distribucion\Candidata final á 0.1.0-rc3\MotorSim`.
rc1/rc2, sus ZIP y evidencias conservados. Sin cambio del worker ni formatos.

Automatización externa `tests/verify_distribution_windows.py`, etapas uxeditor,
uxanalysis, uxseries, uxpoint y uxcancel. Evidencia en
`E:\MotorSim distribucion\Comprobación final rc3`, archivos `*-evidence.json`;
`Editor teclado/uxeditor-evidence.json` acredita la navegación corregida del harness.
Se ejecutó EXE directamente, cwd distinto y PATH sistema, sin PYTHONPATH/VIRTUAL_ENV.
UIA Select no cambia índice actual de QTreeWidget: primeros intentos de análisis
se detuvieron antes de abrir resultados. Se corrigió solo el harness a teclado
real y se cerraron ventanas propias residuales antes del recorrido aprobado.
No se borró la evidencia fallida ni se recreó el paquete por cambios de pruebas.

Comprobados guardar/Nuevo/reabrir Unicode y navegación 4T/geometría; abrir resultado,
serie y consultar punto; comparación compatible/exportar CSV; declaración/previa/
guardar importación sintética, contraste y exportación sin ejecutar worker.
Capturas de escritorio del EXE realmente inspeccionadas: rc3-resumen-150.png,
rc3-comparacion-150.png, rc3-externos-150.png, rc3-punto-150.png y
rc3-punto-historico-150.png. Scroll vertical local permite consultar contenido.
Estas operaciones son automatizadas con ventanas visibles, no aceptación humana.

Único punto nuevo 2T referencia B100/3000: convergido, 10 ciclos,
W_C 16,49050751206088 J, pmax 1331530,846070603 Pa; balances aprobados.
Entradas, todos los ciclos y muestras físicas exactamente iguales a la referencia
rc2, comprobación en numerical-comparison.json. Se excluye únicamente run_id de
identidad en muestras; tiempos/memoria no se comparan por igualdad. No hubo otra
integración para comparar. Integración 13,469 s, escritura 0,219 s, total 13,875 s,
percibido 15,203 s. Cancelación 0,250 s, cooperativa, diagnóstico no aceptado y sin
worker huérfano. Total de esta orden 13,719 s; acumulado histórico 98,157 s de 300 s.
Sin repetir estudios A/B/C, R2 ni barridos físicos. Pruebas/harness posteriores al
commit fuente y documentación se registran aparte; código empaquetado intacto.

## Por verificar, sin atribuir aceptación
- [ ] Aceptación manual final de la usuaria para esta navegación/candidata.
- [ ] Escritorio físico 1920×1080: disponible 1440×900, limitación descrita arriba.
Se conservan por separado los pendientes anteriores de distribución sin Python,
offline aislado, clasificación F del incidente rc1 y validación experimental.
