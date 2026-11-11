"""Generate and render standalone SVG design artifacts (not product captures)."""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
from html import escape
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage,QPainter,QFontDatabase,QFont,QRawFont
from PySide6.QtSvg import QSvgRenderer

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'docs/frontend-audit-v1/wireframes'
OUT.mkdir(parents=True,exist_ok=True)
app=QApplication([])
# The Windows offscreen plugin has no system font database. Load a real font;
# otherwise a technically valid PNG can contain placeholder boxes only.
font_directory=Path(os.environ['WINDIR'])/'Fonts'
for name in ['segoeui.ttf','segoeuib.ttf']:
    assert QFontDatabase.addApplicationFont(str(font_directory/name))>=0
app.setFont(QFont('Segoe UI',10))
assert QRawFont.fromFont(app.font()).supportsCharacter('A')


def rect(x,y,w,h,fill='#fff',stroke='#d3dce7',radius=7):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke}"/>'


def text(x,y,value,size=14,color='#20364c',bold=False):
    return f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" font-weight="{700 if bold else 400}">{escape(value)}</text>'


def lines(x,y,values,size=14,color='#53657a',step=22):
    return ''.join(text(x,y+i*step,v,size,color) for i,v in enumerate(values))


def button(x,y,w,label,primary=False):
    return rect(x,y,w,35,'#145d86' if primary else '#fff')+text(x+12,y+23,label,13,'#fff' if primary else '#20364c',primary)


def shell(title,page,project='MX125 · ejemplo de proyecto',family='2T nativo'):
    items=['Inicio y proyecto','Motor y componentes','Preparar simulación','Corridas y cola','Resultados','Comparar variantes']
    s='<svg xmlns="http://www.w3.org/2000/svg" width="1360" height="860" viewBox="0 0 1360 860"><title>'+escape(title)+'</title><desc>Wireframe ilustrativo. No captura del producto ni datos de simulación.</desc><g font-family="Segoe UI">'
    s+=rect(0,0,1360,860,'#f3f5f8',radius=0)+rect(0,0,1360,30,'#263546',radius=0)
    s+=text(18,20,'PROPUESTA UX · WIREFRAME · datos ilustrativos, sin solver ni validación',13,'#fff')
    s+=rect(0,30,1360,80,radius=0)+text(22,78,'DINO',27,bold=True)
    s+=text(155,61,project,17,bold=True)+text(155,86,family+' · núcleo del proyecto',13,'#53657a')
    s+=text(640,57,'VARIANTE ACTIVA',11,'#53657a')+text(640,81,'Motor base',15,bold=True)
    s+=text(820,57,'REVISIÓN APLICADA',11,'#53657a')+text(820,81,'R7 · demostración',15,bold=True)
    s+=rect(1050,53,130,30,'#e3f3e9')+text(1062,73,'Guardado · demo',12,'#246345')+button(1200,50,135,'Compartir…')
    s+=rect(0,110,196,750,'#edf1f5',radius=0)+button(13,130,170,'Abrir / crear…',True)
    s+=text(18,203,'TRABAJO DEL PROYECTO',11,'#53657a',True)
    for i,label in enumerate(items):
        y=222+i*47
        if label==page:s+=rect(9,y-5,178,37,'#d8e9f2',stroke='#d8e9f2')
        s+=text(18,y+18,label,13,'#145d86' if label==page else '#20364c',label==page)
    s+=lines(18,590,['Estado científico','Validación experimental','no realizada.','Predictividad no declarada.'],12,step=22)
    s+=text(18,757,'Ayuda y diagnóstico',13,'#145d86')
    s+=text(220,840,'Diseño ilustrativo · contratos científicos independientes · selección y revisión persistentes',12,'#53657a')
    return s


def finish(name,svg):
    path=OUT/(name+'.svg')
    path.write_text(svg+'</g></svg>',encoding='utf-8')
    renderer=QSvgRenderer(str(path))
    assert renderer.isValid(),path
    image=QImage(1360,860,QImage.Format.Format_ARGB32)
    image.fill(0xffffffff)
    painter=QPainter(image)
    renderer.render(painter)
    painter.end()
    assert image.save(str(path.with_suffix('.png')))


