"""Author the Fromm cutout masks and a reproducible performance on frozen audio."""
import json
import random
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter
from klassic.project import read_json, write_json, digest

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT/'assets/episodes/fromm-v3'
SIZE = (1448,1086)

# Traced stage silhouettes; the lower portion stays fixed beneath the waist.
HOST = [(69,593),(67,562),(72,533),(87,497),(111,454),(127,420),(144,402),
 (184,390),(233,380),(265,372),(272,339),(257,355),(245,358),(233,355),
 (226,354),(215,349),(205,351),(192,345),(184,334),(171,332),(164,325),
 (156,323),(146,309),(145,298),(135,293),(128,280),(126,266),(121,264),
 (118,253),(124,246),(117,238),(118,228),(124,224),(118,215),(108,216),
 (103,211),(110,206),(99,203),(99,197),(109,190),(120,190),(126,184),
 (139,184),(148,190),(161,188),(170,194),(173,200),(184,197),(193,201),
 (204,211),(216,208),(226,213),(232,218),(240,218),(241,198),(248,178),
 (260,158),(272,148),(263,151),(260,143),(264,133),(275,128),(265,125),
 (263,119),(270,110),(280,109),(287,105),(298,108),(307,102),(324,99),
 (335,104),(339,116),(349,124),(353,133),(351,138),(372,146),(390,163),
 (402,188),(408,215),(415,219),(422,214),(426,207),(439,204),(446,198),
 (449,184),(459,181),(469,184),(476,177),(488,176),(497,177),(505,172),
 (519,171),(528,177),(526,183),(514,187),(512,196),(504,207),(497,210),
 (496,220),(486,226),(484,239),(476,246),(470,257),(471,266),(462,276),
 (450,279),(449,291),(441,295),(436,308),(427,316),(417,327),(417,347),
 (395,372),(378,389),(395,400),(423,410),(438,423),(444,449),(467,482),
 (473,463),(473,446),(481,429),(497,424),(508,409),(519,412),(531,427),
 (554,417),(558,426),(539,434),(544,452),(539,476),(531,495),(526,515),
 (526,535),(514,563),(502,585),(481,591),(469,580),(490,620),(530,671),
 (454,740),(214,700),(214,642),(203,642),(199,627),(195,613),(177,604),
 (145,595)]
GUEST = [(886,582),(882,559),(886,538),(900,507),(910,488),(918,469),
 (941,451),(927,434),(931,426),(954,445),(970,448),(986,453),(995,467),
 (990,477),(998,484),(991,494),(983,497),(980,516),(975,523),(974,533),
 (988,529),(987,423),(1014,403),(1040,395),(1025,385),(1007,369),
 (991,346),(982,322),(984,299),(991,280),(991,251),(987,239),(1006,235),
 (1010,216),(1022,184),(1042,161),(1047,144),(1053,137),(1066,131),
 (1070,122),(1087,112),(1106,113),(1123,114),(1139,119),(1150,124),
 (1169,126),(1180,132),(1191,134),(1208,143),(1213,156),(1227,163),
 (1230,177),(1241,188),(1246,205),(1243,222),(1244,238),(1237,258),
 (1236,281),(1231,301),(1229,323),(1215,343),(1201,351),(1205,360),
 (1228,364),(1265,379),(1306,392),(1335,414),(1353,451),(1378,497),
 (1393,528),(1405,559),(1406,582),(1398,594),(1324,604),(1301,619),
 (1297,645),(1284,661),(1272,665),(1263,659),(1253,660),(1248,654),
 (1238,655),(1230,650),(1224,650),(1220,640),(1207,704),(1060,737),
 (945,699),(973,608),(978,588),(955,594),(933,590),(908,585)]


def polygon(points):
    mask = Image.new('L',(SIZE[0]*4,SIZE[1]*4))
    ImageDraw.Draw(mask).polygon([(x*4,y*4) for x,y in points],fill=255)
    return mask.resize(SIZE,Image.Resampling.LANCZOS)


