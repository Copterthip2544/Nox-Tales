"""Build measured full-film performance timeline and deterministic local sound mix."""
import argparse, csv, json, math, wave
from pathlib import Path
import numpy as np
from scipy.signal import butter, sosfilt

FPS=30; SR=24000
EXTRA={8:1.8,22:2.0,34:.6,46:1.2,53:2.,56:.8,63:1.,69:1.,77:2.2,79:.9,
       91:1.8,98:1.8,101:1.,102:.7,121:2.,124:1.,125:1.5,129:1.5,
       135:1.3,137:1.4,140:3.,143:7.0,145:1.8,147:11.4,149:1.6,
       150:1.,152:1.4,154:1.5,157:.6,161:2.,162:1.5}

def readwav(path):
    with wave.open(str(path),'rb') as w:
        assert w.getframerate()==SR and w.getsampwidth()==2
        x=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').astype(np.float32)/32768
        if w.getnchannels()>1:x=x.reshape(-1,w.getnchannels()).mean(axis=1)
    return x

def timeline(rows,audio):
    out=[];holds=[];rings=[];cursor=0.;previous_original=0.;anchors={}
    for r in rows:
        eid=r['event_id'];n=int(eid[1:]);x=readwav(audio/r['file']);duration=len(x)/SR
        gap=round(float(r['start_seconds'])-previous_original,4)
        previous_original=float(r['end_seconds'])
        start=cursor+max(gap,0);holdstart=start
        if n==36:
            anchors['first']=start;rings.append({'kind':'hotel','start':start,'count':13,'period':1.6,'answer_event':'E040'});start+=8.
        elif n==40:start=max(start,anchors['first']+20.4)
        elif n==105:
            anchors['second']=start;rings.append({'kind':'hotel','start':start,'count':13,'period':1.6,'answer_event':'E113'});start+=4.8
        elif n in (107,109,111):start=max(start,anchors['second']+{107:8.,109:12.8,111:17.6}[n])
        elif n==113:start=max(start,anchors['second']+20.4)
        elif n==159:
            anchors['third']=start;rings.append({'kind':'mobile','start':start,'count':13,'period':1.6,'answer_event':'E159'});start+=20.4
        else:start+=EXTRA.get(n,0.)
        if start>holdstart+.05:holds.append({'before':eid,'start':holdstart,'end':start})
        end=start+duration
        out.append({'event_id':eid,'speaker':r['speaker'],'file':r['file'],'text':r['text'],
                    'start':round(start,4),'end':round(end,4),'duration':duration})
        cursor=end
    return out,holds,rings,cursor+5.5

