"""Standalone visual evidence from original, unedited Qt captures."""
import argparse,base64,hashlib,html,json,os,struct
from pathlib import Path


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True);args=parser.parse_args();root=args.root
    before=root.parent/'frontend-commercial-integration-v1/packaged-qt';after=root/'windows-f23-v2';candidate=json.loads((root/'candidate.json').read_text(encoding='utf-8'));artifacts=[]
    def picture(path,label):
        raw=path.read_bytes();width,height=struct.unpack('>II',raw[16:24]);relative=os.path.relpath(path,root).replace(chr(92),'/');digest=hashlib.sha256(raw).hexdigest();artifacts.append(dict(file=relative,sha256=digest,width=width,height=height))
        return '<figure><figcaption>'+html.escape(label)+f' · {width}×{height}</figcaption><img alt="'+html.escape(label)+'" src="data:image/png;base64,'+base64.b64encode(raw).decode()+'"></figure>'
    pairs=[('Componentes coordinados',before/'01-integrated-2t.png',after/'01-2t-components.png'),('Explorar datos y unidades',before/'13-reference-result.png',after/'07-reference-cursor.png'),('Comparación A/B · fixture sintética',before/'14-synthetic-presentation-comparison.png',after/'05b-expanded-ab.png'),('Modelo nativo compacto',before/'21-compact.png',after/'08-native-980.png')]
    body='<h1>Dino · evolución F2/F3</h1><p>Antes: rc13 aceptado8712f290. Después: rc14 '+html.escape(candidate['source_commit'][:8])+'. Capturas de ejecutables Windows reales. Comparación de interfaz; no acredita diferencias físicas ni validación experimental.</p>'
    for title,left,right in pairs:body+='<section><h2>'+html.escape(title)+'</h2><div class="pair">'+picture(left,'Antes · rc13')+picture(right,'Después · rc14')+'</div></section>'
    body+='<section><h2>Lectura exacta y recuperación</h2><p>El cursor selecciona muestras existentes. La recuperación identifica borradores, permite posponer y guarda una copia sin sobrescribir el original. Las referencias0D mantienen borradores separados.</p><div class="pair">'+picture(after/'03b-expanded-trace.png','Traza real de integración · sin validación experimental')+picture(after/'09-recovery-preview.png','Selector real de recuperación')+'</div></section>'
    document='<!doctype html><html lang="es"><meta charset="utf-8"><title>Dino F2 F3 · evidencia visual</title><style>body{font:15px Segoe UI,sans-serif;color:#e5edf6;background:#101722;margin:28px}h1,h2{font-weight:600}p{max-width:1100px;line-height:1.5;color:#bbcfdf}.pair{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}figure{margin:0;background:#172434;border:1px solid #405a72;padding:10px;border-radius:6px}figcaption{margin-bottom:8px}img{width:100%;height:auto;display:block}section{margin:28px 0}@media(max-width:900px){.pair{grid-template-columns:1fr}}</style>'+body+'</html>'
    path=root/'visual-before-after.html';path.write_text(document,encoding='utf-8');artifacts.append(dict(file=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    (root/'visual-evidence.json').write_text(json.dumps(dict(schema='DINO_FRONTEND_VISUAL_EVIDENCE_V1',method='Original Qt captures embedded losslessly; SELF_REVIEW, no physical comparison claim',candidate_commit=candidate['source_commit'],artifacts=artifacts),ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print('Visual evidence:',len(artifacts),'artifacts')


if __name__=='__main__':main()
