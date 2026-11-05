#!/usr/bin/env python3
"""Run the repository's isolated software suites; retain bounded per-suite evidence."""
import argparse,json,os,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
 result={'started':time.time(),'status':'running','hardware_verified':False,'real_email_verified':False,'suites':[],'coverage':'qa-prd-coverage.json'}
 def save():
  f=a.output/'regression-results.json';f.write_text(json.dumps(result,indent=2));os.chmod(f,0o644)
 save()
 commands=[('python',['python3','-m','unittest','discover','-s','tests','-v'])]
 commands += [(f.name,['node','--test',str(f.relative_to(ROOT))]) for f in sorted((ROOT/'tests').iterdir()) if f.suffix in ('.js','.cjs')]
 for name,cmd in commands:
  log=a.output/('regression-'+name+'.txt');started=time.time()
  with log.open('w') as out:
   try:r=subprocess.run(cmd,cwd=ROOT,stdout=out,stderr=subprocess.STDOUT,timeout=600);code=r.returncode
   except subprocess.TimeoutExpired:code=124
   except OSError as e:out.write(type(e).__name__);code=127
  os.chmod(log,0o644)
  result['suites'].append({'suite':name,'status':'passed' if code==0 else 'failed','exit_code':code,'seconds':round(time.time()-started,1),'log':log.name});save()
 result['status']='passed-software-suites' if all(s['exit_code']==0 for s in result['suites']) else 'findings';result['finished']=time.time();save()
if __name__=='__main__':main()
