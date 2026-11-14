"""Render only hash-registered illustrations; resumable smooth-motion cache."""
from pathlib import Path
import json,subprocess,math,hashlib,re,concurrent.futures,argparse
from PIL import Image,ImageDraw,ImageFont
from post_graphics import decorate_prop
R=Path(__file__).parent;D=R/'scene_assets';O=R/'outputs';C=O/'clip_cache';C.mkdir(exist_ok=True)
FONT='/usr/share/fonts/truetype/noto/NotoSansThai-Regular.ttf';DIG='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
def run(x):return subprocess.run(x,check=True,capture_output=True,text=True)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--available-only',action='store_true');ap.add_argument('--workers',type=int,default=2);args=ap.parse_args()
 plan=json.loads((O/'full_edit_plan.json').read_text());reg=json.loads((D/'asset_registry.json').read_text());fps=plan['fps']
 missing=sorted(set(s['asset'] for s in plan['shots'])-set(reg));
 if missing and not args.available_only:raise RuntimeError('Missing reviewed images: '+', '.join(missing))
 for key,a in reg.items():
  if a['status']!='reviewed_for_edit':raise RuntimeError('Unreviewed '+key)
  if digest(Path(a['file']))!=a['sha256']:raise RuntimeError('Image changed after review '+key)
 # Typography belongs to post, never a prompt-generated timestamp.
 def decorated(s):
  a=s['asset'];p=Path(reg[a]['file']);meta=None
  cam6={'monitor_detail','grey_future','cleaner_preview','ceiling_danger','ceiling_empty','double_at_door','double_looks_up','double_smile','door_empty_after'}
  cam1={'hall_six','hall_five','hall_after_collapse','grey_live','wet_tracks','witthaya_arrives'}
  n=int(re.search(r'_E(\d+)',s['cue']).group(1)) if re.search(r'_E(\d+)',s['cue']) else 0
  if a in cam6:
   current='05:52'
   if n in range(27,39):current='21:00'
   if n in range(39,45):current='21:30'
   elif n in range(45,65):current='23:16'
   elif n in range(95,110):current='03:40'
   elif n in range(135,140):current='06:00'
   elif n==140:current='06:02'
   elif n>=141:current='06:12'
   h,m=map(int,current.split(':'));future=f'{(h+(m+10)//60)%24:02}:{(m+10)%60:02}:00';meta=('CAM 06',future)
   # Audience cutaways are not shots of Nat using forbidden camera6.
   if a=='double_smile' and n in [128,131,133]:meta=None
  elif a in cam1:
   t='23:16:00'
   if a in ['hall_six','grey_live']:t='21:40:00' if a=='grey_live' else '21:00:00'
   if a=='hall_after_collapse':t='23:26:00'
   if a=='wet_tracks':t='23:30:00'
   if a=='witthaya_arrives':t='06:12:00'
   meta=('CAM 01 · LIVE',t)
   if a=='hall_five' and n==63:meta=('CAM 01 · PLAYBACK','20:55:00')
   if a=='hall_after_collapse' and n>=150:meta=('CAM 01 · PLAYBACK','23:26:00')
  clock=None
  if a in ['room_bathroom','nat_stops_at_door','nat_backs_chair','nat_bolt_close','handover']:
   clock='21:00'
   if n>=39:clock='21:30'
   if n>=45:clock='23:16'
   if n>=60:clock='23:30'
   if n>=75:clock='00:10'
   if n>=95:clock='03:40'
   if n>=110:clock='05:31'
   if n>=125:clock='05:52'
   if n>=135:clock='06:00'
   if n>=140:clock='06:02'
   if n>=144:clock='06:12'
  key=hashlib.sha256((reg[a]['sha256']+str(meta)+str(clock)+str(n)+'post-v4').encode()).hexdigest()[:22];out=O/'prepared_frames'/(key+'.png');out.parent.mkdir(exist_ok=True)
  if out.exists():return out
  im=Image.open(p).convert('RGB')
  im=decorate_prop(im,a,n)
  if clock:
   d=ImageDraw.Draw(im);cx,cy=856,155;hh,mm=map(int,clock.split(':'))
   for angle,length,width in [((hh%12+mm/60)*math.pi/6,23,4),(mm*math.pi/30,35,3)]:d.line((cx,cy,cx+length*math.sin(angle),cy-length*math.cos(angle)),fill=(28,35,39),width=width)
   d.ellipse((cx-3,cy-3,cx+3,cy+3),fill=(28,35,39))
  if meta:
   im=im.resize((1920,1080),Image.Resampling.LANCZOS);dr=ImageDraw.Draw(im);dr.rectangle((0,0,1920,70),fill=(12,18,22));dr.text((50,15),meta[0],font=ImageFont.truetype(DIG,30),fill=(199,214,210));dr.text((1550,15),meta[1],font=ImageFont.truetype(DIG,30),fill=(199,214,210))
  im.save(out);return out
 clips=[];jobs={}
 for index,s in enumerate(plan['shots']):
  if s['asset'] not in reg:clips.append(None);continue
  src=decorated(s);n=s['end_frame']-s['start_frame'];settings={'source':digest(src),'frames':n,'motion':s['motion'],'crop_variant':s['crop_variant'],'fadein':index==0,'fadeout':index==len(plan['shots'])-1,'version':'nw-3840-smooth-v1'};key=hashlib.sha256(json.dumps(settings,sort_keys=True).encode()).hexdigest()[:24];clip=C/(key+'.mp4');clips.append(clip)
  if not clip.exists():jobs[key]=(src,clip,settings,s['asset'])
 def render(job):
  src,dest,v,aid=job;n=v['frames'];u=f'on/{max(n-1,1)}'
  if v['motion']=='zoom_in':z=f'1.006+0.021*({u})';x='(iw-iw/zoom)/2'
  else:z='1.027';x=f'(iw-iw/zoom)*({u})' if v['motion']=='pan_right' else f'(iw-iw/zoom)*(1-({u}))'
  vf=f"scale=7680:4320:force_original_aspect_ratio=increase:flags=lanczos,crop=7680:4320,format=yuv444p,zoompan=z='{z}':x='{x}':y='(ih-ih/zoom)/2':d={n}:s=1920x1080:fps={fps},setsar=1,format=yuv420p"
  if v['fadein']:vf+=',fade=t=in:st=0:d=0.4'
  if v['fadeout']:vf+=f',fade=t=out:st={max(0,n/fps-.8):.4f}:d=0.8'
  tmp=dest.with_suffix('.partial.mp4');run(['ffmpeg','-hide_banner','-loglevel','error','-y','-threads','1','-i',str(src),'-vf',vf,'-frames:v',str(n),'-an','-filter_threads','1','-c:v','libx264','-threads','1','-preset','fast','-crf','18','-pix_fmt','yuv420p','-color_primaries','bt709','-color_trc','bt709','-colorspace','bt709',str(tmp)]);tmp.replace(dest);return aid
 print(f'Caching {len(jobs)} shots; missing {len(missing)} assets',flush=True)
 with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
  for i,f in enumerate(concurrent.futures.as_completed([pool.submit(render,j) for j in jobs.values()]),1):print(f'{i}/{len(jobs)} {f.result()}',flush=True)
 if args.available_only:print('Available shots cached. Full export waits for remaining images.',flush=True);return
 assert all(p and p.exists() for p in clips)
 concat=O/'full_concat.txt';concat.write_text(''.join("file '"+str(p)+"'\n" for p in clips))
 measure=run(['ffmpeg','-hide_banner','-nostats','-i',str(O/'film_mix.wav'),'-af','loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json','-f','null','-']);m=json.loads(re.findall(r'\{[^{}]+\}',measure.stderr)[-1]);norm='loudnorm=I=-16:TP=-1.5:LRA=11:'+f"measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true:print_format=json"
 dest=O/'Frame_Tales_Nightwatch9_Full_v01.mp4';res=run(['ffmpeg','-hide_banner','-nostats','-y','-f','concat','-safe','0','-i',str(concat),'-i',str(O/'film_mix.wav'),'-map','0:v','-map','1:a','-t',str(plan['duration_seconds']),'-c:v','copy','-af',norm,'-ar','48000','-ac','2','-c:a','aac','-b:a','256k','-movflags','+faststart','-metadata','title='+plan['title'],'-metadata','artist=Frame Tales',str(dest)])
 norms=re.findall(r'\{[^{}]+\}',res.stderr);report={'file':str(dest),'duration_seconds':plan['duration_seconds'],'fps':fps,'resolution':[1920,1080],'shots':len(plan['shots']),'asset_keys':len(reg),'unique_source_hashes':len(set(a['sha256'] for a in reg.values())),'loudness':json.loads(norms[-1]) if norms else m,'source_speech_regenerated':False,'screen_reset_frames':plan['count_reset'],'motion':'Gentle single-axis pan or zoom; no shake'};(O/'render_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False),flush=True)
if __name__=='__main__':main()
