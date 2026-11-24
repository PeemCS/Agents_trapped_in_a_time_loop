"""Compare archived same-base PEFT LoRA updates using NumPy on CPU."""
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import struct

import numpy as np

HERE = Path(__file__).resolve().parent
ARCHIVE = HERE.parent / 'results'
KEY = re.compile(r'base_model\.model\.model\.layers\.(\d+)\.(?:mlp|self_attn)\.(\w+)\.lora_([AB])\.weight$')

def load_adapter(folder):
    config = json.loads((folder / 'adapter_config.json').read_text())
    receipt = json.loads((folder.parent / 'training.json').read_text())
    assert config['peft_type'] == 'LORA'
    assert not any(config[k] for k in ('use_rslora', 'use_dora', 'fan_in_fan_out', 'rank_pattern', 'alpha_pattern', 'modules_to_save', 'lora_bias'))
    assert config['bias'] == 'none'
    data = (folder / 'adapter_model.safetensors').read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    assert digest == receipt['adapter_sha256']
    header_bytes = struct.unpack('<Q', data[:8])[0]
    header = json.loads(data[8:8 + header_bytes])
    start = 8 + header_bytes
    factors = {}
    for name, tensor in header.items():
        if name == '__metadata__':
            continue
        match = KEY.fullmatch(name)
        assert match and tensor['dtype'] == 'F32', name
        layer, target, side = match.groups()
        lo, hi = tensor['data_offsets']
        shape = tensor['shape']
        assert hi - lo == 4 * math.prod(shape) and start + hi <= len(data)
        arr = np.frombuffer(data, dtype='<f4', count=math.prod(shape), offset=start+lo).reshape(shape)
        factors.setdefault((int(layer), target), {})[side] = arr
    for f in factors.values():
        assert f.keys() == {'A','B'} and f['A'].shape[0] == f['B'].shape[1] == config['r']
    return factors, config['lora_alpha']/config['r'], digest, config

def inner(x, y):
    """x and y are (scaled B, A) pairs for matching rectangular linear operators."""
    b1, a1 = x
    b2, a2 = y
    return float(np.sum((b1.T @ b2) * (a1 @ a2.T)))

def spectrum(x):
    b, a = x
    rb = np.linalg.qr(b, mode='r')
    ra = np.linalg.qr(a.T, mode='r')
    return np.linalg.svd(rb @ ra.T, compute_uv=False)

def effective(sigma):
    p = sigma[sigma>0] / sigma.sum()
    return float(np.exp(-np.dot(p,np.log(p))))

def spectrum_info(sig):
    e = sig**2
    return dict(entropy_effective_rank=effective(sig),stable_rank=float(e.sum()/e.max()),
                spectral_norm=float(sig.max()),top_mode_energy_share=float(e.max()/e.sum()),
                modes_for_90pct_energy=int(np.searchsorted(np.cumsum(np.sort(e)[::-1]),.90*e.sum())+1))

def measures(first, second):
    e1,e2,dot = inner(first,first),inner(second,second),inner(first,second)
    diff = (np.concatenate([second[0],-first[0]],axis=1), np.concatenate([second[1],first[1]],axis=0))
    s1,s2,sd = spectrum(first),spectrum(second),spectrum(diff)
    assert np.allclose([s1@s1,s2@s2,sd@sd],[e1,e2,e1+e2-2*dot],rtol=1e-10,atol=1e-13)
    return e1,e2,dot,s1,s2,sd

def aggregate(rows):
    e1=sum(r['energy1'] for r in rows)
    e2=sum(r['energy2'] for r in rows)
    cross=sum(r['dot'] for r in rows)
    d=e1+e2-2*cross
    n=sum(r['rows']*r['cols'] for r in rows)
    return dict(matrices=len(rows),represented_weight_entries=n,rms_entry_difference=math.sqrt(d/n),
                v2_projection_coefficient_on_v1=cross/e1,v2_projected_energy_fraction=cross**2/(e1*e2),
                frobenius_v1=math.sqrt(e1),frobenius_v2=math.sqrt(e2),
                cosine=cross/math.sqrt(e1*e2),difference_frobenius=math.sqrt(d),
                difference_relative_to_v1=math.sqrt(d/e1),energy_v1=e1,energy_v2=e2,difference_energy=d,
                median_matrix_entropy_rank_v1=float(np.median([effective(r['s1']) for r in rows])),
                median_matrix_entropy_rank_v2=float(np.median([effective(r['s2']) for r in rows])),
                median_difference_entropy_rank=float(np.median([effective(r['sd']) for r in rows])))

