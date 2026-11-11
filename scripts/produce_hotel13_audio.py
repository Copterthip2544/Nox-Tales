"""Produce approved v1.3 speech turns, with verified resumable artifacts."""
import base64, csv, hashlib, io, json, os, re, subprocess, sys, time, wave
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

MODEL='gemini-3.8-flash-tts'
PLAN=Path('episodes/hotel13/v1.3/production/audio_plan.json')
OUT=Path('production-output')

def signature(turn):
    data={'text':turn['text'],'style':turn['performance']['style'],
          'voice':turn['performance']['voice'],'model':MODEL}
    return hashlib.sha256(json.dumps(data,sort_keys=True,ensure_ascii=False).encode()).hexdigest()

def wav_duration(path):
    with wave.open(str(path),'rb') as w:
        if w.getnframes()<1:raise ValueError('Empty audio')
        return w.getnframes()/w.getframerate()

def audio_bytes(response):
    c=response.get('candidates',[])
    if len(c)!=1 or c[0].get('finishReason')!='STOP':raise ValueError('Incomplete audio')
    parts=[p['inlineData'] for p in c[0].get('content',{}).get('parts',[]) if 'inlineData' in p]
    if len(parts)!=1 or parts[0].get('mimeType','').split(';')[0].lower() not in {'audio/wav','audio/x-wav','audio/wave'}:
        raise ValueError('Unexpected audio format')
    b=base64.b64decode(parts[0]['data'],validate=True)
    if b[:4]!=b'RIFF' or b[8:12]!=b'WAVE':raise ValueError('Invalid WAV')
    with wave.open(io.BytesIO(b),'rb') as w:
        if w.getnframes()<1:raise ValueError('Empty WAV')
    return b

