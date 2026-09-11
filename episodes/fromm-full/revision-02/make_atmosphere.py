"""Build nonrepeating room tone from measured quiet spectra, ducked through Fromm's runs."""
from pathlib import Path
import json
import numpy as np
from scipy.io import wavfile
from scipy.ndimage import gaussian_filter1d
from klassic.project import read_json,write_json,digest
from klassic.presentation import title_at,screen_time
b=Path('build/fromm-full-02');study=Path('build/fromm-revision-study');t=read_json(b/'timeline.json')
rate=48000;title_seconds=6.25;cut=title_at(t);total=t['duration']+title_seconds+40;n=int(round(total*rate))
g=np.load(study/'guest-noise-spectrum.npz');h=np.load(study/'host-noise-spectrum.npz');f=g['frequency'];extra=np.maximum(g['psd']-h['psd'],0)
if not extra.any():raise ValueError('Guest noise does not exceed the host spectrum; cannot derive an additive bed')
extra=gaussian_filter1d(extra,.6);extra[(f<90)|(f>6500)]=0
analysis=read_json(study/'noise-analysis.json');guest_db=analysis['guest']['quiet_rms_dbfs_percentiles'][3];host_db=analysis['host']['quiet_rms_dbfs_percentiles'][3]
additional_power=10**(guest_db/10)-10**(host_db/10)
if additional_power<=0:raise ValueError('No positive additional noise level was measured')
target=np.sqrt(additional_power);target_db=20*np.log10(target)
# Independent ten-second random blocks, with half-second equal-power overlaps.
rng=np.random.default_rng(19580525);length=rate*10;overlap=rate//2;hop=length-overlap
freq=np.fft.rfftfreq(length,1/rate);shape=np.sqrt(np.interp(freq,f,extra));shape/=max(shape)
window=np.ones(length);angle=np.linspace(0,np.pi/2,overlap);window[:overlap]=np.sin(angle);window[-overlap:]=np.cos(angle)
temporary=b/'atmosphere-buffer.npy';y=np.lib.format.open_memmap(temporary,mode='w+',dtype=np.float32,shape=(n,));y[:]=0
for start in range(0,n,hop):
 block=np.fft.irfft(np.fft.rfft(rng.standard_normal(length))*shape,n=length);block*=target/np.sqrt(np.mean(block*block));stop=min(n,start+length);y[start:stop]+=(block*window)[:stop-start].astype(np.float32)
# Merge adjacent guest chunks into sustained speaker runs, including their pauses.
runs=[]
for turn in t['turns']:
 if turn['speaker']!='guest':continue
 start=screen_time(turn['start'],cut,title_seconds);end=screen_time(turn['end']+turn['pause_after'],cut,title_seconds)
 if runs and abs(runs[-1][1]-start)<.002:runs[-1][1]=end
 else:runs.append([start,end])
env_rate=100;times=np.arange(int(np.ceil(total*env_rate))+1)/env_rate;presence=np.zeros(len(times))
for start,end in runs:
 local=np.minimum(np.clip((times-(start-.25))/.25,0,1),np.clip((end+.5-times)/.5,0,1));local=.5-.5*np.cos(np.pi*local);presence=np.maximum(presence,local)
gain=1-presence*(1-10**(-18/20))
for start in range(0,n,rate*10):
 stop=min(n,start+rate*10);at=np.arange(start,stop)/rate;envelope=np.interp(at,times,gain);envelope*=np.clip(at/.3,0,1)*np.clip((total-at)/.8,0,1);y[start:stop]*=envelope.astype(np.float32)
y.flush();wavfile.write(b/'atmosphere.wav',rate,y);del y;temporary.unlink()
report={'file':'atmosphere.wav','sha256':digest(b/'atmosphere.wav'),'duration_seconds':total,'additional_level_dbfs':float(target_db),'duck_db':18,'attack_seconds':.25,'release_seconds':.5,'guest_quiet_level_dbfs':guest_db,'host_quiet_level_dbfs':host_db,'seed':19580525,'method':'Difference of measured guest and host quiet PSDs; independently colored random blocks with equal-power joins; raised-cosine ducking throughout guest speaker runs. No speech copied and no repeating tape loop.'}
t['presentation']['atmosphere']=report;write_json(b/'timeline.json',t);write_json(b/'atmosphere.json',report);print(json.dumps(report,indent=2))
