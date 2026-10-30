import * as THREE from 'three';
import { CSS3DRenderer, CSS3DObject } from 'three/addons/renderers/CSS3DRenderer.js';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';

const PW = 3.2, PH = 4.64, BOTTOM = -.18, TOP = .19;
const clamp = n => Math.max(0, Math.min(1, n));
const smooth = n => { n = clamp(n); return n * n * (3 - 2 * n); };
const lerp = (a, b, n) => a + (b - a) * n;

// Local, deterministic textile and paper microstructure. No remote textures.
function textureCanvas(width, height, draw) {
  const canvas = document.createElement('canvas'); canvas.width = width; canvas.height = height;
  draw(canvas.getContext('2d'), width, height);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace; texture.anisotropy = 4;
  return texture;
}
function clothTexture() {
  return textureCanvas(512, 512, (ctx, w, h) => {
    const pixels = ctx.createImageData(w, h);
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      const i = (y * w + x) * 4;
      const weave = (x % 4 === 0 ? -7 : x % 4 === 1 ? 3 : 0) + (y % 4 === 0 ? 5 : y % 4 === 1 ? -3 : 0);
      const grain = ((x * 17 + y * 31) % 19 - 9) * .25;
      pixels.data[i] = 49 + weave + grain; pixels.data[i + 1] = 86 + weave + grain; pixels.data[i + 2] = 107 + weave + grain; pixels.data[i + 3] = 255;
    }
    ctx.putImageData(pixels, 0, 0);
  });
}
function paperTexture(edge = false) {
  return textureCanvas(256, 512, (ctx, w, h) => {
    const pixels = ctx.createImageData(w, h), base = edge ? [228,224,214] : [244,241,232];
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      const i = (y * w + x) * 4, grain = edge ? (y % 4 === 0 ? -20 : 2) : ((x + y * 3) % 7 - 3) * .45;
      pixels.data[i] = base[0] + grain; pixels.data[i + 1] = base[1] + grain; pixels.data[i + 2] = base[2] + grain; pixels.data[i + 3] = 255;
    }
    ctx.putImageData(pixels, 0, 0);
  });
}
function shadowTexture() {
  return textureCanvas(512, 512, (ctx, w, h) => {
    const gradient = ctx.createRadialGradient(w / 2, h / 2, 10, w / 2, h / 2, w / 2);
    gradient.addColorStop(0, 'rgba(21,34,39,.3)'); gradient.addColorStop(.4, 'rgba(21,34,39,.13)'); gradient.addColorStop(1, 'rgba(21,34,39,0)');
    ctx.fillStyle = gradient; ctx.fillRect(0, 0, w, h);
  });
}
function paperGeometry(side = 1) {
  const geometry = new THREE.PlaneGeometry(PW, PH, 48, 4);
  const positions = geometry.attributes.position;
  for (let i = 0; i < positions.count; i++) {
    const u = (positions.getX(i) + PW / 2) / PW;
    positions.setX(i, side * u * PW);
    positions.setZ(i, TOP + .055 * Math.sin(u * Math.PI) * Math.exp(-u * 2));
  }
  if (side < 0) {
    const uv = geometry.attributes.uv;
    for (let i = 0; i < uv.count; i++) uv.setX(i, 1 - uv.getX(i));
    const index = geometry.index;
    for (let i = 0; i < index.count; i += 3) { const a = index.getX(i); index.setX(i, index.getX(i + 2)); index.setX(i + 2, a); }
  }
  geometry.computeVertexNormals(); return geometry;
}
function fallbackPage(page, width = 768) {
  const height = Math.round(width * PH / PW);
  return textureCanvas(width, height, (ctx, w, h) => {
    ctx.fillStyle = '#f6f3ea'; ctx.fillRect(0, 0, w, h);
    ctx.fillStyle = '#506671'; ctx.font = `600 ${w * .018}px "Booki Nexa", sans-serif`;
    ctx.fillText('S O U N D B O O K I', w * .1, h * .075);
    const title = page.querySelector('h2:not(.mobile-title),h3,.living-sentence')?.textContent.trim() || 'Những trang sách cất tiếng.';
    ctx.fillStyle = '#223b4b'; ctx.font = `600 ${w * .075}px "Booki Nexa", sans-serif`;
    let y = h * .26, line = '';
    for (const word of title.split(/\s+/)) {
      if (ctx.measureText(line + word).width > w * .78) { ctx.fillText(line, w * .1, y); line = ''; y += w * .095; }
      line += word + ' ';
    }
    ctx.fillText(line, w * .1, y);
    const copy = [...page.querySelectorAll('.page-body>p')].map(n => n.textContent.trim()).join(' ');
    y += w * .14; line = ''; ctx.font = `400 ${w * .03}px "Booki Nexa", sans-serif`; ctx.fillStyle = '#586b74';
    for (const word of copy.split(/\s+/)) {
      if (ctx.measureText(line + word).width > w * .78) { ctx.fillText(line, w * .1, y); line = ''; y += w * .06; }
      line += word + ' ';
    }
    ctx.fillText(line, w * .1, y);
  });
}

