## ADDED Requirements
### Requirement: Sistema visual común
La UI SHALL usar la paleta técnica gris/azul de la referencia, paneles compactos,
encabezados, badges textuales, tablas de propiedades, foco visible y título nativo.
SHALL conservar menú, shortcuts, navegación contextual y estado real con ruta elidida.
#### Scenario: Proyecto nuevo
- **WHEN** se crea un proyecto
- **THEN** mantiene Sin título y 2T, sin datos ni resultados inventados.
### Requirement: Resumen y copia de ejemplos
Resumen SHALL agrupar proyecto y preparación a izquierda, geometría y ejemplos a
derecha. SHALL derivar preparación de validadores existentes y advertir que la
convergencia no está garantizada. Los cuatro JSON SHALL cargarse como copia protegida.
#### Scenario: Seleccionar ejemplo
- **WHEN** se confirma la sustitución del proyecto por un ejemplo
- **THEN** path es None, dirty es True, Guardar solicita destino y no se ejecuta un cálculo.
### Requirement: Cálculo y contexto adaptables
Simulación SHALL separar preparación, estado y contexto; apilar y colapsar contexto
según ancho real sin scroll horizontal global. SHALL conservar validate_rpm,
plan_rpms, validaciones, QProcess, resultados, cancelación y procedencia reales.
#### Scenario: Entrada inválida
- **WHEN** RPM o barrido no es admitido
- **THEN** conserva el texto, marca campos y muestra el error real sin reparar valores.
#### Scenario: Curvas y estados
- **WHEN** no hay ciclo aceptado o se carga uno
- **THEN** muestra ejes vacíos sin presiones inventadas o muestras reales en orden temporal;
el ciclo conserva 360°/720°, los estados son textuales y derivan de la ejecución.
### Requirement: Análisis y comprobación preservados
Resultados, Comparar, Externos y editores SHALL compartir lenguaje visual sin
alterar reglas, formatos, modelos, contratos o worker. SHALL conservar accesibilidad.
#### Scenario: Candidata rc5
- **WHEN** se entrega la candidata
- **THEN** preserva anteriores, acredita suite, revisión puntual, Windows/DPI y
recorrido del paquete; separa límites y aceptación manual pendiente.
