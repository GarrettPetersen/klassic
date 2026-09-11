"""Inspect complete arm poses at the extremes of the authored body lean."""
from PIL import Image,ImageDraw,ImageFont
from render_film import BUILD,FilmFrames


def contact_sheets():
    comp=FilmFrames().comp;comp.width,comp.height=comp.scene.size;puppet=comp.puppet
    sheets={s:Image.new('RGB',(1950,1140),(60,60,60)) for s in ('host','guest')}
    free=['relaxed','turn','up','sweep','up','relaxed']
    far=['relaxed','up','down','sweep','down','relaxed']
    leans=[-1.8,0,1.8,-1.8,0,1.8]
    font=ImageFont.load_default(size=18)
    for i,pose in enumerate(far):
        state={'lean':leans[i],'blink':0,'gaze':0,'free':0,'cigarette':0,
               'free_pose':free[i],'cigarette_pose':pose}
        puppet.state=lambda speaker,at:state
        frame=comp.frame(2)
        for speaker,left in [('host',5),('guest',730)]:
            tile=frame.crop((left,350,left+720,730)).resize((650,343),Image.Resampling.LANCZOS).convert('RGB')
            xy=(i%3*650,i//3*570)
            sheets[speaker].paste(tile,xy)
            # A close view makes thumb roots, cuffs and ink legible in review.
            handbox=((490,405,660,640) if speaker=='host' else (830,395,1030,650))
            detail=frame.crop(handbox).resize((156,180),Image.Resampling.LANCZOS).convert('RGB')
            sheets[speaker].paste(detail,(xy[0]+14,xy[1]+374))
            ImageDraw.Draw(sheets[speaker]).text((xy[0]+182,xy[1]+390),
                f'Far: {pose}\nNear: {free[i]}\nLean: {leans[i]} degrees',font=font,fill='white')
    for speaker,sheet in sheets.items():sheet.save(BUILD/f'{speaker}-seam-review.png')


def verify_lap_ink():
    frames=FilmFrames();comp=frames.comp;comp.width,comp.height=comp.scene.size
    puppet=comp.puppet;counts={}
    for speaker in ('host','guest'):
        for at in (0,2,10,20,30,1559,1565):
            state=puppet.state(speaker,at)
            if state['cigarette_pose']!='relaxed' or state['free_pose']!='relaxed':
                raise ValueError('Opening or closing unexpectedly uses an offering gesture')
    for pose in ('relaxed','up','sweep','down'):
        for lean in (-1.8,0,1.8):
            state=dict(lean=lean,blink=0,gaze=0,free=0,cigarette=0,
                       free_pose='relaxed',cigarette_pose=pose)
            puppet.state=lambda speaker,at:state
            frame=comp.frame(2).convert('L')
            for speaker in ('host','guest'):
                layer=puppet.lap_fronts[speaker]
                roi=(440,545,488,605) if speaker=='host' else (973,610,1010,645)
                checked=0
                for y in range(roi[1],roi[3]):
                    for x in range(roi[0],roi[2]):
                        r,_,_,alpha=layer.getpixel((x,y))
                        if alpha==255 and r<12:
                            if frame.getpixel((x,y))!=r:
                                raise ValueError(f'Trouser contour lost: {speaker}/{pose}/{lean} at {x},{y}')
                            checked+=1
                if checked<=10:raise ValueError(f'No useful contour coverage for {speaker}')
                counts[f'{speaker}/{pose}/{lean}']=checked
    return counts


if __name__=='__main__':contact_sheets()
