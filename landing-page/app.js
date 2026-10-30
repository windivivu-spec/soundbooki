'use strict';

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const icon = name => `<svg class="icon" aria-hidden="true"><use href="assets/icons/sprite.svg#${name}"/></svg>`;
const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)');
const compact = matchMedia('(max-width: 767px)');
const systemDark = matchMedia('(prefers-color-scheme: dark)');
const config = window.SOUNDBOOKI_SITE || {};

// A single audio element for the listening page. Setting a voice never plays it.
const audio = new Audio();
audio.preload = 'none';
let samples = [], selectedVoice = 'minh-tai', audioRevision = 0, lastAudioState = '';

document.addEventListener('soundbooki:audio-start',event=>{if(event.detail?.source!=='sample')audio.pause();});

const clamp = n => Math.max(0, Math.min(1, n));
const timeLabel = n => `${Math.floor(Math.max(0, n || 0) / 60)}:${String(Math.floor(Math.max(0, n || 0) % 60)).padStart(2, '0')}`;
const currentSample = () => samples.find(sample => sample.id === selectedVoice);
function syncAudio() {
  const playing = !audio.paused && !audio.ended;
  const sample = currentSample();
  const state = selectedVoice + ':' + playing;
  if (lastAudioState !== state) {
    lastAudioState = state;
    $('#audio-play').innerHTML = icon(playing ? 'pause' : 'play');
    $('#audio-play').setAttribute('aria-label', `${playing ? 'Tạm dừng mẫu' : 'Nghe mẫu'} ${sample?.name || 'Minh Tài'}`);
    $('#audio-play').setAttribute('aria-pressed', String(playing));
  }
  const duration = Number.isFinite(audio.duration) ? audio.duration : sample?.duration || 8.5;
  const progress = duration ? audio.currentTime / duration : 0;
  $('#audio-current').textContent = timeLabel(audio.currentTime);
  $('#audio-duration').textContent = timeLabel(duration);
  $('#audio-seek').value = clamp(progress) * 100;
  $$('#audio-wave span').forEach((bar, i, all) => bar.classList.toggle('played', i / all.length < progress));
}
function selectVoice(id) {
  const sample = samples.find(item => item.id === id);
  if (!sample) return;
  audioRevision++; audio.pause(); selectedVoice = id; audio.src = sample.file;
  $('#voice-select').value = id; $('#voice-name').textContent = sample.name; $('#voice-character').textContent = sample.character;
  $('#audio-wave').replaceChildren(...sample.waveform.map(amplitude => { const bar = document.createElement('span'); bar.style.setProperty('--amp', amplitude); return bar; }));
  $('#audio-play').disabled = false; $('#audio-status').textContent = 'Bấm Play để nghe. Âm thanh luôn do bạn bật.';
  syncAudio();
}
$('#voice-select').addEventListener('change', event => selectVoice(event.target.value));
$('#audio-play').addEventListener('click', async () => {
  if (!currentSample()) return;
  if (!audio.paused) { audio.pause(); return; }
  const revision = audioRevision;
  try {
    $('#audio-status').textContent = 'Đang tải mẫu giọng…';
    if (audio.ended) audio.currentTime = 0;
    document.dispatchEvent(new CustomEvent('soundbooki:audio-start',{detail:{source:'sample'}}));
    await audio.play();
    if (revision === audioRevision) $('#audio-status').textContent = 'Đang nghe mẫu ' + currentSample().name;
  } catch (error) {
    if (revision === audioRevision && error.name !== 'AbortError') $('#audio-status').textContent = 'Chưa phát được mẫu. Bấm Play để thử lại.';
  }
});
$('#audio-seek').addEventListener('input', event => { if (Number.isFinite(audio.duration) && audio.readyState >= 1) { audio.currentTime = Number(event.target.value) / 100 * audio.duration; syncAudio(); } });
for (const type of ['play', 'pause', 'timeupdate', 'loadedmetadata', 'ended']) audio.addEventListener(type, syncAudio);
audio.addEventListener('pause', () => { if (!audio.ended) $('#audio-status').textContent = 'Đã tạm dừng. Bấm Play để nghe tiếp.'; });
audio.addEventListener('ended', () => $('#audio-status').textContent = 'Đã nghe hết mẫu. Bấm Play để nghe lại.');
audio.addEventListener('error', () => { if (currentSample()) $('#audio-status').textContent = 'Chưa tải được mẫu. Bấm Play để thử lại.'; });
fetch('assets/audio/samples.json').then(response => { if (!response.ok) throw Error('Audio catalog unavailable'); return response.json(); }).then(data => { samples = data; selectVoice(selectedVoice); }).catch(() => { $('#audio-status').textContent = 'Chưa tải được danh sách mẫu. Vui lòng tải lại trang.'; $('#audio-play').disabled = true; });

