"""Estimate paragraph timestamps from the approved E001 audio using Gemini."""
import base64,json,os,sys
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError

def main():
    key=os.environ.get('GEMINI_API_KEY','').strip()
    if not key:print('Missing Gemini key');return 1
    root=Path('production-output');manifest=json.loads((root/'manifest.json').read_text())
    text=manifest['turns']['E001']['text'];paragraphs=text.split('\n\n')
    audio=root/manifest['turns']['E001']['file']
    prompt='''Listen to this Thai narration. Align each supplied paragraph to the actual audio in seconds from the start. Do not regenerate or rewrite any text. Return JSON only with key paragraphs, an array of objects with index (zero-based), start_seconds and end_seconds. Find actual acoustic phrase boundaries rather than allocating time proportional to characters. The clip is 61.32 seconds. Use every paragraph once, ordered, with no overlaps; do not put long silence inside words. These are the exact paragraphs: '''+json.dumps(paragraphs,ensure_ascii=False)
    body={'contents':[{'role':'user','parts':[{'text':prompt},{'inlineData':{'mimeType':'audio/wav','data':base64.b64encode(audio.read_bytes()).decode()}}]}],
          'generationConfig':{'responseMimeType':'application/json','temperature':0,'maxOutputTokens':4096}}
    req=Request('https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent',
        data=json.dumps(body).encode(),headers={'x-goog-api-key':key,'Content-Type':'application/json'},method='POST')
    try:
        with urlopen(req,timeout=180) as r:response=json.load(r)
        content=''.join(p.get('text','') for p in response['candidates'][0]['content']['parts'] if not p.get('thought'))
        data=json.loads(content);items=data['paragraphs'];assert len(items)==len(paragraphs)
        previous=0
        for i,item in enumerate(items):
            assert item['index']==i
            a=float(item['start_seconds']);b=float(item['end_seconds'])
            assert previous-.05<=a<b<=61.4
            previous=b;item['text']=paragraphs[i]
        out=Path('opening-alignment');out.mkdir(exist_ok=True)
        data.update({'source_event':'E001','method':'Gemini audio-based estimated paragraph alignment; not word-level forced alignment','audio_duration_seconds':61.32})
        (out/'paragraph_alignment.json').write_text(json.dumps(data,ensure_ascii=False,indent=2))
        print(json.dumps(data,ensure_ascii=False,indent=2));return 0
    except HTTPError as e:print(f'Alignment API returned HTTP {e.code}');return 1
    except Exception:print('Alignment response failed validation.');return 1

if __name__=='__main__':sys.exit(main())
