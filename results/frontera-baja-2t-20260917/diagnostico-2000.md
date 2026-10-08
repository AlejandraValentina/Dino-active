# Diagnóstico 2000 rpm — positividad de etapas RK4

La primera negativa ocurre en el ciclo1 y se recupera con rechazos/reducción. La negativa terminal ocurre en el ciclo6. Se conservan cinco ciclos completos como diagnóstico; no son una ejecución convergida.

## Primera negativa observada

| Campo | Valor |
| --- | --- |
| cycle | 1 |
| advance_angle_deg | 182.75 |
| angle_deg | 183 |
| substage | K4 |
| rk_branch | full |
| attempt_full_deg | 0.25 |
| attempt_full_dt_s | 2.083333333e-05 |
| rk_dt_s | 2.083333333e-05 |
| F_rk_base_kg | 0 |
| F_previous_stage_K3_kg | 1.657922418e-08 |
| F_increment_kg | -7.798989747e-11 |
| F_candidate_kg | -7.798989747e-11 |
| candidate_m_C_kg | 9.293812437e-05 |
| candidate_U_C_J | 51.61992497 |
| candidate_Y_C | -8.391593654e-07 |
| negative_overshoot | 259.9663249 |
| safe_scale_kg | 3e-13 |
| Bdot_kg_s | 0 |
| heat_active | False |
| before_rejection_count | 0 |


Los flujos siguientes se evalúan en el estado físico K3 que construye el candidato K4; no se evalúa RHS sobre el candidato negativo.

| Enlace | Área m² | Fresca firmada hacia C kg/s | Donante | p arriba Pa | p abajo Pa | Retorno |
| --- | --- | --- | --- | --- | --- | --- |
| 2 | 0.00012 | -1.517564403e-07 | C | 123749.7511 | 123655.6534 | True |
| 3 | 0.00012 | -1.517564403e-07 | C | 123749.7511 | 123655.6534 | True |
| 4 | 0.0002 | -3.440002198e-06 | C | 123749.7511 | 105904.5326 | False |


| Balance de etapa | Valor |
| --- | --- |
| net_outflow_stage_increment_kg | 7.798989747e-11 |
| exceeds_rk_base_inventory | True |
| exceeds_K3_inventory | False |
| internal_global_fresh_rate_residual | 4.235164736e-22 |
| global_fresh_rate_residual | 7.516003699e-23 |
| only_F_invalid | True |


## Negativa terminal

| Campo | Valor |
| --- | --- |
| cycle | 6 |
| advance_angle_deg | 2272.789249 |
| angle_deg | 2272.799593 |
| substage | K4 |
| rk_branch | full |
| attempt_full_deg | 0.01034414647 |
| attempt_full_dt_s | 8.620122062e-07 |
| rk_dt_s | 8.620122062e-07 |
| F_rk_base_kg | 0 |
| F_previous_stage_K3_kg | 1.20288235e-11 |
| F_increment_kg | -9.523239929e-18 |
| F_candidate_kg | -9.523239929e-18 |
| candidate_m_C_kg | 5.723536152e-05 |
| candidate_U_C_J | 32.96684181 |
| candidate_Y_C | -1.663873465e-13 |
| negative_overshoot | 3.17441331e-05 |
| safe_scale_kg | 3e-13 |
| Bdot_kg_s | 0 |
| heat_active | False |
| before_rejection_count | 7 |


Los flujos siguientes se evalúan en el estado físico K3 que construye el candidato K4; no se evalúa RHS sobre el candidato negativo.

| Enlace | Área m² | Fresca firmada hacia C kg/s | Donante | p arriba Pa | p abajo Pa | Retorno |
| --- | --- | --- | --- | --- | --- | --- |
| 2 | 0 | 0 | — | 123242.4196 | 100288.6164 | False |
| 3 | 0 | 0 | — | 123242.4196 | 100288.6164 | False |
| 4 | 0.0002 | -1.104768571e-11 | C | 100288.6164 | 100288.4747 | False |


| Balance de etapa | Valor |
| --- | --- |
| net_outflow_stage_increment_kg | 9.523239929e-18 |
| exceeds_rk_base_inventory | True |
| exceeds_K3_inventory | False |
| internal_global_fresh_rate_residual | 0 |
| global_fresh_rate_residual | 0 |
| only_F_invalid | True |


## Interpretación offline

RK4 construye K4 como y_base+dt*k3, no como y_K3+dt*k3. En ambas negativas F_base=0: K2 había aportado fresca a K3; luego K3 prescribe salida y K4 resta esa salida del inventario base cero. El incremento excede F_base, pero no F_K3. Esto identifica pérdida de positividad de una subetapa, no agotamiento físico demostrado del inventario que produjo el caudal.

En la negativa terminal el escape cambia de C→E (K1, Δp=+1,19879Pa) a E→C (K2,−0,305042Pa) y vuelve a C→E (K3,+0,141702Pa). El donante de masa/entalpía/fresca es consistente con cada signo de presión. Transferencias cerradas, escape abierto, Bdot=0 y calor inactivo. La primera negativa en cambio incluye retorno C→K en las transferencias y salida C→E.

Los transportes internos se suman con signos opuestos: residuo global de fresca 0 en el episodio terminal;7,516e-23kg/s en el primero, redondeo flotante. No se observa pérdida global ni incoherencia de donante. m/U/T/p permanecen en dominio; la violación observada es del marcador F.

negative_overshoot=abs(F_candidate)/max(abs(F_base),3e-13kg). La escala 3e-13kg es atol_mass del perfil B, exclusivamente para diagnóstico. No es un floor ni permiso para aceptar valores negativos.

La secuencia terminal contiene seis rechazos por error local y dos por estado no físico. Corrige la descripción abreviada anterior de “ocho rechazos no físicos”: el límite cuenta todos los motivos consecutivos.

| h intento ° | Motivo | Error normalizado | Rechazo consecutivo |
| --- | --- | --- | --- |
| 0.05270310436 | local_error | 1.022377506 | 1 |
| 0.04722331271 | local_error | 1.107049918 | 2 |
| 0.04164525427 | local_error | 1.197964453 | 3 |
| 0.03615091061 | local_error | 1.301783113 | 4 |
| 0.03086412889 | local_error | 1.444326397 | 5 |
| 0.02580854158 | local_error | 1.784048182 | 6 |
| 0.02068829295 | nonphysical | — | 7 |
| 0.01034414647 | nonphysical | — | 8 |


El rechazo7 se produce en half-1 de h=0,0206882929494°; el8 repite exactamente esa trayectoria como paso completo de h=0,0103441464747°. Esa reducción no evita la violación. La siguiente reducción algebraica sería h=0.00517207323735°, medio=0.00258603661868°: aún por encima del mínimo, pero no autorizada por el límite de ocho rechazos. No se ejecutó. No puede afirmarse que evitaría la violación.

El paso final potencial queda **indeterminado**: producirlo requeriría evaluar k4 en un estado prohibido, lo cual no se hizo. La evidencia sí localiza el fallo antes del estado final. No se aplicó clipping, floor, renormalización, limiter ni sustitución de integrador.

**Mecanismo identificado:** positividad de etapas explícitas con F_base=0 y cambio de donante en una restricción interna no regularizada. Causa de parada adicional: presupuesto de rechazos consumido también por error local.