function openDialog(dialog) {
  audio.pause();
  $$('dialog[open]').forEach(other => other.close());
  dialog.showModal();
}
$$('[data-download]').forEach(button => button.addEventListener('click', () => openDialog($('#download-dialog'))));
$('#offer-details').addEventListener('click', () => openDialog($('#offer-dialog')));
$('#faq-details').addEventListener('click', () => openDialog($('#faq-dialog')));
$('#app-preview-trigger').addEventListener('click', () => openDialog($('#app-dialog')));
$$('[data-close]').forEach(button => button.addEventListener('click', () => button.closest('dialog').close()));
$$('dialog').forEach(dialog => dialog.addEventListener('click', event => {
  const rect = dialog.getBoundingClientRect();
  if (event.target === dialog && (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom)) dialog.close();
}));
const mac = config.mac;
if (mac) {
  $('#download-file-label').textContent = `Mac Apple Silicon${mac.version ? ' / ' + mac.version : ''}`;
  $('#download-size').textContent = mac.sizeBytes ? `${Math.round(mac.sizeBytes / 1024 / 1024)} MB` : '';
  $('#download-checksum').textContent = mac.sha256 || 'Đang chuẩn bị';
  try {
    const url = new URL(mac.url);
    if (url.protocol === 'https:' && !url.username && !url.password) {
      const link = $('#download-file'); link.href = url.href; link.download = mac.filename; link.rel = 'noopener'; link.setAttribute('aria-disabled', 'false');
      $('#download-state').textContent = 'Bản trải nghiệm chưa được Apple công chứng. Xem hướng dẫn cài đặt bên dưới.';
    }
  } catch {}
}
$('#download-file').addEventListener('click', event => { if (event.currentTarget.getAttribute('aria-disabled') === 'true') event.preventDefault(); });
function refreshOffer() {
  if (config.offer && Date.now() >= Date.parse(config.offer.endsAt)) {
    $('#offer-details').disabled = true; $('#offer-details').textContent = 'Ưu đãi ra mắt đã kết thúc';
    $('#offer-cutoff').textContent = 'Bạn vẫn có thể tạo và nghe bằng Lite miễn phí.';
  }
}
refreshOffer();
document.addEventListener('visibilitychange', () => { if (document.hidden) audio.pause(); else refreshOffer(); });
window.addEventListener('pagehide', () => audio.pause());

// Decorative word-to-note loops are independent of the narration clock.
// CSS does the drawing; events only suspend work when it cannot be seen.
(() => {
 const atmosphere=$('.hero-atmosphere'), toggle=$('#hero-motion-toggle');
 if(!atmosphere||!toggle)return;
 let inView=false, userPaused=false;
 let preludeDone=!document.body.classList.contains('has-prelude')||document.body.classList.contains('prelude-entered');
 function syncAtmosphere(){
  const paused=userPaused||reduceMotion.matches||document.hidden||!inView||!preludeDone||!!$('dialog[open]');
  document.body.classList.toggle('hero-atmosphere-paused',paused);
  toggle.hidden=reduceMotion.matches;
 }
 toggle.addEventListener('click',()=>{
  userPaused=!userPaused;
  const label=userPaused?'Tiếp tục chuyển động nền':'Tạm dừng chuyển động nền';
  toggle.setAttribute('aria-pressed',String(userPaused));
  toggle.setAttribute('aria-label',label);toggle.title=label;
  toggle.innerHTML=icon(userPaused?'play':'pause');
  syncAtmosphere();
 });
 document.addEventListener('soundbooki:prelude-start',()=>{preludeDone=false;syncAtmosphere();});
 document.addEventListener('soundbooki:prelude-end',()=>{preludeDone=true;syncAtmosphere();});
 document.addEventListener('visibilitychange',syncAtmosphere);
 reduceMotion.addEventListener('change',syncAtmosphere);
 window.addEventListener('pagehide',()=>document.body.classList.add('hero-atmosphere-paused'));
 window.addEventListener('pageshow',syncAtmosphere);
 if('IntersectionObserver' in window){
  new IntersectionObserver(entries=>{inView=entries[0].isIntersecting;syncAtmosphere();},{threshold:.01}).observe(atmosphere);
 }else inView=true;
 const dialogs=new MutationObserver(syncAtmosphere);
 $$('dialog').forEach(dialog=>dialogs.observe(dialog,{attributes:true,attributeFilter:['open']}));
 syncAtmosphere();
})();

if (window.gsap && window.ScrollTrigger && !reduceMotion.matches) {
 gsap.registerPlugin(ScrollTrigger);
 gsap.utils.toArray('.reveal').forEach(el => gsap.from(el, {y:32, opacity:0, duration:1, ease:'power3.out', scrollTrigger:{trigger:el,start:'top 94%',once:true}}));
 document.addEventListener('visibilitychange',()=>document.hidden?gsap.globalTimeline.pause():gsap.globalTimeline.resume());
 reduceMotion.addEventListener('change',()=>{if(reduceMotion.matches){gsap.globalTimeline.getChildren().forEach(t=>t.progress(1).kill());gsap.set('.reveal',{clearProps:'all'});}});
}
