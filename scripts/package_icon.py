"""Package PNG icon representations as ICNS without a silent old-icon fallback."""
from pathlib import Path
import struct
import sys

def package(source,destination):
    source=Path(source);destination=Path(destination)
    representations=[('icp4','icon_16x16.png',16),('icp5','icon_32x32.png',32),('icp6','icon_32x32@2x.png',64),('ic07','icon_128x128.png',128),('ic08','icon_256x256.png',256),('ic09','icon_512x512.png',512),('ic10','icon_512x512@2x.png',1024),('ic11','icon_16x16@2x.png',32),('ic12','icon_32x32@2x.png',64),('ic13','icon_128x128@2x.png',256),('ic14','icon_256x256@2x.png',512)]
    chunks=[]
    for code,name,size in representations:
        data=(source/name).read_bytes()
        if data[:8]!=b'\x89PNG\r\n\x1a\n' or struct.unpack('>II',data[16:24])!=(size,size):raise ValueError('Invalid icon representation: '+name)
        chunks.append(code.encode()+struct.pack('>I',len(data)+8)+data)
    body=b''.join(chunks);destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_bytes(b'icns'+struct.pack('>I',len(body)+8)+body)
    print('Updated ICNS with 11 validated sizes, 16–1024 px.')

if __name__=='__main__':package(*sys.argv[1:])
