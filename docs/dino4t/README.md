# Dino 4T

Simulador 0D/1D de motores de cuatro tiempos de encendido por chispa
(monocilíndrico). Es independiente de Dino 2T y comparte la plataforma
mediante `motorsim/engine_platform.py`. Estado: **etapa 2 cerrada** (ver evaluación).

* [Evaluación crítica de la etapa 2 (estado científico vigente)](stage2_assessment.md)
* [Contrato de integración para Desktop / plataforma (`DINO4T_API_V1`)](integration_contract.md)
* [Referencia de modelos, ecuaciones e hipótesis](model_reference.md)
* [Informe de verificación de la etapa 1 (parcialmente superado)](verification_report.md)
* [Procedencia de los resultados](../../results/dino4t-stage2-v1/PROVENANCE.md)

## Uso

```
# Punto de operación hasta periodicidad (resumen JSON, configuración resuelta y traza CSV del último ciclo)
python -m motorsim.dino4t run configs/dino4t/example_single_cylinder_500cc.json --out OUT [--rpm 8000] [--phi 1.1] [--dx-mm 5]

# Barridos y sensibilidades locales (herramientas de estudio; no forman parte de DINO4T_API_V1)
python -m motorsim.dino4t sweep CONFIG --out OUT --param operating_point.rpm=3000:9000:7 --dx-mm 20
python -m motorsim.dino4t sensitivity CONFIG --out OUT --dx-mm 20

# Suite de verificación (--quick omite el estudio de malla)
python -m motorsim.dino4t verify --out OUT [--quick]
```

Desde Python (superficie estable; ver el contrato):

```python
from motorsim.dino4t import api, config
env = api.run(config.load(config.EXAMPLE_PATH), out_dir="OUT")
env["ok"], env["error"], env["summary"]["final_cycle"]["imep_net_bar"]
```

## Ejemplo reproducible

En `results/dino4t-stage2-v1/example/{4000,6000,8000}rpm/` está el motor
sintético de 500 cm³ (contorno V2, combustión de dos zonas), cada punto corrido
hasta periodicidad. Son resultados **plausibles, no validados**: la geometría,
los Cd y la fricción son supuestos y la combustión es una entrada.

@@TABLE@@

La caída de η_v a 8000 rpm refleja el dimensionamiento de válvulas supuesto
(su área efectiva limita el caudal), no una propiedad del modelo.
Los resultados de la etapa 1 (`results/dino4t-foundation-v1/`) se conservan como
**histórico**: usan un contorno con un defecto de primer orden (−29 % de caudal en
un extremo abierto ideal) y no deben usarse.

## Estado

| | |
|---|---|
| Verificación numérica | L0 + L1, ver la evaluación de la etapa 2 |
| Revisión | `SELF_REVIEW` (no hay revisión independiente) |
| Calibración | no realizada |
| Validación experimental | no realizada |
| Capacidad predictiva | no afirmada |
