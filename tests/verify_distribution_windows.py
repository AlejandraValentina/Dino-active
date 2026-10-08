"""Automatización externa UIA/teclado del EXE: no se incorpora al paquete.

Etapas separadas para repetir únicamente comprobaciones afectadas. Las numéricas
rechazan destinos existentes y usan un presupuesto compartido de 300 s.
"""
import argparse
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import subprocess
import shutil
import sys
import time

import win32con
import win32gui
import win32process
from pywinauto.uia_element_info import UIAElementInfo
from pywinauto.controls.uiawrapper import UIAWrapper
from pywinauto.keyboard import send_keys

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--exe',type=Path,required=True)
parser.add_argument('--work',type=Path,required=True)
parser.add_argument('--resume-two',type=Path,help='Resultado 2T ya ejecutado: continuar solo 4T, sin repetirlo')
parser.add_argument('--scale',default='1.5',choices=['1','1.25','1.5'])
parser.add_argument('--projects-root',type=Path,help='Carpeta de JSON físicos; por defecto Ejemplos del paquete')
parser.add_argument('--stage',choices=['editor','numerical','history','cancel','missing','external','about','provenance','process','hardening','cancel-once','reopen','uxeditor','uxpoint','uxcancel','uxanalysis','uxseries','examples','uxvisual','physical-examples','cae-examples','cae-points','performance'],required=True)
args=parser.parse_args();exe=args.exe.resolve();work=args.work.resolve();work.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from motorsim.reference_results import load_result
from motorsim.sweep import load_sweep

env=os.environ.copy()
for key in ('PYTHONPATH','PYTHONHOME','VIRTUAL_ENV','QT_PLUGIN_PATH','QT_QPA_PLATFORM_PLUGIN_PATH'):
    env.pop(key,None)
env.update(PATH=os.environ['SystemRoot']+'\\System32;'+os.environ['SystemRoot'],
    QT_SCALE_FACTOR=args.scale,QT_QPA_PLATFORM='windows',LOCALAPPDATA=str(work/'Datos'))
cwd=work/'Directorio distinto';cwd.mkdir(exist_ok=True)
process=subprocess.Popen([str(exe)],cwd=cwd,env=env)
checks=[];workers=[];screens=[]
def note(text):checks.append(text);print('PASS',text,flush=True)
def wait(fn,seconds=15):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        result=fn()
        if result:return result
        time.sleep(.15)
    raise RuntimeError('Tiempo agotado: '+getattr(fn,'__name__','condición'))
def windows():
    found=[]
    def visit(h,_):
        if win32gui.IsWindowVisible(h) and win32process.GetWindowThreadProcessId(h)[1]==process.pid:
            found.append((h,win32gui.GetWindowText(h)))
    win32gui.EnumWindows(visit,None);return found
def window(fragment):
    h=wait(lambda:next((h for h,title in windows() if fragment in title),None))
    return UIAWrapper(UIAElementInfo(h))
def front(w,width=1350,height=800):
    win32gui.ShowWindow(w.handle,win32con.SW_RESTORE)
    win32gui.SetWindowPos(w.handle,win32con.HWND_TOPMOST,20,20,width,height,win32con.SWP_SHOWWINDOW)
    try:win32gui.SetForegroundWindow(w.handle)
    except Exception:pass
def control(w,kind,name=None,suffix=None):
    name={'Ejecutar':'Ejecutar cálculo','Comprobar entradas':'Comprobar'}.get(name,name)
    return wait(lambda:next((x for x in w.descendants() if x.element_info.control_type==kind
        and (name is None or x.window_text()==name or x.element_info.name==name)
        and (suffix is None or x.element_info.automation_id.endswith(suffix))),None))
def button(w,name):
    if name=='Cerrar':
        win32gui.PostMessage(w.handle,win32con.WM_CLOSE,0,0)
        wait(lambda:not win32gui.IsWindowVisible(w.handle));return
    # Invoke se bloquea en algunos diálogos modales Qt; teclado conserva el flujo real.
    b=control(w,'Button',name);b.set_focus();send_keys('{SPACE}');time.sleep(.2)
def tab(w,name):control(w,'TabItem',name).select();time.sleep(.2)

def navigate(name):
    # Navegación por teclado, incluidos los encabezados no seleccionables.
    steps={'Datos externos':0,'Comparar':1,'Resultados':2,'Rendimiento':4,'Simulación':5,
           'Motor 2T':7,'Motor 4T':7,'Geometría':8,'Resumen':10}
    control(main,'Tree').set_focus();send_keys('{END}')
    if steps[name]:send_keys('{UP '+str(steps[name])+'}')
    time.sleep(.2)
def combo(w,name,index):
    if name in ('Tipo de motor','Ejecución'):
        c=[x for x in w.descendants() if x.element_info.control_type=='ComboBox'][0 if name=='Tipo de motor' else 1]
    else:c=control(w,'ComboBox',name)
    select_combo(c,index)

def select_combo(c,index):
    c.click_input();time.sleep(.2)
    items=[]
    for h,_ in windows():
        items.extend(x for x in UIAWrapper(UIAElementInfo(h)).descendants() if x.element_info.control_type=='ListItem')
    assert len(items)>index, 'No aparece la lista del selector'
    expected=items[index].window_text();items[index].click_input();time.sleep(.2)
    assert c.selected_text()==expected, (c.selected_text(),expected)