def cutout(scene, clean, rough):
    """Refine the traced matte against the actual ink; no generated redrawing."""
    import cv2
    import numpy as np
    source=np.asarray(scene)
    difference=np.abs(source.astype('int16')-np.asarray(clean).astype('int16')).clip(0,255).astype('uint8')
    features=np.stack((source,source,difference),axis=2)
    inside=np.asarray(rough)>127
    dilated=cv2.dilate(inside.astype('uint8'),np.ones((51,51),'uint8'))>0
    eroded=cv2.erode(inside.astype('uint8'),np.ones((31,31),'uint8'))>0
    labels=np.full(source.shape,cv2.GC_BGD,'uint8')
    labels[dilated]=cv2.GC_PR_BGD
    labels[inside]=cv2.GC_PR_FGD
    labels[eroded]=cv2.GC_FGD
    cv2.grabCut(features,labels,None,np.zeros((1,65)),np.zeros((1,65)),5,cv2.GC_INIT_WITH_MASK)
    mask=((labels==cv2.GC_FGD)|(labels==cv2.GC_PR_FGD)).astype('uint8')*255
    # Fill enclosed holes in a connected character (same-gray regions aren't cutouts).
    contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    contours=[c for c in contours if cv2.contourArea(c)>1000]
    if len(contours)!=1:raise ValueError(f'Expected one connected character matte, found {len(contours)}')
    mask[:]=0;cv2.drawContours(mask,contours,-1,255,cv2.FILLED)
    # Preserve the rest-pose lower crop: only the upper body is animated.
    mask[690:]=np.asarray(rough)[690:]
    return Image.fromarray(mask).filter(ImageFilter.GaussianBlur(.45))


def hand_matte(scene, box):
    """Keep the original hand/cuff ink, excluding the adjacent chair upholstery."""
    import cv2
    import numpy as np
    region=np.asarray(scene.crop(box))
    threshold=(region>175).astype('uint8')*255
    contours,_=cv2.findContours(threshold,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    if max(cv2.contourArea(c) for c in contours)<500:raise ValueError('Hand/cuff matte has no usable connected region')
    contours=[c for c in contours if cv2.contourArea(c)>50]
    threshold[:]=0;cv2.drawContours(threshold,contours,-1,255,cv2.FILLED)
    local=Image.fromarray(threshold).filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(.4))
    mask=Image.new('L',SIZE);mask.paste(local,box[:2]);return mask


def performance(timeline):
    duration = timeline['duration']
    result = {'turns':[{k:t[k] for k in ('id','speaker','start','end')} for t in timeline['turns']], 'characters':{}}
    runs=[]
    for turn in timeline['turns']:
        if runs and runs[-1]['speaker']==turn['speaker']:
            runs[-1]['end']=turn['end']
        else:
            runs.append({'speaker':turn['speaker'],'start':turn['start'],'end':turn['end']})
    for index,speaker in enumerate(('host','guest')):
        rng=random.Random(1958+index)
        channels={name:{0.0:0.0,duration:0.0} for name in ('lean','free','cigarette','blink','gaze')}
        def key(name,at,value):
            if 0 <= at < duration: channels[name][round(at,6)]=value
        sign=1 if speaker=='host' else -1
        for run in runs:
            start,end=run['start'],run['end']
            length=end-start
            if length<4: continue
            active=run['speaker']==speaker
            key('lean',start,0)
            key('lean',start+min(2.3,length*.24),sign*(rng.uniform(1.4,2.7) if active else rng.uniform(-.9,.6)))
            if length>10:
                key('lean',start+length*.57,sign*rng.uniform(-1.3,-.4))
            key('lean',end-.3,0)
            if active:
                at=start+1.0
                while at+3.6<end:
                    strength=rng.uniform(.55,1)
                    for name,scale in [('free',1),('cigarette',.55)]:
                        for dt,value in [(0,0),(.8,.8),(1.5,1),(2.3,.65),(3.6,0)]:
                            key(name,at+dt,strength*scale*value)
                    at+=rng.uniform(8.5,14)
        # Blink schedules use separate seeds and do not restart on camera cuts.
        at=2.2+index*1.13
        while at+.25<duration:
            for dt,value in [(0,0),(2/24,1),(4/24,1),(6/24,0)]:key('blink',at+dt,value)
            at+=rng.uniform(3.4,6.4)
        if speaker=='host':
            by_id={t['id']:t for t in timeline['turns']}
            # Teaser, audience welcome, then look at Fromm for the first question.
            key('gaze',0,1)
            key('gaze',by_id['t004']['start']+7.0,1)
            key('gaze',by_id['t004']['start']+7.4,0)
            # Thank the guest first; address the audience for the closing argument.
            key('gaze',by_id['t118']['start']+3.6,0)
            key('gaze',by_id['t118']['start']+4.0,1)
            channels['gaze'][duration]=1
        result['characters'][speaker]={name:sorted(values.items()) for name,values in channels.items()}
    return result


