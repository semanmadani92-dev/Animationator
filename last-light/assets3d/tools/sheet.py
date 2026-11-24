import sys,os,glob
from PIL import Image,ImageDraw
d=sys.argv[1]; fs=sorted(glob.glob(d+'/*.png')); cols=int(sys.argv[2]) if len(sys.argv)>2 else 10; S=160
im=Image.new('RGB',(cols*S,((len(fs)+cols-1)//cols)*(S+16)),'#111'); dr=ImageDraw.Draw(im)
for i,f in enumerate(fs):
    x,y=(i%cols)*S,(i//cols)*(S+16); im.paste(Image.open(f).resize((S,S)),(x,y)); dr.text((x+2,y+S+2),os.path.basename(f)[:-8].replace('Ultimate_Animated_Character_Pack_-_Nov_','')[:24],fill='#ccc')
im.save(d+'.png')
