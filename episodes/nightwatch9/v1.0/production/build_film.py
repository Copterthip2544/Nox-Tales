"""Measured edit/audio assembly. Source speech is immutable approved audio."""
from pathlib import Path
import json,math,wave,csv,re
import numpy as np
from scipy.signal import butter,sosfilt
R=Path(__file__).parent; A=R/'complete_speech'; O=R/'outputs';O.mkdir(exist_ok=True)
SR=24000;FPS=30
source=json.loads((A/'events_for_edit.json').read_text())['events']
# Holds are action beats, not arbitrary padding. The five-second count remains exact source audio.
BEFORE={8:1.4,16:1.5,25:1.,42:1.5,48:.45,52:.15,54:.15,57:.6,62:.6,67:1.4,75:2.6,87:.65,90:1.4,100:1.5,108:.65,114:2.6,122:.5,128:1.4,136:1.3,140:1.8,144:2.,150:1.2,152:1.2,164:2.6,180:1.4,184:.48}
ev=[];holds=[];cursor=0;prev_end=0;prev_scene=None
for e in source:
 n=int(e['event_id'].split('_E')[1]);gap=max(0,e['start_seconds']-prev_end);prev_end=e['end_seconds']
 if prev_scene and prev_scene!=e['scene']:gap=max(gap,.65)
 cursor+=gap;extra=BEFORE.get(n,0)
 if extra:holds.append({'before':e['event_id'],'n':n,'start':cursor,'end':cursor+extra});cursor+=extra
 x=dict(e);x.update(start=round(cursor,5),end=round(cursor+e['duration_seconds'],5));ev.append(x);cursor=x['end'];prev_scene=e['scene']
duration=math.ceil((cursor+3.4)*FPS)/FPS;E={int(e['event_id'].split('_E')[1]):e for e in ev}
assert abs(E[52]['end']-E[52]['start']-5)<.001
# Explicit event-to-image choices: no uniform scene subdivisions.
G={
'nox':[2,3,193,194,195], 'room_master':[4,25,38,39,49,95], 'nat_fear':[5,9,10,40,44,46,48,55,57,59,62,64,68,73,85,96,98,103,106,108,109,112,124,129,132,136,140],
'building_night':[12], 'arrival_lobby':[13,14], 'somchai_briefing':[16,17,19,20,21,22,23],
'rules_full':[27,34,37], 'door_bolt':[28,32], 'clock_hook':[29,35], 'phone_insert':[33], 'hall_six':[31], 'duty_drawer':[36,147,148,150],
'grey_future':[41], 'grey_live':[42], 'cleaner_preview':[45], 'ceiling_danger':[47], 'nat_power_button':[50], 'monitor_off':[52], 'ceiling_empty':[54], 'hall_five':[63], 'hall_after_collapse':[60],
'nat_basin':[65], 'nat_stops_at_door':[67,70], 'wet_tracks':[72],
'nat_answers001':[75,76,77,78,79,80,81,82,83,84,87,114,115,116,117,118,119,120,166,167,168,169,170,171,172,173,174,175],
'nat_hangs_up':[88], 'inspector_door':[90,92,93], 'nat_backs_chair':[100,102,105],
'clock_mismatch':[110], 'rules_missing7':[122], 'double_smile':[125,128,131,133],
'clock_0600':[135,137], 'clock_0612':[141], 'witthaya_arrives':[144,145,146],
'handover':[152], 'nat_somchai_question':[153,154,155,156,157,158,159,160,161,162], 'witthaya_passes_phone':[164,165],
'nat_outside_call':[178,180,182,185,187], 'witthaya_live_call':[181,184,186], 'nat_back_at_building':[189], 'double_pleads':[191]}
asset_for={n:k for k,ns in G.items() for n in ns}
asset_for.update({8:'door_bolt',30:'monitor_detail',177:'nat_bolt_close',29:'clock_2100',35:'clock_2100'})
for n in [76,78,80,82,84,87,114,116,118,120,167,169,171,173,175]:asset_for[n]='nat_rule6_close'
# Every spoken event must have a deliberate visual assignment.
assert not [n for n in E if n not in asset_for],[n for n in E if n not in asset_for]
cuts=[]
def put(t,a,cue='',**kw):cuts.append({'time':t,'asset':a,'cue':cue,**kw})
for n,e in E.items():put(e['start'],asset_for[n],e['event_id'])
# Narration/action-specific inserts rather than shots of someone talking for an entire paragraph.
for n,off,a in [(4,4.6,'double_at_door'),(10,2.2,'clock_hook'),(12,7.2,'arrival_lobby'),(17,2.2,'room_bathroom'),(19,2.1,'phone_insert'),(23,2.2,'duty_drawer'),(27,4.,'rules_full'),(30,0.,'monitor_detail'),(30,6.,'phone_insert'),(31,0.,'hall_six'),(36,5.,'duty_drawer'),(37,7.,'rules_full'),(39,3.2,'clock_2130'),(40,2.4,'grey_future'),(42,0.,'clock_2140'),(42,3.,'grey_live'),(45,3.,'cleaner_preview'),(46,3.,'ceiling_danger'),(49,0.,'hall_six'),(50,2.,'nat_power_button'),(54,0.,'ceiling_empty'),(57,0.,'hall_five'),(60,0.,'clock_2326'),(60,5.,'hall_after_collapse'),(63,0.,'hall_five'),(65,0.,'room_bathroom'),(65,2.4,'nat_basin'),(72,2.,'wet_tracks'),(83,2.5,'nat_rule6_close'),(88,0.,'nat_hangs_up'),(95,3.,'double_looks_up'),(98,0.,'nat_rule7_close'),(106,0.,'nat_covers_ears'),(108,0.,'door_bolt'),(110,0.,'clock_mismatch'),(122,0.,'rules_missing7'),(124,0.,'nat_stops_pen'),(125,0.,'clock_hook'),(125,5.,'double_smile'),(137,3.,'double_at_door'),(140,0.,'door_empty_after'),(141,0.,'clock_0602'),(141,2.6,'clock_0612'),(141,4.4,'door_empty_after'),(150,0.,'duty_drawer'),(153,3.2,'nat_fear'),(162,3.,'nat_fear'),(173,3.,'hall_after_collapse'),(178,0.,'building_dawn'),(178,4.,'nat_outside_call'),(184,1.7,'double_live_door'),(186,2.2,'witthaya_live_call'),(189,0.,'nat_back_at_building'),(189,4.4,'nat_walks_away')]:
 if n in E and off<E[n]['duration_seconds']:put(E[n]['start']+off,a,E[n]['event_id']+' insert')
