"""Prepare editable dialogue, exact five-second count and measured speech references."""
import array,csv,hashlib,json,math,shutil,subprocess,wave
from pathlib import Path
ROOT=Path('nightwatch9-full-speech');p=json.loads(Path('episodes/nightwatch9/v1.0/audio_plan.json').read_text());m=json.loads((ROOT/'manifest.json').read_text())
assert all(m['units'].get(u['unit_id'],{}).get('status')=='complete' for u in p['units'])
OUT=ROOT/'turns';OUT.mkdir(exist_ok=True);REV=ROOT/'by_scene';REV.mkdir(exist_ok=True)
SR=24000
def readwav(f):
 with wave.open(str(f),'rb') as w:
  assert (w.getframerate(),w.getnchannels(),w.getsampwidth())==(SR,1,2)
  return array.array('h',w.readframes(w.getnframes()))
def writewav(f,x):
 with wave.open(str(f),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(SR);w.writeframes(x.tobytes())
def trimmed(x,start_pad=.08,end_pad=.16):
 peak=max((abs(n) for n in x),default=0)
 if peak<20:raise ValueError('Silent audio')
 threshold=max(26,min(98,round(peak*.015)))
 a=next(i for i,n in enumerate(x) if abs(n)>=threshold);b=len(x)-next(i for i,n in enumerate(reversed(x)) if abs(n)>=threshold)
 return x[max(0,a-round(start_pad*SR)):min(len(x),b+round(end_pad*SR))]
for uid,v in m['units'].items():assert hashlib.sha256((ROOT/v['file']).read_bytes()).hexdigest()==v['sha256'],uid
timeline=[];cursor=0;reference=ROOT/'full_speech_reference.wav';per_scene={};counts=[]
with wave.open(str(reference),'wb') as target:
 target.setnchannels(1);target.setsampwidth(2);target.setframerate(SR)
 for e in p['events']:
  if e.get('assembly',{}).get('type')=='exact_five_second_count':
   x=array.array('h',[0])*(5*SR)
   for uid,sec in zip(e['unit_ids'],[0,1,2,3,4]):
    word=trimmed(readwav(ROOT/m['units'][uid]['file']),.02,.035)
    if len(word)>.98*SR:raise ValueError('Count numeral exceeds slot; needs a shorter natural take: '+uid)
    pos=sec*SR;x[pos:pos+len(word)]=word
   counts.append({'event_id':e['event_id'],'duration_seconds':len(x)/SR,'number_onsets_seconds':[0,1,2,3,4]})
  else:x=trimmed(readwav(ROOT/m['units'][e['unit_ids'][0]]['file']))
  dest=OUT/(e['event_id']+'_'+e['speaker']+'.wav');writewav(dest,x)
  duration=len(x)/SR;start=cursor/SR;target.writeframes(x.tobytes());cursor+=len(x)
  row={'event_id':e['event_id'],'scene':e['scene'],'speaker':e['speaker'],'voice':e['voice'],'file':str(dest.relative_to(ROOT)),'start_seconds':round(start,4),'end_seconds':round(cursor/SR,4),'duration_seconds':round(duration,4),'text':e['text'],'timing_status':'MEASURED_SPEECH_REFERENCE_NOT_FINAL_FILM'};timeline.append(row);per_scene.setdefault(e['scene'],[]).append(dest)
  gap=round(SR*(.45 if e['speaker']=='nox' else .22));target.writeframes(b'\0\0'*gap);cursor+=gap
for scene,files in per_scene.items():
 wav=REV/(scene+'.wav')
 with wave.open(str(wav),'wb') as w:
  w.setnchannels(1);w.setsampwidth(2);w.setframerate(SR)
  for f in files:w.writeframes(readwav(f).tobytes());w.writeframes(b'\0\0'*round(.25*SR))
 subprocess.run(['ffmpeg','-v','error','-y','-i',str(wav),'-af','loudnorm=I=-18:TP=-2:LRA=11','-ar','24000','-ac','1','-c:a','libmp3lame','-b:a','128k',str(REV/(scene+'.mp3'))],check=True);wav.unlink()
subprocess.run(['ffmpeg','-v','error','-y','-i',str(reference),'-af','loudnorm=I=-18:TP=-2:LRA=11','-ar','24000','-ac','1','-c:a','libmp3lame','-b:a','128k',str(ROOT/'Frame_Tales_Nightwatch9_Full_Voice_Reference_v01.mp3')],check=True)
with (ROOT/'speech_timeline.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=list(timeline[0]));w.writeheader();w.writerows(timeline)
(ROOT/'events_for_edit.json').write_text(json.dumps({'version':'audio-v1.0','events':timeline},ensure_ascii=False,indent=2))
report={'speech_events':len(timeline),'generation_units':len(p['units']),'new_requests':sum(v['source']=='new generation' for v in m['units'].values()),'reused_approved':sum(v['source']!='new generation' for v in m['units'].values()),'speech_seconds_without_reference_gaps':round(sum(t['duration_seconds'] for t in timeline),3),'reference_seconds':round(cursor/SR,3),'count_segments':counts,'all_source_hashes_verified':True,'all_voice_files_24khz_mono_pcm16':True,'listening_review':'pending user full-episode review','reference_is_final_film':False,'note':'Clean speech only. Music, SFX and physical-action holds belong to the later film edit. Duration is measured reference speech, not final video.'}
assert len(timeline)==145 and len(counts)==1 and counts[0]['duration_seconds']==5.
(ROOT/'technical_QA.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));(ROOT/'spoken_text.txt').write_text('\n\n'.join(f"{e['event_id']} | {e['speaker']}\n{e['text']}" for e in p['events']))
(ROOT/'README.txt').write_text('Frame Tales / Nightwatch9 / Full speech v01\n\nListen: Frame_Tales_Nightwatch9_Full_Voice_Reference_v01.mp3\nIndividual editable turns: turns/\nPer-scene listening files: by_scene/\nUnmodified service output: raw/\nMeasured reference timing: speech_timeline.csv\nFive-second count assembled on exact 0,1,2,3,4s onsets, no time stretching.\nThis is a clean speech reference, NOT the final film soundtrack. No music or SFX yet.\n')
print(json.dumps(report,ensure_ascii=False),flush=True)
