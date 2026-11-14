"""Scene-scored original instrumental music; no external services or licensed tracks."""
from pathlib import Path
import json,wave,shutil
import numpy as np
from scipy.signal import butter,sosfilt
R=Path(__file__).parent;B=R/'outputs'/'v02';O=R/'outputs'/'v05';O.mkdir(parents=True,exist_ok=True)
SR=24000;p=json.loads((B/'full_edit_plan.json').read_text());duration=p['duration_seconds'];events=p['events'];E={int(e['event_id'].split('_E')[1]):e for e in events};size=round(duration*SR);rng=np.random.default_rng(41914)
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
# Individually written phrase/rhythm profiles; each phrase is played once, never looped.
# None = a deliberate rest. Slow dialogue scenes use fewer phrases and less pulse.
profiles={
 'IN':(.28,42,49,[[69,None,64,72,67,None,71],[76,74,None,69,65,68]],'invitation'),
 'SC01':(.72,58,76,[[64,67,None,63,70,66],[73,None,68,62,65,71]],'future image'),
 'SC02':(.12,39,43,[[64,67,71,None,69,62]],'ordinary first night'),
 'SC03':(.30,44,50,[[69,None,65,71,64],[72,68,None,66,73,67]],'rules and unease'),
 'SC04':(.49,51,67,[[64,71,67,None,73,68,62],[75,70,66,None,72,63]],'discovery'),
 'SC05':(.91,61,98,[[57,64,None,60,66,62],[69,65,72,67,None,63,70],[74,68,None,71,65,76]],'danger and reset'),
 'SC06':(.57,48,62,[[76,None,69,73,None,66],[71,65,None,74,68]],'someone outside'),
 'SC07':(.74,55,79,[[62,68,65,None,72,63],[70,66,None,73,67,61]],'001 deception'),
 'SC08':(.97,64,105,[], 'the double'),
 'SC09':(.79,47,72,[[67,None,74,66,71,63],[76,69,None,64,72,68]],'time distorts'),
 'SC10':(1.,72,112,[[60,66,None,63,70,65],[73,None,67,62,69,75]],'final confrontation'),
 'SC11':(.27,43,47,[[64,71,None,67,74,69],[72,None,68,65,73,66]],'false relief'),
 'SC12':(.82,46,92,[[76,71,None,67,74,69],[63,None,70,66,73,62],[75,68,64,None,71,65]],'dawn then reveal'),
 'OUT':(.26,40,44,[[69,64,None,72,67,71],[76,None,73,68,65,62]],'unresolved ending')}
