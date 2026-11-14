"""Remaster audio and stream-copy approved picture. No image or TTS regeneration."""
from pathlib import Path
import json,subprocess,re,hashlib,argparse
from fractions import Fraction
R=Path(__file__).parent;O=R/'outputs'/'v05'
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,default=R/'source_film'/'Frame_Tales_Nightwatch9_Full_v02.mp4');args=p.parse_args();src=args.source
assert src.exists()
def run(cmd):return subprocess.run(cmd,check=True,capture_output=True,text=True)
def probe(f):return json.loads(run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(f)]).stdout)
plan=json.loads((O/'full_edit_plan.json').read_text());duration=plan['duration_seconds']
res=run(['ffmpeg','-hide_banner','-nostats','-i',str(O/'film_mix.wav'),'-af','loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json','-f','null','-']);m=json.loads(re.findall(r'\{[^{}]+\}',res.stderr)[-1])
norm='loudnorm=I=-16:TP=-1.5:LRA=11:'+f"measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true:print_format=json"
dest=O/'Frame_Tales_Nightwatch9_Full_v05.mp4'
res=run(['ffmpeg','-hide_banner','-nostats','-y','-i',str(src),'-i',str(O/'film_mix.wav'),'-map','0:v:0','-map','1:a:0','-t',str(duration),'-c:v','copy','-af',norm,'-ar','48000','-ac','2','-c:a','aac','-b:a','256k','-movflags','+faststart','-metadata','title='+plan['title'],'-metadata','artist=Frame Tales',str(dest)])
loudness=json.loads(re.findall(r'\{[^{}]+\}',res.stderr)[-1]);meta=probe(dest);base=probe(src)
v=next(x for x in meta['streams'] if x['codec_type']=='video');a=next(x for x in meta['streams'] if x['codec_type']=='audio');bv=next(x for x in base['streams'] if x['codec_type']=='video')
assert (v['width'],v['height'])==(1920,1080);assert Fraction(v['r_frame_rate'])==30;assert abs(float(Fraction(v['avg_frame_rate']))-30)<.005
assert a['channels']==2 and a['codec_name']=='aac';assert abs(float(meta['format']['duration'])-duration)<.15
assert v['nb_frames']==bv['nb_frames']
def video_hash(f):return run(['ffmpeg','-hide_banner','-v','error','-i',str(f),'-map','0:v:0','-c:v','copy','-f','hash','-hash','sha256','-']).stdout.strip()
assert video_hash(src)==video_hash(dest),'Picture stream changed'
run(['ffmpeg','-hide_banner','-v','error','-i',str(dest),'-f','null','-'])
sound=json.loads((O/'sound_report.json').read_text());ring=sound['final_mobile_ring'];assert ring['end']<ring['hello_start']-.2
assert plan['count_reset']['end_frame']-plan['count_reset']['start_frame']==150
qa={'status':'technical_checks_passed','version':'v05','file':dest.name,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'bytes':dest.stat().st_size,'duration_seconds':float(meta['format']['duration']),'resolution':[1920,1080],'fps':30,'audio':'AAC stereo 48kHz','picture_stream_unchanged':True,'frames':int(v['nb_frames']),'full_file_decode_passed':True,'speech_regenerated':False,'final_phone_ring_before_answer':ring,'master_loudness':loudness,'review':'Audio balance ready for user listening review; no social publishing'}
(O/'final_QA_v05.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2)+'\n');print(json.dumps(qa,ensure_ascii=False),flush=True)
run(['ffmpeg','-hide_banner','-v','error','-y','-ss','632','-i',str(dest),'-t','22','-vn','-c:a','libmp3lame','-q:a','2',str(O/'preview_final_phone_v05.mp3')])

run(['ffmpeg','-hide_banner','-v','error','-y','-ss','255','-i',str(dest),'-t','40','-vn','-c:a','libmp3lame','-q:a','2',str(O/'preview_music_tension_v05.mp3')])

# Three short scenes illustrate calm, escalating danger and confrontation.
scenes=["SC02","SC05","SC10"];parts=[]
for idx,name in enumerate(scenes):
 s=next(x for x in sound["music_cues"] if x["scene"]==name);start=s["start"]+min(5.,(s["end"]-s["start"])*.12);end=min(start+18.,s["end"]-.1);parts.append(f"[0:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS,afade=t=in:d=0.1,afade=t=out:st={end-start-.15}:d=0.15[a{idx}]")
filters=";".join(parts)+";[a0][a1][a2]concat=n=3:v=0:a=1[out]"
run(["ffmpeg","-hide_banner","-v","error","-y","-i",str(dest),"-filter_complex",filters,"-map","[out]","-c:a","libmp3lame","-q:a","2",str(O/"preview_scene_changes_v05.mp3")])
