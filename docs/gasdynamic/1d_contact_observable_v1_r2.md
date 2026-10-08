# 1D_CONTRACT_V1_R2 — único delta científico

Adoptado tras P1_R2_PASS_CONTACT_OBSERVABLE y revisión independiente del estudio.
El contrato v1 original se conserva íntegro. El manifest R2 hereda sus campos y
estados históricos; su adopción posterior se acredita en reviewed-evidence.json.

T02 localiza el contacto mediante HYDRO_CONTACT_CHARACTERISTIC_V1. Para cada
cara interior entre centros x_i,x_j: h=x_j-x_i, rho_bar=(rho_i+rho_j)/2,
p_bar=(p_i+p_j)/2, a²=gamma*p_bar/rho_bar, delta q=q_j-q_i:

    c0 = delta rho - delta p/a²
    c- = (delta p/a² - rho_bar*delta u/a)/2
    c+ = (delta p/a² + rho_bar*delta u/a)/2

Son contribuciones características en unidades de densidad. Candidata si
|c0|>|c-|+|c+|. Elegir el máximo global único de |c0|/h y devolver
(x_i+x_j)/2. Ausencia o empate: detección no inequívoca, nunca PASS.
Se evalúan todas las caras: sin ventanas, Y, exacto, IC o tiempo en el detector.
Código normativo fijado antes de evaluar: motorsim/gas1d/contact.py, commit3b5c82b.

La onda central de Euler cambia rho manteniendo p/u, a diferencia de las ondas
acústicas; véase [Clawpack, Euler approximate](https://www.clawpack.org/riemann_book/html/Euler_approximate.html).
La proyección local es un observable para Sod/contacto único, no un solver ni
un clasificador universal de múltiples contactos. No modifica flujos ni estados.

Error de contacto **<=2dx**, N400 y todos los demás criterios T02 intactos.
Shock sigue con su observable original; A/B/C basados en Y son diagnósticos.
T06 conserva íntegros transporte, L1, conservación y 0<=Y<=1. La separación
hidrodinámica/trazador cambia qué se mide, no la precisión requerida.

El diff literal y hash del contrato original están en 1d_contract_v1_r2_delta.json.
La revisión y ocho casos se conservan en results/p1-r2-contacto-20260918.
R2 PASS autoriza los fixes P2; reanudación T01–T12 requiere además T05 PASS.