HOLD_ASSET={8:'door_bolt',16:'sign_in',25:'door_bolt',42:'clock_2140',48:'ceiling_danger',52:'nat_power_button',54:'monitor_off',57:'hall_five',62:'hall_after_collapse',67:'nat_basin',75:'phone_insert',87:'nat_answers001',90:'door_bolt',100:'nat_backs_chair',108:'nat_covers_ears',114:'phone_insert',122:'rules_missing7',128:'door_bolt',136:'door_bolt',140:'clock_0602',144:'witthaya_arrives',150:'duty_drawer',152:'handover',164:'phone_insert',180:'nat_outside_call',184:'witthaya_live_call'}
for h in holds:put(h['start'],HOLD_ASSET[h['n']], 'action before '+h['before'])
put(E[195]['end']+.25,'door_bolt','final three knocks')
# Quantize the exact five-second black-screen counting shot to 150 frames.
count_start=round(E[52]['start']*FPS);count_end=count_start+150
framecuts={round(c['time']*FPS):c for c in cuts};framecuts[count_start]={'asset':'monitor_off','cue':'exact five-second reset'};framecuts[count_end]={'asset':'ceiling_empty','cue':'screen returns after exactly five seconds'}
framecuts[0]=framecuts.get(0,{'asset':'nox','cue':'intro'})
keys=sorted(k for k in framecuts if 0<=k<round(duration*FPS));shots=[]
for i,k in enumerate(keys):
 c=framecuts[k];end=keys[i+1] if i+1<len(keys) else round(duration*FPS)
 if shots and shots[-1]['asset']==c['asset'] and c['asset']!='monitor_off':shots[-1]['end_frame']=end;continue
 shots.append({'start_frame':k,'end_frame':end,'asset':c['asset'],'cue':c.get('cue','')})