s=shell('Motor y componentes','Motor y componentes')
s+=text(220,153,'Motor y componentes',27,bold=True)+text(220,181,'Una selección física, un inspector y una revisión aplicada.',14,'#53657a')
s+=rect(220,205,174,590)+text(235,235,'Componentes',16,bold=True)
for i,label in enumerate(['Cilindro y culata','Cárter','Admisión','Transferencias','Escape','Combustión','Pérdidas','Ambiente']):
    if i==0:s+=rect(230,252+i*43,154,34,'#e6f1f7')
    s+=text(240,274+i*43,label,13,'#145d86' if i==0 else '#20364c',i==0)
s+=text(240,731,'Avanzado...',13,'#53657a')
s+=rect(412,205,550,590)+text(431,238,'Cilindro y culata',19,bold=True)
s+=rect(431,260,510,250,'#f8fbfe')+text(447,282,'ESQUEMA · NO A ESCALA',11,'#53657a')
s+='<g stroke="#476982" stroke-width="2" fill="#e0eaf2"><rect x="630" y="300" width="100" height="100" rx="5"/><ellipse cx="680" cy="452" rx="59" ry="33"/><path d="M675 370V430L690 450"/></g>'
s+='<path d="M636 365H724" stroke="#d89d32" stroke-width="5"/><path d="M480 453H620M621 453H590V375H630M730 330H780L820 312H905" fill="none" stroke="#287ca3" stroke-width="6"/>'
s+=text(486,432,'Admisión',13)+text(770,296,'Escape',13)+text(642,491,'Cárter',13)+text(460,354,'Transferencias',12)
s+=text(432,552,'Diámetro del cilindro',14,bold=True)+rect(432,565,215,38)+text(444,589,'56,0 mm',15)
s+=text(679,552,'Carrera',14,bold=True)+rect(679,565,261,38)+text(691,589,'50,6 mm',15)
s+=lines(432,631,['Fuente: supuesto del ejemplo. Revisar al cargar medidas reales.',
                    'Los campos derivados muestran su relación; no se editan aparte.'],12)
s+=rect(432,681,508,45,'#fff8e8')+text(444,707,'Borrador → aplicar → guardar. Ejecutar exige una decisión.',12,'#805000')
s+=button(432,744,208,'Aplicar borrador · demo',True)+button(652,744,160,'Descartar edición')
s+=rect(980,205,355,590,'#f9fbfd')+text(998,238,'Inspector del componente',18,bold=True)
s+=lines(998,277,['Magnitud · unidad · convención','Procedencia del dato','Relaciones y valores derivados'],14)
s+=text(998,381,'Estado de edición',16,bold=True)+lines(998,409,['El borrador conserva sus cambios.','Una corrida usa la revisión aplicada.','Un resultado no pisa el formulario.'],13)
s+=text(998,523,'Acciones de contexto',16,bold=True)+lines(998,551,['Ver ayuda del parámetro','Inspeccionar configuración original','Revisar errores por campo'],13)
s+=button(998,737,314,'Preparar simulación →',True)
finish('modelo',s)

s=shell('Preparar simulación y ejecución','Preparar simulación')
s+=text(220,153,'Preparar simulación',27,bold=True)+text(220,181,'Planificar antes de gastar tiempo de cálculo.',14,'#53657a')
s+=rect(220,205,720,590)+text(240,238,'Punto operativo  /  Curva RPM',19,bold=True)
for x,label,value in [(240,'RPM inicial','3000'),(470,'RPM final','4000'),(700,'Incremento','500')]:
    s+=text(x,286,label,14,bold=True)+rect(x,300,210,40)+text(x+12,326,value+' RPM',15)
