"""Build v02 from approved original voices, fourteen Charon patches and an original scene score."""
import argparse,csv,hashlib,importlib.util,json,math,shutil,wave
from pathlib import Path
import numpy as np
from scipy.signal import butter,sosfilt

SR=24000;FPS=30
def wavread(p):
 with wave.open(str(p),'rb') as w:
  assert w.getframerate()==SR and w.getsampwidth()==2 and w.getnchannels()==1,str(p)
  return np.frombuffer(w.readframes(w.getnframes()),'<i2').astype(np.float32)/32768
def wavwrite(p,x):
 with wave.open(str(p),'wb') as w:
  w.setnchannels(1);w.setsampwidth(2);w.setframerate(SR);w.writeframes(np.clip(x*32767,-32768,32767).astype('<i2').tobytes())
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--base-root',type=Path,required=True);ap.add_argument('--root',type=Path,required=True);ap.add_argument('--audio',type=Path,required=True);ap.add_argument('--patch',type=Path,required=True);a=ap.parse_args()
 root=a.root;out=root/'outputs';out.mkdir(parents=True,exist_ok=True);audio=root/'audio';audio.mkdir(exist_ok=True)
 spec=importlib.util.spec_from_file_location('base_edit',a.base_root/'build_full_edit.py' if (a.base_root/'build_full_edit.py').exists() else a.base_root/'tools/build_full_edit.py');base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
 rev=json.loads((root/'revision_plan.json').read_text());patches={t['id']:t for t in rev['turns']};pm=json.loads((a.patch/'manifest.json').read_text());assert len(pm['turns'])==14 and all(v['status']=='complete' for v in pm['turns'].values())
 rows=list(csv.DictReader((a.audio/'speech_timeline.csv').open(encoding='utf-8-sig')))
 parts={}
 for k,t in patches.items():
  src=a.patch/pm['turns'][k]['file'];assert hashlib.sha256(src.read_bytes()).hexdigest()==pm['turns'][k]['sha256'];x=wavread(src);rms=float(np.sqrt(np.mean(x*x)));x*=min(2.,max(.5,.085/max(rms,1e-8)));parts[k]=x;wavwrite(audio/(k+'_nox.wav'),x)
 merged=[];offset=0;newpars=[]
 for j,k in enumerate(['R125A','R125B','R125C']):
  x=parts[k];newpars.append({'index':j,'start_seconds':offset,'end_seconds':offset+len(x)/SR,'text':patches[k]['text']});merged.append(x);offset+=len(x)/SR
  if j<2:merged.append(np.zeros(round(.13*SR),np.float32));offset+=.13
 wavwrite(audio/'E125_nox.wav',np.concatenate(merged))
 for row in rows:
  if row['event_id']!='E125':shutil.copy2(a.audio/row['file'],audio/Path(row['file']).name)
 events=[];holds=[];cursor=0.;prev=0.;ringstart={}
 extra=dict(base.EXTRA);extra.update({121:.4,124:.25,125:.15,129:.25,135:.15,137:.1,140:.2,143:.15,147:5.4})
 after={38:['R039'],109:['R110'],111:['R112'],133:['R134'],135:['R136'],138:['R139'],141:['R142A','R142B','R142C'],145:['R146']}
 def addpatch(k):
  nonlocal cursor
  t=patches[k];start=cursor+.14;x=parts[k];end=start+len(x)/SR
  events.append({'event_id':k,'speaker':'nox','file':k+'_nox.wav','text':t['text'],'start':round(start,4),'end':round(end,4),'duration':len(x)/SR});cursor=end
 for row in rows:
  eid=row['event_id'];n=int(eid[1:]);gap=max(0,float(row['start_seconds'])-prev);prev=float(row['end_seconds'])
  if n==159:
   ringstart['third']=cursor+.2;addpatch('R158')
  start=cursor+gap;holdstart=start
  if n==36:ringstart['first']=start;start+=1.8
  elif n==105:ringstart['second']=start;start+=1.2
  elif n in [40,107,109,111,113,159]:start+=0
  else:start+=extra.get(n,0.)
  if start>holdstart+.05:holds.append({'before':eid,'start':holdstart,'end':start})
  f='E125_nox.wav' if n==125 else Path(row['file']).name;x=wavread(audio/f);text='\n\n'.join(patches[k]['text'] for k in ['R125A','R125B','R125C']) if n==125 else row['text']
  events.append({'event_id':eid,'speaker':row['speaker'],'file':f,'text':text,'start':round(start,4),'end':round(start+len(x)/SR,4),'duration':len(x)/SR});cursor=start+len(x)/SR
  for k in after.get(n,[]):addpatch(k)
 duration=cursor+5.5;assert 600<duration<900,duration
 ev={e['event_id']:e for e in events};hs={h['before']:h for h in holds}
 rings=[{'kind':'hotel','start':ringstart['first'],'story_count':13,'audible_numbers':[1,2,13],'audible_times':[ringstart['first'],ringstart['first']+1.6,ev['R039']['end']-.9],'answer_event':'E040'},
 {'kind':'hotel','start':ringstart['second'],'story_count':13,'audible_numbers':[1,4,6,9,12,13],'audible_times':[ringstart['second'],ev['E105']['start']-.25,ev['E107']['start']-.25,ev['E109']['start']-.25,ev['E111']['start']-.25,ev['R112']['end']-.9],'answer_event':'E113'},
 {'kind':'mobile','start':ringstart['third'],'story_count':13,'audible_numbers':[1,2,12,13],'audible_times':[ringstart['third'],ringstart['third']+1.6,ev['R158']['start']+ev['R158']['duration']*.5,ev['R158']['end']-.9],'answer_event':'E159'}]
 align=json.loads((a.base_root/'alignment/paragraph_alignment.json').read_text());align['events']['E125']['paragraphs']=newpars
 opening=json.loads((a.base_root/'opening_report_v03.json').read_text())
 original=base.make_cuts(events,holds,[],duration,align,opening);cuts={s['start_frame']:{'asset':s['asset'],'cue':s['cue'],'motion':s['motion']} for s in original}
 def cut(t,aid,cue):cuts[round(t*FPS)]={'asset':aid,'cue':cue,'motion':None}
 for e in events:
  if e['event_id'] not in patches:continue
  k=e['event_id'];images=patches[k]['assets']
  for j,aid in enumerate(images):cut(e['start']+e['duration']*j/len(images),aid,k+f' visual {j+1}')
 for r in rings:cut(r['start'],'J07_phone13' if r['kind']=='mobile' else 'A14_phone_insert','Time-elided thirteen-ring sequence')
 # Preserve first phone's child interaction; third call changes shots at the near-answer.
 cut(ev['R158']['start']+ev['R158']['duration']*.5,'J08_Maysa_home_fear_v2','hand hesitates')
 cut(ev['R158']['end']-.9,'J07_phone13','thirteenth ring then automatic answer')
 frames=sorted(cuts);shots=[]
 for i,k in enumerate(frames):
  c=cuts[k];end=frames[i+1] if i+1<len(frames) else math.ceil(duration*FPS)
  if k>=end:continue
  overlay=None
  if c['asset']=='I04_Pim_key_grip_v2' and k/FPS>=ev['R139']['start']-.1:overlay='05:58'
  if c['asset']=='I06_Maysa_returnskey_v2' and k/FPS>=ev['R142C']['start']-.1:overlay='05:59'
  if shots and shots[-1]['asset']==c['asset'] and shots[-1]['overlay']==overlay and c['motion'] is None:shots[-1]['end_frame']=end;continue
  shots.append({'id':f'SH{len(shots)+1:03}','start_frame':k,'end_frame':end,'asset':c['asset'],'cue':c['cue'],'motion':c['motion'] or ['zoom_in','pan_right','pan_left'][len(shots)%3],'overlay':overlay})
 plan={'script_version':'1.4','edit_version':'v02','duration_seconds':duration,'fps':FPS,'events':events,'holds':holds,'rings':rings,'shots':shots,'timing':'Measured approved and newly generated Charon WAVs. Phone waits elided explicitly in narration; audible rings differ from story count.'}
 (out/'full_edit_plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2))
 with (out/'shot_list.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=list(shots[0]));w.writeheader();w.writerows(shots)
 assert len(events)==122 and all(x['end']<=y['start']+.001 for x,y in zip(events,events[1:]))
 assert all(r['audible_times'][-1]+.7<=ev[r['answer_event']]['start'] for r in rings)
 # Make approved assets and old cached clips available without duplicating images locally.
 for name,target in [('assets',a.base_root/'assets'),('base_visual_QA.json',a.base_root/'base_visual_QA.json')]:
  link=root/name
  if not link.exists():link.symlink_to(target.resolve(),target.is_dir())
 state=json.loads((a.base_root/'production_state.json').read_text());state.update(stage='editing_authorized',user_approval='authorized_usable_image_selection',script='v1.4');(root/'production_state.json').write_text(json.dumps(state,ensure_ascii=False,indent=2))
 cache=out/'clip_cache';cache.mkdir(exist_ok=True)
 for f in (a.base_root/'outputs/clip_cache').glob('*.mp4'):
  dest=cache/f.name
  if not dest.exists() and '.partial' not in f.name:dest.symlink_to(f.resolve())
 mix_audio(events,holds,rings,duration,audio,out)
 print(json.dumps({'duration':duration,'shots':len(shots),'speech_turns':len(events),'music':'original scene-specific instrumental score','phone_waits':'time-elided'},ensure_ascii=False),flush=True)

def mix_audio(events,holds,rings,duration,audio,out):
 size=math.ceil(duration*SR);speech=np.zeros(size,np.float32);fx=np.zeros(size,np.float32);score=np.zeros(size,np.float32);amb=np.zeros(size,np.float32);rng=np.random.default_rng(1402)
 ev={e['event_id']:e for e in events};hs={h['before']:h for h in holds}
 def add(bus,x,start,gain=1.):
  i=round(start*SR);n=min(len(x),len(bus)-i)
  if i>=0 and n>0:bus[i:i+n]+=np.asarray(x[:n],np.float32)*gain
 for e in events:
  x=wavread(audio/e['file']);n=int(e['event_id'][1:]) if e['event_id'].startswith('E') else -1
  if n in {40,42,46,113,115,117,119,159,161,105,107,109,111}:x=sosfilt(butter(2,[230,6000],btype='bandpass',fs=SR,output='sos'),x).astype(np.float32)*1.1
  add(speech,x,e['start'])
 def ring(kind):
  t=np.arange(round(.7*SR))/SR
  x=(np.sin(2*np.pi*1050*t)+.5*np.sin(2*np.pi*1610*t)+.24*np.sin(2*np.pi*2137*t))*(.42+.58*np.maximum(np.sin(2*np.pi*23*t),0)) if kind=='hotel' else np.sin(2*np.pi*660*t)+.45*np.sin(2*np.pi*880*t)
  return x*np.minimum(t/.018,1)*np.minimum((.7-t)/.06,1)*.042
 for r in rings:
  for t in r['audible_times']:add(fx,ring(r['kind']),t)
 def impact(start,amp=.025,freq=120,seconds=.3):
  t=np.arange(round(seconds*SR))/SR;add(fx,(np.sin(2*np.pi*freq*t)+.2*rng.normal(size=len(t)))*np.exp(-t*25),start,amp)
 for eid in ['E022','E079','E098','E121','E124','E125','E149']:
  if eid in hs:impact(hs[eid]['start']+.1,.022,95)
 for r in rings:impact(ev[r['answer_event']]['start']-.1,.012,1000,.12)
 impact(ev['R142A']['end']-.4,.04,1800,.5)
 for off in [.15,.6,1.05]:impact(hs['E161']['start']+off,.028,90,.25)
 for off in [.3,.65,1.]:impact(hs['E149']['start']+off,.026,105,.25)
 bell_start=ev['R146']['end']+.2
 for k in range(6):
  t=np.arange(round(1.8*SR))/SR;add(fx,(np.sin(2*np.pi*440*t)+.5*np.sin(2*np.pi*661*t)+.28*np.sin(2*np.pi*1041*t))*np.exp(-t*2.2),bell_start+k*.8,.025)
 add(fx,ring('hotel'),duration-3.2)
 rain_end=ev['E099']['start'];n=round(rain_end*SR);noise=rng.normal(size=n).astype(np.float32);rain=sosfilt(butter(2,[450,6500],btype='bandpass',fs=SR,output='sos'),noise).astype(np.float32)*.0035;rain[-SR*2:]*=np.linspace(1,0,SR*2);amb[:n]+=rain
 for sec in np.arange(61.4,bell_start,1.):impact(sec,.0035,1800,.07)
 # Original D-minor/add-nine motif and related voicings. Each cue has its own pace,
 # density and instruments. These are locally composed synthesized instruments.
 cues=[(0,ev['E024']['start'],'mystery',54),(ev['E024']['start'],ev['E063']['start'],'unease',62),(ev['E063']['start'],ev['E079']['start'],'discovery',56),(ev['E079']['start'],ev['E099']['start'],'pressure',68),(ev['E099']['start'],ev['E105']['start'],'decision',56),(ev['E105']['start'],ev['E121']['start'],'suspense',76),(ev['E121']['start'],ev['E129']['start'],'suspense',82),(ev['E129']['start'],ev['R139']['start'],'urgent',94),(ev['R139']['start'],ev['E143']['end'],'countdown',104),(ev['E143']['end'],bell_start,'release',52),(bell_start,ev['E150']['start'],'dread',54),(ev['E150']['start'],ev['R158']['start'],'aftermath',54),(ev['R158']['start'],duration,'final_dread',64)]
 def note(freq,seconds,kind):
  t=np.arange(round(seconds*SR))/SR
  if kind=='piano':x=(np.sin(2*np.pi*freq*t)+.32*np.sin(2*np.pi*freq*2.002*t)+.1*np.sin(2*np.pi*freq*3.997*t))*np.exp(-t*1.8)
  elif kind=='pluck':x=(np.sin(2*np.pi*freq*t)+.22*np.sin(2*np.pi*freq*2*t))*np.exp(-t*5.)
  elif kind=='bass':x=np.sin(2*np.pi*freq*t)*np.exp(-t*5)
  else:x=sum(np.sin(2*np.pi*(freq*(1+.0008*v))*t+v)*(.5**abs(v)) for v in [-2,-1,0,1,2])*.35
  env=np.minimum(t/(.12 if kind=='strings' else .012),1)*np.minimum((seconds-t)/(.4 if kind=='strings' else .06),1)
  return (x*env).astype(np.float32)
 music_report=[]
 for start,end,kind,bpm in cues:
  length=end-start;bus=np.zeros(round(length*SR),np.float32);beat=60/bpm
  def put(x,sec,gain):
   i=round(sec*SR);n=min(len(x),len(bus)-i)
   if i>=0 and n>0:bus[i:i+n]+=x[:n]*gain
  tense=kind in {'pressure','suspense','urgent','countdown','final_dread'};urgent=kind in {'urgent','countdown'};warm=kind=='release'
  roots=[146.832,130.813,110.,164.814] if not warm else [174.614,146.832,130.813,110.]
  for k,sec in enumerate(np.arange(0,length,beat*8)):
   f=roots[k%4];s=min(beat*9,length-sec)
   for freq,gain in [(f/2,.16),(f,.10),(f*1.5,.06),(f*2.25,.025)]:put(note(freq,s,'strings'),sec,gain)
  motif=[293.665,440.,329.628,349.228,293.665,220.,261.626,329.628]
  spacing=beat*(.5 if urgent else 2 if tense else 4)
  for k,sec in enumerate(np.arange(.25,length,spacing)):
   f=motif[k%len(motif)];put(note(f,min(3.,max(.2,length-sec)),'pluck' if urgent else 'piano'),sec,rng.uniform(.1,.2))
  if tense:
   for k,sec in enumerate(np.arange(0,length,beat)):
    put(note(55. if k%4<2 else 73.416,.5,'bass'),sec,.14 if urgent else .085)
    if urgent:
     t=np.arange(round(.24*SR))/SR;tom=np.sin(2*np.pi*(75*t-35*t*t))*np.exp(-t*19);put(tom.astype(np.float32),sec,.12 if k%4==0 else .06)
  if kind in {'discovery','dread','final_dread'}:
   for sec in np.arange(1.,length,beat*8):put(note(587.33,3.,'piano'),sec,.035)
  fade=min(2.,length/3);f=round(fade*SR);bus[:f]*=np.linspace(0,1,f);bus[-f:]*=np.linspace(1,0,f)
  # Normalize cue RMS, keeping true peaks restrained and dialogue dominant.
  rms=float(np.sqrt(np.mean(bus*bus)));target=.040 if urgent else .028 if tense else .020
  if rms:bus*=target/rms
  if urgent:bus*=np.linspace(.75,1.15,len(bus))
  add(score,bus,start);music_report.append({'start':round(start,3),'end':round(end,3),'cue':kind,'bpm':bpm,'target_rms_dbfs':round(20*math.log10(target),1)})
 # Smooth gain automation around speech, with extra space on key dialogue lines.
 duck=np.ones(size,np.float32)
 for e in events:
  start=max(0,round((e['start']-.1)*SR));end=min(size,round((e['end']+.1)*SR));gain=.58
  if e['event_id'] in {'E137','E140','E141','E145','E159','E161'}:gain=.22
  duck[start:end]=np.minimum(duck[start:end],gain)
  attack=max(0,start-round(.12*SR));release=min(size,end+round(.45*SR))
  if start>attack:duck[attack:start]=np.minimum(duck[attack:start],np.linspace(1,gain,start-attack))
  if release>end:duck[end:release]=np.minimum(duck[end:release],np.linspace(gain,1,release-end))
 # Let the apology, final question and solitary last ring breathe.
 score*=duck;score[round((duration-4.4)*SR):]*=np.linspace(1,0,size-round((duration-4.4)*SR))
 amb*=duck;mix=speech+fx+amb+score;mix[-round(1.8*SR):]*=np.linspace(1,0,round(1.8*SR));peak=float(np.max(np.abs(mix)));mix*=min(1,.92/max(peak,1e-6))
 wavwrite(out/'film_mix.wav',mix);wavwrite(out/'music_stem.wav',score)
 (out/'sound_report.json').write_text(json.dumps({'duration_seconds':duration,'speech_clips':len(events),'new_charon_requests':14,'score_source':'Original locally composed instrumental music synthesized with piano-like, plucked, sustained string-like and bass/percussion timbres; no external music recording.','music_cues':music_report,'phone_sequences':rings,'phone_edit':'Narrated time elision, never answer before story ring13','six_strikes_start':bell_start,'final_single_ring':duration-3.2,'dialogue_ducking':True,'no_shake':True},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
