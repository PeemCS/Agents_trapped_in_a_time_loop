"use strict";
window.TownStageAssets=(()=>{
  function inspect(bytes){
    const d=new DataView(bytes);
    if(d.byteLength<24||d.getUint32(0,true)!==0x46546c67||d.getUint32(4,true)!==2||d.getUint32(8,true)!==d.byteLength)
      throw new Error("Choose a binary glTF 2.0 file (.glb).");
    const size=d.getUint32(12,true);
    if(d.getUint32(16,true)!==0x4e4f534a||size>d.byteLength-20)throw new Error("The GLB JSON chunk is invalid.");
    let doc;
    try{doc=JSON.parse(new TextDecoder().decode(new Uint8Array(bytes,20,size)).trim());}
    catch{throw new Error("The GLB scene description is invalid.");}
    if(!Array.isArray(doc.meshes)||!doc.meshes.length)throw new Error("This GLB contains no character mesh.");
    for(const entry of [...(doc.images||[]),...(doc.buffers||[])]){
      if(entry.uri && !entry.uri.startsWith("data:"))throw new Error("Embed textures and buffers in the GLB for offline use.");
    }
    const externalDecoder=(doc.extensionsRequired||[]).find(k=>["KHR_draco_mesh_compression","KHR_texture_basisu","EXT_meshopt_compression"].includes(k));
    if(externalDecoder)throw new Error("Export an uncompressed GLB for this offline player ("+externalDecoder+").");
  }
  async function parse(file,{height=1.3,yaw=0}={}){
    if(!file||typeof file.arrayBuffer!=="function")throw new TypeError("Choose a local GLB file.");
    if(file.size>64*1024*1024)throw new RangeError("Choose a GLB under 64 MiB.");
    if(!Number.isFinite(height)||height<.25||height>3.5||!Number.isFinite(yaw))throw new RangeError("Invalid artist scale or heading.");
    const bytes=await file.arrayBuffer();inspect(bytes);
    const T=window.THREE,manager=new T.LoadingManager();
    manager.setURLModifier(url=>{
      if(url.startsWith("blob:")||url.startsWith("data:"))return url;
      throw new Error("This asset references an external resource.");
    });
    const model=await new Promise((resolve,reject)=>new TownGLTF.GLTFLoader(manager).parse(bytes,"",resolve,reject));
    const carrier=new T.Group(),orient=new T.Group();carrier.add(orient);orient.add(model.scene);orient.rotation.y=yaw*Math.PI/180;
    model.scene.updateMatrixWorld(true);
    const bounds=new T.Box3().setFromObject(model.scene),size=bounds.getSize(new T.Vector3()),center=bounds.getCenter(new T.Vector3());
    const dispose=()=>{
      const geometries=new Set(),materials=new Set(),textures=new Set();
      model.scene.traverse(o=>{if(o.geometry)geometries.add(o.geometry);for(const m of Array.isArray(o.material)?o.material:o.material?[o.material]:[])materials.add(m);});
      for(const m of materials)for(const v of Object.values(m))if(v?.isTexture)textures.add(v);
      textures.forEach(t=>{t.dispose();if(typeof t.image?.close==="function")t.image.close();});
      materials.forEach(m=>m.dispose());geometries.forEach(g=>g.dispose());carrier.removeFromParent();
    };
    if(!(size.y>.0001)||!Number.isFinite(size.y)){dispose();throw new Error("The mesh needs a finite standing height.");}
    const scale=height/size.y;
    // Preserve the artist's root transform beneath a normalization parent. The native
    // role transform remains the authoritative world-space location.
    model.scene.position.sub(new T.Vector3(center.x,bounds.min.y,center.z));orient.scale.setScalar(scale);
    model.scene.traverse(o=>{if(o.isMesh){o.castShadow=true;o.receiveShadow=true;}});
    const mixer=new T.AnimationMixer(model.scene),clips=model.animations||[];
    const byName=(re)=>clips.find(c=>re.test(c.name));let active=null;
    const animations={walk:byName(/walk|locomotion/i),idle:byName(/idle|stand|rest/i),call:byName(/phone|call/i),
      film:byName(/film|camera/i),mark:byName(/write|mark/i),broadcast:byName(/switch|broadcast/i),talk:byName(/talk|speak/i)};
    function pose(p,t){
      const action=p.action||"";
      const cue=p.moving?"walk":/call_/.test(action)?"call":/film_/.test(action)?"film":/pencil_mark/.test(action)?"mark":
        /patch_|bulletin/.test(action)?"broadcast":/talk_to_/.test(action)?"talk":"idle";
      const clip=animations[cue]||animations.idle;
      if(clip!==active){mixer.stopAllAction();active=clip;if(clip)mixer.clipAction(clip).reset().play();}
      if(clip&&clip.duration>0)mixer.setTime(Math.max(0,t)%clip.duration);
    }
    return {carrier,pose,get activeClip(){return active?.name||null;},name:String(file.name||"Local GLB").slice(0,140),clipNames:clips.map(c=>c.name),
      dispose(){mixer.stopAllAction();mixer.uncacheRoot(model.scene);dispose();}};
  }
  return {parse};
})();
