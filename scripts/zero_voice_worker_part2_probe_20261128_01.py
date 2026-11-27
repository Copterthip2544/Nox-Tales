"""Single-actor serial TTS with encrypted request/results and per-cue audio QA."""
import os,json,sys,time,re,io,wave,base64,hashlib,secrets,zipfile,subprocess,difflib,unicodedata
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from cryptography.hazmat.primitives import serialization,hashes
from cryptography.hazmat.primitives.asymmetric import rsa,padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
R=Path('private-work');R.mkdir(mode=0o700,exist_ok=True)
OAEP=padding.OAEP(mgf=padding.MGF1(hashes.SHA256()),algorithm=hashes.SHA256(),label=None)
CAST={'NOX':'Charon','ETHAN':'Orus','MAYA':'Kore','ARTHUR':'Algenib','CLAIRE':'Achernar','GABRIEL':'Algieba','MICHAEL':'Iapetus','MARGARET':'Gacrux','DELIVERY':'Rasalgethi','MARCUS':'Fenrir','COLLEAGUE':'Rasalgethi'}
def write(p,obj):
 p.write_text(json.dumps(obj,ensure_ascii=False,indent=2))
def args():return json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())['inputs']
def setup():
 key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
 p=R/'request_private.pem';p.write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()));p.chmod(0o600)
 Path('request_public.pem').write_bytes(key.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo))
def receive():
 a=args();rid=a['request_id'];assert re.fullmatch('[a-f0-9]{24}',rid)
 url='https://api.github.com/repos/'+os.environ['GITHUB_REPOSITORY']+'/contents/.voice_requests/'+rid+'.json?ref=main'
 incoming=None
 for _ in range(150):
  try:
   req=Request(url,headers={'Authorization':'Bearer '+os.environ['REPO_READ_TOKEN'],'Accept':'application/vnd.github+json','Cache-Control':'no-cache'})
   with urlopen(req,timeout=30) as response:meta=json.load(response)
   if meta.get('encoding')=='base64' and meta.get('content'):
    incoming=json.loads(base64.b64decode(meta['content']))
   else:
    rawreq=Request(url,headers={'Authorization':'Bearer '+os.environ['REPO_READ_TOKEN'],'Accept':'application/vnd.github.raw+json','Cache-Control':'no-cache'})
    with urlopen(rawreq,timeout=30) as rawresp:incoming=json.load(rawresp)
   break
  except HTTPError as e:
   if e.code!=404:raise RuntimeError('Encrypted request retrieval HTTP '+str(e.code)) from None
  time.sleep(4)
 if incoming is None:raise RuntimeError('No encrypted request received')
 private=serialization.load_pem_private_key((R/'request_private.pem').read_bytes(),password=None)
 key=private.decrypt(base64.b64decode(incoming['wrapped_key']),OAEP)
 p=json.loads(AESGCM(key).decrypt(base64.b64decode(incoming['nonce']),base64.b64decode(incoming['ciphertext']),rid.encode()))
 assert p['model']=='gemini-3.8-flash-tts' and p['part']==2 and p['cue_count']==219
 assert p['source_sha256']=='b9380f6aadd3626276f232327dd87be9331fec9a289469ab325840bc483db49f'
 assert {a['actor']:a['voice'] for a in p['actors']}=={'NOX':'Charon','ETHAN':'Orus','MAYA':'Kore','ARTHUR':'Algenib','CLAIRE':'Achernar','GABRIEL':'Algieba','MARCUS':'Fenrir','COLLEAGUE':'Rasalgethi'}
 assert len(p['actors'])==8 and sum(len(a['cues']) for a in p['actors'])==219
 for actor in p['actors']:
  assert 1<=len(actor['cues'])<=120
  assert all(c['actor']==actor['actor'] and c['cue_id'].startswith('P2_') and 0<len(c['text'])<=600 for c in actor['cues'])
 write(R/'plan.json',p)
 for previous in p.get('verified_complete_actors',[]):
  assert previous['status']=='passed' and previous['source_sha256']==p['source_sha256']
  assert previous['voice']==CAST[previous['actor']]
  expected=next(a for a in p['actors'] if a['actor']==previous['actor'])
  assert previous['cues']==len(expected['cues'])
  folder=R/previous['actor'];folder.mkdir(exist_ok=True)
  write(folder/'QA.json',{**previous,'actor_total_complete':len(expected['cues'])})
 print('Approved Part 2 only; 219 locked turns; eight audition voices; one actor at a time; Part 1 untouched.',flush=True)
def actor(index):
 p=json.loads((R/'plan.json').read_text());a=p['actors'][index];out=R/a['actor'];out.mkdir(exist_ok=True)
 a=dict(a);a['cues']=[c for c in a['cues'] if c['cue_id'] not in set(p.get('completed_cue_ids',[]))]
 a['cues']=a['cues'][:p.get('max_new_cues_this_run',len(a['cues']))]
 return p,a,out
