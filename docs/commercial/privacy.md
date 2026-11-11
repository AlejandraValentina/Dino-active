# Dino Commercial - privacidad y telemetría

Fecha: 2026-11-11.

## Posición por defecto

Dino no envía telemetría automática. No hay cuentas, analytics, crash reporting
remoto ni comprobación de actualización en segundo plano.

La comprobación de actualización es manual: el usuario selecciona un manifiesto
local desde **Ayuda → Buscar actualización…**. El manifiesto sólo se lee; no se
descarga ni se ejecuta nada.

## Diagnóstico

**Ayuda → Exportar diagnóstico…** crea un ZIP local. El usuario decide si
incluye el proyecto actual. El ZIP puede contener datos de ingeniería, rutas
locales y logs; no incluye credenciales. El usuario debe revisarlo antes de
enviarlo a soporte.

## Datos del usuario

- Proyectos y resultados permanecen en las rutas elegidas por el usuario.
- Autosave/recovery usa una raíz externa al repositorio.
- Desinstalar el ZIP portable no borra proyectos, resultados ni artefactos.
- No se codifican secretos ni se suben datos automáticamente.

## Cambios futuros

Cualquier telemetría opt-in exigirá documento, consentimiento explícito,
contenido visible y posibilidad de desactivarla. No se implementa por defecto.
