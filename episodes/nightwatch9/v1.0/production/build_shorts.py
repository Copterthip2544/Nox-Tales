"""Vertical promotional cuts from approved v05. Preserve the full illustrated picture."""
from pathlib import Path
import json,subprocess,hashlib,re,argparse
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).parent;D=R/'shorts';O=D/'outputs';O.mkdir(parents=True,exist_ok=True)
ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,default=R/'outputs/v05/Frame_Tales_Nightwatch9_Full_v05.mp4');args=ap.parse_args();src=args.source
FPS=30;W=1080;H=1920
font=R/'fonts/FrameTalesThai-Regular.ttf';bold=R/'fonts/FrameTalesThai-Bold.ttf'
def run(cmd):return subprocess.run(cmd,check=True,capture_output=True,text=True)
def tm(t):
 cs=round(t*100);return f'{cs//360000}:{cs//6000%60:02}:{cs//100%60:02}.{cs%100:02}'
def fontobj(size,b=False):return ImageFont.truetype(str(bold if b else font),size)
def centered(draw,txt,y,size,fill,b=False):
 f=fontobj(size,b);box=draw.textbbox((0,0),txt,font=f);draw.text(((W-(box[2]-box[0]))/2,y),txt,font=f,fill=fill)
clips=[
 dict(id='Short01',hook=['คนที่เคาะประตู…','หน้าตาเหมือนคุณ'],segments=[(20.2536,47.8982),(166.4706,174.8924)],question=['ถ้าสิ่งนั้นไม่ใช่ณัฐ','แล้วมันเป็นใคร?'],title='คนที่เคาะประตู…หน้าตาเหมือนคุณ | กฎ 9 ข้อ #Shorts',caption='กล้องหกเห็นอนาคตล่วงหน้า 10 นาที แต่เสียงเคาะกลับดังขึ้นแล้ว…\nถ้าเป็นคุณ จะเปิดประตูไหม?\n\nจากเรื่อง กฎ 9 ข้อสำหรับเจ้าหน้าที่เฝ้ากล้องกะดึก — FRAME TALES\nเรื่องแต่งแนวสยองขวัญ',
 captions=[(20.2536,24.1,'ตีห้าห้าสิบสองนาที\\Nณัฐนั่งอยู่ในห้องควบคุม'),(24.1,27.0,'กล้องหมายเลขหก\\Nกลับแสดงภาพใครอีกคน'),(27.,30.1621,'ยืนอยู่หน้าประตู\\Nห้องเดียวกัน'),(30.6121,33.7928,'มันยังอยู่…\\Nหน้าเหมือนเราทุกอย่าง'),(35.4128,37.9958,'เปิดหน่อย\\Nผมมารับช่วงต่อ'),(38.2158,40.7612,'เสียงเรานี่หว่า'),(40.9812,44.5,'ภาพที่เขาเพิ่งเห็น\\Nมีเวลานำอยู่สิบนาที'),(44.5,47.8982,'แต่เสียงจากอีกฝั่งของประตู\\Nดังขึ้นแล้ว'),(166.4706,170.5,'ข้อเจ็ด ถ้ากล้องหก\\Nแสดงภาพตัวคุณ'),(170.5,174.8924,'อย่าสนใจ อย่าออกไปดู\\Nสิ่งนั้นไม่ใช่ตัวคุณ')]),
 dict(id='Short02',hook=['ได้ยินเสียงเคาะ…','ห้ามตอบเด็ดขาด'],segments=[(141.9949,153.8004),(420.3783,439.5475)],question=['เขาเผลอตอบไปแล้ว…','จะเกิดอะไรขึ้น?'],title='ห้ามตอบเสียงเคาะ…แม้เป็นเสียงตัวเอง | กฎ 9 ข้อ #Shorts',caption='กฎเขียนไว้ชัดเจน: ห้ามเปิด ห้ามตอบ\nแต่ถ้าคนนอกประตูเรียกชื่อคุณ ด้วยเสียงของคุณเองล่ะ?\n\nจากเรื่อง กฎ 9 ข้อสำหรับเจ้าหน้าที่เฝ้ากล้องกะดึก — FRAME TALES\nเรื่องแต่งแนวสยองขวัญ',
 captions=[(141.9949,145.4,'ข้อห้า ถ้ามีเสียงเคาะ\\Nห้ามเปิด ห้ามตอบ'),(145.4,149.1,'ห้ามใช้กล้องหกดูว่า\\Nใครอยู่ข้างนอก'),(149.1,153.8004,'ยกเว้นถามชื่อและเปิดรับ\\Nผู้เปลี่ยนเวรตามข้อเก้า'),(420.3783,423.9563,'ณัฐ… ฉันรู้ว่านายอยู่ในนั้น\\Nเปิดประตูหน่อย'),(424.1763,428.0490,'ฉันไม่ได้จะทำอะไร\\Nฉันแค่อยากกลับเข้าไป'),(428.2690,429.2676,'กลับเข้าไป?'),(429.4876,432.7259,'นายได้ยินใช่ไหม\\Nตอบหน่อยสิ'),(432.9459,434.5459,'หยุดพูดสักที!'),(435.4159,439.5475,'พอคำพูดหลุดออกไป\\Nทุกเสียงนอกห้องก็หยุดพร้อมกัน')])]
