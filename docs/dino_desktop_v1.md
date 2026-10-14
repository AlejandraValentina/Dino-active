# Dino 2T para Windows

Dino 2T es una aplicación nativa Qt Widgets que reutiliza `ENGINE_CONFIGURATION_V1`.
No incluye un solver propio. Los proyectos guardan configuraciones y referencias
livianas; primarias y checkpoints permanecen fuera del proyecto.

## Desarrollo

Desde la raíz del repositorio, con Python 3.11 y PySide6 instalado:

```powershell
$env:QT_QPA_PLATFORM = "offscreen"  # opcional; sólo para sesión sin escritorio
python -m motorsim.dino_desktop
```

Al iniciar, el proyecto nuevo parte de un fixture sintético de ejemplo. También
se incluye `examples/projects/dino-2t-starter.dino2t.json`, que se puede abrir
desde **Archivo → Abrir**.

## Paquete Windows reproducible

La receta fijada genera una distribución `onedir` que contiene `MotorSim.exe` y
`Dino2T.exe`, más sus dependencias, avisos y proyectos de ejemplo (incluida la
comparación de geometría de escape). Requiere Windows x64,
Python **3.11.0**, un checkout Git limpio y las versiones exactas de
`packaging/requirements-build.txt`:

```powershell
py -3.11 --version
py -3.11 -c "import struct,sys; assert sys.version_info[:3] == (3,11,0); assert struct.calcsize('P') == 8"
py -3.11 -m venv .venv-build
.venv-build\Scripts\python -m pip install -r packaging\requirements-build.txt
.venv-build\Scripts\python packaging\build_windows.py
```

La línea `py -3.11-32` sólo sirve para identificar una instalación x86 si está
presente; la receta exige Python x64. Ejecutar `packaging\build_windows.py` sin
`--trial` requiere un árbol limpio. El resultado se crea en una nueva carpeta
bajo `dist`; la receta no sobrescribe un destino existente. Abrir
`dist\MotorSim-…\MotorSim\Dino2T.exe` y luego el ejemplo
`Ejemplos\desktop-dino-2t-starter.dino2t.json`.

## Uso y límites

- **Motor** edita geometría, distribución, condiciones operativas y parámetros
  de combustión soportados. El snapshot de combustible y sus hashes se muestran
  en sólo lectura; no se inventa una biblioteca de combustibles.
- **Escape** edita secciones cónicas de diámetro lineal. El perfil representa
  geometría, no predice ondas, potencia ni el comportamiento de componentes que
  el solver no soporte.
- **Proyecto** crea/abre/guarda proyectos, exporta/importa configuraciones y
  administra variantes. Guardar usa validación e intercambio atómico del
  backend.
- **Resultados** importa el aggregate IMPL2 externo, permite superponer curvas,
  seleccionar puntos y exportar tabla CSV y gráfico PNG. Los tres
  `NUMERICAL_INVALID` siguen como huecos, sin interpolación; potencia negativa,
  provenance y clasificación se conservan. `PERIOD_1` no equivale a PASS
  científico.
- **Simulación** ejecuta sólo EXPLORATORY local después de mostrar preflight,
  RPM, horizonte, límites y artifact root y recibir confirmación explícita.
  Verified/campañas permanecen bloqueadas sin contrato, preregistro y
  autorización exactos. Cancelar conserva el último checkpoint completo.
- Para límites del modelo, identidad, artifact root, recuperación y
  clasificación provisional, ver [DINO_SIMULATION_WORKFLOW_V1](dino_simulation_workflow_v1.md).

El aggregate predeterminado se busca en el artifact store IMPL2 externo. Para
otro root, establecer `DINO_ARTIFACT_ROOT` antes de iniciar; los resultados
pueden abrirse desde el diálogo aunque ese root no exista. No copiar artifacts
masivos dentro del repositorio.

Validación de interfaz:

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
python -m pytest tests/test_dino_desktop.py -q
```
