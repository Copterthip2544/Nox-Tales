"""Generate only the fourteen requested Charon patches; preserve uncertain requests."""
import base64,hashlib,json,os,sys,time,wave
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
sys.path.insert(0,'scripts')
from produce_hotel13_audio_batch5 import audio_bytes

root=Path('episodes/hotel13/v1.4');out=Path('revision-audio');out.mkdir(exist_ok=True)
p=json.loads((root/'revision_plan.json').read_text());mf=out/'manifest.json'
m=json.loads(mf.read_text()) if mf.exists() else {'model':p['model'],'voice':'Charon','turns':{}}
def save():mf.write_text(json.dumps(m,ensure_ascii=False,indent=2))
key=os.environ['GEMINI_API_KEY'];new=0
for t in p['turns']:
 tid=t['id'];dest=out/(tid+'_nox.wav');stamp=hashlib.sha256(json.dumps(t,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
 old=m['turns'].get(tid,{})
 if old.get('status')=='complete' and old.get('fingerprint')==stamp and dest.exists():continue
 if old.get('status')=='uncertain':raise SystemExit(f'{tid}: uncertain prior request, stop before billing again')
 if new>=5:break
 m['turns'][tid]={'status':'uncertain','fingerprint':stamp,'text':t['text'],'voice':'Charon','file':dest.name};save()
 payload={'contents':[{'role':'user','parts':[{'text':t['text'],'speech_metadata':{'style':t['style']}}]}], 'generationConfig':{'responseModalities':['AUDIO'],'speechConfig':{'voiceConfig':{'voice':'Charon'}}}}
 req=Request(f'https://generativelanguage.googleapis.com/v1beta/models/{p["model"]}:generateContent',data=json.dumps(payload,ensure_ascii=False).encode(),headers={'x-goog-api-key':key,'Content-Type':'application/json'},method='POST')
 try:
  for attempt in range(3):
   try:
    with urlopen(req,timeout=180) as r:result=json.load(r)
    break
   except HTTPError as ex:
    if ex.code!=429 or attempt==2:raise
    detail=ex.read().decode(errors='replace')
    if 'perday' in detail.lower().replace('_',''):raise
    print(f'{tid}: rejected 429, waiting 45s',flush=True);time.sleep(45)
  raw=audio_bytes(result);tmp=dest.with_suffix('.tmp');tmp.write_bytes(raw);tmp.replace(dest)
  with wave.open(str(dest),'rb') as w:dur=w.getnframes()/w.getframerate()
 except HTTPError as ex:
  m['turns'][tid].update(status='http_error',http_status=ex.code);save();raise SystemExit(f'{tid}: HTTP {ex.code}; stopped')
 m['turns'][tid].update(status='complete',duration_seconds=dur,sha256=hashlib.sha256(raw).hexdigest());save();new+=1
 print(f'Saved {tid}: {dur:.2f}s',flush=True);time.sleep(7)
print(f'Complete {sum(v["status"]=="complete" for v in m["turns"].values())}/{len(p["turns"])}',flush=True)