def synth(index):
 p,a,out=actor(index)
 if p.get('not_before_utc'):
  from datetime import datetime,timezone
  target=datetime.fromisoformat(p['not_before_utc'])
  while (target-datetime.now(timezone.utc)).total_seconds()>0:
   time.sleep(max(0,min(30,(target-datetime.now(timezone.utc)).total_seconds())))
 if index:
  prev=p['actors'][index-1]['actor']
  prior=json.loads((R/prev/'QA.json').read_text())
  assert prior['status']=='passed' and prior.get('actor_total_complete',prior['cues'])==len(p['actors'][index-1]['cues']), 'Previous actor is not fully completed and checked'
 mf=out/'Manifest.json';m={'actor':a['actor'],'label':a['label'],'voice':a['voice'],'model':p['model'],'source_sha256':p['source_sha256'],'status':'generating','cues':[]};write(mf,m)
 try:
  for c in a['cues']:
   t=time.monotonic();record={**c,'voice':a['voice'],'status':'request_started'};m['cues'].append(record);write(mf,m)
   payload={'contents':[{'role':'user','parts':[{'text':c['text'],'speech_metadata':{'style':c['style']}}]}],'generationConfig':{'responseModalities':['AUDIO'],'speechConfig':{'voiceConfig':{'voice':a['voice']}}}}
   req=Request('https://generativelanguage.googleapis.com/v1beta/models/'+p['model']+':generateContent',data=json.dumps(payload,ensure_ascii=False).encode(),headers={'x-goog-api-key':os.environ['GEMINI_API_KEY'],'Content-Type':'application/json'},method='POST')
   if c.get('recovered_raw_flac'):
    recovered=out/(c['cue_id']+'.recovered.flac');recovered.write_bytes(base64.b64decode(c['recovered_raw_flac']))
    raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(recovered),'-c:a','pcm_s16le','-f','wav','-'])
    # Rewrite RIFF length from seekable file rather than streaming WAV header.
    recovered_wav=out/(c['cue_id']+'.recovered.wav')
    subprocess.run(['ffmpeg','-v','error','-y','-i',str(recovered),'-c:a','pcm_s16le',str(recovered_wav)],check=True)
    raw=recovered_wav.read_bytes();recovered.unlink();recovered_wav.unlink();record.pop('recovered_raw_flac',None)
   else:
    with urlopen(req,timeout=240) as response:result=json.load(response)
    cs=result.get('candidates',[])
    assert len(cs)==1 and cs[0].get('finishReason')=='STOP','Incomplete generation'
    data=[x['inlineData'] for x in cs[0].get('content',{}).get('parts',[]) if 'inlineData' in x]
    assert len(data)==1,'Expected single audio payload'
    raw=base64.b64decode(data[0]['data'],validate=True)
   assert raw[:4]==b'RIFF' and raw[8:12]==b'WAVE','Unexpected audio format'
   with wave.open(io.BytesIO(raw)) as w:
    duration=w.getnframes()/w.getframerate();rate=w.getframerate();channels=w.getnchannels();width=w.getsampwidth();frames=w.readframes(w.getnframes())
    assert len(frames)==w.getnframes()*channels*width and .12<duration<150
   rawfile=out/(c['cue_id']+'.raw.wav');rawfile.write_bytes(raw)
   file=out/(c['cue_id']+'.wav')
   # Two-pass loudness matching keeps each original performance and speaking speed.
   measure=subprocess.run(['ffmpeg','-hide_banner','-i',str(rawfile),'-af','loudnorm=I=-19.2:TP=-4.5:LRA=7:print_format=json','-f','null','-'],capture_output=True,text=True,check=True)
   measure=json.JSONDecoder().raw_decode(measure.stderr[measure.stderr.rfind('{'):])[0]
   filt='loudnorm=I=-19.2:TP=-4.5:LRA=7:measured_I='+measure['input_i']+':measured_TP='+measure['input_tp']+':measured_LRA='+measure['input_lra']+':measured_thresh='+measure['input_thresh']+':offset='+measure['target_offset']+':linear=true'
   if measure['input_i']=='-inf':raise ValueError('Silent audio')
   subprocess.run(['ffmpeg','-v','error','-y','-i',str(rawfile),'-af',filt,'-ar',str(rate),'-ac',str(channels),'-c:a','pcm_s16le',str(file)],check=True)
   subprocess.run(['ffmpeg','-v','error','-y','-i',str(rawfile),'-c:a','flac',str(out/(c['cue_id']+'.raw.flac'))],check=True);rawfile.unlink()
   record.update(status='complete',file=file.name,duration_seconds=duration,sample_rate=rate,channels=channels,sha256=hashlib.sha256(file.read_bytes()).hexdigest(),original_audio_measurement=measure)
   write(mf,m);print(a['actor']+' '+c['cue_id']+' complete '+str(round(duration,2))+'s',flush=True)
   time.sleep(max(0,15-(time.monotonic()-t)))
  m['status']='generated_waiting_QA';write(mf,m)
 except Exception as e:
  detail=e.read(12000).decode(errors='replace') if isinstance(e,HTTPError) else str(e)
  m.update(status='stopped_without_retry',error_type=type(e).__name__,http_status=getattr(e,'code',None),provider_detail=detail);write(mf,m)
  print(a['actor']+' stopped without retry: '+type(e).__name__+' '+str(getattr(e,'code','')),flush=True)
  raise RuntimeError('Stopped; existing cues preserved') from None