def main():
    scene=Image.open(OUT/'neutral.png').convert('L')
    clean=Image.open(OUT/'clean-plate.png').convert('L')
    if clean.size!=SIZE: raise ValueError('Generated clean plate registration changed')
    background=scene.copy()
    for speaker,points in [('host',HOST),('guest',GUEST)]:
        mask=cutout(scene,clean,polygon(points))
        mask.save(OUT/f'{speaker}-mask.png')
        erase=mask.filter(ImageFilter.MaxFilter(9))
        # Leave the static lower legs intact instead of exposing a seam at the matte boundary.
        ImageDraw.Draw(erase).rectangle((0,688,SIZE[0],SIZE[1]),fill=0)
        background.paste(clean,(0,0),erase)
    background.save(OUT/'background.png')
    timeline=read_json(ROOT/'build/fromm-full-02/timeline.json')
    write_json(OUT/'performance.json',performance(timeline))
    spec={'version':1,'canvas':SIZE,'background':'background.png','performance':'performance.json','characters':{
        'host':{'mask':'host-mask.png','bounds':[32,55,610,766],'waist':[320,625],
                'joint_overlaps':[{'polygon':[(82,521),(141,512),(190,535),(237,562),(276,580),(256,619),(230,668),(215,642),(195,604),(138,583),(84,573)],'gray':36},
                                  {'polygon':[(439,494),(477,477),(506,511),(513,555),(489,586),(453,578),(432,547)],'gray':34}],
                'eyes':[{'polygon':[(330,262),(333,252),(341,243),(351,238),(360,238),(372,243),(380,252),(386,264),(383,276),(376,286),(365,293),(354,295),(344,291),(336,283),(331,273)],'lid_gray':216},
                        {'polygon':[(385,248),(392,241),(402,239),(412,241),(421,247),(426,259),(424,268),(418,276),(408,277),(391,280),(390,264)],'lid_gray':217}],
                'pupils':[{'rest':[383,267],'camera':[358,267],'radius':5,'white':240},
                          {'rest':[422,265],'camera':[403,263],'radius':4.5,'white':243}],
                'cigarette_tip':[554,421],
                'arms':{'free':{'elbow':[111,554],'wrist':[185,580],'joint_radius':38,'degrees':-18},
                        'cigarette':{'elbow':[475,563],'wrist':[501,490],'joint_radius':26,'degrees':6}}},
        'guest':{'mask':'guest-mask.png','bounds':[843,65,1440,770],'waist':[1150,628],
                 'joint_overlaps':[{'polygon':[(1279,524),(1379,518),(1399,551),(1388,576),(1332,585),(1302,602),(1281,632),(1265,673),(1225,700),(1214,662),(1222,615),(1212,581)],'gray':35},
                                   {'polygon':[(955,501),(982,506),(997,540),(977,580),(953,592),(918,589),(889,567),(909,544)],'gray':34}],
                 'eyes':[{'polygon':[(1008,250),(1012,245),(1020,241),(1030,242),(1040,245),(1046,250),(1030,266),(1020,265),(1013,261),(1009,256)],'lid_gray':197},
                         {'polygon':[(1076,263),(1080,257),(1088,253),(1101,253),(1113,257),(1122,263),(1126,271),(1122,277),(1112,280),(1099,280),(1088,277),(1080,271)],'lid_gray':197}], 'pupils':[],
                 'cigarette_tip':[930,430],
                 'arms':{'free':{'elbow':[1361,563],'wrist':[1289,605],'joint_radius':38,'degrees':18},
                         'cigarette':{'elbow':[920,577],'wrist':[934,516],'joint_radius':26,'degrees':-6}}}}}
    arm_shapes={
        'host':{'free':[(68,572),(72,550),(83,532),(109,525),(141,531),(165,543),(182,551),(199,557),(233,568),(252,589),(260,613),(257,638),(246,645),(222,647),(202,646),(195,622),(178,609),(149,599),(70,598)],
                'cigarette':[(442,540),(442,516),(463,480),(473,458),(471,440),(480,427),(498,423),(507,407),(522,410),(531,424),(556,413),(562,428),(543,437),(548,455),(540,479),(531,500),(530,532),(514,568),(496,587),(476,590),(455,574)]},
        'guest':{'free':[(1321,531),(1342,524),(1377,526),(1397,541),(1410,565),(1409,593),(1327,608),(1306,626),(1298,655),(1286,670),(1258,670),(1229,661),(1215,645),(1217,615),(1225,590),(1247,573),(1270,565),(1302,548)],
                 'cigarette':[(883,551),(891,531),(906,504),(910,483),(920,465),(939,451),(923,434),(929,422),(955,442),(972,444),(990,451),(996,469),(992,478),(1000,485),(991,499),(981,510),(978,530),(977,558),(965,588),(945,596),(915,592),(892,583)]}}
    for speaker,arms in arm_shapes.items():
        body_mask=Image.open(OUT/f'{speaker}-mask.png').convert('L')
        for name,points in arms.items():
            mask=ImageChops.multiply(polygon(points),body_mask)
            if name=='free':
                sleeve=([(68,572),(72,550),(83,532),(109,525),(141,531),(165,543),(183,551),
                         (167,553),(155,564),(149,579),(147,596),(70,598)] if speaker=='host' else
                        [(1321,531),(1342,524),(1377,526),(1397,541),(1410,565),(1405,593),
                         (1320,602),(1312,582),(1302,566),(1277,557),(1268,568)])
                box=(142,544,261,646) if speaker=='host' else (1215,552,1325,668)
                mask=ImageChops.lighter(ImageChops.multiply(polygon(sleeve),body_mask),hand_matte(scene,box))
            filename=f'{speaker}-{name}-arm.png';mask.save(OUT/filename)
            spec['characters'][speaker]['arms'][name]['mask']=filename
    write_json(OUT/'puppet.json',spec)
    rig=read_json(ROOT/'assets/episodes/fromm-v2/rig.json')
    rig['scene']='../fromm-v2/scene.png'
    # Sip is an authored full-frame cutaway; it is handled explicitly by the compositor.
    rig['poses']['host_sip']['scene']='../fromm-v2/host_sip.png'
    rig['puppet']='puppet.json'
    write_json(OUT/'rig.json',rig)
    write_json(OUT/'source.json',{'base_rig':'../fromm-v2/rig.json','base_scene_sha256':digest(ROOT/'assets/episodes/fromm-v2/scene.png'),
        'generation_mode':'built-in image_gen','clean_plate_sha256':digest(OUT/'clean-plate.png'),
        'notes':'Original artwork retained; generated empty stage. Native cutout masks, eyelid geometry, pupil layer and inverse mesh rig. Separate generated blink drawing rejected by image tool; no rejected artwork used.'})


if __name__=='__main__':main()