s+=text(240,379,'Máximo de ciclos por punto',14,bold=True)+rect(240,394,320,40)+text(252,420,'24 ciclos · ejemplo',15)
s+=text(580,379,'Presupuesto por punto',14,bold=True)+rect(580,394,340,40)+text(592,420,'60 segundos · ejemplo',15)
s+=rect(240,464,680,110,'#eaf3f9')+text(256,495,'3 puntos · 3000, 3500, 4000 RPM',17,bold=True)
s+=text(256,525,'Presupuesto agregado: 180 s + preparación / escritura.',14)
s+=text(256,553,'Estimación de duración: desconocida sin una corrida comparable.',13,'#53657a')
s+=text(240,614,'Configuración fijada al iniciar',16,bold=True)+lines(240,643,['Proyecto + variante + revisión + modelos + condiciones.',
    'Una edición pendiente exige aplicar, descartar o cancelar.'],14)
s+=button(240,737,238,'Revisar plan y preflight…',True)+button(490,737,205,'Agregar a cola…')
s+=rect(960,205,375,290)+text(980,238,'Preflight y alcance',18,bold=True)
s+=lines(980,280,['OK · Identidad del proyecto','OK · Revisión de la variante','! Resolver ediciones pendientes','! Comprobar dominio del núcleo','! Espacio y destino de resultados'],14,step=32)
s+=rect(960,513,375,282)+text(980,548,'Durante la ejecución',18,bold=True)
s+=lines(980,580,['Fase: inicializar / integrar / escribir','Progreso por punto y ciclo','Transcurrido y presupuesto restante','Motivo de detención y datos persistidos'],13,step=28)
s+=rect(980,697,333,45,'#fff8e8')+text(990,716,'Cancelar respeta el punto seguro del modelo.',12,'#805000')+text(990,733,'Reintentar no equivale a reinicio exacto.',12,'#805000')
s+=text(980,774,'Wireframe: no se hace preflight real.',12,'#53657a')
finish('simulacion',s)

s=shell('Resultados y comparación','Resultados')
s+=text(220,153,'Resultados de la corrida',27,bold=True)+text(220,181,'Ejemplo A · revisión R7 · datos ilustrativos, sin solver.',14,'#53657a')
s+=rect(220,205,1115,58,'#fff8e8')+text(238,229,'No convergida: se pueden inspeccionar muestras transitorias.',15,'#805000',True)
s+=text(238,251,'Las prestaciones no representan un resultado estacionario validado.',13,'#805000')
s+=rect(220,282,720,337)+text(240,315,'Curvas · muestras · presión y eventos',18,bold=True)
s+='<g fill="none"><path d="M280 365V570H900" stroke="#70879b"/><path d="M280 420H900M280 470H900M280 520H900" stroke="#d4dee7"/><path d="M310 535L420 485L530 433M750 402L860 435" stroke="#287ca3" stroke-width="3"/><path d="M638 432l15 15m0-15l-15 15" stroke="#a86612" stroke-width="3"/></g>'
s+=text(310,355,'ESQUEMA ILUSTRATIVO · SIN DATOS DE SOLVER',11,'#53657a')+text(593,487,'punto no admitido',13,'#805000')+text(854,595,'RPM',12)
s+=rect(960,282,375,337)+text(980,315,'Interpretación del resultado',18,bold=True)
s+=lines(980,355,['Ejecución: límite de ciclos','Periodicidad: no convergida','Integridad: hashes comprobados','Validación experimental: no realizada'],13,step=39)
s+=text(980,552,'Cada eje conserva su significado.',13,'#53657a')+button(980,570,335,'Ver muestras y procedencia…')
s+=rect(220,637,1115,158)+text(240,669,'Comparar: elegir primero el par y conocer su elegibilidad',17,bold=True)
s+=lines(240,700,['A: Motor base · R7     B: Escape B · R8','Familia, núcleo, RPM, condiciones y procedencia se comprueban antes de calcular.',
                     'La diferencia geométrica no implica ganancia de potencia demostrada.'],13)
s+=button(1000,738,313,'Construir comparación A/B…',True)
finish('resultados',s)
print('Rendered 3 standalone SVG wireframes and PNG previews')
