"""Compose only the canonical town static set with new, replayed local coordinate tracks."""
import hashlib,json,re,shutil,subprocess,sys,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"stage3d"))
from export_stage import actor,group,v,samples_block
OUT=HERE/"evidence"
def main():
    sample=json.loads((OUT/"native-samples.json").read_text());frames=sample["samples"];last=len(frames)-1
    cast=group("Cast","".join(actor(sample,i) for i in range(3)))
    source=group("Source","\n".join(f'custom string event_{i}_{j} = "{r["id"]} {r["request_sha256"]}"' for i,slot in enumerate(sample["slots"]) for j,r in enumerate(slot))+"\n")
    cam='def Camera "ReporterCamera" {\nfloat focalLength = 27\nfloat horizontalAperture = 30\nfloat verticalAperture = 16.875\n'
    cam+=samples_block("double3","xformOp:translate",[(row["frame"],v((row["actors"][0]["x"]+4.8,5.2,row["actors"][0]["z"]+7))) for row in frames])
    cam+='float xformOp:rotateY = 34.44\nfloat xformOp:rotateX = -28.20\nuniform token[] xformOpOrder = ["xformOp:translate","xformOp:rotateY","xformOp:rotateX"]\n}\n'
    header=f'#usda 1.0\n(\n defaultPrim = "Stage"\n upAxis = "Y"\n metersPerUnit = 1\n startTimeCode = 0\n endTimeCode = {last}\n framesPerSecond = 24\n timeCodesPerSecond = 24\n)\n'
    town='def Xform "MillCreek" (\n prepend references = @../../stage3d/rehearsal/another-tuesday.usda@</Stage/MillCreek>\n) {}\n'
    src=OUT/"free-953.usda";src.write_text(header+group("Stage",f'custom string sourceSHA256 = "{sample["sourceSha"]}"\n'+town+cast+source+cam))
    with tempfile.TemporaryDirectory() as temp:
        usdc=Path(temp)/"free-953.usdc";subprocess.run(["usdcat",str(src),"--flatten","-o",str(usdc)],check=True)
        target=Path(temp)/"free-953.usdz";subprocess.run(["usdzip","-a",str(usdc),str(target)],check=True,capture_output=True)
        valid=subprocess.run(["usdchecker",str(target)],capture_output=True,text=True,check=True)
        cooked=subprocess.check_output(["usdcat",str(target)],text=True)
        maxdiff=0;n=0
        for i,name in enumerate(("Phil","Rita","Larry")):
            part=cooked.split(f'def Xform "{name}"',1)[1].split('def Cube "Coat"',1)[0]
            values=re.search(r'double3 xformOp:translate\.timeSamples\s*=\s*\{([^}]+)\}',part)[1]
            vals={int(t):tuple(map(float,triple.split(','))) for t,triple in re.findall(r'(\d+):\s*\(([^)]+)\)',values)}
            assert len(vals)==len(frames)
            for row in frames:
                a=row["actors"][i];expect=(a["x"],0,a["z"]);error=max(abs(x-y) for x,y in zip(expect,vals[row["frame"]]))
                maxdiff=max(maxdiff,error);n+=1
        assert n==864 and maxdiff<.000006
        shutil.copyfile(target,OUT/target.name)
    report={"take":"free-953","source_sha256":sample["sourceSha"],"usd_sha256":hashlib.sha256((OUT/"free-953.usdz").read_bytes()).hexdigest(),
            "frame_count":len(frames),"actors":3,"translated_samples":n,"max_error_metres":maxdiff,"units_metres":1,"up":"Y","checker":valid.stdout.strip() or valid.stderr.strip()}
    (OUT/"native-verification.json").write_text(json.dumps(report,indent=2)+"\n");print(report)
if __name__=="__main__":main()
