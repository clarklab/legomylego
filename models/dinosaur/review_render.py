"""CPU-only orthographic mesh review, independent of the shared Blender renderer."""
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from brickkit.engine import Engine
from brickkit.project import Project

e = Engine()
p = Project("dinosaur")
m = p.build(e.catalog)
tri, colors = [], []
for item in m.flatten():
    mesh = e.geom.mesh(item.part)
    xyz = mesh.tris @ item.M[:3,:3].T + item.M[:3,3]
    tri.append(xyz)
    rgb = np.array([int(item.color.rgb.lstrip('#')[i:i+2],16) for i in (0,2,4)])
    colors.append(np.tile(rgb,(len(xyz),1)))
t = np.concatenate(tri)
c = np.concatenate(colors)
n = np.cross(t[:,1]-t[:,0], t[:,2]-t[:,0])
n /= np.maximum(np.linalg.norm(n,axis=1)[:,None],1e-9)
light=np.array([-.4,-.7,-.5]); light/=np.linalg.norm(light)
shade=.55+.45*np.abs(n@light)
c=np.clip(c*shade[:,None],0,255).astype(np.uint8)
out=p.out/'review'
out.mkdir(exist_ok=True)
for name,az,el in [('three_quarter',-35,16),('side',90,3)]:
    a,b=np.deg2rad([az,el])
    right=np.array([np.cos(a),0,np.sin(a)])
    up=np.array([-np.sin(a)*np.sin(b),-np.cos(b),np.cos(a)*np.sin(b)])
    toward=np.array([np.sin(a)*np.cos(b),-np.sin(b),-np.cos(a)*np.cos(b)])
    xy=t@np.column_stack((right,up))
    low=xy.min(axis=(0,1)); high=xy.max(axis=(0,1))
    size=1600; scale=1350/max(high-low)
    xy=(xy-(low+high)/2)*scale
    xy[:,:,1]*=-1
    xy+=size/2
    canvas=np.full((size,size,3),[241,240,235],dtype=np.uint8)
    zbuffer=np.full((size,size),-np.inf)
    depth=t@toward
    for i,vertices in enumerate(xy):
        xmin,ymin=np.maximum(np.floor(vertices.min(axis=0)).astype(int),0)
        xmax,ymax=np.minimum(np.ceil(vertices.max(axis=0)).astype(int),size-1)
        if xmax<xmin or ymax<ymin: continue
        x0,y0=vertices[0]; x1,y1=vertices[1]; x2,y2=vertices[2]
        den=(y1-y2)*(x0-x2)+(x2-x1)*(y0-y2)
        if abs(den)<1e-8: continue
        yy,xx=np.mgrid[ymin:ymax+1,xmin:xmax+1]
        a=((y1-y2)*(xx+.5-x2)+(x2-x1)*(yy+.5-y2))/den
        b=((y2-y0)*(xx+.5-x2)+(x0-x2)*(yy+.5-y2))/den
        cc=1-a-b
        z=a*depth[i,0]+b*depth[i,1]+cc*depth[i,2]
        old=zbuffer[ymin:ymax+1,xmin:xmax+1]
        mask=(a>=-1e-7)&(b>=-1e-7)&(cc>=-1e-7)&(z>old)
        old[mask]=z[mask]
        canvas[ymin:ymax+1,xmin:xmax+1][mask]=c[i]
    im=Image.fromarray(canvas)
    im.resize((1000,1000),Image.Resampling.LANCZOS).save(out/(name+'.png'))
    print(out/(name+'.png'))