def main():
    key=os.environ.get('GEMINI_API_KEY','').strip()
    if not key or os.environ.get('CONFIRM_GENERATION','').lower()!='true':
        print('Missing key or generation authorization.');return 1
    plan=json.loads(PLAN.read_text())
    turns=[e for e in plan['events'] if e['type']=='speech']
    assert len(turns)==111 and len({e['event_id'] for e in turns})==111
    assert all(e['performance']['voice'] for e in turns)
    OUT.mkdir(exist_ok=True);(OUT/'turns').mkdir(exist_ok=True)
    manifest_path=OUT/'manifest.json'
    manifest=json.loads(manifest_path.read_text()) if manifest_path.exists() else {'model':MODEL,'script_version':'1.3','turns':{}}
    def save():manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    generated=0
    for turn in turns:
        tid=turn['event_id'];stamp=signature(turn);dest=OUT/'turns'/f'{tid}_{turn["speaker"]}.wav'
        item=manifest['turns'].get(tid,{})
        if item.get('fingerprint')==stamp and dest.exists():
            wav_duration(dest);print(f'Reuse {tid}',flush=True);continue
        if item.get('request_state')=='uncertain':
            print(f'Stopping: {tid} has an uncertain prior request; review before resubmitting.');return 1
        payload={'contents':[{'role':'user','parts':[{'text':turn['text'],
            'speech_metadata':{'style':turn['performance']['style']}}]}],
            'generationConfig':{'responseModalities':['AUDIO'],
              'speechConfig':{'voiceConfig':{'voice':turn['performance']['voice']}}}}
        manifest['turns'][tid]={'fingerprint':stamp,'speaker':turn['speaker'],'voice':turn['performance']['voice'],
            'text':turn['text'],'file':str(dest.relative_to(OUT)),'request_state':'uncertain'};save()
        req=Request(f'https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent',
            data=json.dumps(payload,ensure_ascii=False).encode(),method='POST',
            headers={'x-goog-api-key':key,'Content-Type':'application/json'})
        try:
            # HTTP 429 rejects the request before generation. Only this status is safe
            # to retry automatically. Timeouts and ambiguous responses still stop.
            for attempt in range(7):
                try:
                    with urlopen(req,timeout=180) as response:result=json.load(response)
                    break
                except HTTPError as error:
                    if error.code!=429:raise
                    details=[]
                    try:details=json.loads(error.read()).get('error',{}).get('details',[])
                    except Exception:pass
                    wait=65
                    quota=[]
                    for detail in details:
                        if str(detail.get('@type','')).endswith('RetryInfo'):
                            match=re.fullmatch(r'(\d+(?:\.\d+)?)s',str(detail.get('retryDelay','')))
                            if match:wait=max(wait,int(float(match.group(1)))+2)
                        if str(detail.get('@type','')).endswith('QuotaFailure'):
                            for violation in detail.get('violations',[]):
                                quota.append({k:violation[k] for k in ['quotaMetric','quotaId','quotaValue'] if k in violation})
                    manifest['turns'][tid]['quota_diagnostics']=quota;save()
                    if any('perday' in str(q).lower().replace('_','') for q in quota) or attempt==6 or wait>180:
                        raise
                    print(f'{tid}: rate limited; waiting {wait}s before retrying rejected request. Quota: {json.dumps(quota)}',flush=True)
                    time.sleep(wait)
            data=audio_bytes(result)
            temporary=dest.with_suffix('.tmp');temporary.write_bytes(data);temporary.replace(dest)
            duration=wav_duration(dest)
        except HTTPError as error:
            manifest['turns'][tid]['request_state']='http_error';manifest['turns'][tid]['http_status']=error.code;save()
            print(f'{tid}: HTTP {error.code}; stopped without automatic retry.');return 1
        except Exception:
            save();print(f'{tid}: request or audio validation failed. Prior output preserved; no automatic retry.');return 1
        manifest['turns'][tid].update({'duration_seconds':round(duration,4),'request_state':'complete','listening_review':'pending'})
        save();generated+=1;print(f'Saved {tid} {turn["speaker"]}: {duration:.2f}s',flush=True)
        # Modest pace; do not overlap generation or retry billable requests automatically.
        time.sleep(7)
    # Reference assembly is speech + short conversational gaps, not the final sound edit.
    sample_rate=24000;timeline=[];position=0
    reference=OUT/'dialogue_reference.wav'
    with wave.open(str(reference),'wb') as target:
        target.setnchannels(1);target.setsampwidth(2);target.setframerate(sample_rate)
        for turn in turns:
            item=manifest['turns'][turn['event_id']];src=OUT/item['file'];normalized=OUT/'normalized.wav'
            subprocess.run(['ffmpeg','-v','error','-y','-i',str(src),'-ac','1','-ar',str(sample_rate),'-c:a','pcm_s16le',str(normalized)],check=True)
            with wave.open(str(normalized),'rb') as part:
                frames=part.getnframes();target.writeframes(part.readframes(frames))
            start=position/sample_rate;position+=frames
            timeline.append({'event_id':turn['event_id'],'source_v12':turn['source_v12'],'speaker':turn['speaker'],
                'voice':item['voice'],'start_seconds':round(start,4),'end_seconds':round(position/sample_rate,4),
                'text':turn['text'],'file':item['file'],'time_status':'MEASURED_REFERENCE_NOT_FINAL_EDIT'})
            gap=int(sample_rate*(0.55 if turn['speaker']=='nox' else 0.3));target.writeframes(b'\x00\x00'*gap);position+=gap
    (OUT/'normalized.wav').unlink(missing_ok=True)
    with (OUT/'speech_timeline.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(timeline[0]));writer.writeheader();writer.writerows(timeline)
    report={'all_111_turns_present':len(manifest['turns'])==111,
        'speech_seconds':round(sum(x['duration_seconds'] for x in manifest['turns'].values()),2),
        'reference_seconds':round(wav_duration(reference),2),'generated_this_run':generated,
        'final_video_duration_verified':False,'listening_and_visual_review':'pending',
        'note':'Reference omits staged holds, phone rings, effects and final mixing. Do not claim it is a final 10–15 minute film.'}
    (OUT/'production_report.json').write_text(json.dumps(report,indent=2))
    (OUT/'events_for_edit.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2))
    summary='## Hotel 13 full speech production\n\n'+json.dumps(report,ensure_ascii=False,indent=2)+'\n\nArtifact: hotel13-full-audio. Listening review required.\n'
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'],'a') as f:f.write(summary)
    print(json.dumps(report),flush=True);return 0

if __name__=='__main__':sys.exit(main())