def texts(w):return '\n'.join(x.window_text() for x in w.descendants() if x.element_info.control_type=='Text')
def file_dialog(fragment,path):
    d=window(fragment)
    edits=[x for x in d.descendants() if x.element_info.control_type=='Edit']
    e=next((x for x in edits if x.element_info.automation_id.endswith('fileNameEdit') or x.element_info.automation_id=='1148'),None)
    if e is not None:e.set_edit_text(str(path));e.set_focus()
    else:
        # Campo de nombre enfocado al abrir el diálogo nativo Windows.
        send_keys('^a');send_keys(str(path),with_spaces=True)
    send_keys('{ENTER}');time.sleep(.5)
    wait(lambda:not win32gui.IsWindowVisible(d.handle))
def open_project(path):button(main,'Abrir');file_dialog('Abrir proyecto',path)
def save_as(path):button(main,'Guardar como');file_dialog('Guardar proyecto como',path)
def screenshot(w,name):
    from PySide6.QtWidgets import QApplication
    global capture_app
    capture_app=QApplication.instance() or QApplication([])
    front(w);time.sleep(.3);l,t,r,b=win32gui.GetWindowRect(w.handle)
    path=work/(name+'.png');pixels=capture_app.primaryScreen().grabWindow(0,l,t,r-l,b-t)
    assert pixels.save(str(path));screens.append(str(path));print('CAPTURE',path,flush=True)
def worker_paths():
    class Entry(ctypes.Structure):
        _fields_=[('size',wintypes.DWORD),('usage',wintypes.DWORD),('pid',wintypes.DWORD),('heap',ctypes.c_size_t),
            ('module',wintypes.DWORD),('threads',wintypes.DWORD),('parent',wintypes.DWORD),('priority',wintypes.LONG),
            ('flags',wintypes.DWORD),('name',wintypes.WCHAR*260)]
    k=ctypes.WinDLL('kernel32',use_last_error=True);k.CreateToolhelp32Snapshot.restype=wintypes.HANDLE
    k.Process32FirstW.argtypes=[wintypes.HANDLE,ctypes.POINTER(Entry)];k.Process32NextW.argtypes=k.Process32FirstW.argtypes
    k.CloseHandle.argtypes=[wintypes.HANDLE];k.OpenProcess.restype=wintypes.HANDLE
    k.QueryFullProcessImageNameW.argtypes=[wintypes.HANDLE,wintypes.DWORD,wintypes.LPWSTR,ctypes.POINTER(wintypes.DWORD)]
    snap=k.CreateToolhelp32Snapshot(2,0);e=Entry();e.size=ctypes.sizeof(e);found=[]
    try:
        valid=k.Process32FirstW(snap,ctypes.byref(e))
        while valid:
            if e.parent==process.pid:
                h=k.OpenProcess(0x1000,False,e.pid)
                try:
                    buf=ctypes.create_unicode_buffer(32768);size=wintypes.DWORD(len(buf))
                    if k.QueryFullProcessImageNameW(h,0,buf,ctypes.byref(size)):found.append((e.pid,buf.value))
                finally:k.CloseHandle(h)
            valid=k.Process32NextW(snap,ctypes.byref(e))
    finally:k.CloseHandle(snap)
    return found
def result_folders():
    root=work/'Datos/MotorSim/Resultados'
    return set(root.iterdir()) if root.exists() else set()
def start_calculation():
    before=result_folders();button(main,'Ejecutar')
    actual=wait(worker_paths)
    assert len(actual)==1 and Path(actual[0][1]).resolve()==exe.with_name('MotorSimWorker.exe')
    workers.extend(actual);note('Auxiliar real del paquete: '+actual[0][1])
    assert not control(main,'Button','Ejecutar').is_enabled()
    folder=wait(lambda:next((p for p in result_folders()-before if p.is_dir()),None))
    return folder
def account(folder):
    ledger_path=work/'budget.json'
    ledger=json.loads(ledger_path.read_text(encoding='utf-8')) if ledger_path.exists() else dict(limit=300,seconds=0,runs=[])
    paths=[folder/'manifest.json'] if (folder/'manifest.json').exists() else [folder/p['result'] for p in json.loads((folder/'series.json').read_text(encoding='utf-8'))['points'] if p['result']]
    for path in paths:
        r=load_result(path);ledger['seconds']+=r['result']['seconds'];ledger['runs'].append(dict(path=str(path),status=r['status'],seconds=r['result']['seconds']))
    ledger_path.write_text(json.dumps(ledger,indent=2),encoding='utf-8');assert ledger['seconds']<=300
    return ledger
def finish_calculation(folder,series=False):
    wait(lambda:not worker_paths(),75 if not series else 140)
    wait(lambda:control(main,'Button','Ejecutar').is_enabled())
    account(folder)
    return load_sweep(folder/'series.json') if series else load_result(folder/'manifest.json')