def norm(t):return ''.join(c for c in unicodedata.normalize('NFC',t) if c.isalnum() or '\u0e00'<=c<='\u0e7f')
def check(index,partial=False):
 p,a,out=actor(index)
 if not (out/'Manifest.json').exists():return
 m=json.loads((out/'Manifest.json').read_text());records=[c for c in m['cues'] if c['status']=='complete']
 if not records:return
 from faster_whisper import WhisperModel
 import numpy as np
 assert partial or (len(records)==len(a['cues']) and all(c['status']=='complete' for c in records))
 model=WhisperModel('small',device='cpu',compute_type='int8',cpu_threads=4,download_root=os.environ.get('ZERO_WHISPER_MODEL_ROOT'))
 reports=[];critical=[]
 for c in records:
  f=out/c['file'];assert hashlib.sha256(f.read_bytes()).hexdigest()==c['sha256']
  subprocess.run(['ffmpeg','-v','error','-i',str(f),'-f','null','-'],check=True)
  audio=np.frombuffer(subprocess.check_output(['ffmpeg','-v','error','-i',str(f),'-ac','1','-ar','16000','-f','f32le','-']),dtype='<f4')
  segments,_=model.transcribe(audio,language='th',beam_size=3,temperature=0,condition_on_previous_text=False)
  segments=[{'text':s.text,'start':s.start,'end':s.end} for s in segments]
  heard=' '.join(s['text'] for s in segments);sim=difflib.SequenceMatcher(None,norm(c['text']),norm(heard),autojunk=False).ratio()
  flag=sim<.72
  if not heard.strip() or (len(norm(c['text']))>40 and sim<.35):critical.append(c['cue_id'])
  reports.append({'cue_id':c['cue_id'],'text':c['text'],'heard':heard,'similarity':sim,'segments':segments,'review_flag':flag})
  write(out/'Transcript_Checks.json',reports)
  print(a['actor']+' '+c['cue_id']+' ASR '+str(round(sim,3))+(' FLAG' if flag else ''),flush=True)
 qa={'status':'passed' if not critical else 'needs_review','actor':a['actor'],'voice':a['voice'],'cues':len(records),'actor_total_complete':sum(c['cue_id'] in set(p.get('completed_cue_ids',[])) for c in p['actors'][index]['cues'])+len(records),'expected_actor_total':len(p['actors'][index]['cues']),'critical':critical,'review_flags':[r['cue_id'] for r in reports if r['review_flag']],'checks':{'single_approved_voice':True,'one_speaker_per_request':True,'source_exact_text_sent':True,'full_decode_passed':True,'independent_transcript_check':True,'source_hash_locked':p['source_sha256']},'note':'ASR similarity flags require review; automated checks do not prove emotional performance or perceived speaker identity.'}
 write(out/'QA.json',qa)
 (out/'บทเทียบเสียง.txt').write_text('\n\n'.join(c['cue_id']+' | '+c['speaker']+' | '+a['voice']+'\n'+c['text'] for c in records))
 if critical:raise RuntimeError('Critical transcript check; paused before next actor')
 m['status']='complete_checked' if qa['actor_total_complete']==qa['expected_actor_total'] else 'partial_checked';write(out/'Manifest.json',m)
def package(index):
 p,a,out=actor(index);arg=args();rid=arg['request_id']
 if not any(out.iterdir()):return
 public=serialization.load_pem_public_key(base64.b64decode(arg['delivery_public_key']))
 stream=io.BytesIO()
 with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as z:
  for f in sorted(out.iterdir()):
   if f.is_file():z.writestr(f.name,f.read_bytes())
 key=secrets.token_bytes(32);nonce=secrets.token_bytes(12)
 env={'request_id':rid,'actor':a['actor'],'zip_sha256':hashlib.sha256(stream.getvalue()).hexdigest(),'wrapped_key':base64.b64encode(public.encrypt(key,OAEP)).decode(),'nonce':base64.b64encode(nonce).decode(),'ciphertext':base64.b64encode(AESGCM(key).encrypt(nonce,stream.getvalue(),rid.encode())).decode()}
 write(Path('encrypted-'+a['actor']+'.json'),env)
if __name__=='__main__':
 command=sys.argv[1]
 if command=='setup':setup()
 elif command=='receive':receive()
 elif command=='synth':synth(int(sys.argv[2]))
 elif command=='check':check(int(sys.argv[2]),partial=len(sys.argv)>3 and sys.argv[3]=='partial')
 elif command=='package':package(int(sys.argv[2]))
