"""Create unified GT | B0 | B1 | B2 sheets after final evaluation."""
from pathlib import Path
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/try4_1B';TRY4=ROOT/'try4';A=ROOT/'experiments/try4_1A';out=HERE/'contact_sheets';out.mkdir(exist_ok=True)
for pid in ('R02_P04','R02_P06'):
 paths=[TRY4/f'artifacts/R02/isolated/{pid}/isometric.png',A/f'A1/{pid}/round_0/renders/isometric.png',HERE/f'B1/{pid}/round_0/renders/isometric.png',HERE/f'B2/{pid}/round_0/renders/isometric.png'];canvas=Image.new('RGB',(1200,330),'white');d=ImageDraw.Draw(canvas)
 for i,(p,label) in enumerate(zip(paths,['GT','B0 frozen A1','B1 executable family','B2 structural replan'])):
  im=Image.open(p).convert('RGB');im.thumbnail((280,280));canvas.paste(im,(i*300+(280-im.width)//2,35));d.text((i*300+8,8),label,fill='black')
 canvas.save(out/f'{pid}.png')
