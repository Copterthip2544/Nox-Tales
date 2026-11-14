"""Scene-scored original instrumental music; no external services or licensed tracks."""
from pathlib import Path
import json,wave,shutil
import numpy as np
from scipy.signal import butter,sosfilt
R=Path(__file__).parent;B=R/'outputs'/'v02';O=R/'outputs'/'v03';O.mkdir(parents=True,exist_ok=True)
SR=24000;p=json.loads((B/'full_edit_plan.json').read_text());duration=p['duration_seconds'];events=p['events'];E={int(e['event_id'].split('_E')[1]):e for e in events};size=round(duration*SR);rng=np.random.default_rng(31914)
music=np.zeros(size,np.float32)
def read(f):
 with wave.open(str(f)) as w: assert w.getframerate()==SR;return np.frombuffer(w.readframes(w.getnframes()),'<i2').astype(np.float32)/32768
voice=read(B/'speech_stem.wav');fx=read(B/'sfx_stem.wav')
def fade(x,a=.03,z=.2):
 n=min(round(a*SR),len(x)//2);m=min(round(z*SR),len(x)//2)
 if n:x[:n]*=np.linspace(0,1,n)
 if m:x[-m:]*=np.linspace(1,0,m)
 return x

def add(x,at,g=1.):
 i=round(at*SR);n=min(len(x),size-i)
 if i>=0 and n>0: music[i:i+n]+=x[:n]*g

def piano(midi,d=3.2):
 f=440*2**((midi-69)/12);t=np.arange(round(d*SR))/SR;x=np.zeros(len(t),np.float32)
 for h,amp in [(1,1),(2,.4),(3,.2),(4,.085),(5,.035)]:
  x+=amp*np.sin(2*np.pi*f*h*(1+.00015*h*h)*t)*np.exp(-t*(1.2+h*.45))
 x*=1-np.exp(-t*140)
 return fade(x,.004,.35)
scenes=[]
for e in events:
 if not scenes or scenes[-1]['scene']!=e['scene']:scenes.append(dict(scene=e['scene'],start=e['start'],end=e['end']))
 else:scenes[-1]['end']=e['end']
qmap={'IN':.3,'SC01':.7,'SC02':.15,'SC03':.3,'SC04':.5,'SC05':.9,'SC06':.55,'SC07':.75,'SC08':1.,'SC09':.8,'SC10':1.,'SC11':.25,'SC12':.8,'OUT':.25}
cue=[]
for j,s in enumerate(scenes):
 start=max(0,s['start']-.15);end=scenes[j+1]['start'] if j+1<len(scenes) else duration;d=end-start;t=np.arange(round(d*SR))/SR;q=qmap[s['scene']];x=np.zeros(len(t),np.float32)
 # Quiet bowed minor/suspended chord with slow movement, above sub-bass frequencies.
 chord=[45,52,57,60] if j%3 else [45,52,59,62]
 for k,m in enumerate(chord):
  f=440*2**((m-69)/12);v=.0014*np.sin(2*np.pi*(.18+k*.025)*t)
  for h in range(1,5):x+=np.sin(2*np.pi*f*h*t+v*np.sin(2*np.pi*.13*t))/(h**1.7)*(.0048 if k else .007)
 x*=.78+.22*np.sin(2*np.pi*.11*t)**2
 air=sosfilt(butter(2,[220,1800],fs=SR,btype='bandpass',output='sos'),rng.standard_normal(len(t))).astype(np.float32)*.0009
 x+=air*(.3+q)
 add(fade(x,.9,1.),start)
 # Piano/soft celesta motif, deliberately sparse during rules and conversations.
 motif=[69,72,71,64] if s['scene']!='SC11' else [64,67,69,71]
 step=3.2 if q>.7 else (5.8 if s['scene']=='SC03' else 4.8)
 at=start+.7;k=0
 while at<end-1.8:
  g=.014 if q>.65 else .011
  add(piano(motif[k%4],min(3.2,end-at)),at,g)
  add(piano(motif[k%4]-12,min(2.8,end-at)),at+.075,g*.32)
  at+=step;k+=1
 if q>.4:
  # Damped low strings/percussion ostinato grows faster in confrontation scenes.
  beat=1.12 if q<.8 else .78;at=start+.45;k=0
  while at<end-.4:
   tt=np.arange(round(.65*SR))/SR;f=[110,110,130.813,103.826][k%4]
   pluck=(np.sin(2*np.pi*f*tt)+.22*np.sin(2*np.pi*f*2*tt))*np.exp(-tt*8)*(.012+q*.008)
   add(fade(pluck.astype(np.float32),.005,.12),at)
   if k%4==0:
    th=(np.sin(2*np.pi*(48*tt+16*(1-np.exp(-tt*8))))*np.exp(-tt*12)).astype(np.float32)*.012
    add(fade(th,.004,.1),at)
   at+=beat;k+=1
 cue.append({'scene':s['scene'],'start':start,'end':end,'tension':q,'instruments':['soft piano','bowed minor strings']+(['pizzicato pulse','muted low percussion'] if q>.4 else [])})
# Dawn initially feels safe. Suspense returns after the phone exchange begins.
a=round(E[178]['start']*SR);b=round(E[180]['start']*SR);music[a:b]*=.42
# Smooth dialogue ducking, avoids abrupt per-word level changes.
active=np.zeros(size,np.float32)
for e in events: active[round(e['start']*SR):round(e['end']*SR)]=1
smooth=sosfilt(butter(1,3,fs=SR,output='sos'),active).astype(np.float32);music*=1-.46*np.clip(smooth,0,1)
# Make room for practical sounds and preserve the narrative's deliberate silence.
windows=[]
for h in p['holds']:
 if h['n'] in [8,67,75,90,100,114,128,136,144,164]:windows.append((h['start']-.04,h['end']+.12,.18))
windows += [(E[106]['end'],E[108]['start'],0.),(E[180]['start']-1.65,E[180]['start']+.1,.12),(E[184]['start']-.4,E[184]['start']+.8,.1),(E[191]['end']-.25,E[191]['end']+.65,0.)]
for lo,hi,g in windows:
 i=max(0,round(lo*SR));k=min(size,round(hi*SR));n=k-i
 if n<=0:continue
 ramp=min(round(.075*SR),n//3);env=np.full(n,g,np.float32)
 if ramp:env[:ramp]=np.linspace(1,g,ramp);env[-ramp:]=np.linspace(g,1,ramp)
 music[i:k]*=env
# A clearly audible score while keeping measured speech foreground.
mask=active>0;vr=float(np.sqrt(np.mean(voice[mask]**2)));mr=float(np.sqrt(np.mean(music[mask]**2)));gain=vr*10**(-15.5/20)/max(mr,1e-9);music*=gain
assert float(np.max(np.abs(music)))<.35
mix=voice+music+fx;peak=float(np.max(np.abs(mix)));mix*=min(1,.95/max(peak,.001))
def write(f,x):
 with wave.open(str(f),'wb') as w:w.setparams((1,2,SR,0,'NONE','not compressed'));w.writeframes((np.clip(x,-.98,.98)*32767).astype('<i2').tobytes())
write(O/'music_stem.wav',music);write(O/'film_mix.wav',mix)
for name in ['speech_stem.wav','sfx_stem.wav','full_edit_plan.json','Frame_Tales_Nightwatch9_th.srt','shot_list.csv']:shutil.copyfile(B/name,O/name)
report=json.loads((B/'sound_report.json').read_text());report.update(revision='v03_scene_music',music_source='Original locally composed and synthesized piano, minor bowed strings, pizzicato pulse and muted low percussion; no external music or API calls',additional_score='Scene-specific instrumental cues with smooth dialogue ducking and silence at knocks, ringing and final reveal',music_below_dialogue_db=15.5,music_cues=cue,music_dip_windows=windows,additional_score_gain_applied=gain,previous_sparse_score_replaced=True,picture_timing_changed=False)
report.pop('music_bed_gain_db_vs_v01',None)
(O/'sound_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'duration':duration,'scene_cues':len(cue),'music_below_dialogue_db':15.5,'phone_ring_preserved':report['final_mobile_ring'],'peak_before_mastering':peak}),flush=True)
