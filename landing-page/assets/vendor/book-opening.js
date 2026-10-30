/* Soundbooki's small articulated book renderer. No external runtime/textures.
   Curved page surfaces and cover shells rotate about a shared 3D spine. */
(()=>{
  'use strict';
  const PI=Math.PI,pitch=48*PI/180,cp=Math.cos(pitch),sp=Math.sin(pitch);
  const clamp=x=>Math.max(0,Math.min(1,x)),smooth=x=>{x=clamp(x);return x*x*(3-2*x);};
  const mix=(a,b,t)=>a+(b-a)*t;
  function bezier(points,t){const m=1-t;return [0,1].map(k=>m*m*m*points[0][k]+3*m*m*t*points[1][k]+3*m*t*t*points[2][k]+t*t*t*points[3][k]);}
  const straight=(a,b)=>[a,[mix(a[0],b[0],1/3),mix(a[1],b[1],1/3)],[mix(a[0],b[0],2/3),mix(a[1],b[1],2/3)],b];
  function surface(top,bottom,side,zOffset=0){
    return (u,v)=>{const a=bezier(top,u),b=bezier(bottom,u),sx=mix(a[0],b[0],v),sy=mix(a[1],b[1],v),hingeY=mix(top[0][1],bottom[0][1],v);return [side*(sx-500),(hingeY-198)/cp,(hingeY-sy)/sp+zOffset];};
  }
  function polyline(points,t){for(let i=1;i<points.length;i++){if(t<=points[i][0]){const k=(t-points[i-1][0])/(points[i][0]-points[i-1][0]);return [mix(points[i-1][1],points[i][1],k),mix(points[i-1][2],points[i][2],k)];}}return points.at(-1).slice(1);}
  function cover(side){return (u,v)=>{const a=polyline([[0,500,232],[.102,532,218],[1,814,208]],u),b=polyline([[0,500,498],[.066,528,498],[.109,546,476],[1,924,496]],u),sx=mix(a[0],b[0],v),sy=mix(a[1],b[1],v),hingeY=mix(232,498,v);return [side*(sx-500),(sy-198-sp*20)/cp,-20];};}
  function normals(points,indices){
    const out=points.map(()=>[0,0,0]);
    for(let i=0;i<indices.length;i+=3){const [ia,ib,ic]=indices.slice(i,i+3),a=points[ia],b=points[ib],c=points[ic],u=b.map((n,k)=>n-a[k]),v=c.map((n,k)=>n-a[k]);const n=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]];for(const j of [ia,ib,ic])for(let k=0;k<3;k++)out[j][k]+=n[k];}
    return out.map(n=>{const length=Math.hypot(...n)||1;return n.map(x=>x/length);});
  }
  function geometry(fn,side,flatZ,thickness=3,nu=18,nv=5,bottomZ=null){
    const points=[],flat=[],indices=[],row=nu+1;
    const add=(p,z)=>{points.push(p);flat.push([p[0],p[1],z]);return points.length-1;};
    for(let face=0;face<2;face++){
      const start=points.length;
      for(let v=0;v<=nv;v++)for(let u=0;u<=nu;u++){const p=fn(u/nu,v/nv);add([p[0],p[1],(face&&bottomZ!==null?bottomZ:p[2]-face*thickness)],flatZ-face*thickness);}
      for(let v=0;v<nv;v++)for(let u=0;u<nu;u++){const a=start+v*row+u,b=a+row;const tri=[a,a+1,b,a+1,b+1,b];if(face)for(let k=0;k<tri.length;k+=3)[tri[k+1],tri[k+2]]=[tri[k+2],tri[k+1]];indices.push(...tri);}
    }
    const boundary=[];for(let u=0;u<=nu;u++)boundary.push(u);for(let v=1;v<=nv;v++)boundary.push(v*row+nu);for(let u=nu-1;u>=0;u--)boundary.push(nv*row+u);for(let v=nv-1;v>0;v--)boundary.push(v*row);
    for(let i=0;i<boundary.length;i++){const ia=boundary[i],ib=boundary[(i+1)%boundary.length],a=points[ia],b=points[ib],j=points.length,bottomStart=row*(nv+1);add([...a],flatZ);add([...b],flatZ);add([...points[bottomStart+ib]],flatZ-thickness);add([...points[bottomStart+ia]],flatZ-thickness);indices.push(j,j+2,j+1,j,j+3,j+2);}
    if(side<0)for(let i=0;i<indices.length;i+=3)[indices[i+1],indices[i+2]]=[indices[i+2],indices[i+1]];
    const n=normals(points,indices),f=normals(flat,indices),data=[];
    points.forEach((p,i)=>data.push(...p,...n[i],flat[i][2],...f[i]));
    return {data:new Float32Array(data),indices:new Uint16Array(indices)};
  }
  function strokes(fn,flatZ,withInk){
    const data=[],indices=[];
    function line(uv,closed=false){const first=data.length/10;uv.forEach(([u,v])=>{const p=fn(u,v);data.push(p[0],p[1],p[2]+2.5,0,0,1,flatZ+2.5,0,0,1);});for(let i=0;i<uv.length-1;i++)indices.push(first+i,first+i+1);if(closed)indices.push(first+uv.length-1,first);}
    const edge=[];for(let i=0;i<=18;i++)edge.push([i/18,0]);for(let i=1;i<=5;i++)edge.push([1,i/5]);for(let i=17;i>=0;i--)edge.push([i/18,1]);for(let i=4;i>0;i--)edge.push([0,i/5]);line(edge,true);
    if(withInk)for(let row=0;row<5;row++)line(Array.from({length:15},(_,i)=>[.1+i/14*.78,.25+row*.12]));
    return {data:new Float32Array(data),indices:new Uint16Array(indices)};
  }
  function mount(host,{lowPower=false,background=null}={}){
    const canvas=document.createElement('canvas');canvas.setAttribute('aria-hidden','true');
    const gl=canvas.getContext('webgl',{alpha:true,antialias:true,premultipliedAlpha:true,powerPreference:'low-power',depth:true,stencil:false,preserveDrawingBuffer:false});
    if(!gl){host.dataset.model='static-fallback';return null;}
    const resources=[];
    function shader(type,source){const s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS)){gl.deleteShader(s);throw Error('Book shader unavailable');}resources.push(['shader',s]);return s;}
    try{
      const vertex=shader(gl.VERTEX_SHADER,`
        precision highp float;
        attribute vec3 a_position;attribute vec3 a_normal;attribute float a_flatZ;attribute vec3 a_flatNormal;
        uniform float u_angle,u_curve,u_yaw,u_open;
        varying vec3 v_normal;varying vec3 v_position;
        void main(){
          vec3 p=vec3(a_position.xy,mix(a_flatZ,a_position.z,u_curve));
          vec3 n=normalize(mix(a_flatNormal,a_normal,u_curve));
          float c=cos(u_angle),s=sin(u_angle);
          p=vec3(c*p.x+s*p.z,p.y,-s*p.x+c*p.z);
          n=vec3(c*n.x+s*n.z,n.y,-s*n.x+c*n.z);
          v_position=p;v_normal=n;
          float cy=cos(u_yaw),sy=sin(u_yaw);
          float x=cy*p.x+sy*p.z,z=-sy*p.x+cy*p.z;
          float y=${cp.toFixed(8)}*p.y-${sp.toFixed(8)}*z;
          float depth=${sp.toFixed(8)}*p.y+${cp.toFixed(8)}*z;
          vec2 pixel=vec2(500.0+x+50.0*(1.0-u_open),198.0+y+50.0*(1.0-u_open));
          gl_Position=vec4(pixel.x/500.0-1.0,1.0-pixel.y/290.0,-depth/1600.0,1.0);
        }`);
      const fragment=shader(gl.FRAGMENT_SHADER,`
        precision mediump float;
        uniform vec3 u_color;uniform float u_alpha,u_unlit,u_shine;
        varying vec3 v_normal;varying vec3 v_position;
        void main(){
          if(u_unlit>.5){gl_FragColor=vec4(u_color,u_alpha);return;}
          vec3 n=normalize(gl_FrontFacing?v_normal:-v_normal);
          vec3 light=normalize(vec3(-.45,-.55,1.0));
          vec3 fill=normalize(vec3(.7,.1,.6));
          vec3 eye=normalize(vec3(100.0,600.0,950.0)-v_position);
          float diffuse=max(dot(n,light),0.0),rim=max(dot(n,fill),0.0);
          float spec=pow(max(dot(n,normalize(light+eye)),0.0),45.0)*u_shine;
          vec3 color=u_color*(.46+.55*diffuse+.22*rim)+vec3(.57,.79,1.0)*spec;
          gl_FragColor=vec4(color,u_alpha);
        }`);
      const program=gl.createProgram();gl.attachShader(program,vertex);gl.attachShader(program,fragment);gl.linkProgram(program);if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw Error('Book program unavailable');resources.push(['program',program]);gl.useProgram(program);
      const attrs=['a_position','a_normal','a_flatZ','a_flatNormal'].map(x=>gl.getAttribLocation(program,x));
      const uniforms=Object.fromEntries(['angle','curve','yaw','open','color','alpha','unlit','shine'].map(x=>[x,gl.getUniformLocation(program,'u_'+x)]));
      const faces=[],lines=[];
      function upload(g){const vertex=gl.createBuffer(),index=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,vertex);gl.bufferData(gl.ARRAY_BUFFER,g.data,gl.STATIC_DRAW);gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,index);gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,g.indices,gl.STATIC_DRAW);resources.push(['buffer',vertex],['buffer',index]);return {vertex,index,count:g.indices.length};}
      function layer(fn,side,flatZ,thickness,lag,color,shine,ink=false,bottomZ=null){
        const face={...upload(geometry(fn,side,flatZ,thickness,lowPower?12:18,lowPower?4:5,bottomZ)),side,lag,color,shine};faces.push(face);
        lines.push({...upload(strokes(fn,flatZ,ink)),side,lag,color:ink?[.32,.29,.24]:(flatZ<0?[.31,.32,.31]:[.66,.62,.54]),shine:0});
      }
      for(const side of [-1,1]){
        layer(cover(side),side,-20,6,0,[.11,.13,.14],.012);
        const stack=[
          [[502,222],[790,196],[[502,468],[616,434],[750,440],[882,468]],4,-11],
          [[502,214],[776,178],[[502,462],[612,418],[738,422],[864,450]],9,-7],
          [[502,206],[762,160],[[502,456],[608,402],[728,402],[846,430]],14,-3]
        ];
        stack.forEach(([a,b,bottom,z,offset],i)=>layer(surface(straight(a,b),bottom,side,offset),side,z,i===0?12:3,.035+i*.025,[.69+i*.016,.66+i*.016,.59+i*.016],.006,false,i===0?-16:null));
        layer(surface([[500,198],[558,106],[668,96],[754,134]],[[500,458],[594,376],[722,366],[834,412]],side),side,19,4,.12,[.79,.76,.69],.01,true);
      }
      const spine=geometry((u,v)=>[-4+8*u,v*448,5],1,5,24,1,1);
      faces.push({...upload(spine),side:0,lag:0,color:[.065,.07,.07],shine:.004});
      gl.enable(gl.DEPTH_TEST);gl.depthFunc(gl.LEQUAL);gl.frontFace(gl.CW);gl.clearColor(...(background||[0,0,0,0]));host.append(canvas);host.classList.add('has-book-model');host.dataset.model='articulated-3d';host.dataset.triangles=String(faces.reduce((n,item)=>n+item.count/3,0));
      let width=0,height=0,current=0,disposed=false,lastRender=-Infinity;
      const ratio=Math.min(devicePixelRatio||1,lowPower?1.2:1.35);
      function bind(item){gl.bindBuffer(gl.ARRAY_BUFFER,item.vertex);gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,item.index);const sizes=[3,3,1,3],offsets=[0,12,24,28];attrs.forEach((a,i)=>{gl.enableVertexAttribArray(a);gl.vertexAttribPointer(a,sizes[i],gl.FLOAT,false,40,offsets[i]);});}
      function drawItem(item,p,isLine){
        const local=smooth((p-item.lag)/(1-item.lag));
        gl.uniform1f(uniforms.angle,-item.side*86*PI/180*(1-local));
        gl.uniform1f(uniforms.curve,smooth(local));gl.uniform3fv(uniforms.color,item.color);gl.uniform1f(uniforms.alpha,isLine?.3:1);gl.uniform1f(uniforms.unlit,isLine?1:0);gl.uniform1f(uniforms.shine,item.shine);
        bind(item);gl.drawElements(isLine?gl.LINES:gl.TRIANGLES,item.count,gl.UNSIGNED_SHORT,0);
      }
      function draw(p=current){
        if(disposed||gl.isContextLost())return;
        const now=performance.now();if(lowPower&&p>0&&p<1&&now-lastRender<28)return;lastRender=now;current=clamp(p);
        const w=Math.round(host.clientWidth*ratio),h=Math.round(host.clientHeight*ratio);if(!w||!h)return;
        if(w!==width||h!==height){width=w;height=h;canvas.width=w;canvas.height=h;gl.viewport(0,0,w,h);}
        gl.useProgram(program);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);gl.uniform1f(uniforms.open,current);gl.uniform1f(uniforms.yaw,-.27*(1-current));
        gl.disable(gl.BLEND);gl.depthMask(true);gl.enable(gl.POLYGON_OFFSET_FILL);gl.polygonOffset(1,1);for(const item of faces)drawItem(item,current,false);gl.disable(gl.POLYGON_OFFSET_FILL);
        gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);gl.depthMask(false);for(const item of lines)drawItem(item,current,true);gl.depthMask(true);
      }
      canvas.addEventListener('webglcontextlost',event=>{event.preventDefault();host.classList.remove('has-book-model');host.dataset.model='static-fallback';});
      const observer=typeof ResizeObserver==='function'?new ResizeObserver(()=>draw()):null;observer?.observe(host);draw(0);
      return {draw,destroy(){disposed=true;observer?.disconnect();for(const [kind,r] of resources){if(kind==='buffer')gl.deleteBuffer(r);else if(kind==='shader')gl.deleteShader(r);else gl.deleteProgram(r);}host.classList.remove('has-book-model');canvas.remove();}};
    }catch{for(const [kind,r] of resources){if(kind==='buffer')gl.deleteBuffer(r);else if(kind==='shader')gl.deleteShader(r);else gl.deleteProgram(r);}canvas.remove();return null;}
  }
  window.SoundbookiBookOpening={mount};
})();
