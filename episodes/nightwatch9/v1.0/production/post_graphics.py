"""Exact labels and diegetic monitor replacement in the edit, not AI lettering."""
from pathlib import Path
import numpy as np,math
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).parent;D=R/'scene_assets';FONT=str(R/'fonts/FrameTalesThai-Regular.ttf');DIG='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
def quad_composite(base,layer,quad):
 w,h=layer.size;uv=[(0,0),(w-1,0),(w-1,h-1),(0,h-1)];mat=[];ys=[]
 for (x,y),(u,v) in zip(quad,uv):mat.extend([[x,y,1,0,0,0,-u*x,-u*y],[0,0,0,x,y,1,-v*x,-v*y]]);ys.extend([u,v])
 coeff=np.linalg.solve(np.asarray(mat,float),np.asarray(ys,float));warped=layer.convert('RGBA').transform(base.size,Image.Transform.PERSPECTIVE,tuple(coeff),Image.Resampling.BICUBIC,fillcolor=(0,0,0,0));return Image.alpha_composite(base.convert('RGBA'),warped).convert('RGB')
def current(n):
 if n<27:return '05:52' if n<12 else '21:00'
 for upper,t in [(39,'21:00'),(45,'21:30'),(60,'23:16'),(75,'23:30'),(95,'00:10'),(110,'03:40'),(125,'05:47'),(135,'05:52'),(140,'06:00'),(141,'06:02'),(144,'06:12'),(178,'06:12')]:
  if n<upper:return t
 return '06:19'
def decorate_prop(im,a,n):
 if a=='phone_insert':
  layer=Image.new('RGBA',(500,150),(0,0,0,0));d=ImageDraw.Draw(layer);d.text((80,15),'001',font=ImageFont.truetype(DIG,110),fill=(35,48,37,255));im=quad_composite(im,layer,[(634,393),(781,383),(818,428),(671,449)])
 if a=='duty_drawer':
  layer=Image.new('RGBA',(1000,460),(0,0,0,0));d=ImageDraw.Draw(layer);d.text((120,35),'รายชื่อเจ้าหน้าที่กะเช้า',font=ImageFont.truetype(FONT,49),fill=(41,36,27,255));d.text((170,160),'วิทยา',font=ImageFont.truetype(FONT,64),fill=(41,36,27,255));d.text((650,160),'0472',font=ImageFont.truetype(DIG,62),fill=(41,36,27,255));im=quad_composite(im,layer,[(910,416),(1406,445),(1360,645),(825,614)])
 placements={
 'room_master':[(743,379),(1108,379),(1108,563),(743,563)],
 'nat_reads_rules':[(748,384),(1106,384),(1106,564),(748,564)],
 'somchai_briefing':[(751,365),(1096,365),(1096,535),(751,535)],
 'nat_answers001':[(956,339),(1249,339),(1249,528),(956,528)],
 'nat_hangs_up':[(956,339),(1249,339),(1249,528),(956,528)],
 'nat_rule6_close':[(1135,421),(1579,421),(1579,706),(1135,706)],
 'nat_power_button':[(691,350),(1217,350),(1217,610),(691,610)],
 'nat_somchai_question':[(744,390),(1033,390),(1033,554),(744,554)]}
 if a in placements:
  plate='door_empty'
  if n>=45:plate='door_empty_after'
  if n<12 or 95<=n<141:plate='double_smile'
  if 39<=n<45:plate='grey_future'
  if a=='nat_power_button':plate='ceiling_danger'
  p=D/(plate+'.png')
  if p.exists():
   layer=Image.open(p).convert('RGB').resize((1672,941),Image.Resampling.LANCZOS);d=ImageDraw.Draw(layer);d.rectangle((0,0,1672,65),fill=(5,13,17));hh,mm=map(int,current(n).split(':'));future=f'{(hh+(mm+10)//60)%24:02}:{(mm+10)%60:02}:00';d.text((45,10),'CAM 06',font=ImageFont.truetype(DIG,37),fill=(195,214,207));d.text((1360,10),future,font=ImageFont.truetype(DIG,37),fill=(195,214,207));im=quad_composite(im,layer,placements[a])
 return im
