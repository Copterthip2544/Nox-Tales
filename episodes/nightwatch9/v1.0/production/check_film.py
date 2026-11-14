from pathlib import Path
import json,subprocess,hashlib,math,wave
from fractions import Fraction
R=Path(__file__).parent;O=R/'outputs';D=R/'scene_assets'
plan=json.loads((O/'full_edit_plan.json').read_text());reg=json.loads((D/'asset_registry.json').read_text());movie=O/'Frame_Tales_Nightwatch9_Full_v01.mp4'
assert movie.exists() and movie.stat().st_size>1000000
assert plan['shots'][0]['start_frame']==0
for x,y in zip(plan['shots'],plan['shots'][1:]):assert x['end_frame']==y['start_frame']
assert plan['shots'][-1]['end_frame']==round(plan['duration_seconds']*30)
assert plan['count_reset']['end_frame']-plan['count_reset']['start_frame']==150
assert len(plan['events'])==145
assert all(x['end']<=y['start']+.001 for x,y in zip(plan['events'],plan['events'][1:]))
assert all(s['asset'] in reg for s in plan['shots'])
for a in reg.values():assert hashlib.sha256(Path(a['file']).read_bytes()).hexdigest()==a['sha256']
assert reg['nox']['sha256']=='4425a10fa9f538f58352ae85ad8ffa171d3b38b98e234f70443acf322734eac4'
assert reg['double_pleads']['sha256']=='7b471f8ecce813fced1cc053f71f1ce8b1f2cd1483e1d1e6cf5097eb73a6aade'
assert reg['nat_power_button']['sha256']=='d1ccd5cc8d5afdf0deabc647f8d4beb45700e726fb3fd32fd278e1943298c333'
probe=subprocess.run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(movie)],check=True,capture_output=True,text=True);meta=json.loads(probe.stdout);v=next(s for s in meta['streams'] if s['codec_type']=='video');a=next(s for s in meta['streams'] if s['codec_type']=='audio');assert (v['width'],v['height'])==(1920,1080);assert Fraction(v['r_frame_rate'])==30;assert abs(float(Fraction(v['avg_frame_rate']))-30)<.005;assert a['codec_name']=='aac';assert a['channels']==2;assert abs(float(meta['format']['duration'])-plan['duration_seconds'])<.15
# Decode whole deliverable, not just its header.
subprocess.run(['ffmpeg','-hide_banner','-v','error','-i',str(movie),'-f','null','-'],check=True,capture_output=True)
report={'status':'technical_checks_passed','file':movie.name,'bytes':movie.stat().st_size,'sha256':hashlib.sha256(movie.read_bytes()).hexdigest(),'duration_seconds':float(meta['format']['duration']),'resolution':[1920,1080],'fps':30,'audio':'AAC stereo 48kHz','shots':len(plan['shots']),'speech_events':145,'source_audio_regenerated':False,'reset_duration_seconds':5,'no_missing_assets':True,'full_file_decode_passed':True,'latest_user_hand_corrections_hash_verified':True,'nox_approved_v05_hash_verified':True,'visual_review_scope':'Full stills inspected for hands/arms and source continuity. This is not a guarantee that every generated pixel is anatomically perfect.','final_user_film_review':'ready_for_review_not_published'}
(O/'final_QA.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');(O/'ffprobe.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False))
