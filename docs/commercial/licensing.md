# Dino Commercial - licenciamiento offline y perpetuo

Fecha: 2026-11-11. Decisión del dueño: **opción A**, licencia perpetua con
activación offline y modo TRIAL. Este documento no modifica contratos
científicos ni evidencia histórica.

## Arquitectura

- La aplicación empaqueta **sólo la clave pública Ed25519** en
  `motorsim/licensing/vendor_keys.py`.
- El emisor offline firma un payload JSON canónico con la clave privada. La
  clave privada no se commitea, no se empaqueta y no se entrega al usuario.
- La activación es un archivo `.dinolicense` firmado. Dino lo verifica sin red,
  lo copia de forma atómica a `DINO_LICENSE_ROOT` (o
  `DINO_ARTIFACT_ROOT/licensing`) y no modifica proyectos ni resultados.
- Verificación y firma usan una implementación Ed25519 RFC 8032 incluida para
  evitar dependencias criptográficas nuevas en el paquete.

### Payload

```json
{
  "schema": "DINO_LICENSE_V1",
  "product": "Dino Desktop",
  "license_type": "PERPETUAL",
  "activation": "OFFLINE",
  "license_id": "customer-2026-0001",
  "customer": "Cliente",
  "issued_at": "2026-11-11T12:00:00+00:00"
}
```

No se admite `expires_at`/`expiry`: la licencia perpetua no tiene vencimiento de
uso. La versión del software y el estado de validación científica son campos
separados y no se derivan de la licencia.

### Emisión y custodia

- Generar par de claves con `python tools/license_tool.py generate-key` guardando
  la privada **fuera del repositorio**, en un volumen controlado y con backup.
- Firmar: `python tools/license_tool.py sign --private-key ... --payload ...`.
- Verificar: `python tools/license_tool.py verify --license ... --public-key ...`.
- Rotación: agregar una nueva clave pública con nuevo `key_id`; mantener la
  anterior mientras existan licencias válidas. La privada comprometida se retira.
- Revocación: no es posible offline; una lista de revocación requeriría un
  mecanismo online o una actualización firmada. Se documenta como limitación.

## Estados visibles

| Estado | Significado | Acceso a proyectos/resultados |
|---|---|---|
| `LICENSED` | Licencia perpetua válida | Siempre |
| `TRIAL` | Prueba local vigente | Siempre |
| `TRIAL_EXPIRED` | Prueba local vencida | Siempre |
| `INVALID_LICENSE` | Archivo ilegible/firma inválida | Siempre |
| `UNLICENSED` | Sin licencia/error de almacenamiento | Siempre |

La barra de estado, **Ayuda → Licencia…** y **Acerca de Dino → Licencia**
muestran el estado. Un error de activación nunca borra ni bloquea proyectos,
resultados o exportaciones.

## TRIAL

- Duración por defecto de ingeniería: **30 días**. Es un valor provisional;
  la duración comercial definitiva sigue **pendiente de decisión del dueño**.
- `DINO_TRIAL_DAYS` permite configurarla por despliegue (1–3650).
- El estado local guarda inicio, último uso, duración y detecta rollback de
  reloj. Si el archivo local se borra, el TRIAL puede reiniciarse: es una
  limitación aceptada de un modo offline sin DRM; no se bloquean datos.
- El TRIAL no habilita un claim científico ni cambia `NOT_PERFORMED`/
  `NOT_CLAIMED`.

## Reinstalación y recuperación

El usuario conserva su archivo `.dinolicense` y lo vuelve a importar. No hay
activación online ni dependencia de una máquina concreta por defecto. La
recuperación de la licencia es la reimportación del mismo archivo firmado.

## Actualizaciones

El alcance de actualizaciones incluidas **sigue pendiente de decisión
comercial**. La licencia perpetua no caduca el uso; la aplicación no bloquea
actualizaciones ni las impone. La comprobación es manual y valida un manifiesto
local (`DINO_UPDATE_MANIFEST_V1`) sin descargar ni ejecutar nada.

## Pruebas

- `tests/test_licensing.py`: vector RFC 8032, firma/manipulación, licencia
  inválida sin bloqueo, TRIAL configurable/vencido/rollback, reinstalación,
  activación sin red, separación científica.
- `tests/test_desktop_license_ui.py`: estado visible, activación offline,
  pestaña de licencia y estado científico independiente.

## Riesgos residuales

- Sin revocación offline; una licencia filtrada sigue siendo válida hasta que se
  distribuya una actualización o se cambie de clave.
- El TRIAL local puede reiniciarse borrando su estado; no es DRM y no debe
  presentarse como control antifraude fuerte.
- La custodia/backup de la clave privada es crítica: perderla impide emitir
  licencias nuevas para la clave pública activa.
- La duración final del TRIAL y el alcance de actualizaciones requieren decisión
  comercial; no se fijaron restricciones irreversibles.
