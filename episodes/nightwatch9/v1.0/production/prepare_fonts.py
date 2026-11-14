from pathlib import Path
from fontTools.merge import Merger
r=Path(__file__).parent/'fonts';r.mkdir(exist_ok=True)
for w in ['Regular','Bold']:
 f=Merger().merge([f'/usr/share/fonts/truetype/noto/NotoSans-{w}.ttf',f'/usr/share/fonts/truetype/noto/NotoSansThai-{w}.ttf']);f.save(r/f'FrameTalesThai-{w}.ttf')
print('Thai, Latin and digit glyphs available.')