# Long holds get purposeful reframing, count reset exempt so duration remains auditable.
expanded=[]
for s in shots:
 span=s['end_frame']-s['start_frame'];parts=math.ceil(span/(7.8*FPS)) if s['asset']!='monitor_off' else 1
 for j in range(parts):
  x=dict(s);x['start_frame']=s['start_frame']+round(span*j/parts);x['end_frame']=s['start_frame']+round(span*(j+1)/parts);x['id']=f'SH{len(expanded)+1:03}';x['motion']=['zoom_in','pan_right','pan_left'][len(expanded)%3];x['crop_variant']=j%2;expanded.append(x)
plan={'title':'กฎ 9 ข้อสำหรับเจ้าหน้าที่เฝ้ากล้องกะดึก','brand':'Frame Tales','fps':FPS,'resolution':[1920,1080],'duration_seconds':duration,'events':ev,'holds':holds,'shots':expanded,'timing_status':'MEASURED_APPROVED_AUDIO_WITH_EXPLICIT_ACTION_HOLDS','count_reset':{'start_frame':count_start,'end_frame':count_end,'duration_seconds':5},'source_audio_unchanged':True}
(O/'full_edit_plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n')
with (O/'shot_list.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=expanded[0]);w.writeheader();w.writerows(expanded)
# Sidecar subtitles only; no mandatory burnt-in text covering visual clues.
def ts(t):
 t=round(t*1000);return f'{t//3600000:02}:{t//60000%60:02}:{t//1000%60:02},{t%1000:03}'
(O/'Frame_Tales_Nightwatch9_th.srt').write_text('\n\n'.join(f'{i+1}\n{ts(e["start"])} --> {ts(e["end"])}\n{e["text"]}' for i,e in enumerate(ev))+'\n',encoding='utf-8')
def wavread(p):
 with wave.open(str(p)) as w:
  assert w.getframerate()==SR and w.getsampwidth()==2 and w.getnchannels()==1
  return np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').astype(np.float32)/32768
size=math.ceil(duration*SR);voice=np.zeros(size,np.float32);music=np.zeros(size,np.float32);fx=np.zeros(size,np.float32);rng=np.random.default_rng(91413)
def add(bus,x,t,g=1):
 i=round(t*SR);n=min(len(x),len(bus)-i)
 if i>=0 and n>0:bus[i:i+n]+=x[:n]*g
def fade(x,d=.08):
 n=min(round(d*SR),len(x)//2);x[:n]*=np.linspace(0,1,n);x[-n:]*=np.linspace(1,0,n);return x
for e in ev:
 x=wavread(A/e['file']);speaker=e['speaker'];n=int(e['event_id'].split('_E')[1]);gain=1
 if speaker=='voice001' and n not in [90,92,93]:x=sosfilt(butter(2,[260,4200],fs=SR,btype='bandpass',output='sos'),x).astype(np.float32);gain=1.1
 if speaker in ['double_nat','cleaner'] or n in [90,92,93]:
  x=sosfilt(butter(2,[170,5300],fs=SR,btype='bandpass',output='sos'),x).astype(np.float32);gain=1.03
 add(voice,x,e['start'],gain)
# Original procedural score: sparse minor/suspended harmony with scene-dependent pace.
scenes=[]
for e in ev:
 if not scenes or scenes[-1]['scene']!=e['scene']:scenes.append({'scene':e['scene'],'start':e['start'],'end':e['end']})
 else:scenes[-1]['end']=e['end']
tension={'IN':.25,'SC01':.65,'SC02':.15,'SC03':.3,'SC04':.4,'SC05':.9,'SC06':.65,'SC07':.75,'SC08':1,'SC09':.75,'SC10':1,'SC11':.35,'SC12':.8,'OUT':.25}
for i,s in enumerate(scenes):
 start=max(0,s['start']-.3);end=(scenes[i+1]['start'] if i+1<len(scenes) else duration);t=np.arange(round((end-start)*SR))/SR;q=tension[s['scene']]
 chord=[55,65.406,82.407] if i%3 else [55,73.416,87.307]
 x=np.zeros(len(t),np.float32)
 for j,f in enumerate(chord):
  x+=(np.sin(2*np.pi*f*t+.06*np.sin(2*np.pi*.12*t))+ .25*np.sin(2*np.pi*2*f*t)+.12*np.sin(2*np.pi*4*f*t))*.006/(1+j*.4)
 x*=.65+.35*np.sin(2*np.pi*.08*t)**2
 if q>.3:
  beat=1.5-q*.65;u=np.mod(t,beat);x+=np.sin(2*np.pi*110*t)*np.exp(-u*9)*(.004+q*.008)
 if q>.7:x+=np.sin(2*np.pi*233.08*t)*(.0018+.0015*np.sin(2*np.pi*.2*t))
 add(music,fade(x,1),start)
# Duck music to leave narration/dialogue foreground; preserve near-silence after rule breach.
for e in ev:
 i=int(e['start']*SR);j=int(e['end']*SR);music[i:j]*=.62
music[int(E[106]['end']*SR):int(E[108]['start']*SR)]*=.05
music*=2.0
# Generated practical SFX, kept below voices.
def knock(strong=False):
 t=np.arange(round(.18*SR))/SR;x=(rng.standard_normal(len(t))*.25+np.sin(2*np.pi*155*t)+.3*np.sin(2*np.pi*340*t))*np.exp(-t*32);return fade(x.astype(np.float32),.002)*(.13 if strong else .08)
def ring():
 t=np.arange(round(.65*SR))/SR;x=(np.sin(2*np.pi*1050*t)+.4*np.sin(2*np.pi*1600*t))*(.4+.6*np.sin(2*np.pi*23*t)**2);return fade(x.astype(np.float32),.02)*.055
for n in [8,90,100,128,136,144]:
 h=next(h for h in holds if h['n']==n)
 for k in range(3):add(fx,knock(),h['start']+.08+k*.37)
for n in [67]:
 h=next(h for h in holds if h['n']==n)
 for k in range(2):add(fx,knock(),h['start']+.1+k*.42)
for n in [75,114,164]:
 h=next(h for h in holds if h['n']==n)
 for k in range(2):add(fx,ring(),h['start']+.05+k*1.2)
for t0 in [E[52]['start']-.07,E[52]['end']+.01]:add(fx,knock()[:1200],t0,.3)
for n in [48,62]:
 h=next(h for h in holds if h['n']==n);t=np.arange(SR)/SR;x=sosfilt(butter(2,1800,fs=SR,output='sos'),rng.standard_normal(SR)).astype(np.float32)*np.exp(-t*5)*.11;add(fx,x,h['start'])
for k in range(3):add(fx,knock(),E[195]['end']+.5+k*.5,.65)
# Rain/room air at restrained level, with daylight scenes quieter.
noise=rng.standard_normal(size).astype(np.float32);air=sosfilt(butter(2,[450,3500],fs=SR,btype='bandpass',output='sos'),noise).astype(np.float32)*.0015
fx+=air
# Water at internal wash basin, short and subtle.
t=np.arange(round(E[65]['duration_seconds']*SR))/SR;water=sosfilt(butter(2,[800,6500],fs=SR,btype='bandpass',output='sos'),rng.standard_normal(len(t))).astype(np.float32)*.014;add(fx,fade(water,.25),E[65]['start'])
def write(p,x):
 with wave.open(str(p),'wb') as w:w.setparams((1,2,SR,0,'NONE','not compressed'));w.writeframes((np.clip(x,-.98,.98)*32767).astype('<i2').tobytes())
write(O/'speech_stem.wav',voice*min(1,.95/max(float(np.max(np.abs(voice))),.001)));write(O/'music_stem.wav',music);write(O/'sfx_stem.wav',fx);mix=voice+music+fx;mix*=min(1,.95/max(float(np.max(np.abs(mix))),.001));write(O/'film_mix.wav',mix)
report={'duration_seconds':duration,'speech_events':len(ev),'shots':len(expanded),'unique_asset_keys':len(set(s['asset'] for s in expanded)),'reset_exactly_five_seconds':True,'source_audio_regenerated':False,'music_source':'Original procedural sparse harmonic score synthesized locally; no third-party tracks.','sfx_source':'Original locally synthesized practical sounds','mix_peak_before_mastering':float(np.max(np.abs(mix))),'output_loudness_target':'-16 LUFS, -1.5 dBTP in final two-pass master','listening_review':'Final mix still requires listening review'}
(O/'sound_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False))
