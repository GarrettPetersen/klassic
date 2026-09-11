import json,subprocess
from pathlib import Path
import numpy as np
from scipy import signal
b=Path('build/fromm-full-01');out=Path('build/fromm-revision-study')
t=json.loads((b/'timeline.json').read_text()); rate=48000
raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(b/'preview.mp4'),'-vn','-ar',str(rate),'-ac','1','-f','f32le','-'])
x=np.frombuffer(raw,dtype='<f4')
results={}
for speaker in ['host','guest']:
 windows=[]
 for turn in t['turns']:
  if turn['speaker']!=speaker:continue
  for pause in turn['silences']:
   a=int((turn['start']+pause['start']+.05)*rate);z=int((turn['start']+pause['end']-.05)*rate)
   for j in range(a,z-4096,4096):
    y=x[j:j+4096];rms=float(np.sqrt(np.mean(y*y)))
    windows.append((rms,j))
 windows.sort()
 vals=np.array([r for r,j in windows]); print(speaker,len(vals), np.percentile(20*np.log10(np.maximum(vals,1e-12)),[0,10,25,50,75,90,100]))
 # Middle-to-upper quiet windows avoid near-digital silence, with no loud breath transients.
 chosen=windows[int(len(windows)*.4):int(len(windows)*.8)]
 spectra=[]
 for rms,j in chosen:
  f,p=signal.welch(x[j:j+4096],fs=rate,nperseg=4096);spectra.append(p)
 psd=np.median(spectra,axis=0);np.savez(out/f'{speaker}-noise-spectrum.npz',frequency=f,psd=psd)
 peaks,_=signal.find_peaks(10*np.log10(psd+1e-20),prominence=5)
 peaks=sorted(peaks,key=lambda i:psd[i],reverse=True)[:12]
 results[speaker]={'windows':len(windows),'quiet_rms_dbfs_percentiles':np.percentile(20*np.log10(np.maximum(vals,1e-12)),[10,25,50,75,90]).tolist(),'selected_windows':[{'start':j/rate,'rms_dbfs':20*np.log10(max(r,1e-12))} for r,j in chosen],'strongest_spectral_peaks_hz':[float(f[i]) for i in peaks]}
 print('peaks',results[speaker]['strongest_spectral_peaks_hz'])
(out/'noise-analysis.json').write_text(json.dumps(results,indent=2)+'\n')
