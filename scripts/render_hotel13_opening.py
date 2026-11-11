"""Render the first approved narration turn as a motion-slideshow assembly."""
import argparse,json,math,subprocess,wave
from pathlib import Path

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--assets',type=Path,default=Path('episodes/hotel13/v1.3/production/masters'))
    parser.add_argument('--audio',type=Path,default=Path('production-output'))
    parser.add_argument('--out',type=Path,default=Path('opening-output'))
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    audio=args.audio/'turns/E001_nox.wav'
    with wave.open(str(audio),'rb') as w:duration=w.getnframes()/w.getframerate()
    assert duration>46
    segments=[('A01_NOX_host.png',8.0),('A02_key_insert.png',13.0),
              ('L03_exterior_master.png',25.0),('L01_lobby_master.png',duration-46)]
    for name,_ in segments:assert (args.assets/name).exists(),name
    filters=[];inputs=[];position=0;timeline=[]
    for index,(name,seconds) in enumerate(segments):
        inputs+=['-i',str(args.assets/name)]
        frames=math.ceil(seconds*24)
        filters.append(f"[{index}:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,zoompan=z='min(1+on*0.00015,1.05)':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d={frames}:s=1920x1080:fps=24,setsar=1,format=yuv420p[v{index}]")
        timeline.append({'asset':name,'start':position,'end':round(position+seconds,3),
                         'alignment':'editorial placement within E001, not word-level forced alignment'})
        position+=seconds
    filters.append(''.join(f'[v{i}]' for i in range(len(segments)))+f'concat=n={len(segments)}:v=1:a=0,fade=t=in:st=0:d=0.5[video]')
    dest=args.out/'Frame_Tales_Hotel13_Opening_Assembly_v01.mp4'
    subprocess.run(['ffmpeg','-v','error','-y',*inputs,'-i',str(audio),'-filter_complex',';'.join(filters),
                    '-map','[video]','-map',f'{len(segments)}:a','-t',str(duration),'-c:v','libx264',
                    '-preset','fast','-crf','20','-pix_fmt','yuv420p','-r','24',
                    '-af','loudnorm=I=-16:TP=-1:LRA=11','-ar','48000','-c:a','aac','-b:a','192k',
                    '-movflags','+faststart',str(dest)],check=True)
    report={'stage':'opening_assembly_only_not_final_film','source_voice_turn':'E001',
            'duration_seconds':duration,'resolution':[1920,1080],'fps':24,
            'source_stills_upscaled_for_export':True,'music_and_sfx':'not_yet_added',
            'human_character_shots':'awaiting_original_reference_files',
            'key_tag_number_overlay':'pending','shots':timeline}
    (args.out/'opening_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