reports=[]
for c in clips:
 name=c['id'];base=O/name;base.mkdir(exist_ok=True);duration=sum(b-a for a,b in c['segments']);end=2.6;total=round((duration+end)*FPS)/FPS
 # Transparent title/subtitle-safe frame; no crop of character anatomy.
 im=Image.new('RGBA',(W,H),(0,0,0,0));dr=ImageDraw.Draw(im)
 dr.rounded_rectangle((76,180,1004,245),radius=15,fill=(5,9,14,175));centered(dr,'FRAME TALES',185,38,(215,181,113,255),True)
 for i,line in enumerate(c['hook']):centered(dr,line,310+i*89,72,(245,240,231,255),True)
 dr.line((75,540,1005,540),fill=(184,150,92,210),width=2);dr.line((75,1150,1005,1150),fill=(184,150,92,210),width=2)
 centered(dr,'กฎ 9 ข้อ สำหรับเจ้าหน้าที่เฝ้ากล้องกะดึก',1505,39,(224,211,188,255),True)
 centered(dr,'ติดตามเรื่องเต็มที่ FRAME TALES',1570,42,(245,240,230,255),True)
 overlay=base/'frame.png';im.save(overlay)
 endim=Image.new('RGB',(W,H),(8,14,22));dr=ImageDraw.Draw(endim);centered(dr,'FRAME TALES',380,65,(215,181,113),True)
 for i,line in enumerate(c['question']):centered(dr,line,735+i*100,65,(241,236,228),True)
 centered(dr,'ติดตามเรื่องเต็มที่ช่อง',1160,50,(204,198,187));centered(dr,'FRAME TALES',1240,63,(215,181,113),True);endpath=base/'endcard.png';endim.save(endpath)
 ass='[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 2\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: Default,Noto Sans Thai,56,&H00FFFFFF,&H00FFFFFF,&H00100B08,&H78000000,-1,0,0,0,100,100,0,0,1,3,1,2,100,130,520,1\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n'
 offset=0
 for a,b in c['segments']:
  for ca,cb,txt in c['captions']:
   if a<=ca<b:ass+=f'Dialogue: 0,{tm(offset+ca-a)},{tm(offset+min(cb,b)-a)},Default,,0,0,0,,{txt}\n'
  offset+=b-a
 (base/'captions.ass').write_text(ass)
 # Build one filter graph: blurred backdrop + full-width source picture, then burned captions.
 filters=[];vlabels=[];alabels=[]
 for i,(a,b) in enumerate(c['segments']):
  filters.append(f'[{i}:v]setpts=PTS-STARTPTS,fps=30,split=2[b{i}][f{i}]')
  filters.append(f'[b{i}]scale=360:640:force_original_aspect_ratio=increase,crop=360:640,gblur=sigma=18,scale=1080:1920,eq=brightness=-0.23:saturation=0.55[bg{i}]')
  filters.append(f'[f{i}]scale=1080:608[fg{i}]');filters.append(f'[bg{i}][fg{i}]overlay=0:542,setsar=1[v{i}]')
  filters.append(f'[{i}:a]asetpts=PTS-STARTPTS,afade=t=in:d=0.025,afade=t=out:st={b-a-.025}:d=0.025[a{i}]');vlabels.append(f'[v{i}]');alabels.append(f'[a{i}]')
 filters.append(''.join(x+y for x,y in zip(vlabels,alabels))+f'concat=n={len(vlabels)}:v=1:a=1[mainv][maina]')
 filters.append(f"[mainv][{len(c['segments'])}:v]overlay=0:0,ass=filename='{base/'captions.ass'}':fontsdir='{R/'fonts'}'[subv]")
 filters.append(f'[{len(c["segments"])+1}:v]scale=1080:1920,fps=30,trim=duration={end},setpts=PTS-STARTPTS[endv]')
 filters.append(f'anullsrc=r=48000:cl=stereo,atrim=duration={end}[enda]');filters.append('[subv][maina][endv][enda]concat=n=2:v=1:a=1[v][a]')
 dest=O/f'Frame_Tales_Nightwatch9_{name}_v01.mp4'
 inputs=[]
 for a,b in c['segments']:inputs+=['-ss',str(a),'-t',str(b-a),'-i',str(src)]
 run(['ffmpeg','-hide_banner','-loglevel','error','-y',*inputs,'-i',str(overlay),'-loop','1','-t',str(end),'-i',str(endpath),'-filter_complex_threads','1','-filter_complex',';'.join(filters),'-map','[v]','-map','[a]','-t',str(total),'-r','30','-c:v','libx264','-threads','2','-preset','fast','-crf','19','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-ar','48000','-ac','2','-movflags','+faststart',str(dest)])
 meta=json.loads(run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(dest)]).stdout);v=next(x for x in meta['streams'] if x['codec_type']=='video');assert (v['width'],v['height'])==(W,H);assert abs(float(meta['format']['duration'])-total)<.15
 run(['ffmpeg','-hide_banner','-v','error','-i',str(dest),'-f','null','-'])
 run(['ffmpeg','-hide_banner','-v','error','-y','-ss','8','-i',str(dest),'-frames:v','1',str(O/f'{name}_preview.jpg')])
 report={k:c[k] for k in ['id','title','caption','segments']};report.update(file=dest.name,duration_seconds=float(meta['format']['duration']),resolution=[W,H],fps=30,sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),full_decode_passed=True,subtitles_burned_in=True,published=False,tags=['FrameTales','เล่าเรื่องสยองขวัญ','RulesHorror','กฎ9ข้อ'],facebook_caption=c['caption']+'\n\n#FrameTales #เล่าเรื่องสยองขวัญ #RulesHorror',youtube_description=c['caption']+'\n\n#Shorts #FrameTales #เล่าเรื่องสยองขวัญ',made_for_kids=False,youtube_category='Entertainment',ai_disclosure='AI-generated illustrations and narration',publishing_status='Awaiting user release dates and times');reports.append(report);print(json.dumps(report,ensure_ascii=False),flush=True)
(O/'shorts_package.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2)+'\n')
