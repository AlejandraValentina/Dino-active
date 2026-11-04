# Dino 4T

Simulador 0D/1D de motores de cuatro tiempos de encendido por chispa
(monocilíndrico, V1). Es independiente de Dino 2T y comparte la plataforma
mediante `motorsim/engine_platform.py`.

* [Referencia de modelos, ecuaciones e hipótesis](model_reference.md)
* [Informe de verificación numérica](verification_report.md)

## Uso

```
# Punto de operación hasta periodicidad (resumen JSON, configuración resuelta y traza CSV del último ciclo)
python -m motorsim.dino4t run configs/dino4t/example_single_cylinder_500cc.json --out OUT [--rpm 8000] [--phi 1.1] [--dx-mm 5]

# Suite de verificación (--quick omite el estudio de malla)
python -m motorsim.dino4t verify --out OUT [--quick]
```

Desde Python:

```python
from motorsim.dino4t import config, runner
out = runner.run_operating_point(config.load(config.EXAMPLE_PATH), out_dir="OUT")
out["summary"]["final_cycle"]["imep_net_bar"]
```

## Ejemplo reproducible

En `results/dino4t-foundation-v1/example/{4000,6000,8000}rpm/` está el motor
sintético de 500 cm³, cada punto corrido hasta periodicidad. Son resultados
**plausibles, no validados**: la geometría, los Cd y la fricción son supuestos
y la combustión es una entrada.

| rpm | ciclos | IMEP neto [bar] | PMEP [bar] | BMEP [bar] | η_v | P_efectiva [kW] | BSFC [g/kWh] | residuo IVC | cierre máx. |
|---|---|---|---|---|---|---|---|---|---|
| 4000 | 5 | 14,43 | 0,35 | 12,62 | 0,990 | 21,0 | 221 | 0,029 | 2,2e‑14 |
| 6000 | 6 | 12,50 | 1,45 | 10,04 | 0,923 | 25,1 | 259 | 0,050 | 2,2e‑14 |
| 8000 | 5 | 9,01 | 1,43 | 5,91 | 0,686 | 19,7 | 327 | 0,078 | 5,2e‑15 |

La caída de η_v a 8000 rpm refleja el dimensionamiento de válvulas supuesto
(su área efectiva limita el caudal), no una propiedad del modelo.

## Estado

| | |
|---|---|
| Verificación numérica | L0 + L1, ver informe |
| Calibración | no realizada |
| Validación experimental | no realizada |
| Capacidad predictiva | no afirmada |
