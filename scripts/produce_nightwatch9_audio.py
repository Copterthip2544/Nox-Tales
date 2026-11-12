"""Resumable full speech in batches of five. No ambiguous request is repeated."""
import base64,hashlib,io,json,os,time,wave
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
P=Path('episodes/nightwatch9/v1.0/audio_plan.json');OUT=Path('nightwatch9-full-speech');RAW=OUT/'raw';RAW.mkdir(parents=True,exist_ok=True)
p=json.loads(P.read_text());mf=OUT/'manifest.json';m=json.loads(mf.read_text()) if mf.exists() else {'model':p['model'],'version':p['version'],'units':{}}
def save():
 tmp=mf.with_suffix('.tmp');tmp.write_text(json.dumps(m,ensure_ascii=False,indent=2));tmp.replace(mf)
def fingerprint(u):return hashlib.sha256(json.dumps({'model':p['model'],**{k:u[k] for k in ['voice','text','style']}},sort_keys=True,ensure_ascii=False).encode()).hexdigest()
def info(raw):
 if raw[:4]!=b'RIFF' or raw[8:12]!=b'WAVE':raise ValueError('Not a WAV')
 with wave.open(io.BytesIO(raw),'rb') as w:
  if w.getsampwidth()!=2 or w.getnchannels()!=1 or w.getframerate()!=24000 or w.getnframes()==0:raise ValueError('Unexpected audio format')
  return w.getnframes()/w.getframerate()
audit=Path('approved-auditions');am=json.loads((audit/'manifest.json').read_text()) if (audit/'manifest.json').exists() else {'samples':{}}
new=0;key=os.environ['GEMINI_API_KEY']
for u in p['units']:
 uid=u['unit_id'];dest=RAW/(uid+'_'+u['speaker']+'.wav');stamp=fingerprint(u);old=m['units'].get(uid,{})
 if old.get('fingerprint')==stamp and old.get('status')=='complete' and dest.exists():
  if hashlib.sha256(dest.read_bytes()).hexdigest()!=old['sha256']:raise SystemExit('Saved audio hash mismatch: '+uid)
  continue
 if old.get('status')=='uncertain':raise SystemExit('Uncertain previous request, no automatic resubmit: '+uid)
 # Reuse a user-approved complete take only when whole text and voice match.
 match=next((v for v in am['samples'].values() if v.get('status')=='complete' and v['text']==u['text'] and v['voice']==u['voice']),None)
 if match:
  raw=(audit/match['file']).read_bytes()
  if hashlib.sha256(raw).hexdigest()!=match['sha256']:raise SystemExit('Audition hash mismatch')
  dest.write_bytes(raw);m['units'][uid]={'status':'complete','fingerprint':stamp,'file':str(dest.relative_to(OUT)),'voice':u['voice'],'text':u['text'],'duration_seconds':info(raw),'sha256':hashlib.sha256(raw).hexdigest(),'source':'approved audition 43214117186'};save();print('Reused approved '+uid,flush=True);continue
 if new>=5:break
 m['units'][uid]={'status':'uncertain','fingerprint':stamp,'voice':u['voice'],'text':u['text'],'file':str(dest.relative_to(OUT))};m.pop('blocked',None);save()
 payload={'contents':[{'role':'user','parts':[{'text':u['text'],'speech_metadata':{'style':u['style']}}]}],'generationConfig':{'responseModalities':['AUDIO'],'speechConfig':{'voiceConfig':{'voice':u['voice']}}}}
 req=Request(f'https://generativelanguage.googleapis.com/v1beta/models/{p["model"]}:generateContent',data=json.dumps(payload,ensure_ascii=False).encode(),method='POST',headers={'x-goog-api-key':key,'Content-Type':'application/json'})
 try:
  for attempt in range(4):
   try:
    with urlopen(req,timeout=180) as resp:result=json.load(resp)
    break
   except HTTPError as ex:
    if ex.code!=429:raise
    body=ex.read().decode(errors='replace');daily='perday' in body.lower().replace('_','').replace('-','')
    if daily or attempt==3:raise
    print(f'{uid}: rejected 429, waiting 45s',flush=True);time.sleep(45)
  c=result.get('candidates',[])
  if len(c)!=1 or c[0].get('finishReason')!='STOP':raise ValueError('Incomplete speech')
  parts=[x['inlineData'] for x in c[0].get('content',{}).get('parts',[]) if 'inlineData' in x]
  if len(parts)!=1:raise ValueError('Expected one audio result')
  raw=base64.b64decode(parts[0]['data'],validate=True);dur=info(raw);tmp=dest.with_suffix('.tmp');tmp.write_bytes(raw);tmp.replace(dest)
 except HTTPError as ex:
  m['units'][uid].update(status='uncertain' if ex.code>=500 else 'http_error',http_status=ex.code);m['blocked']={'unit':uid,'http_status':ex.code,'reason':'daily quota' if ex.code==429 and locals().get('daily',False) else 'HTTP rejection'};save();raise SystemExit(f'{uid}: HTTP {ex.code}; saved completed work and stopped')
 m['units'][uid].update(status='complete',duration_seconds=dur,sha256=hashlib.sha256(raw).hexdigest(),source='new generation');save();new+=1
 print(f'Saved {uid} {u["speaker"]}: {dur:.2f}s',flush=True);time.sleep(7)
complete=sum(v.get('status')=='complete' for v in m['units'].values());m['progress']={'completed':complete,'total':len(p['units']),'remaining':len(p['units'])-complete,'new_in_last_batch':new};save();print(json.dumps(m['progress']),flush=True)
