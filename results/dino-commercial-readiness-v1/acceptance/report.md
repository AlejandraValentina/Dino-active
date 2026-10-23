# DINO Commercial Readiness V1 — aceptación parcial

Fecha: 2026-10-23. Ejecución de aceptación en Windows 11 desde el ZIP TRIAL y el EXE extraídos fuera del repositorio. La precisión experimental no se evalúa ni se afirma.

## Implementado

- El proyecto nuevo guiado parte de una plantilla técnica sin resultados; permite cambiar bore, stroke, admission control y clasificación de procedencia. Diámetros y carrera aparecen como medido y estimado; el resto de la plantilla conserva la etiqueta de supuesto.
- La pantalla muestra magnitudes derivadas (cilindrada, cámara y compresión primaria) y expone la geometría de lumbreras existente. La entrada de control de admisión modifica la configuración nativa.
- El editor de escape muestra el perfil y edita longitudes/diámetros por tramo. La variante de aceptación cambió el primer tramo de 83 a 103 mm y presentó delta respecto de la baseline.
- Un punto integrado EXPLORATORY de 3000 rpm y un ciclo se ejecutó desde el EXE. Corrió 9.776 s; generó un ciclo y quedó `MAX_CYCLES_NONCONVERGED` / `INSUFFICIENT_CYCLES`, correctamente transitorio. Valores disponibles en el ciclo: potencia indicada −1.431 kW, torque indicado −4.556 Nm, IMEP −229.692 kPa, AFR suministrado 11.5, AFR atrapado 11.500000000000014 y combustible quemado 6.2320e−7 kg. Estos son valores de una única evolución transitoria; no son curva periódica ni resultado validado.
- El proyecto se guardó en `E:\Dino-artifacts\Dino-Commercial-Readiness-V1\Designs\demo-dino-2t.dino2t.json`, se cerró y se volvió a abrir en el EXE. Al recuperar se vieron el motor base `Motor Demo 54` y una variante.
- Tras la primera corrida, el EXE mostró un registro local. En el segundo intento, el coordinador recuperó el checkpoint previo con el mismo Run ID y no creó un segundo resultado para la variante. La comparación de dos ejecuciones de este diseño no pasó.

## Pendiente para aceptación

- El EXE cargó `Curvas-periodicas-125cc.dino.json` desde `Ejemplos`, pero no materializó las seis referencias en su historial local. La pantalla de análisis mostró cero registros y ninguna corrida seleccionada; por lo tanto, no se pudo verificar visualmente la comparación A/B del ejemplo dentro de esta sesión.
- Hay que resolver en el producto la importación de referencias del ejemplo o proveer una acción de carga que las haga disponibles, y permitir iniciar una corrida nueva con identidad/checkpoint nuevo tras cambiar de variante. Luego repetir dos corridas al mismo RPM y completar una comparación con fuentes identificables.
- La demostración no satisface todavía el criterio final completo. No convertir el estado transitorio ni las curvas históricas en claim de validación comercial o experimental.

## Paquete

- ZIP: `E:\Dino-artifacts\Windows\MotorSim-0.1.0-rc7-windows-x64-7c79016f-trial-20261023T160920Z.zip`
- EXE extraído: `E:\Dino-Commercial-Readiness-TRIAL-v1-final\MotorSim\Dino2T.exe`
- SHA-256 ZIP: `d2992cc184d71e91ed0b22eb89bb3a9e4f2f9f4afe7cf856b442d4cd45ec2020`
- Las nuevas corridas se dirigieron a `%LOCALAPPDATA%\MotorSim\Artifacts`; la carpeta antigua no se modificó.

## Capturas

- `../captures/02-exe-new-project.png` — nuevo proyecto con ejecución habilitada.
- `../captures/03-new-engine-dialog.png`, `../captures/04-new-engine-configured.png` — creación y configuración desde UI.
- `../captures/06-exhaust-editor.png`, `../captures/07-exhaust-edited.png` — perfil y dimensión de escape editada.
- `../captures/08-reopened-project.png`, `../captures/11-recovered-demo-project.png` — proyecto y variante después de reiniciar/abrir.
- `../captures/12-reopened-analysis.png` — análisis recuperado con el único registro disponible y sin selección.
- `../captures/13-periodic-example-analysis.png` — análisis vacío al abrir el proyecto periódico empaquetado; evidencia del límite actual.