def validate(first,second):
    # A block of an actual checkpoint update: both dimensions exceed the LoRA rank.
    one=(first[0][:41],first[1][:,:53])
    two=(second[0][:41],second[1][:,:53])
    dense1,dense2 = (b@a for b,a in (one,two))
    e1,e2,dot,s1,s2,sd=measures(one,two)
    correct=np.array([np.sum(dense1*dense1),np.sum(dense2*dense2),np.sum(dense1*dense2)])
    max_gram_error=float(np.max(np.abs(correct-[e1,e2,dot])))
    spectral_errors=[np.max(np.abs(np.linalg.svd(mat,compute_uv=False)[:len(s)]-s)) for s,mat in
                     ((s1,dense1),(s2,dense2),(sd,dense2-dense1))]
    # A nonorthogonal change of latent coordinates alters factors and leaves BA fixed.
    r=one[0].shape[1]
    gauge=np.diag(np.geomspace(.5,2,r))+np.diag(np.full(r-1,.3),1)
    transformed=(one[0]@gauge,np.linalg.solve(gauge,one[1]))
    gauge_dense_error=float(np.max(np.abs(transformed[0]@transformed[1]-dense1)))
    gauge_inner_error=abs(inner(transformed,two)-dot)
    err=max([max_gram_error,gauge_dense_error,gauge_inner_error,*spectral_errors])
    assert err<1e-10
    return dict(explicit_block_shape=list(dense1.shape),max_abs_gram_vs_explicit=max_gram_error,
                max_abs_spectrum_vs_explicit=float(max(spectral_errors)),nonorthogonal_gauge_condition=float(np.linalg.cond(gauge)),
                max_abs_gauge_dense_difference=gauge_dense_error,max_abs_gauge_cross_inner_difference=gauge_inner_error)

def main():
    f1,scale1,sha1,c1=load_adapter(ARCHIVE/'adapter')
    f2,scale2,sha2,c2=load_adapter(ARCHIVE/'v2/adapter')
    assert f1.keys()==f2.keys() and c1['revision']==c2['revision'] and c1['base_model_name_or_path']==c2['base_model_name_or_path']
    rows=[]
    verification=None
    for layer,target in sorted(f1):
        fx,fy=f1[layer,target],f2[layer,target]
        x=(np.asarray(fx['B'],dtype=np.float64)*scale1,np.asarray(fx['A'],dtype=np.float64))
        y=(np.asarray(fy['B'],dtype=np.float64)*scale2,np.asarray(fy['A'],dtype=np.float64))
        assert x[0].shape==y[0].shape and x[1].shape==y[1].shape
        if verification is None:
            verification=validate(x,y)
            verification.update(layer=layer,target=target)
        e1,e2,cross,s1,s2,sd=measures(x,y)
        rows.append(dict(layer=layer,target=target,rows=x[0].shape[0],cols=x[1].shape[1],energy1=e1,energy2=e2,dot=cross,s1=s1,s2=s2,sd=sd))
    assert len(rows)==168
    # An independent full-matrix check uses matrix multiplication directly.
    fx,fy=f1[11,'k_proj'],f2[11,'k_proj']
    mat1=scale1*(fx['B'].astype('float64')@fx['A'].astype('float64'))
    mat2=scale2*(fy['B'].astype('float64')@fy['A'].astype('float64'))
    exact=np.array([np.vdot(mat1,mat1),np.vdot(mat2,mat2),np.vdot(mat1,mat2)])
    row=next(r for r in rows if (r['layer'],r['target'])==(11,'k_proj'))
    grams=np.array([row['energy1'],row['energy2'],row['dot']])
    full_error=float(np.max(np.abs(exact-grams)/np.abs(exact)))
    assert full_error<1e-10
    verification['full_explicit_check']=dict(layer=11,target='k_proj',shape=list(mat1.shape),
                                              max_relative_inner_product_error=full_error)
    total=aggregate(rows)
    def group(key):
        result={}
        for name in sorted({r[key] for r in rows}):
            ag=aggregate([r for r in rows if r[key]==name])
            ag.update(share_v1_energy=ag['energy_v1']/total['energy_v1'],share_v2_energy=ag['energy_v2']/total['energy_v2'],
                      share_difference_energy=ag['difference_energy']/total['difference_energy'])
            result[str(name)]=ag
        return result
    layers,targets=group('layer'),group('target')
    matrix_rows=[]
    for row in rows:
        output={k:row[k] for k in ['layer','target','rows','cols']}
        ag=aggregate([row])
        output.update({k:ag[k] for k in ('frobenius_v1','frobenius_v2','cosine','difference_frobenius')})
        output['share_difference_energy']=ag['difference_energy']/total['difference_energy']
        for suffix,key in [('v1','s1'),('v2','s2'),('difference','sd')]:
            output.update({k+'_'+suffix:v for k,v in spectrum_info(row[key]).items()})
        matrix_rows.append(output)
    with (HERE/'matrices.csv').open('w',newline='') as out:
        writer=csv.DictWriter(out,fieldnames=list(matrix_rows[0]))
        writer.writeheader()
        writer.writerows(matrix_rows)
    pairs=[r['cosine'] for r in matrix_rows]
    summary=dict(base=c1['base_model_name_or_path'],revision=c1['revision'],input_sha256=dict(v1=sha1,v2=sha2),
                 scale=dict(v1=scale1,v2=scale2),numpy=np.__version__,dtype='float64',global_update=total,per_target=targets,
                 per_layer=layers,matrix_cosine=dict(min=min(pairs),median=float(np.median(pairs)),max=max(pairs)),
                 largest_layer_norms={key:sorted(layers,key=lambda n:layers[n][key],reverse=True)[:5] for key in ('frobenius_v1','frobenius_v2','difference_frobenius')},
                 validation=verification)
    (HERE/'comparison.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:summary[k] for k in ('global_update','matrix_cosine','largest_layer_norms','validation')},indent=2))

if __name__=='__main__':
    main()
