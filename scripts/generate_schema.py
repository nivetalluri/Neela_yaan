"""Run from project root: python scripts/generate_schema.py.
Regenerates shared sensor interfaces, preserving derived dashboard envelope.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.telemetry_models import Telemetry
schema=Telemetry.model_json_schema()
def typ(v):
 if '$ref' in v:return v['$ref'].split('/')[-1]
 if 'anyOf' in v:return ' | '.join(typ(x) for x in v['anyOf'])
 if 'enum' in v:return ' | '.join(repr(x) for x in v['enum'])
 return {'number':'number','integer':'number','boolean':'boolean','null':'null','string':'string'}.get(v.get('type'),'unknown')
p=Path('frontend/src/types.ts');derived=p.read_text().split('export interface Telemetry {',1)[1]
text='// Sensor interfaces generated from backend Pydantic schema.\n'
for name,v in schema['$defs'].items():text+='export interface '+name+' {\n'+''.join('  '+k+': '+typ(x)+';\n' for k,x in v['properties'].items())+'}\n'
p.write_text(text+'export interface Telemetry {'+derived)
Path('telemetry.schema.json').write_text(json.dumps(schema,indent=2))
