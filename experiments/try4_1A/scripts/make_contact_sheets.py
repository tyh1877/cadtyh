"""Create unified GT | A0 | A1 | A2 contact sheets after all runs."""
import json
from pathlib import Path
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/try4_1A';TRY4=ROOT/'try4';out=HERE/'contact_sheets';out.mkdir(exist_ok=True)
for pid in ['R02_P02','R02_P04','R02_P05','R02_P06']:
 paths=[TRY4/f'artifacts/R02/isolated/{pid}/isometric.png',TRY4/f'T1/{pid}/round_0/renders/isometric.png',HERE/f'A1/{pid}/round_0/renders/isometric.png',HERE/f'A2/{pid}/round_0/renders/isometric.png'];canvas=Image.new('RGB',(1200,320),'white');d=ImageDraw.Draw(canvas)
 for i,(p,label) in enumerate(zip(paths,['GT','A0 frozen','A1 + topology','A2 + shape family'])):
  im=Image.open(p).convert('RGB');im.thumbnail((280,270));canvas.paste(im,(i*300+(280-im.width)//2,35));d.text((i*300+8,8),label,fill='black')
 canvas.save(out/f'{pid}.png')
