"""Generate only requested cast auditions, save each completed take, never retry uncertain requests."""
import base64,hashlib,io,json,os,sys,time,wave
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError

plan=json.loads(Path('episodes/nightwatch9/audition/plan_v01.json').read_text())
out=Path('nightwatch9-auditions');out.mkdir(exist_ok=True);mf=out/'manifest.json'
m=json.loads(mf.read_text()) if mf.exists() else {'model':plan['model'],'samples':{}}
key=os.environ['GEMINI_API_KEY'];limit=5;generated=0
def save():mf.write_text(json.dumps(m,ensure_ascii=False,indent=2))
for t in plan['samples']:
 tid=t['id'];stamp=hashlib.sha256(json.dumps({k:t[k] for k in ['voice','text','style']},sort_keys=True,ensure_ascii=False).encode()).hexdigest();dest=out/f"{t['number']:02}_{tid}_{t['voice']}.wav";old=m['samples'].get(tid,{})
 if old.get('fingerprint')==stamp and old.get('status')=='complete' and dest.exists():continue
 if old.get('status')=='uncertain':raise SystemExit(f'{tid}: unresolved earlier request; stop before generating again')
 if generated>=limit:break
 m['samples'][tid]={'character':t['character'],'voice':t['voice'],'text':t['text'],'file':dest.name,'fingerprint':stamp,'status':'uncertain'};save()
 payload={'contents':[{'role':'user','parts':[{'text':t['text'],'speech_metadata':{'style':t['style']}}]}],'generationConfig':{'responseModalities':['AUDIO'],'speechConfig':{'voiceConfig':{'voice':t['voice']}}}}
 req=Request(f'https://generativelanguage.googleapis.com/v1beta/models/{plan["model"]}:generateContent',data=json.dumps(payload,ensure_ascii=False).encode(),method='POST',headers={'x-goog-api-key':key,'Content-Type':'application/json'})
 try:
  for attempt in range(3):
   try:
    with urlopen(req,timeout=180) as resp:result=json.load(resp)
    break
   except HTTPError as err:
    if err.code!=429 or attempt==2:raise
    msg=err.read().decode(errors='replace')
    if 'perday' in msg.lower().replace('_',''):raise
    print(f'{tid}: rejected rate limit, waiting 45s',flush=True);time.sleep(45)
  candidates=result.get('candidates',[])
  if len(candidates)!=1 or candidates[0].get('finishReason')!='STOP':raise ValueError('Incomplete generation')
  parts=[p['inlineData'] for p in candidates[0].get('content',{}).get('parts',[]) if 'inlineData' in p]
  if len(parts)!=1:raise ValueError('Expected one audio result')
  raw=base64.b64decode(parts[0]['data'],validate=True)
  if raw[:4]!=b'RIFF' or raw[8:12]!=b'WAVE':raise ValueError('Expected WAV')
  with wave.open(io.BytesIO(raw),'rb') as w:
   duration=w.getnframes()/w.getframerate()
   if not duration>0:raise ValueError('Empty WAV')
  tmp=dest.with_suffix('.tmp');tmp.write_bytes(raw);tmp.replace(dest)
 except HTTPError as err:
  m['samples'][tid].update(status='http_error',http_status=err.code);save();raise SystemExit(f'{tid}: HTTP {err.code}; stopped, completed files retained')
 m['samples'][tid].update(status='complete',duration_seconds=duration,sha256=hashlib.sha256(raw).hexdigest());save();generated+=1
 print(f"Saved {tid} / {t['voice']} / {duration:.2f}s",flush=True);time.sleep(7)
print(f"Completed {sum(v['status']=='complete' for v in m['samples'].values())}/{len(plan['samples'])}",flush=True)