def make_cuts(events,holds,rings,duration,alignment,opening):
    ev={e['event_id']:e for e in events};cuts=[]
    def put(t,asset,cue='',motion=None):cuts.append({'time':float(t),'asset':asset,'cue':cue,'motion':motion})
    def at(eid,asset,offset=0,cue=''):put(ev[eid]['start']+offset,asset,cue or eid)
    def group(ids,asset):
        for n in ids:at(f'E{n:03}',asset)
    for s in opening['shots']:put(s['start'],Path(s['asset']).stem,s['cue'],s['motion'])
    group([3,5,9,13,19,81,85,94],'A09_manager_waiting')
    group([4],'A08_lobby_entry');group([6],'B01_contract')
    group([8,18,26,31,37,49],'B02_Maysa_uniform')
    group([11],'B03_checkout_ledger_v2');group([14,21],'A02_key13_insert')
    group([15,107],'A14_phone_insert');group([16],'L02_landing_master')
    group([22,34],'L01_lobby_master');group([24],'C01_Phakhin_shadow')
    group([28,57],'C03_Maysa_key_v2');group([30,33],'C02_Phakhin_lit')
    group([36,48,51,54,60,65,127],'D02_Lin_close');group([38],'D01_Lin_arrives')
    group([40,41,44,113,114,116,118],'D03_Maysa_receiver')
    group([42,46,115,117,119],'D04_Pim_phone_shadow')
    group([53,67],'D06_Maysa_Lin_blanket_v2');group([55],'D07_Maysa_mobile')
    group([56,58,63],'D08_faceless_shadow');group([62,105,111],'G04_Maysa_waiting')
    group([66],'D09_old_staff_photo');group([68],'D02_Lin_close')
    group([69,71,73],'E05_Phakhin_sad');group([74,78,82,84,89,91,95],'F02_Maysa_confront')
    group([75],'E04_fire_corridor');group([77],'E06_burned_hand_v2')
    group([79,87],'F01_manager_office');group([83,92,93],'F03_manager_guilt')
    group([96,101,109],'G02_Lin_sleep_solo');group([98],'F04_manager_takes_ledger')
    group([99],'G01_Maysa_exit');group([102],'G02_Lin_sleep')
    group([121,122],'H01_Pim_landing');group([130,132,133,141],'H05_Pim_close');group([124],'H02_manager_key_stairs')
    group([125],'H04_Maysa_takes_ledger');group([129,131,135],'I01_landing_confront')
    group([137,138],'I03_Phakhin_blocks_v2');group([140],'I09_manager_pleading')
    group([143],'I06_Maysa_returnskey_v2');group([145],'I10_Lin_touch_hand')
    group([147,149],'I08_manager_trapped_v2');group([150,152,155,156],'J01_police_Maysa')
    group([154],'J02_abandoned_lobby');group([157],'J04_cut_phone_v2')
    group([159],'J07_phone13');group([161],'J08_Maysa_home_fear_v2');group([162],'A01_NOX_host')
    # Actual acoustic paragraph boundaries from approved narration recordings.
    para_assets={
      'E022':['L01_lobby_master','C01_Phakhin_shadow'],
      'E034':['L01_lobby_master','L01_lobby_master','A14_phone_insert'],
      'E055':['D07_Maysa_mobile','D08_faceless_shadow'],
      'E063':['D08_faceless_shadow','D06_Maysa_Lin_blanket_v2'],
      'E068':['D02_Lin_close','E01_Maysa_archive','E02_charred_ledger_v2','E02_charred_ledger_v2','E03_news_family_v2','E01_Maysa_archive','E03_news_family_v2'],
      'E099':['G01_Maysa_exit','G01_Maysa_exit'],
      'E102':['G02_Lin_sleep','G02_Lin_sleep_solo','A14_phone_insert'],
      'E122':['H01_Pim_landing','H02_manager_key_stairs'],
      'E125':['H04_Maysa_takes_ledger','H03_office_papers_v2','H04_Maysa_takes_ledger'],
      'E150':['J01_police_Maysa','J01_police_Maysa'],
      'E157':['J04_cut_phone_v2','J03_scratched_door','J05_Maysa_home_ledger','J06_new_ledger_entry','J06_new_ledger_entry','J08_Maysa_home_fear_v2','J07_phone13'],
      'E162':['A01_NOX_host','A02_key13_insert']}
    for eid,assets in para_assets.items():
        pars=alignment['events'][eid]['paragraphs'];assert len(pars)==len(assets),(eid,len(pars),len(assets))
        for p,asset in zip(pars,assets):at(eid,asset,p['start_seconds'],f'{eid} paragraph {p["index"]}')
    at('E071','E04_fire_corridor',3.7,'memory of blocked smoke-filled stairs')
    at('E073','D04_Pim_phone_shadow',3.5,'annual return - mother calls')
    at('E073','D01_Lin_arrives',6.5,'annual return - daughter downstairs')
    at('E073','C01_Phakhin_shadow',9.2,'annual return - father asks key')
    # Silent physical actions, with no extra narrator added.
    actions={8:'B02_Maysa_uniform',22:'L01_lobby_master',46:'D04_Pim_phone_shadow',
      53:'D06_Maysa_Lin_blanket_v2',56:'D08_faceless_shadow',63:'D08_faceless_shadow',
      77:'E06_burned_hand_v2',79:'F01_manager_office',98:'F04_manager_takes_ledger',
      101:'G01_Maysa_exit',102:'G02_Lin_sleep',121:'H01_Pim_landing',124:'H02_manager_key_stairs',
      125:'H02_manager_key_stairs',129:'I01_landing_confront',135:'I02_Maysa_writing_v2',
      137:'I03_Phakhin_blocks_v2',140:'I04_Pim_key_grip_v2',143:'I05_key_fallen',
      145:'I10_Lin_touch_hand',147:'I07_family_exit_v2',149:'I08_manager_trapped_v2',
      152:'J01_police_Maysa',154:'J02_abandoned_lobby',159:'J07_phone13',161:'J08_Maysa_home_fear_v2'}
    for h in holds:
        n=int(h['before'][1:])
        if n in actions:put(h['start'],actions[n],f'Action before {h["before"]}')
        if n==143:put(h['start']+3.,'I06_Maysa_returnskey_v2','hot key returned to rack')
    for r in rings:
        if r['kind']=='mobile':
            put(r['start'],'J07_phone13','one-year call ring1');put(r['start']+17.6,'J08_Maysa_home_fear_v2','ring12 - hand stops');put(r['start']+19.2,'J07_phone13','ring13 - automatic answer')
        else:put(r['start'],'A14_phone_insert','ring1 - handset remains on base')
    # Anchor first visible new action precisely after the approved opening.
    at('E006','B01_contract')
    put(duration-4.4,'A02_key13_insert','final solitary ring, no answer')
    # Frame-quantized timeline; last cut at a frame wins, adjacent repeats merge.
    framed={round(c['time']*FPS):c for c in cuts if 0<=c['time']<duration}
    keys=sorted(framed);result=[]
    for i,k in enumerate(keys):
        c=framed[k];end=keys[i+1] if i+1<len(keys) else math.ceil(duration*FPS)
        if result and result[-1]['asset']==c['asset'] and not c.get('motion'):
            result[-1]['end_frame']=end;continue
        result.append({'id':f'SH{len(result)+1:03}','start_frame':k,'end_frame':end,
          'asset':c['asset'],'cue':c['cue'],'motion':c['motion'] or ['zoom_in','pan_right','pan_left'][len(result)%3]})
    assert result[0]['start_frame']==0
    return result