try:
    main=window('MotorSim');front(main)
    note('GUI EXE directo, cwd distinto, PATH sistema, sin PYTHONPATH/VIRTUAL_ENV; factor Qt '+args.scale)
    if args.stage=='performance':
        import csv,hashlib
        from motorsim.performance import result_metrics
        root=Path(__file__).resolve().parents[1]/'results/simulacion-2t'
        sources={'2T':root/'barrido-20260915/gui-sweep',
                 '4T':root/'cuatro-tiempos-20260916/R2/gui-sweep'}
        before_results=result_folders()
        hashes={p:hashlib.sha256(p.read_bytes()).hexdigest() for folder in sources.values() for p in folder.rglob('*') if p.is_file()}
        for cycle,folder in sources.items():
            navigate('Rendimiento');button(main,'Abrir barrido…');file_dialog('Abrir barrido para Rendimiento',folder/'series.json')
            assert cycle in texts(main) and '3 / 3' in texts(main)
            screenshot(main,'rc6-'+cycle+'-resumen')
            plot=next(x for x in main.descendants() if x.element_info.name.startswith('Potencia indicada / Par indicado equivalente'))
            plot.set_focus();send_keys('{END}');time.sleep(.3)
            assert '3500 rpm' in texts(main)
            screenshot(main,'rc6-'+cycle+'-combinado')
            table=next(x for x in main.descendants() if x.element_info.name=='Puntos de rendimiento indicado')
            table.set_focus();send_keys('^{HOME}{DOWN}');time.sleep(.3)
            screenshot(main,'rc6-'+cycle+'-tabla')
            button(main,'Abrir resultado del punto')
            assert 'Potencia indicada' in texts(main) and 'Par indicado equivalente' in texts(main)
            screenshot(main,'rc6-'+cycle+'-resultado')
            navigate('Rendimiento');button(main,'Exportar rendimiento CSV…')
            target=work/('CSV rendimiento '+cycle);file_dialog('Carpeta nueva para rendimiento.csv',target)
            with (target/'rendimiento.csv').open(encoding='utf-8') as f:rows=list(csv.DictReader(f))
            expected=load_sweep(folder/'series.json')
            for row,result in zip(rows,expected['results']):
                for key in ('indicated_power_W','indicated_torque_Nm'):
                    assert float(row[key])==result_metrics(result)[key]
            assert not worker_paths()
            note(cycle+': barrido, gráfico/selección, tabla, punto individual y CSV preciso en EXE sin solver')
        folder=sources['4T'].parent
        navigate('Resultados');button(main,'Abrir barrido…');file_dialog('Abrir barrido',folder/'gui-sweep/series.json')
        navigate('Rendimiento');button(main,'Usar barrido actual');assert '4T' in texts(main)
        navigate('Comparar');button(main,'Abrir resultado A…');file_dialog('Abrir resultado A',folder/'gui-sweep/point-02/manifest.json')
        button(main,'Abrir resultado B…');file_dialog('Abrir resultado B',folder/'gui-compression/manifest.json')
        assert 'Compatibles' in texts(main);screenshot(main,'rc6-comparacion')
        button(main,'Exportar CSV…');file_dialog('Crear carpeta nueva',work/'CSV comparación')
        with (work/'CSV comparación/resumen.csv').open(encoding='utf-8') as f:rows=list(csv.DictReader(f))
        assert {'indicated_power_W','indicated_torque_Nm'} <= {row['magnitude'] for row in rows}
        assert not worker_paths() and result_folders()==before_results
        assert all(hashlib.sha256(p.read_bytes()).hexdigest()==digest for p,digest in hashes.items())
        note('Reutilización, comparación y CSV; archivos científicos intactos, ningún resultado nuevo ni worker')
    elif args.stage=='cae-examples':
        from motorsim.examples import PROJECT_FILES
        from motorsim.storage import load_project
        for index,key in enumerate(PROJECT_FILES):
            navigate('Resumen')
            select_combo(control(main,'ComboBox','Proyecto de ejemplo sintético'),index)
            original=exe.parent/'Ejemplos'/PROJECT_FILES[key];before=original.read_bytes()
            button(main,'Cargar copia editable')
            assert 'Cambios pendientes' in main.window_text() and 'Sin archivo asociado' in texts(main)
            assert not worker_paths()
            screenshot(main,'rc5-resumen-'+key)
            target=work/(key+' copia á.json');button(main,'Guardar');file_dialog('Guardar proyecto como',target)
            assert load_project(target)==load_project(original) and original.read_bytes()==before
            navigate('Motor '+key[:2].upper());navigate('Simulación');button(main,'Comprobar entradas')
            assert 'Entradas admitidas' in texts(main) and not worker_paths()
        note('Cuatro JSON como copia sin ruta, dirty, Guardar como, ciclo contextual y validación sin worker')
    elif args.stage=='cae-points':
        record=work/'cae-points.json'
        if record.exists():raise RuntimeError('No repetir puntos de rc5: conservar registro incluso incompleto.')
        records={};record.write_text('{}',encoding='utf-8')
        navigate('Simulación');screenshot(main,'rc5-simulacion-inicial')
        for cycle,index in (('2T',0),('4T',2)):
            select_combo(control(main,'ComboBox','Origen de la próxima ejecución'),index)
            folder=start_calculation();records[cycle]={'path':str(folder/'manifest.json'),'started':True}
            record.write_text(json.dumps(records,indent=2),encoding='utf-8')
            screenshot(main,'rc5-ejecutando-'+cycle)
            navigate('Resumen');navigate('Simulación')
            result=finish_calculation(folder);records[cycle]['status']=result['status']
            record.write_text(json.dumps(records,indent=2),encoding='utf-8')
            assert result['status']=='converged'
            screenshot(main,'rc5-convergido-'+cycle)
            navigate('Resultados');screenshot(main,'rc5-resultados-'+cycle);navigate('Simulación')
        note('Dos únicos puntos rc5 B100/3000, 2T y 4T, proceso del paquete y navegación conservados')
    elif args.stage=='physical-examples':
        from motorsim.examples import PROJECT_FILES,example_file_project
        from motorsim.storage import load_project
        directory=args.projects_root or exe.parent/'Ejemplos'
        for cycle in ('2t','4t'):
            key=cycle+'-reference';original=directory/PROJECT_FILES[key];before=original.read_bytes()
            main.set_focus();send_keys('^o');file_dialog('Abrir proyecto',original)
            navigate('Resumen');assert 'Listo para simular' in texts(main)
            navigate('Geometría');assert control(main,'Edit',suffix='.bore_mm').get_value()=='54'
            navigate('Motor '+cycle.upper());screenshot(main,'json-'+cycle+'-configuracion');tab(main,'Conductos')
            screenshot(main,'json-'+cycle+'-conductos')
            navigate('Simulación')
            select_combo(control(main,'ComboBox'),1);button(main,'Comprobar entradas')
            assert 'Entradas admitidas para este modelo' in texts(main) and not worker_paths()
            navigate('Resumen');screenshot(main,'json-'+cycle+'-listo')
            target=work/(cycle+' copia á.json')
            main.set_focus();send_keys('^+s');file_dialog('Guardar proyecto como',target)
            assert load_project(target)==example_file_project(key)
            assert original.read_bytes()==before
            note(cycle.upper()+': Archivo/Abrir, geometría, conductos, listo, entradas y Guardar como sin modificar original')
        assert not worker_paths()
    elif args.stage=='uxvisual':
        from pywinauto import mouse
        source=Path(__file__).resolve().parents[1]/'results/simulacion-2t/cuatro-tiempos-20260916/R2'
        open_project(exe.parent/'Ejemplos/EJEMPLO_SINTETICO_2T_REFERENCIA.json')
        for name in ('Resumen','Geometría','Motor 2T','Simulación'):
            navigate(name);screenshot(main,'rc4-'+name+'-'+args.scale)
        open_project(exe.parent/'Ejemplos/EJEMPLO_SINTETICO_4T_REFERENCIA.json')
        navigate('Motor 4T');screenshot(main,'rc4-Motor 4T-'+args.scale)
        navigate('Resultados');button(main,'Abrir resultado…');file_dialog('Abrir resultado',source/'gui-sweep/point-02/manifest.json')
        screenshot(main,'rc4-Resultados-'+args.scale)
        navigate('Comparar');button(main,'Abrir resultado A…');file_dialog('Abrir resultado A',source/'gui-sweep/point-02/manifest.json')
        button(main,'Abrir resultado B…');file_dialog('Abrir resultado B',source/'gui-compression/manifest.json')
        screenshot(main,'rc4-Comparar-'+args.scale)
        navigate('Datos externos');button(main,'Abrir importación…');file_dialog('Abrir importación',work/'Importación UX/metadata.json')
        button(main,'Seleccionar barrido…');file_dialog('Seleccionar barrido guardado',source/'gui-sweep/series.json')
        screenshot(main,'rc4-Datos externos-'+args.scale)
        # Recorrido del contenido inferior real, sin editar ni ejecutar.
        mouse.scroll(coords=(1200,650),wheel_dist=-12);time.sleep(.3)
        screenshot(main,'rc4-Contraste inferior-'+args.scale)
        assert not worker_paths();note('Ocho vistas y desplazamiento del contraste: capturas de escritorio, sin worker')
    elif args.stage=='examples':
        from motorsim.examples import example_project
        def example(title):
            main.set_focus();send_keys('%a');send_keys('e')
            control(main,'MenuItem',title)  # Opciones del menú realmente expuestas.
            index=['2T referencia','2T compresión 8.2','4T referencia','4T compresión 8.2'].index(title)
            send_keys('{HOME}'+('{DOWN '+str(index)+'}' if index else '')+'{ENTER}');time.sleep(.3)
        example('2T referencia')
        assert 'Cambios pendientes' in main.window_text() and 'Sin archivo asociado' in texts(main)
        button(main,'Guardar');file_dialog('Guardar proyecto como',work/'Ejemplo 2T á.json')
        assert json.loads((work/'Ejemplo 2T á.json').read_text(encoding='utf-8'))==example_project('2t-reference').to_dict()
        example('4T compresión 8.2')
        assert 'Cambios pendientes' in main.window_text() and 'Sin archivo asociado' in texts(main)
        navigate('Motor 4T');navigate('Resumen');screenshot(main,'rc4-ejemplo-4t-150')
        navigate('Simulación');button(main,'Comprobar entradas')
        assert '8.2:1' in texts(main)
        navigate('Resultados')
        historical=work/'Historico/manifest.json'
        button(main,'Abrir resultado…');file_dialog('Abrir resultado',historical)
        assert 'Trabajo indicado' in texts(main) and not worker_paths()
        note('Carga canónica 2T/4T8.2, Guardar como, dirty/ruta, comprobación de entradas y resultado existente sin integrar')
        navigate('Resumen');example('2T compresión 8.2')
        button(window('Cambios pendientes'),'Cancelar')
        assert '4T COMPRESIÓN 8.2' in main.window_text()
        example('2T compresión 8.2');button(window('Cambios pendientes'),'Descartar')
        assert '2T COMPRESIÓN 8.2' in main.window_text()
        example('4T referencia');button(window('Cambios pendientes'),'Descartar')
        assert '4T REFERENCIA' in main.window_text()
        button(main,'Guardar');file_dialog('Guardar proyecto como',work/'Ejemplo 4T á.json')
        assert json.loads((work/'Ejemplo 4T á.json').read_text(encoding='utf-8'))==example_project('4t-reference').to_dict()
        note('Cuatro opciones accesibles, Cancelar/Descartar, referencias guardadas equivalentes y sin tocar recursos incluidos')
    elif args.stage=='uxeditor':
        navigate('Resumen');tab(main,'Datos del proyecto')
        control(main,'Edit',suffix='.project_name').set_edit_text('PRUEBA SINTÉTICA UX á')
        button(main,'Guardar');file_dialog('Guardar proyecto como',work/'Proyecto UX á.json')
        original=(work/'Proyecto UX á.json').read_bytes()
        button(main,'Nuevo');open_project(work/'Proyecto UX á.json')
        assert (work/'Proyecto UX á.json').read_bytes()==original
        navigate('Resumen');tab(main,'Datos del proyecto')
        assert control(main,'Edit',suffix='.project_name').get_value()=='PRUEBA SINTÉTICA UX á'
        open_project(exe.parent/'Ejemplos/EJEMPLO_SINTETICO_4T_REFERENCIA.json')
        navigate('Motor 4T');navigate('Geometría');navigate('Resumen');tab(main,'Resumen')
        screenshot(main,'rc3-resumen-150');note('Guardar/Nuevo/reabrir Unicode; navegación 4T y geometría conservada')
    elif args.stage=='uxpoint':
        if result_folders():raise RuntimeError('No repetir el único punto UX autorizado.')
        navigate('Simulación');first=start_calculation()
        navigate('Resumen');navigate('Simulación')
        result=finish_calculation(first);assert result['status']=='converged'
        (work/'ux-point.json').write_text(json.dumps(dict(path=str(first/'manifest.json')),indent=2),encoding='utf-8')
        navigate('Resultados');screenshot(main,'rc3-punto-150');note('Único punto 2T B100/3000 convergido; navegar conserva worker')
    elif args.stage=='uxcancel':
        if (work/'ux-cancel.json').exists():raise RuntimeError('Cancelación UX ya registrada.')
        navigate('Simulación');first=start_calculation()
        wait(lambda:'RHS:' in texts(main));button(main,'Cancelar')
        result=finish_calculation(first);assert result['status']=='cancelled'
        (work/'ux-cancel.json').write_text(json.dumps(dict(path=str(first/'manifest.json')),indent=2),encoding='utf-8')
        note('Cancelación cooperativa; sin hijo activo ni resultado aceptado')
    elif args.stage=='uxseries':
        source=Path(__file__).resolve().parents[1]/'results/simulacion-2t/cuatro-tiempos-20260916/R2/gui-sweep'
        navigate('Resultados');button(main,'Abrir barrido…');file_dialog('Abrir barrido',source/'series.json')
        button(main,'Consultar punto convergido')
        assert '2500 rpm' in texts(main) and 'Trabajo indicado' in texts(main)
        screenshot(main,'rc3-punto-historico-150')
        assert not worker_paths();note('Barrido histórico embebido y consulta de su primer punto sin cálculo')
    elif args.stage=='uxanalysis':
        source=Path(__file__).resolve().parents[1]/'results/simulacion-2t/cuatro-tiempos-20260916/R2'
        navigate('Resultados');button(main,'Abrir resultado…');file_dialog('Abrir resultado',source/'gui-compression/manifest.json')
        assert 'Trabajo indicado' in texts(main)
        navigate('Comparar');button(main,'Abrir resultado A…');file_dialog('Abrir resultado A',source/'gui-sweep/point-02/manifest.json')
        button(main,'Abrir resultado B…');file_dialog('Abrir resultado B',source/'gui-compression/manifest.json')
        assert 'Compatibles' in texts(main);screenshot(main,'rc3-comparacion-150')
        button(main,'Exportar CSV…');file_dialog('Crear carpeta nueva',work/'CSV comparación UX')
        assert (work/'CSV comparación UX/resumen.csv').exists()
        navigate('Datos externos')
        csv=work/'PRUEBA SINTÉTICA.csv';csv.write_text('rpm,value\n2500,52\n3000,50\n',encoding='utf-8')
        button(main,'Importar CSV…');file_dialog('Seleccionar CSV externo',csv)
        cs=[x for x in main.descendants() if x.element_info.control_type=='ComboBox']
        select_combo(cs[0],2);select_combo(cs[1],1);select_combo(cs[2],3)
        control(main,'CheckBox','Declaro que los datos cumplen esta definición completa').click_input()
        button(main,'Revisar vista previa');button(main,'Confirmar y guardar…')
        file_dialog('Carpeta nueva para la importación',work/'Importación UX')
        button(main,'Seleccionar barrido…');file_dialog('Seleccionar barrido guardado',source/'gui-sweep/series.json')
        assert '2 coincidencias convergidas' in texts(main)
        button(main,'Exportar contraste…');file_dialog('Carpeta nueva para contraste.csv',work/'Contraste UX')
        assert (work/'Contraste UX/contraste.csv').exists()
        tab(main,'Puntos / RPM');screenshot(main,'rc3-externos-150')
        assert not worker_paths();note('Resultado, comparación/CSV e importación/contraste embebidos sin worker')
    elif args.stage=='editor':
        control(main,'Edit',suffix='.project_name').set_edit_text('PRUEBA SINTÉTICA — cigüeñal á')
        button(main,'Guardar');file_dialog('Guardar proyecto como',work/'incompleto á.json')
        saved=json.loads((work/'incompleto á.json').read_text(encoding='utf-8'));assert saved['bore_mm'] is None
        note('Guardar incompleto con nombre/ruta Unicode')
        save_as(work/'copia ñ.json');assert (work/'copia ñ.json').exists();note('Guardar como')
        control(main,'Edit',suffix='.bore_mm').set_edit_text('inválido')
        button(main,'Guardar');button(window('MotorSim — Error'),'Aceptar')
        assert json.loads((work/'copia ñ.json').read_text(encoding='utf-8'))['bore_mm'] is None
        button(main,'Nuevo');button(window('Cambios pendientes'),'Cancelar')
        assert control(main,'Edit',suffix='.bore_mm').get_value()=='inválido'
        button(main,'Nuevo');button(window('Cambios pendientes'),'Descartar')
        note('Inválidos no guardados, Nuevo protegido por Cancelar/Descartar')
        open_project(exe.parent/'Ejemplos/EJEMPLO_SINTETICO_4T_REFERENCIA.json')
        combo(main,'Tipo de motor',0);combo(main,'Tipo de motor',1)
        save_as(work/'alternancia 4T.json')
        assert json.loads((work/'alternancia 4T.json').read_text(encoding='utf-8'))==json.loads((exe.parent/'Ejemplos/EJEMPLO_SINTETICO_4T_REFERENCIA.json').read_text(encoding='utf-8'))
        note('Abrir ejemplo y alternar 2T/4T sin pérdida')
        old=work/'antiguo v1.json';old.write_text(json.dumps(dict(format_version=1,name='ANTIGUO á',cycle='2T')),encoding='utf-8')
        open_project(old);save_as(work/'antiguo convertido.json')
        assert json.loads((work/'antiguo convertido.json').read_text(encoding='utf-8'))['format_version']==6
        assert json.loads(old.read_text())['format_version']==1
        open_project(exe.parent/'Ejemplos/EJEMPLO_SINTETICO_4T_REFERENCIA.json')
        note('Lectura v1 sin reescritura, conversión explícita v6')
        screenshot(main,'paquete-editor-150')
        front(main,1000,740)
        # Captura compacta sin restaurar el ancho grande.
        from PySide6.QtWidgets import QApplication
        capture_app=QApplication.instance() or QApplication([]);time.sleep(.3)
        l,t,r,b=win32gui.GetWindowRect(main.handle);path=work/'paquete-compacto-150.png'
        assert capture_app.primaryScreen().grabWindow(0,l,t,r-l,b-t).save(str(path));screens.append(str(path))
    elif args.stage=='numerical':
        if (work/'numerical.json').exists():raise RuntimeError('No repetir los puntos registrados.')
        ledger=work/'budget.json'
        if ledger.exists():assert json.loads(ledger.read_text())['seconds']+180<=300
        tab(main,'Simulación')
        if args.resume_two:
            first=args.resume_two.resolve().parent;two=load_result(first/'manifest.json')
            assert any(Path(r['path'])==first/'manifest.json' for r in json.loads(ledger.read_text())['runs'])
            note('2T previamente completado, no se repite')
        else:
            first=start_calculation();two=finish_calculation(first)
        assert two['status']=='converged';note('Referencia 2T convergida')
        if not args.resume_two:screenshot(main,'paquete-2t-150')
        open_project(exe.parent/'Ejemplos/EJEMPLO_SINTETICO_4T_REFERENCIA.json')
        tab(main,'Simulación');combo(main,'Origen de la próxima ejecución',1)
        # La segunda combo es modo de ejecución; selección por nombre accesible de formulario.
        combo(main,'Ejecución',1)
        control(main,'Edit','Final [rpm]').set_edit_text('3000')
        second=start_calculation();four=finish_calculation(second,True)
        assert four['index']['state']=='converged'
        dialog=window('Barrido de RPM');screenshot(dialog,'paquete-barrido-150');button(dialog,'Cerrar')
        paths=dict(two_stroke=str(first/'manifest.json'),four_stroke=str(second/'series.json'))
        (work/'numerical.json').write_text(json.dumps(paths,indent=2),encoding='utf-8')
        note('Barrido GUI 4T B2500/3000 convergido')
    elif args.stage=='hardening':
        if result_folders():raise RuntimeError('Protocolo nuevo: no repetir puntos existentes.')
        tab(main,'Simulación');first=start_calculation();two=finish_calculation(first)
        assert two['status']=='converged' and 'interface_wall_seconds' in two['manifest']['timings']
        screenshot(main,'rc2-2t-150')
        open_project(exe.parent/'Ejemplos/EJEMPLO_SINTETICO_4T_REFERENCIA.json');tab(main,'Simulación')
        combo(main,'Origen de la próxima ejecución',1)
        second=start_calculation();four=finish_calculation(second)
        assert four['status']=='converged' and 'interface_wall_seconds' in four['manifest']['timings']
        screenshot(main,'rc2-4t-150')
        (work/'hardening-numerical.json').write_text(json.dumps(dict(two_stroke=str(first/'manifest.json'),four_stroke=str(second/'manifest.json')),indent=2),encoding='utf-8')
        note('Dos únicos puntos completos rc2 B100/3000, 2T y proyecto 4T, con tiempos persistidos')
    elif args.stage in ('cancel','cancel-once'):
        tab(main,'Simulación');first=start_calculation()
        wait(lambda:'RHS:' in texts(main));button(main,'Cancelar')
        result=finish_calculation(first);assert result['status']=='cancelled'
        note('Cancelación cooperativa; diagnóstico no aceptado, sin hijo activo')
        if args.stage=='cancel':
            second=start_calculation();wait(lambda:'RHS:' in texts(main))
            win32gui.PostMessage(main.handle,win32con.WM_CLOSE,0,0)
            process.wait(timeout=10);wait(lambda:not worker_paths());account(second)
            assert load_result(second/'manifest.json')['status']=='cancelled'
            note('Cierre durante cálculo sin huérfanos')
    elif args.stage=='reopen':
        tab(main,'Simulación');n=json.loads((work/'hardening-numerical.json').read_text())
        path=Path(n['two_stroke']);original=path.read_bytes()
        button(main,'Abrir resultado…');file_dialog('Abrir resultado',path)
        assert 'Preparación:' in texts(main) and 'Percibido:' in texts(main)
        assert path.read_bytes()==original
        from pywinauto import mouse
        mouse.scroll(coords=(950,550),wheel_dist=-4);time.sleep(.2)
        screenshot(main,'rc2-tiempos-150')
        broken=work/'Control corrupto';broken.mkdir();(broken/'manifest.json').write_text('{incorrecto',encoding='utf-8')
        button(main,'Abrir resultado…');file_dialog('Abrir resultado',broken/'manifest.json')
        assert 'Se conserva el resultado previamente abierto' in texts(main)
        assert 'Convergencia numérica alcanzada' in texts(main)
        assert not worker_paths();note('Reabrir v1 con tiempos sin escritura; corrupto rechazado conservando resultado')
    elif args.stage=='missing':
        tab(main,'Simulación');button(main,'Ejecutar')
        assert 'Falta el auxiliar' in texts(main) and not worker_paths()
        note('Auxiliar ausente: error útil, botón disponible y sin cálculo ficticio')
    elif args.stage=='process':
        import win32api
        def consoles():
            found=[]
            def visit(h,_):
                if win32gui.IsWindowVisible(h) and win32gui.GetClassName(h)=='ConsoleWindowClass':found.append(h)
            win32gui.EnumWindows(visit,None);return set(found)
        before=consoles();tab(main,'Simulación');folder=start_calculation();actual=worker_paths();assert len(actual)==1
        loaded={}
        for pid in (process.pid,actual[0][0]):
            h=win32api.OpenProcess(0x410,False,pid)
            try:loaded[str(pid)]=[win32process.GetModuleFileNameEx(h,m) for m in win32process.EnumProcessModules(h)]
            finally:h.Close()
        assert consoles()==before
        for modules in loaded.values():
            runtime=[p for p in modules if Path(p).name.lower()=='python311.dll']
            assert len(runtime)==1 and Path(runtime[0]).resolve()==exe.parent/'_internal/python311.dll'
        assert not any('Qt6' in p for p in loaded[str(actual[0][0])])
        (work/'process-modules.json').write_text(json.dumps(loaded,ensure_ascii=False,indent=2),encoding='utf-8')
        button(main,'Cancelar');wait(lambda:not worker_paths())
        if (folder/'manifest.json').exists():
            account(folder);assert load_result(folder/'manifest.json')['status']=='cancelled'
        else:
            # No ocultar una cancelación forzada ni declarar tiempo no medido.
            raise RuntimeError('Cancelación forzada: registrar cota de tiempo y conservar evidencia; no repetir automáticamente')
        note('GUI/worker cargan python311.dll del paquete; worker sin Qt y sin consola visible durante ejecución')
    elif args.stage=='provenance':
        open_project(exe.parent/'Ejemplos/EJEMPLO_SINTETICO_4T_REFERENCIA.json');tab(main,'Simulación')
        n=json.loads((work/'numerical.json').read_text())
        button(main,'Abrir resultado…');file_dialog('Abrir resultado',Path(n['four_stroke']).parent/'point-02/manifest.json')
        assert 'configuración anterior' not in texts(main)
        tab(main,'Ficha');control(main,'Edit',suffix='.bore_mm').set_edit_text('55')
        tab(main,'Simulación');assert 'configuración anterior' in texts(main)
        note('Procedencia preservada y aviso de configuración anterior tras editar')
        button(main,'Abrir resultado…');file_dialog('Abrir resultado',Path(n['two_stroke']))
        assert 'Convergencia numérica alcanzada' in texts(main)
        note('Lector de resultado referencia 2T v1 del paquete')
        front(main,1000,740);control(main,'TabItem','Ficha').set_focus();send_keys('{END}')
        time.sleep(.2);assert control(main,'TabItem','Simulación').is_selected()
        note('Pestaña final accesible por teclado en ventana compacta al 150 %')
        tab(main,'Ficha');control(main,'Edit',suffix='.bore_mm').set_edit_text('54')
    elif args.stage=='about':
        control(main,'MenuItem','Ayuda').click_input();control(main,'MenuItem','Acerca de MotorSim…').click_input()
        d=window('Acerca de MotorSim');info=json.loads((exe.parent/'build.json').read_text(encoding='utf-8'));assert info['app_version'] in texts(d) and info['source_commit'] in texts(d)
        screenshot(d,'paquete-acerca');button(d,'Aceptar');note('Acerca de identifica versión/commit sin Git')
        control(main,'MenuItem','Ayuda').click_input();control(main,'MenuItem','Guía breve…').click_input()
        d=window('MotorSim — Guía breve');assert any('Cancelar' in x.window_text() for x in d.descendants())
        button(d,'Cerrar');note('Ayuda incluida accesible')
    elif args.stage=='external':
        tab(main,'Simulación');button(main,'Datos externos…');d=window('Datos externos');front(d)
        csv=work/'PRUEBA SINTÉTICA importación.csv';csv.write_text('rpm,value\n2500,52\n3000,50\n',encoding='utf-8')
        button(d,'Importar CSV…');file_dialog('Seleccionar CSV externo',csv)
        imp=window('Importar CSV ·');front(imp)
        cs=[x for x in imp.descendants() if x.element_info.control_type=='ComboBox']
        select_combo(cs[0],2);select_combo(cs[1],1);select_combo(cs[2],3)
        control(imp,'CheckBox','Declaro que los datos cumplen esta definición completa').click_input()
        edits=[x for x in imp.descendants() if x.element_info.control_type=='Edit']
        edits[0].set_edit_text('PRUEBA SINTÉTICA — no medida')
        button(imp,'Revisar vista previa');assert control(imp,'Button','Confirmar y guardar…').is_enabled()
        button(imp,'Confirmar y guardar…');file_dialog('Carpeta nueva para la importación',work/'Importación sintética á')
        wait(lambda:not win32gui.IsWindowVisible(imp.handle))
        button(d,'Seleccionar barrido…');file_dialog('Seleccionar barrido guardado',work/'Historicos/gui-sweep/series.json')
        assert '2 coincidencias convergidas' in texts(d)
        screenshot(d,'paquete-importacion-150')
        button(d,'Exportar contraste…');file_dialog('Carpeta nueva para contraste.csv',work/'Contraste sintético á')
        assert (work/'Contraste sintético á/contraste.csv').exists()
        button(d,'Abrir importación…');file_dialog('Abrir importación',work/'Importación sintética á/metadata.json')
        assert 'PRUEBA SINTÉTICA' in texts(d);button(d,'Cerrar')
        note('Importar CSV declarado sintético, vista previa, guardar/reabrir, contraste y exportación sin cálculo')
    elif args.stage=='history':
        tab(main,'Simulación')
        source=Path(__file__).resolve().parents[1]/'results/simulacion-2t/cuatro-tiempos-20260916/R2'
        reference=work/'Historicos'
        if not reference.exists():
            for name in ('gui-sweep','gui-compression'):
                shutil.copytree(source/name,reference/name,ignore=shutil.ignore_patterns('attempts.csv'))
        button(main,'Abrir resultado…');file_dialog('Abrir resultado',reference/'gui-compression/manifest.json')
        assert 'Convergencia numérica alcanzada' in texts(main)
        note('Resultado 4T histórico reabierto')
        button(main,'Comparar resultados…');dialog=window('Comparar resultados')
        button(dialog,'Abrir resultado A…');file_dialog('Abrir resultado A',reference/'gui-sweep/point-02/manifest.json')
        button(dialog,'Abrir resultado B…');file_dialog('Abrir resultado B',reference/'gui-compression/manifest.json')
        assert 'Compatibles' in texts(dialog)
        screenshot(dialog,'paquete-comparacion-150')
        button(dialog,'Exportar CSV…');file_dialog('Crear carpeta nueva',work/'CSV comparación á')
        assert (work/'CSV comparación á/resumen.csv').exists()
        button(dialog,'Cerrar');note('Comparación y CSV sin reintegrar')
        button(main,'Abrir barrido…');file_dialog('Abrir barrido',reference/'gui-sweep/series.json')
        dialog=window('Barrido de RPM');button(dialog,'Exportar CSV…');file_dialog('Carpeta nueva para serie.csv',work/'CSV barrido á')
        assert (work/'CSV barrido á/serie.csv').exists();button(dialog,'Cerrar')
        note('Barrido histórico reabierto y exportado')
    if process.poll() is None:
        win32gui.PostMessage(main.handle,win32con.WM_CLOSE,0,0)
        if args.stage=='provenance':button(window('Cambios pendientes'),'Descartar')
        process.wait(timeout=10)
    (work/(args.stage+'-evidence.json')).write_text(json.dumps(dict(stage=args.stage,exe=str(exe),
        cwd=str(cwd),pid=process.pid,workers=workers,qt_scale_factor=args.scale,checks=checks,
        screenshots=screens,automated=True,manual_acceptance=False),ensure_ascii=False,indent=2),encoding='utf-8')
except Exception as exc:
    (work/(args.stage+'-failure.txt')).write_text(repr(exc),encoding='utf-8')
    print('FAILED',repr(exc),flush=True)
    raise
