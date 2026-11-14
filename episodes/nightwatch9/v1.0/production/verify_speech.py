from pathlib import Path
import json,hashlib
r=Path('complete_speech');units=json.loads((r/'manifest.json').read_text())['units']
assert len(units)==149
for key,u in units.items():
 assert u['status']=='complete',key
 assert hashlib.sha256((r/u['file']).read_bytes()).hexdigest()==u['sha256'],key
print('All 149 approved speech unit hashes verified; no TTS called.')
