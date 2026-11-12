"""Configuration-to-presentation adapter. No solver objects or derived physics."""
from dataclasses import asdict


def applied_component_summary(window,key):
    if window._native_four_stroke_active():
        section=dict(cylinder='geometry',geometry='geometry',intake='intake_duct',exhaust='exhaust_duct',intake_valve='intake_valve',exhaust_valve='exhaust_valve').get(key,'geometry')
        values=window.native_four_stroke.context.engine().get(section,{})
    elif window._four_stroke_active():
        project=window.four_stroke_context.project
        if key in ('geometry','cylinder'):
            values=dict(bore_mm=project.bore_mm,stroke_mm=project.stroke_mm,rod_length_mm=project.rod_length_mm,compression_ratio=project.compression_ratio)
        elif key in ('intake_valve','exhaust_valve'):values=asdict(getattr(project,key.split('_')[0]))
        else:
            return 'Referencia sintética 0D · conductos\n'+str(len(getattr(project.ducts,key)))+' tramos aplicados. Dimensiones en el formulario; no es un motor nativo.'
    else:
        config=window.context.engine()['native_configuration'];slider=config.get('slider_crank',{});crank=slider.get('crankcase',{})
        if key=='cylinder':values={k:crank.get(k) for k in ('bore_mm','stroke_mm','rod_length_mm')};values['compression_ratio']=slider.get('cylinder_compression_ratio')
        elif key=='crankcase':values={k:crank.get(k) for k in ('volume_bdc_cm3','provenance')}
        elif key in ('intake','exhaust','transfer'):
            ducts=[d for d in config.get('ducts',[]) if d.get('role')==key or (key=='transfer' and d.get('role')=='transfer')]
            return 'Configuración aplicada\n'+('\n'.join(str(d.get('id'))+' · '+str(len(d.get('mesh',{}).get('centers',[])))+' celdas' for d in ducts) or 'Ver parámetros del conducto en el editor')
        elif key=='ports':return 'Lumbreras del modelo aplicado\nDimensiones, distribución y áreas efectivas en las vistas del editor. Los eventos se derivan del modelo existente.'
        else:return 'Combustión del modelo aplicado\nParámetros y procedencia en el formulario; sin validación experimental.'
    labels={'bore_mm':'Diámetro [mm]','stroke_mm':'Carrera [mm]','rod_mm':'Biela [mm]','rod_length_mm':'Biela [mm]','compression_ratio':'Compresión [:1]','volume_bdc_cm3':'Cárter en PMI [cm³]','provenance':'Procedencia','count':'Cantidad','diameter_mm':'Diámetro [mm]','length_mm':'Longitud [mm]','seat_mm':'Asiento [mm]','throat_mm':'Garganta [mm]','stem_mm':'Vástago [mm]','lift_mm':'Alzada [mm]','opening_deg':'Apertura [°]','duration_deg':'Duración [°]','max_lift_mm':'Alzada máxima [mm]','open_deg':'Abre [°]','close_deg':'Cierra [°]'}
    rows=[]
    values={**values,**values.get('lift',{})} if isinstance(values.get('lift'),dict) else values
    for name,value in values.items():
        if isinstance(value,(int,float,str)) or value is None:rows.append(f"{labels.get(name,name)}: {'No definido' if value is None else value}")
    return 'Configuración aplicada\n'+'\n'.join(rows[:9])
