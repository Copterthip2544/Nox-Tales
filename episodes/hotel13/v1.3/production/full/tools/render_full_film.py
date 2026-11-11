"""Render reviewed stills into the measured full-film edit; resumable clip cache."""
import argparse, concurrent.futures, hashlib, json, math, re, subprocess
from pathlib import Path

def run(cmd):return subprocess.run(cmd,check=True,capture_output=True,text=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--masters',type=Path,required=True)
    p.add_argument('--available-only',action='store_true');p.add_argument('--workers',type=int,default=2);args=p.parse_args()
    root=args.root;out=root/'outputs';cache=out/'clip_cache';cache.mkdir(parents=True,exist_ok=True)
    plan=json.loads((out/'full_edit_plan.json').read_text());state=json.loads((root/'production_state.json').read_text());base=json.loads((root/'base_visual_QA.json').read_text())
    if state.get('stage')=='paused_for_user_image_review' or state.get('user_approval')=='pending':
        raise RuntimeError('User requested image review before further editing/rendering. Await explicit user approval.')
    fps=plan['fps'];duration=plan['duration_seconds'];jobs={};clips=[];missing=[];reviews={}
    for index,s in enumerate(plan['shots']):
        aid=s['asset'];source=root/'assets'/(aid+'.png');review=state['assets'].get(aid)
        if not source.exists():source=args.masters/(aid+'.png');review=base.get(aid)
        if not source.exists() or not review or review['status']!='reviewed_for_edit':
            missing.append(aid);clips.append(None);continue
        digest=hashlib.sha256(source.read_bytes()).hexdigest()
        if digest!=review['sha256']:raise ValueError(f'Changed after visual review: {aid}')
        reviews[aid]={'sha256':digest,'review':review.get('visual_review',review.get('observations','reviewed'))}
        frames=s['end_frame']-s['start_frame'];assert frames>0
        overlay={'I04_Pim_key_grip_v2':'05:58','I06_Maysa_returnskey_v2':'05:59'}.get(aid)
        settings={'sha':digest,'frames':frames,'fps':fps,'motion':s['motion'],'fade_in':index==0,'fade_out':index==len(plan['shots'])-1,'overlay':overlay,'renderer':'7680-v1-crf19'}
        key=hashlib.sha256(json.dumps(settings,sort_keys=True).encode()).hexdigest()[:24]
        clip=cache/(key+'.mp4');clips.append(clip)
        if not clip.exists():jobs[key]=(source,clip,settings,aid)
    if missing and not args.available_only:raise ValueError('Missing/unreviewed: '+', '.join(sorted(set(missing))))
    def render(job):
        source,clip,c,aid=job;n=c['frames'];u=f'on/{max(n-1,1)}';motion=c['motion']
        if motion=='zoom_in':z=f'1.01+0.025*({u})';x='(iw-iw/zoom)/2'
        elif motion=='pan_left':z='1.045';x=f'(iw-iw/zoom)*(1-({u}))'
        else:z='1.045';x=f'(iw-iw/zoom)*({u})'
        vf=("scale=7680:4320:force_original_aspect_ratio=increase:flags=lanczos,crop=7680:4320,format=yuv444p,"
            f"zoompan=z='{z}':x='{x}':y='(ih-ih/zoom)/2':d={n}:s=1920x1080:fps={fps},setsar=1,format=yuv420p")
        if c['fade_in']:vf+=',fade=t=in:st=0:d=0.4'
        if c['overlay']:
            clock=c['overlay'].replace(':','\\:')
            vf+=f",drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='{clock}':x=72:y=h-110:fontsize=42:fontcolor=0xE9D1A3:box=1:boxcolor=black@0.4:boxborderw=12"
        if c['fade_out']:vf+=f',fade=t=out:st={max(0,n/fps-1.8):.5f}:d=1.8'
        temp=clip.with_suffix('.partial.mp4')
        run(['ffmpeg','-hide_banner','-loglevel','error','-y','-threads','1','-i',str(source),'-vf',vf,
             '-frames:v',str(n),'-an','-filter_threads','1','-c:v','libx264','-threads','1',
             '-preset','fast','-crf','19','-pix_fmt','yuv420p','-color_primaries','bt709','-color_trc','bt709','-colorspace','bt709',str(temp)])
        temp.replace(clip);return aid
    print(f'Ready clips {sum(c is not None and c.exists() for c in clips)}/{len(clips)}, rendering {len(jobs)}, pending assets {len(set(missing))}',flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures=[pool.submit(render,j) for j in jobs.values()]
        for i,f in enumerate(concurrent.futures.as_completed(futures),1):print(f'Rendered {i}/{len(jobs)} {f.result()}',flush=True)
    (out/'used_visual_QA.json').write_text(json.dumps(reviews,ensure_ascii=False,indent=2))
    if args.available_only:
        print('Cached available reviewed shots; full export waits for remaining assets.',flush=True);return
    assert all(c and c.exists() for c in clips)
    concat=out/'full_concat.txt';concat.write_text(''.join("file '"+str(c.resolve())+"'\n" for c in clips))
    mix=out/'film_mix.wav';assert mix.exists()
    loud=run(['ffmpeg','-hide_banner','-nostats','-i',str(mix),'-af','loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json','-f','null','-'])
    measurement=json.loads(re.findall(r'\{[^{}]+\}',loud.stderr)[-1])
    norm=('loudnorm=I=-16:TP=-1.5:LRA=11:'+f"measured_I={measurement['input_i']}:measured_TP={measurement['input_tp']}:measured_LRA={measurement['input_lra']}:measured_thresh={measurement['input_thresh']}:offset={measurement['target_offset']}:linear=true:print_format=json")
    dest=out/'Frame_Tales_Hotel13_Full_v01.mp4'
    result=run(['ffmpeg','-hide_banner','-nostats','-y','-f','concat','-safe','0','-i',str(concat),'-i',str(mix),
         '-map','0:v','-map','1:a','-t',str(duration),'-c:v','copy','-af',norm,'-ar','48000','-ac','2',
         '-c:a','aac','-b:a','256k','-movflags','+faststart','-metadata','title=โรงแรมห้อง 13 — แขกที่ห้ามเช็กเอาต์',
         '-metadata','artist=Frame Tales',str(dest)])
    norms=re.findall(r'\{[^{}]+\}',result.stderr)
    report={'file':dest.name,'duration_seconds':duration,'fps':fps,'resolution':[1920,1080],'shots':len(plan['shots']),
            'unique_reviewed_images':len(reviews),'speech_turns':len(plan['events']),'audio_loudness':json.loads(norms[-1]) if norms else measurement,
            'motion':'Single direction horizontal pan OR gentle zoom, no shake, 7680 sampling canvas',
            'tts_regenerated':False,'script_version':'1.3','brand':'Frame Tales'}
    (out/'render_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps(report,ensure_ascii=False),flush=True)

if __name__=='__main__':main()