def synth_mix(events,holds,rings,duration,audio,out):
    size=math.ceil(duration*SR);speech=np.zeros(size,np.float32);fx=np.zeros(size,np.float32)
    def add(bus,x,start,gain=1.):
        i=round(start*SR);n=min(len(x),len(bus)-i)
        if i>=0 and n>0:bus[i:i+n]+=x[:n]*gain
    phone_ids={40,42,46,113,115,117,119,159,161,105,107,109,111}
    for e in events:
        x=readwav(audio/e['file']);n=int(e['event_id'][1:])
        if n in phone_ids:x=sosfilt(butter(2,[230,6000],btype='bandpass',fs=SR,output='sos'),x).astype(np.float32)*1.1
        add(speech,x,e['start'])
    rng=np.random.default_rng(13059)
    def ring(kind='hotel'):
        t=np.arange(round(.7*SR))/SR
        if kind=='hotel':
            x=(np.sin(2*np.pi*1050*t)+.5*np.sin(2*np.pi*1610*t)+.24*np.sin(2*np.pi*2137*t))
            x*=.42+.58*np.maximum(np.sin(2*np.pi*23*t),0)
        else:x=np.sin(2*np.pi*660*t)+.45*np.sin(2*np.pi*880*t)
        envelope=np.minimum(t/.018,1)*np.minimum((.7-t)/.06,1)
        return (x*envelope*.042).astype(np.float32)
    for r in rings:
        for k in range(r['count']):add(fx,ring(r['kind']),r['start']+k*r['period'])
    ev={e['event_id']:e for e in events};hs={h['before']:h for h in holds}
    def impact(start,amp=.03,freq=130,seconds=.25):
        t=np.arange(round(seconds*SR))/SR;x=(np.sin(2*np.pi*freq*t)+.22*rng.normal(size=len(t)))*np.exp(-t*25)
        add(fx,x.astype(np.float32),start,amp)
    # Door, paper, footsteps and phone receiver Foley; no sharp jump-scare peaks.
    for eid in ['E022','E079','E098','E121','E124','E125','E149']:
        if eid in hs:impact(hs[eid]['start']+.1,.022,95)
    for r in rings:impact(ev[r['answer_event']]['start']-.12,.012,1000,.12)
    for off in [6.7,7.0,7.3]:impact(rings[0]['start']+off,.012,270,.15)
    impact(hs['E143']['start']+.2,.04,1800,.5)
    for t in [hs['E161']['start']+.15,hs['E161']['start']+.6,hs['E161']['start']+1.05]:impact(t,.028,90,.25)
    for t in [hs['E149']['start']+.3,hs['E149']['start']+.65,hs['E149']['start']+1.0]:impact(t,.026,105,.25)
    # Six clock strikes ONLY after family is through threshold, before manager plea.
    bell_start=hs['E147']['start']+6.
    for k in range(6):
        t=np.arange(round(1.8*SR))/SR
        bell=(np.sin(2*np.pi*440*t)+.5*np.sin(2*np.pi*661*t)+.28*np.sin(2*np.pi*1041*t))*np.exp(-t*2.2)
        add(fx,bell.astype(np.float32),bell_start+k*.9,.025)
    add(fx,ring('hotel'),duration-3.2)
    # A restrained original synthesized ambience/score bed, ducked under speech.
    bed=np.zeros(size,np.float32);rain_end=ev['E099']['start'];clock_end=hs['E147']['start']+6.
    n=round(rain_end*SR);noise=rng.normal(size=n).astype(np.float32)
    rain=sosfilt(butter(2,[450,6500],btype='bandpass',fs=SR,output='sos'),noise).astype(np.float32)
    rain*=.0035;rain[-SR*2:]*=np.linspace(1,0,SR*2);bed[:n]+=rain
    for sec in np.arange(61.4,clock_end,1.):impact(sec,.0035,1800,.07)
    for base in np.arange(0,ev['E150']['start'],17.):
        t=np.arange(SR*12)/SR;freq=[110.,130.8128,146.8324,164.8138][int(base/17)%4]
        tone=(np.sin(2*np.pi*freq*t)+.3*np.sin(2*np.pi*freq*2.003*t))*np.sin(np.pi*np.minimum(t/12,1))**2
        add(bed,tone.astype(np.float32),base,.0024)
    duck=np.ones(size,np.float32)
    for e in events:
        a=max(0,round((e['start']-.06)*SR));b=min(size,round((e['end']+.08)*SR));duck[a:b]=.35
    bed*=duck
    # Preserve dialogue level; full-programme loudness normalization is done at export.
    mix=speech+fx+bed;mix[-int(1.8*SR):]*=np.linspace(1,0,int(1.8*SR))
    peak=float(np.max(np.abs(mix)));gain=min(1.,.92/max(peak,1e-6));mix*=gain
    def wavwrite(path,x):
        with wave.open(str(path),'wb') as w:
            w.setnchannels(1);w.setsampwidth(2);w.setframerate(SR);w.writeframes(np.clip(x*32767,-32768,32767).astype('<i2').tobytes())
    wavwrite(out/'film_mix.wav',mix)
    report={'duration_seconds':duration,'native_sample_rate':SR,'dialogue_turns':len(events),
      'tts_regenerated':False,'peak_before_export':float(np.max(np.abs(mix))),
      'telephone_sequences':rings,'six_strikes_start':bell_start,'score':'Original local synthesized restrained tonal bed, no licensed recording',
      'clock_tick_end':clock_end,'rain_stops':rain_end,'final_single_ring':duration-3.2}
    (out/'sound_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))

def main():
    p=argparse.ArgumentParser();p.add_argument('--audio',type=Path,required=True);p.add_argument('--root',type=Path,required=True);p.add_argument('--opening-report',type=Path,required=True);p.add_argument('--plan-only',action='store_true');args=p.parse_args()
    root=args.root;out=root/'outputs';out.mkdir(parents=True,exist_ok=True)
    rows=list(csv.DictReader((args.audio/'speech_timeline.csv').open(encoding='utf-8-sig')))
    events,holds,rings,duration=timeline(rows,args.audio)
    assert len(events)==111 and 600<duration<900
    alignment=json.loads((root/'alignment/paragraph_alignment.json').read_text());opening=json.loads(args.opening_report.read_text())
    shots=make_cuts(events,holds,rings,duration,alignment,opening)
    data={'script_version':'1.3','duration_seconds':duration,'fps':FPS,'events':events,'holds':holds,'rings':rings,'shots':shots,
          'timing':'Actual voice durations; Nox paragraphs use acoustic estimates, physical-action gaps authored for performance.'}
    (out/'full_edit_plan.json').write_text(json.dumps(data,ensure_ascii=False,indent=2))
    with (out/'shot_list.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=shots[0].keys());w.writeheader();w.writerows(shots)
    if not args.plan_only:synth_mix(events,holds,rings,duration,args.audio,out)
    print(json.dumps({'duration':duration,'shots':len(shots),'unique_images':len(set(s['asset'] for s in shots)),'speech_turns':len(events)},ensure_ascii=False))

if __name__=='__main__':main()