export async function mount({ host, book, cover, leftPages, rightPages }) {
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) return null;
  await document.fonts.ready;
  const manifest = await fetch('assets/book-pages/pages.json').then(r => r.ok ? r.json() : null).catch(() => null);
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'default' });
  renderer.setPixelRatio(Math.min(devicePixelRatio, innerWidth < 768 ? 1.5 : 1.8));
  renderer.setClearColor(0x000000, 0);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.32;
  renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFShadowMap;
  renderer.domElement.className = 'book-webgl'; renderer.domElement.setAttribute('aria-hidden', 'true');
  const css = new CSS3DRenderer(); css.domElement.className = 'book-css3d';
  const scene = new THREE.Scene(), cssScene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(33, 1, .1, 70);
  const root = new THREE.Group(), cssRoot = new THREE.Group();
  scene.add(root); cssScene.add(cssRoot);
  const resources = [];
  const cloth = clothTexture(), paper = paperTexture(), edges = paperTexture(true), shadow = shadowTexture();
  resources.push(cloth, paper, edges, shadow);
  const clothMaterial = new THREE.MeshPhysicalMaterial({ color: 0xffffff, map: cloth, bumpMap: cloth, bumpScale: .012, roughness: .84, metalness: .03, sheen: .3, sheenColor: new THREE.Color('#a2bcc1'), sheenRoughness: .88 });
  const endPaper = new THREE.MeshStandardMaterial({ color: '#eae7da', map: paper, roughness: .95 });
  const pageEdge = new THREE.MeshStandardMaterial({ color: '#fffdf3', map: edges, roughness: .9 });
  const pageTopR = new THREE.MeshStandardMaterial({ color: '#fffdf7', map: paper, roughness: .95 });
  const pageTopL = pageTopR.clone();
  resources.push(clothMaterial, endPaper, pageEdge, pageTopR, pageTopL);
  const boardGeometry = new RoundedBoxGeometry(PW + .11, PH + .13, .1, 4, .035);
  const blockGeometry = new RoundedBoxGeometry(PW - .035, PH - .035, .28, 3, .018);
  resources.push(boardGeometry, blockGeometry);
  function mesh(geometry, material, parent, x, y, z) {
    const object = new THREE.Mesh(geometry, material); object.position.set(x, y, z);
    object.castShadow = true; object.receiveShadow = true; parent.add(object); return object;
  }
  const rightBoard = mesh(boardGeometry, clothMaterial, root, PW / 2, 0, BOTTOM - .08);
  const leftAssembly = new THREE.Group(); root.add(leftAssembly);
  mesh(boardGeometry, clothMaterial, leftAssembly, -PW / 2, 0, BOTTOM - .075);
  mesh(blockGeometry, [pageEdge,pageEdge,pageEdge,pageEdge,endPaper,endPaper], root, PW / 2, 0, -.01);
  mesh(blockGeometry, [pageEdge,pageEdge,pageEdge,pageEdge,endPaper,endPaper], leftAssembly, -PW / 2, 0, -.01);
  const rightSurface = mesh(paperGeometry(1), pageTopR, root, 0, 0, 0);
  const leftSurface = mesh(paperGeometry(-1), pageTopL, leftAssembly, 0, 0, 0);
  resources.push(rightSurface.geometry, leftSurface.geometry);
  const gutterTexture = textureCanvas(256, 8, (ctx, w, h) => {
    const g = ctx.createLinearGradient(0, 0, w, 0);
    g.addColorStop(0, 'rgba(37,48,45,0)'); g.addColorStop(.5, 'rgba(37,48,45,.2)'); g.addColorStop(1, 'rgba(37,48,45,0)');
    ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
  });
  const gutterMaterial = new THREE.MeshBasicMaterial({ map: gutterTexture, transparent: true, depthWrite: false });
  const gutterGeometry = new THREE.PlaneGeometry(.32, PH);
  const gutter = mesh(gutterGeometry, gutterMaterial, root, 0, 0, TOP + .024); gutter.castShadow = false;
  resources.push(gutterTexture, gutterMaterial, gutterGeometry);
  const spineGeometry = new THREE.CylinderGeometry(.19, .19, PH + .07, 36);
  resources.push(spineGeometry); const spine = mesh(spineGeometry, clothMaterial, root, -.02, 0, -.075); spine.scale.z = .78;
  const coverHinge = new THREE.Group(); coverHinge.position.z = .225; root.add(coverHinge);
  const frontBoard = mesh(boardGeometry, [clothMaterial,clothMaterial,clothMaterial,clothMaterial,clothMaterial,endPaper], coverHinge, PW / 2, 0, 0);
  const bookmarkGeometry = new THREE.PlaneGeometry(.16, .65, 1, 16);
  for (let i = 0; i < bookmarkGeometry.attributes.position.count; i++) {
    const p = bookmarkGeometry.attributes.position;
    p.setZ(i, Math.sin((p.getY(i) + .325) * 4) * .045);
  }
  bookmarkGeometry.computeVertexNormals(); resources.push(bookmarkGeometry);
  const ribbon = new THREE.MeshStandardMaterial({ color: '#4d7c87', roughness: .64, side: THREE.DoubleSide }); resources.push(ribbon);
  mesh(bookmarkGeometry, ribbon, root, .11, -PH / 2 - .22, -.09);
  const floatingShadow = new THREE.Mesh(new THREE.PlaneGeometry(11, 5), new THREE.MeshBasicMaterial({ map: shadow, transparent: true, depthWrite: false, opacity: .56 }));
  floatingShadow.position.set(0, -2.7, -1.6); scene.add(floatingShadow); resources.push(floatingShadow.geometry, floatingShadow.material);
  scene.add(new THREE.HemisphereLight('#f5f9ff', '#667d7d', 2.4));
  const key = new THREE.DirectionalLight('#fff4de', 3.4); key.position.set(-4, 7, 9); key.castShadow = true;
  key.shadow.mapSize.set(1024, 1024); key.shadow.camera.left = -6; key.shadow.camera.right = 6; key.shadow.camera.top = 5; key.shadow.camera.bottom = -5;
  key.shadow.normalBias = .025; key.shadow.bias = -.0004; key.shadow.radius = 3; scene.add(key);
  const fill = new THREE.DirectionalLight('#b7d4e8', 1.1); fill.position.set(6, -1, 5); scene.add(fill);
  const rim = new THREE.DirectionalLight('#fff8e6', 1.5); rim.position.set(2, 5, -3); scene.add(rim);

  const leafGeometry = new THREE.PlaneGeometry(PW, PH, 64, 8);
  const leafFrontMaterial = new THREE.MeshStandardMaterial({ color: '#fffdf7', map: paper, roughness: .91, side: THREE.FrontSide });
  const leafBackMaterial = leafFrontMaterial.clone(); leafBackMaterial.side = THREE.BackSide;
  const leaf = new THREE.Group(); leaf.position.z = TOP + .025; root.add(leaf);
  const leafFront = mesh(leafGeometry, leafFrontMaterial, leaf, 0, 0, 0);
  const backGeometry = leafGeometry.clone();
  backGeometry.setAttribute('position', leafGeometry.attributes.position);
  backGeometry.setAttribute('normal', leafGeometry.attributes.normal);
  for (let i = 0; i < backGeometry.attributes.uv.count; i++) backGeometry.attributes.uv.setX(i, 1 - backGeometry.attributes.uv.getX(i));
  const leafBack = mesh(backGeometry, leafBackMaterial, leaf, 0, 0, .001);
  resources.push(leafGeometry, backGeometry, leafFrontMaterial, leafBackMaterial);
  function bend(progress) {
    const positions = leafGeometry.attributes.position;
    const curl = .68 * Math.sin(Math.PI * progress), theta = -Math.PI * progress;
    const xs = [0], zs = [0];
    for (let col = 1; col <= 64; col++) {
      const u = (col - .5) / 64;
      const angle = theta - curl * Math.sin(Math.PI * u);
      xs[col] = xs[col - 1] + Math.cos(angle) * PW / 64;
      zs[col] = zs[col - 1] - Math.sin(angle) * PW / 64;
    }
    for (let row = 0; row <= 8; row++) for (let col = 0; col <= 64; col++) {
      const i = row * 65 + col, u = col / 64;
      const corner = Math.sin(Math.PI * u) * Math.sin(Math.PI * progress) * .07 * Math.pow(row / 8, 2);
      positions.setXYZ(i, xs[col], PH / 2 - row / 8 * PH, zs[col] + corner);
    }
    positions.needsUpdate = true; leafGeometry.computeVertexNormals();
  }

  // Use parallel GPU compilation where available; the CSS cover stays visible
  // while shader programs prepare, rather than blocking the first scroll.
  camera.position.set(0, .5, 12); camera.lookAt(0, 0, 0);
  await renderer.compileAsync(scene, camera);

  // DOM remains real, selectable, accessible and interactive on settled pages.
  // During a turn its local raster is placed on the bent WebGL sheet so depth
  // testing correctly occludes the next page. The DOM never paints over a leaf.
  const bookAnchor = document.createComment('book-scene-original'); book.before(bookAnchor);
  const coverAnchor = document.createComment('book-scene-cover'); cover.before(coverAnchor);
  const pageDom = document.createElement('div'); pageDom.className = 'scene-paper-dom'; pageDom.append(book);
  const coverDom = document.createElement('div'); coverDom.className = 'scene-cover-dom'; coverDom.append(cover);
  const pageObject = new CSS3DObject(pageDom), coverObject = new CSS3DObject(coverDom);
  const cssCoverHinge = new THREE.Group(); cssRoot.add(pageObject, cssCoverHinge); cssCoverHinge.add(coverObject);
  host.append(renderer.domElement, css.domElement);
  // Attach real DOM immediately, before the app's synchronous selectors run.
  css.render(cssScene, camera);
  document.documentElement.classList.add('webgl-active'); host.dataset.renderer = 'webgl';
  const textures = new Map(), jobs = new Map(), images = new Map();
  const textureLoader = new THREE.ImageLoader();
  let generation = 0, layoutSignature = '';
  let disposed = false, framePending = false, lastTime = 0, lastOpening = 0, lastTurn = -1, lastProgress = 1;
  let lastTextureKey = '', compact = innerWidth < 768;
  function pageAsset(page) {
    const right = rightPages.includes(page), index = (right ? rightPages : leftPages).indexOf(page);
    return manifest?.[compact && right ? 'mobile' : 'desktop']?.[right ? 'right' : 'left']?.[index];
  }
  function boxInPage(element, page) {
    let x = 0, y = 0, node = element;
    while (node && node !== page) { x += node.offsetLeft; y += node.offsetTop; node = node.offsetParent; }
    return { x, y, w: element.offsetWidth, h: element.offsetHeight };
  }
  function paintInteraction(image, page) {
    const canvas = document.createElement('canvas'); canvas.width = image.width; canvas.height = image.height;
    const ctx = canvas.getContext('2d'); ctx.drawImage(image, 0, 0);
    if (!page.offsetWidth || !page.offsetHeight) return canvas;
    ctx.scale(canvas.width / page.offsetWidth, canvas.height / page.offsetHeight);
    function paintText(element, value = element?.textContent) {
      if (!element || !value) return;
      const b = boxInPage(element, page), style = getComputedStyle(element), fs = parseFloat(style.fontSize);
      const lineHeight = parseFloat(style.lineHeight) || fs * 1.25;
      ctx.fillStyle = '#f6f3ea'; ctx.fillRect(b.x - 2, b.y - 2, b.w + 4, b.h + 4);
      ctx.font = `${style.fontWeight} ${style.fontSize} ${style.fontFamily}`; ctx.fillStyle = style.color; ctx.textBaseline = 'top';
      if ('letterSpacing' in ctx) ctx.letterSpacing = style.letterSpacing === 'normal' ? '0px' : style.letterSpacing;
      let line = '', y = b.y + Math.max(0, (lineHeight - fs) / 2);
      for (const word of value.trim().split(/\s+/)) {
        if (line && ctx.measureText(line + word).width > b.w) { ctx.fillText(line.trim(), b.x, y); y += lineHeight; line = ''; }
        line += word + ' ';
      }
      ctx.fillText(line.trim(), b.x, y);
    }
    for (const selector of ['#voice-name','#voice-character','#audio-current','#audio-duration','#audio-status','#engine-name','#engine-price','#engine-description','#engine-note','#format-title','#format-description']) paintText(page.querySelector(selector));
    const select = page.querySelector('#voice-select');
    if (select) {
      const b = boxInPage(select, page), style = getComputedStyle(select), fs = parseFloat(style.fontSize);
      ctx.fillStyle = '#fdfcf6'; ctx.fillRect(b.x, b.y, b.w, b.h); ctx.strokeStyle = '#b6c7cf'; ctx.lineWidth = 1; ctx.strokeRect(b.x + .5, b.y + .5, b.w - 1, b.h - 1);
      ctx.font = `${style.fontWeight} ${style.fontSize} ${style.fontFamily}`; ctx.fillStyle = style.color; ctx.textBaseline = 'middle';
      ctx.fillText(select.options[select.selectedIndex].text, b.x + 12, b.y + b.h / 2);
      ctx.beginPath(); ctx.moveTo(b.x + b.w - 15, b.y + b.h / 2 - 2); ctx.lineTo(b.x + b.w - 11, b.y + b.h / 2 + 2); ctx.lineTo(b.x + b.w - 7, b.y + b.h / 2 - 2); ctx.stroke();
    }
    const wave = page.querySelector('#audio-wave');
    if (wave) {
      const b = boxInPage(wave, page); ctx.fillStyle = '#f6f3ea'; ctx.fillRect(b.x, b.y, b.w, b.h);
      for (const bar of wave.children) { const r = boxInPage(bar, page); ctx.fillStyle = '#416d98'; ctx.globalAlpha = bar.classList.contains('played') ? 1 : .42; ctx.fillRect(r.x, r.y, r.w, r.h); }
      ctx.globalAlpha = 1;
    }
    return canvas;
  }
  async function capture(page, refresh = false) {
    if (textures.has(page) && !refresh) return textures.get(page);
    if (jobs.has(page)) return jobs.get(page);
    const epoch = generation, url = pageAsset(page);
    const promise = (async () => {
      let texture;
      try {
        if (!url) throw Error('No local page print');
        if (!images.has(url)) images.set(url, textureLoader.loadAsync(url));
        const image = await images.get(url);
        texture = new THREE.CanvasTexture(refresh ? paintInteraction(image, page) : image);
        texture.colorSpace = THREE.SRGBColorSpace; texture.anisotropy = 4;
      } catch { texture = fallbackPage(page, 512); }
      if (disposed || epoch !== generation) { texture.dispose(); return null; }
      const previous = textures.get(page); textures.set(page, texture); previous?.dispose();
      jobs.delete(page); requestRender(); return texture;
    })();
    jobs.set(page, promise); return promise;
  }
  function textureFor(page) { return textures.get(page) || paper; }

  function resize() {
    if (disposed) return;
    compact = innerWidth < 768;
    const width = host.clientWidth, height = host.clientHeight;
    if (!width || !height) return;
    renderer.setSize(width, height); css.setSize(width, height); camera.aspect = width / height; camera.updateProjectionMatrix();
    const pixels = book.offsetWidth, pixelsH = book.offsetHeight;
    const signature = `${pixels}:${pixelsH}:${compact}`;
    if (layoutSignature && layoutSignature !== signature) {
      generation++; for (const texture of textures.values()) texture.dispose(); textures.clear(); jobs.clear(); lastTextureKey = '';
    }
    layoutSignature = signature;
    root.scale.y = compact ? PW * (pixelsH / pixels) / PH : 1;
    pageDom.style.width = `${pixels}px`; pageDom.style.height = `${pixelsH}px`;
    const domWorldWidth = compact ? PW : PW * 2;
    pageObject.scale.set(domWorldWidth / pixels, PH / pixelsH, 1);
    pageObject.position.set(compact ? PW / 2 : 0, 0, TOP + .027);
    coverDom.style.width = `${compact ? pixels : pixels / 2}px`; coverDom.style.height = `${pixelsH}px`;
    coverObject.scale.set(PW / (compact ? pixels : pixels / 2), PH / pixelsH, 1);
    coverObject.position.set(PW / 2, 0, .064); cssCoverHinge.position.z = .225;
    requestRender();
  }
  function pose(time, opening, turnIndex, turnProgress) {
    const opened = smooth(opening), turning = turnIndex >= 0 && turnProgress < 1;
    const easedTurn = smooth(turnProgress);
    const transition = turning ? Math.sin(Math.PI * easedTurn) : 0;
    const distanceY = (PH * root.scale.y + .4) / (2 * Math.tan(THREE.MathUtils.degToRad(33 / 2)) * (compact ? .78 : .8));
    const distanceX = (compact ? PW + .3 : PW * 2 + .3) / (2 * Math.tan(THREE.MathUtils.degToRad(33 / 2)) * camera.aspect * .87);
    const distance = Math.max(distanceY, distanceX);
    root.position.set(compact ? 0 : lerp(-PW / 2, 0, opened), .08 + transition * .035, 0);
    root.rotation.set(lerp(compact ? -.055 : -.1, -.025, opened) - transition * .055, lerp(compact ? -.18 : -.34, .015, opened) + transition * .075, lerp(compact ? -.035 : -.1, -.012, opened));
    const introPush = (compact ? .04 : .075) * (time < 3.2 ? smooth((time - 1.6) / 1.2) : 1 - smooth((time - 3.2) / 1.1));
    camera.position.set((compact ? PW / 2 : 0) + lerp(compact ? .1 : .32, 0, opened), lerp(compact ? .3 : .65, .16, opened) + transition * .22, distance * (lerp(.96, 1, opened) - introPush) - transition * .18);
    camera.lookAt(compact ? PW / 2 : 0, .05, 0);
    coverHinge.rotation.y = -Math.PI * opened;
    coverHinge.position.z = lerp(.225, BOTTOM - .08, smooth((opened - .45) / .55));
    leftAssembly.visible = opened > .49;
    const spread = smooth((opened - .49) / .5); leftAssembly.scale.x = Math.max(.001, spread);
    frontBoard.visible = opened < .999;
    gutter.visible = opened > .9;
    floatingShadow.position.x = compact ? PW / 2 : lerp(0, -.05, opened);
    floatingShadow.scale.x = lerp(.57, 1, opened);
    cssRoot.position.copy(root.position); cssRoot.rotation.copy(root.rotation); cssRoot.scale.copy(root.scale);
    cssCoverHinge.rotation.copy(coverHinge.rotation); cssCoverHinge.position.z = coverHinge.position.z;
    coverDom.style.opacity = opened > .51 ? '0' : '1';
    const introOpacity = smooth((opened - .76) / .24);
    pageDom.style.opacity = turning ? '0' : String(introOpacity);
    pageDom.style.pointerEvents = !turning && opened > .97 ? 'auto' : 'none';
    leaf.visible = turning;
    if (turning) {
      bend(easedTurn);
      const before = turnIndex, after = turnIndex + 1;
      leafFrontMaterial.map = textureFor(rightPages[before]);
      leafBackMaterial.map = textureFor(compact ? rightPages[after] : leftPages[after]);
      pageTopL.map = textureFor(leftPages[before]); pageTopR.map = textureFor(rightPages[after]);
      const key = `${before}:${compact}`;
      if (lastTextureKey !== key) { lastTextureKey = key; capture(rightPages[before], true); capture(compact ? rightPages[after] : leftPages[after]); capture(leftPages[before]); capture(rightPages[after]); }
    } else {
      pageTopL.map = paper; pageTopR.map = paper;
    }
    // All settled materials already have maps. Texture swaps only change
    // uniforms; avoid invalidating shader programs on every scroll frame.
    if (!leafFrontMaterial.userData.mapped && turning) {
      leafFrontMaterial.needsUpdate = true; leafBackMaterial.needsUpdate = true;
      leafFrontMaterial.userData.mapped = true;
    }
  }
  function render() {
    framePending = false; if (disposed || document.hidden) return;
    try {
      pose(lastTime, lastOpening, lastTurn, lastProgress);
      renderer.render(scene, camera); css.render(cssScene, camera);
    } catch { dispose(); }
  }
  function requestRender() { if (!disposed && !framePending) { framePending = true; requestAnimationFrame(render); } }
  function update(time, opening, turnIndex = -1, progress = 1) { lastTime = time; lastOpening = opening; lastTurn = turnIndex; lastProgress = progress; requestRender(); }
  function invalidate(page) { if (!disposed) capture(page, true); }
  function dispose() {
    if (disposed) return; disposed = true;
    bookAnchor.replaceWith(book); coverAnchor.replaceWith(cover);
    renderer.dispose(); renderer.domElement.remove(); css.domElement.remove();
    hostObserver?.disconnect(); document.removeEventListener('visibilitychange', onVisibility);
    for (const texture of textures.values()) texture.dispose();
    for (const resource of resources) resource.dispose?.();
    document.documentElement.classList.remove('webgl-active'); host.dataset.renderer = 'css';
  }
  const onVisibility = () => { if (!document.hidden) requestRender(); };
  document.addEventListener('visibilitychange', onVisibility);
  renderer.domElement.addEventListener('webglcontextlost', event => { event.preventDefault(); dispose(); });
  const hostObserver = 'ResizeObserver' in window ? new ResizeObserver(resize) : null;
  hostObserver?.observe(host);
  resize();
  capture(leftPages[0]); capture(rightPages[0]);
  const remaining = [rightPages[1], leftPages[1]];
  function prewarm() {
    if (disposed || !remaining.length || lastTime >= 3.2) return;
    const page = remaining.shift(); capture(page).finally(() => {
      if ('requestIdleCallback' in window) requestIdleCallback(prewarm, { timeout: 2000 });
    });
  }
  if ('requestIdleCallback' in window) requestIdleCallback(prewarm, { timeout: 2000 });
  return { update, resize, invalidate, dispose };
}
