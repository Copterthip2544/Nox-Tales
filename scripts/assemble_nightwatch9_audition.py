import csv,json,subprocess,wave,hashlib
from pathlib import Path
out=Path('nightwatch9-auditions');plan=json.loads(Path('episodes/nightwatch9/audition/plan_v01.json').read_text());m=json.loads((out/'manifest.json').read_text());assert len(m['samples'])==7 and all(v['status']=='complete' for v in m['samples'].values())
def run(cmd):return subprocess.run(cmd,check=True,capture_output=True,text=True)
rows=[];pos=0;concat=[]
for s in plan['samples']:
 v=m['samples'][s['id']];src=out/v['file'];assert hashlib.sha256(src.read_bytes()).hexdigest()==v['sha256'];stem=src.stem
 norm=out/(stem+'_review.wav');fx='highpass=f=70,loudnorm=I=-18:TP=-2:LRA=11'
 if s['id']=='voice001':fx+=',highpass=f=230,lowpass=f=4500'
 if s['id']=='double_nat':fx+=',lowpass=f=3400'
 run(['ffmpeg','-v','error','-y','-i',str(src),'-af',fx,'-ar','24000','-ac','1','-c:a','pcm_s16le',str(norm)])
 mp3=out/(stem+'.mp3');run(['ffmpeg','-v','error','-y','-i',str(norm),'-c:a','libmp3lame','-b:a','128k',str(mp3)])
 with wave.open(str(norm),'rb') as w:dur=w.getnframes()/w.getframerate()
 rows.append({'character':v['character'],'voice':v['voice'],'file':mp3.name,'start_seconds':round(pos,3),'duration_seconds':round(dur,3),'treatment':'phone band limit' if s['id']=='voice001' else 'through-door low pass' if s['id']=='double_nat' else 'clean speech'})
 concat.append(norm);pos+=dur+.7
combo=out/'combined_review.wav'
with wave.open(str(combo),'wb') as target:
 target.setnchannels(1);target.setsampwidth(2);target.setframerate(24000)
 for i,f in enumerate(concat):
  with wave.open(str(f),'rb') as w:target.writeframes(w.readframes(w.getnframes()))
  if i<len(concat)-1:target.writeframes(b'\0\0'*16800)
run(['ffmpeg','-v','error','-y','-i',str(combo),'-c:a','libmp3lame','-b:a','128k',str(out/'Frame_Tales_Nightwatch9_Voice_Test_v01.mp3')])
combo.unlink()
with (out/'listening_order.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
(out/'listening_order.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
(out/'README.txt').write_text('Frame Tales — Nightwatch9 voice audition v01\n\nCombined MP3 order: Nox / Nat / Somchai / 001 / Cleaner / Witthaya / Nat double.\nSeparate MP3s are playback versions; original WAVs preserve the unprocessed take.\n001 MP3 is phone-filtered; Nat-double MP3 is door-filtered without changing pitch or identity.\nOnly Charon as Nox is already confirmed. Other cast samples await the user listening review.\n')
print(json.dumps({'complete_samples':7,'combined_seconds':round(pos-.7,2),'tts_requests':7,'all_raw_wav_preserved':True}),flush=True)
