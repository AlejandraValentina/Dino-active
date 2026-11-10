# Dino Commercial — política de release y soporte

Fecha: 2026-11-10. Esta política cubre CP0/CP2 y no modifica contratos
científicos, ecuaciones, tolerancias ni evidencia histórica.

## 1. Identidad y versionado

- Versión de producto: `APP_VERSION` (`0.1.0-rcN` durante el ciclo actual).
- Cada candidato se identifica por el commit fuente limpio y el `build.json`
  embebido (versión, commit, inputs empaquetados, hashes).
- El ZIP y los ejecutables se publican con SHA-256. Un candidato no se
  reconstruye “sobre” otro: cada build tiene destino nuevo.
- Los proyectos 2T, 4T 0D y 4T nativo mantienen sus schemas versionados; un
  cambio incompatible exige nueva versión y migración explícita.

## 2. Canales y actualización

- **TRIAL/engineering:** candidato no publicado, uso interno o piloto.
- **Release candidate:** paquete Windows identificado, aceptación documentada.
- **Comercial:** sólo tras CP4 y aceptación del dueño.
- La actualización es manual/opt-in en CP0/CP2. No hay auto-update silencioso
  ni telemetría por defecto.
- El rollback consiste en conservar el paquete anterior y no borrar artefactos
  históricos; no se reescriben resultados.

## 3. Licencias y EULA

- La aplicación incluye avisos de terceros (Qt/PySide6, Python, PyInstaller,
  NumPy, SciPy, etc.) y el texto de licencia del producto.
- El modelo comercial (perpetuo, suscripción, activación, TRIAL) es una
  decisión del dueño. CP0 deja el lugar de integración y el About; CP2
  implementa el modelo elegido.
- Sin DRM improvisado ni bloqueo de datos del usuario. La licencia no debe
  impedir abrir/exportar proyectos propios.

## 4. Privacidad y soporte

- Sin telemetría automática. Cualquier envío de diagnóstico es manual y
  explícito; el ZIP advierte que puede contener datos de ingeniería.
- El diagnóstico no incluye credenciales; el proyecto se incluye sólo si el
  usuario lo autoriza.
- Soporte: distribuidor autorizado/documentación de licencia. El usuario puede
  exportar diagnóstico desde Ayuda y revisar el contenido antes de enviarlo.

## 5. Checklist de candidato Windows

1. Árbol limpio y commit identificado.
2. Storage preflight PASS.
3. `.venv-build` con versiones fijadas.
4. Build no-trial y `packaged_inputs_clean=true`.
5. Hashes de ZIP/EXE/worker registrados.
6. Aceptación empaquetada: worker 2T/4T, rutas, apertura/reapertura, curvas,
   cancelación, exportaciones, trazabilidad y cierre de recursos.
7. About con versión/build/commit/licencias/estado científico.
8. Diagnóstico exportable y recuperación probados.
9. Sin workers huérfanos ni eventos `Application Error`.
10. Evidencia copiada a `results/.../windows/` y referenciada por el recibo.

## 6. Límites científicos

La liberación comercial de software no acredita:

- calibración (`NOT_PERFORMED`),
- validación experimental (`NOT_PERFORMED`),
- capacidad predictiva (`NOT_CLAIMED`).

Un claim científico requiere CP3 con datos medidos, protocolo preregistrado,
holdout e incertidumbre. Sin CP3, el producto se declara TRIAL/engineering.

## 7. Soporte de versiones

- Se conservan los paquetes y resultados históricos; no se limpian
  automáticamente.
- Un cambio de schema de proyecto debe incluir lector del formato anterior o
  una herramienta de migración explícita.
- Los históricos legacy se muestran con su clasificación y no se promocionan
  silenciosamente.
