"""Revised opening: literal action coverage and supersampled, single-axis motion."""
import argparse, csv, hashlib, json, math, subprocess, wave
from pathlib import Path

SHOTS = [
    (0, 3.3, 'A01_NOX_host.png', 'zoom_in', 'โรงแรมส่วนใหญ่'),
    (3.3, 8.4, 'L02_landing_master.png', 'pan_right', 'แขกบางคนจะออกไปได้'),
    (8.4, 11.4, 'A01_NOX_host.png', 'pan_left', 'ผมชื่อน็อกซ์'),
    (11.4, 21.8, 'A02_key13_insert.png', 'zoom_in', 'กุญแจห้องสิบสาม'),
    (21.8, 27.6, 'A03_Maysa_arrival.png', 'zoom_in', 'เมษาเห็นโรงแรมครั้งแรก'),
    (27.6, 32.2, 'L03_exterior_master.png', 'pan_right', 'อาคารเก่าหลังแนวต้นสน'),
    (32.2, 35.3, 'A07_Maysa_steps.png', 'zoom_in', 'โคมไฟเหนือทางเข้า'),
    (35.3, 39.1, 'A04_Maysa_phone_v03.png', 'zoom_in', 'เธอก้มตรวจที่อยู่ในโทรศัพท์'),
    (39.1, 41.8, 'A05_phone_map.png', 'zoom_in', 'ตรงกัน'),
    (41.8, 47.4, 'A06_Maysa_hope.png', 'zoom_in', 'เงื่อนไขงานกับเงินที่เหลือ'),
    (47.4, 53.6, 'A07_Maysa_steps.png', 'pan_left', 'ตัดสินใจเดินเข้าไป'),
    (53.6, 56.7, 'A08_lobby_entry.png', 'pan_right', 'ในล็อบบี้'),
    (56.7, None, 'A09_manager_waiting.png', 'zoom_in', 'ชายในสูทสีเลือดหมูยืนรออยู่'),
]

def run(cmd):
    subprocess.run(cmd, check=True)

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--assets',type=Path,default=Path('episodes/hotel13/v1.3/production/masters'))
    p.add_argument('--audio',type=Path,default=Path('production-output'))
    p.add_argument('--out',type=Path,default=Path('opening-output-v03'))
    p.add_argument('--visual-qa',type=Path,default=Path('episodes/hotel13/v1.3/production/visual_QA_opening_v03.json'))
    args=p.parse_args(); args.out.mkdir(parents=True,exist_ok=True)
    # Only the exact still files actually inspected may enter this edit.
    qa=json.loads(args.visual_qa.read_text())
    for name in set(s[2] for s in SHOTS):
        review=qa['assets'].get(name)
        if not review or review['status']!='reviewed_for_edit':
            raise ValueError(f'Image has no visual review: {name}')
        actual=hashlib.sha256((args.assets/name).read_bytes()).hexdigest()
        if actual!=review['sha256']:
            raise ValueError(f'Image changed after visual review: {name}')
    audio=args.audio/'turns/E001_nox.wav'
    with wave.open(str(audio),'rb') as w: duration=w.getnframes()/w.getframerate()
    fps=30; total=math.ceil(duration*fps); clips=[]; timeline=[]
    for i,(start,end,name,motion,cue) in enumerate(SHOTS):
        first=round(start*fps); last=round(end*fps) if end else total
        frames=last-first; assert frames>1
        source=args.assets/name; assert source.exists(),source
        u=f'on/{frames-1}'
        if motion=='zoom_in':
            z=f'1.01+0.025*({u})'; x='(iw-iw/zoom)/2'; y='(ih-ih/zoom)/2'
        else:
            z='1.045'; x=f'(iw-iw/zoom)*({u})'
            if motion=='pan_left': x=f'(iw-iw/zoom)*(1-({u}))'
            y='(ih-ih/zoom)/2'
        # Scale only the still, before zoompan. Integer crop quantization is
        # <=0.27 output pixels rather than 1+ pixel in the rejected v01.
        vf=("scale=7680:4320:force_original_aspect_ratio=increase:flags=lanczos,"
            "crop=7680:4320,format=yuv444p,"
            f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s=1920x1080:fps={fps},"
            "setsar=1,format=yuv420p")
        if i==0: vf+=',fade=t=in:st=0:d=0.4'
        clip=args.out/f'shot_{i+1:02}.mp4';clips.append(clip)
        run(['ffmpeg','-hide_banner','-loglevel','error','-y','-threads','2',
             '-i',str(source),'-vf',vf,'-frames:v',str(frames),'-an',
             '-filter_threads','1','-c:v','libx264','-threads','2',
             '-preset','fast','-crf','19','-pix_fmt','yuv420p',str(clip)])
        timeline.append(dict(shot=f'SC01_SH{i+1:02}',start=first/fps,
                            end=last/fps,asset=name,motion=motion,cue=cue,frames=frames))
        print(f'Rendered {i+1}/{len(SHOTS)} {name}',flush=True)
    concat=args.out/'concat.txt'
    concat.write_text(''.join("file '"+str(c.resolve())+"'\n" for c in clips))
    dest=args.out/'Frame_Tales_Hotel13_Opening_Assembly_v03.mp4'
    run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','concat','-safe','0',
         '-i',str(concat),'-i',str(audio),'-map','0:v','-map','1:a',
         '-t',str(duration),'-c:v','copy','-af','loudnorm=I=-16:TP=-1:LRA=11',
         '-ar','48000','-c:a','aac','-b:a','192k','-movflags','+faststart',str(dest)])
    report=dict(version='v03',stage='opening_assembly_not_final_film',duration_seconds=duration,
                resolution=[1920,1080],fps=fps,source_voice_turn='E001_nox.wav',
                visual_review_manifest=args.visual_qa.name,voice_regenerated=False,unique_images=len(set(s['asset'] for s in timeline)),
                alignment='Audio-estimated paragraph boundaries; editorial subparagraph timing, not word-level forced alignment',
                motion='Single-direction pan OR gentle zoom, no shake; 7680x4320 sampling canvas',
                references='All six supplied character sheets extracted locally; pre-uniform Maysa has no waistcoat/badge',
                pending=['Final sound design/music','Rest of film'],shots=timeline)
    (args.out/'opening_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    with (args.out/'shot_list.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=timeline[0].keys());writer.writeheader();writer.writerows(timeline)
    print(str(dest),flush=True)

if __name__=='__main__': main()
