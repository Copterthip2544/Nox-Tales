"""Estimate acoustic paragraph boundaries in already approved narration. No TTS."""
import base64, json, os, sys, wave
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

def main():
    root=Path('production-output');out=Path('narration-alignment');out.mkdir(exist_ok=True)
    manifest=json.loads((root/'manifest.json').read_text());results={};failures={}
    for eid,turn in manifest['turns'].items():
        if turn.get('speaker')!='nox' or eid=='E001':continue
        paragraphs=[s.strip() for s in turn['text'].split('\n\n') if s.strip()]
        if len(paragraphs)<2:continue
        audio=root/turn['file']
        with wave.open(str(audio),'rb') as w:duration=w.getnframes()/w.getframerate()
        prompt=(f'Listen to this approved Thai voice recording, duration {duration:.3f} seconds. '
                'Return JSON only: {"paragraphs":[{"index":0,"start_seconds":0.0,"end_seconds":1.0},...]}. '
                'Find actual acoustic start and end of each exact supplied paragraph from the beginning of this clip. '
                'Do not rewrite text or allocate times proportional to text length. Use every paragraph once, ordered, nonoverlapping, '
                'with zero-based indexes. Exact paragraphs: '+json.dumps(paragraphs,ensure_ascii=False))
        body={'contents':[{'role':'user','parts':[{'text':prompt},{'inlineData':{'mimeType':'audio/wav','data':base64.b64encode(audio.read_bytes()).decode()}}]}],
              'generationConfig':{'responseMimeType':'application/json','temperature':0,'maxOutputTokens':4096}}
        req=Request('https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent',data=json.dumps(body).encode(),headers={'x-goog-api-key':os.environ['GEMINI_API_KEY'],'Content-Type':'application/json'},method='POST')
        try:
            with urlopen(req,timeout=180) as r:response=json.load(r)
            content=''.join(p.get('text','') for p in response['candidates'][0]['content']['parts'] if not p.get('thought')).strip()
            (out/f'{eid}_raw.json').write_text(content)
            if content.startswith('```'):content=content.split('\n',1)[1].rsplit('```',1)[0]
            data=json.loads(content);items=data if isinstance(data,list) else data['paragraphs']
            assert len(items)==len(paragraphs),(len(items),len(paragraphs))
            previous=0
            for i,item in enumerate(items):
                assert int(item['index'])==i
                a=float(item['start_seconds']);b=float(item['end_seconds'])
                assert previous-.1<=a<b<=duration+.4,(a,b,duration)
                item.update(index=i,start_seconds=max(a,0),end_seconds=min(b,duration),text=paragraphs[i]);previous=b
            results[eid]={'duration':duration,'paragraphs':items,'method':'Gemini acoustic estimate; not word-level forced alignment'}
            print(f'Aligned {eid}: {len(items)} paragraphs',flush=True)
        except HTTPError as e:failures[eid]=f'HTTP {e.code}';print(f'{eid}: HTTP {e.code}',flush=True)
        except Exception as e:failures[eid]=type(e).__name__;print(f'{eid}: validation failed ({type(e).__name__})',flush=True)
        (out/'paragraph_alignment.json').write_text(json.dumps({'events':results,'failures':failures,'scope':'Already approved Thai Nox narration; no speech generated.'},ensure_ascii=False,indent=2))
    print(f'{len(results)} aligned events, {len(failures)} need editorial timing',flush=True)
    return 0

if __name__=='__main__':sys.exit(main())