qmap={k:v[0] for k,v in profiles.items()};cue=[]
chord_sets=[[45,52,60,64],[43,50,58,62],[46,53,59,65],[44,51,57,63],[47,54,60,66],[45,55,62,65]]
for j,s in enumerate(scenes):
 start=max(0,s['start']-.15);end=scenes[j+1]['start'] if j+1<len(scenes) else duration;d=end-start
 q,bpm0,bpm1,phrases,mood=profiles[s['scene']]
 # Chords change with the dramatic arc, with overlapping long envelopes.
 block=max(8.,d/4);chords=[]
 at=start;k=0
 while at<end-.2:
  dur=min(block+1.4,end-at);tt=np.arange(round(dur*SR))/SR;x=np.zeros(len(tt),np.float32)
  chord=chord_sets[(j+k)%len(chord_sets)];chords.append(chord)
  for h,m in enumerate(chord):
   f=440*2**((m-69)/12);v=.11*np.sin(2*np.pi*(.17+h*.031)*tt)
   x+=(np.sin(2*np.pi*f*tt+v)+.23*np.sin(2*np.pi*2*f*tt+v*.7)+.08*np.sin(2*np.pi*3*f*tt))*(.0043 if h else .006)
  x*=.72+.28*np.sin(np.pi*np.clip(tt/max(dur,.01),0,1))**2
  add(fade(x,.8,.9),at)
  at+=block;k+=1
 # Each authored phrase appears once at a different point in the scene.
 phrase_log=[]
 for pi,notes in enumerate(phrases):
  window=min(11.5,d/max(1,len(phrases))*.7);at=start+d*(.08+.72*pi/max(1,len(phrases)))
  ratios=np.array(([1.4,.65,1.8,.9,1.25,.6,1.65,.8] if (j+pi)%2 else [.8,1.7,.6,1.35,.9,1.9,.7,1.1])[:len(notes)])
  intervals=ratios/ratios.sum()*window
  phrase_log.append({'start':round(at,3),'notes':notes,'intervals':intervals.tolist()})
  for ni,note in enumerate(notes):
   if note is not None and at<end-.8:
    g=(.0065 if q>.8 else .010)*(1+.11*(ni%3))
    add(piano(note,min(3.4,end-at)),at,g)
    if ni in [0,len(notes)-1]:add(piano(note-12,min(2.7,end-at)),at+.06,g*.22)
   at+=float(intervals[ni])
 # Unequal pulse groupings, accelerating with events and leaving breathing space.
 pulse_log=[]
 if q>.4:
  at=start+.55;k=0;groupings=[1.,.7,1.4,.9,1.65,.55,1.2,1.8,.8]
  while at<end-.55:
   progress=np.clip((at-start)/d,0,1);bpm=bpm0+(bpm1-bpm0)*progress
   if s['scene']=='SC12' and at<E[180]['start']:at+=1.7;continue
   # Interrupt the rhythm instead of sustaining one repeated ostinato.
   if k%11 in [7,8] or (s['scene']=='SC06' and k%3!=0):
    at+=(60/bpm)*groupings[(k+j)%len(groupings)];k+=1;continue
   tt=np.arange(round(.7*SR))/SR;notes=[45,52,48,55,46,50,53,47,54,49,57]
   midi=notes[(k*3+j)%len(notes)];f=440*2**((midi-69)/12)
   strength=(.007+q*.009)*(.7+.5*progress)
   pluck=(np.sin(2*np.pi*f*tt)+.18*np.sin(2*np.pi*f*2*tt))*np.exp(-tt*(7+3*(k%3)))*strength
   add(fade(pluck.astype(np.float32),.006,.12),at)
   if k%5==0:
    th=np.sin(2*np.pi*(43*tt+13*(1-np.exp(-tt*8))))*np.exp(-tt*13)*.009*(.5+progress)
    add(fade(th.astype(np.float32),.006,.1),at)
   pulse_log.append(round(at,3));at+=(60/bpm)*groupings[(k+j)%len(groupings)];k+=1
 cue.append({'scene':s['scene'],'start':start,'end':end,'tension':q,'mood':mood,'tempo_range_bpm':[bpm0,bpm1],'chord_changes':chords,'phrases_played_once':phrase_log,'pulse_onsets':pulse_log})
# Dawn initially feels safe. Suspense returns after the phone exchange begins.
a=round(E[178]['start']*SR);b=round(E[180]['start']*SR);music[a:b]*=.42
# Speech activity is used only for measuring the balance, never for music automation.
active=np.zeros(size,np.float32)
for e in events: active[round(e['start']*SR):round(e['end']*SR)]=1
# User revision: no speech-linked attenuation or recovery of the music bus.
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
mask=active>0;vr=float(np.sqrt(np.mean(voice[mask]**2)));mr=float(np.sqrt(np.mean(music[mask]**2)));gain=vr*10**(-16/20)/max(mr,1e-9);music*=gain
assert float(np.max(np.abs(music)))<.35
mix=voice+music+fx;peak=float(np.max(np.abs(mix)));mix*=min(1,.95/max(peak,.001))
def write(f,x):
 with wave.open(str(f),'wb') as w:w.setparams((1,2,SR,0,'NONE','not compressed'));w.writeframes((np.clip(x,-.98,.98)*32767).astype('<i2').tobytes())
write(O/'music_stem.wav',music);write(O/'film_mix.wav',mix)
for name in ['speech_stem.wav','sfx_stem.wav','full_edit_plan.json','Frame_Tales_Nightwatch9_th.srt','shot_list.csv']:shutil.copyfile(B/name,O/name)
report=json.loads((B/'sound_report.json').read_text());report.update(revision='v05_scene_varied_original_tone',music_source='Original local synthesized score in the previous tonal style; individually authored phrases, changing chords and unequal accelerating pulse groups; no external API calls',additional_score='Through-composed phrases played once per scene, scene-specific tempo arcs, changing harmony, interrupted pulses, fixed background gain independent of dialogue, and existing practical cue silences',music_below_dialogue_db=16,dialogue_ducking=False,music_bus_gain_mode="fixed; no speech-triggered gain changes",music_cues=cue,music_dip_windows=windows,additional_score_gain_applied=gain,previous_sparse_score_replaced=True,picture_timing_changed=False)
report.pop('music_bed_gain_db_vs_v01',None)
(O/'sound_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'duration':duration,'scene_cues':len(cue),'music_below_dialogue_db':16,'phone_ring_preserved':report['final_mobile_ring'],'peak_before_mastering':peak}),flush=True)
