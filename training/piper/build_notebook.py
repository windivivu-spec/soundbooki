"""Build a self-contained Colab notebook without any user recording or credentials."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
cells = []


def md(text):
    cells.append(dict(cell_type='markdown', metadata={}, source=text.splitlines(True)))


def code(text):
    cells.append(dict(cell_type='code', metadata={}, execution_count=None, outputs=[], source=text.splitlines(True)))


md('''# Windi — thử giọng sách nói nhỏ (Piper/VITS)
Một người nói · tiếng Việt · ONNX 22.050 Hz · train trên Colab, đọc sách local trên Mac.

**Cấu hình CapCut sạch:** không thêm denoise, EQ, compressor, đổi cao độ hoặc tốc độ. Giữ bản thu gốc; chỉ đổi sample rate/mono cho đúng kiến trúc. Giữ hơi thở và phần nghỉ trong clip, tắt trim_silence khi train. Learning rate thử 3e-5, chưa coi là cấu hình tối ưu trước khi nghe file thật. Kiến trúc và số tham số model giữ nguyên.

Notebook này **không tự train**, không tự đăng model, không dùng API chép lời. Khi có file, chỉ đưa lên bản thu bạn chọn. Bản gốc được giữ riêng. Chép lời bằng faster-whisper chạy trong máy Colab; cần nghe/sửa và duyệt trước khi train.

**Trạng thái ban đầu:** chưa có bản thu, chưa có giọng đã train. Model nền tiếng Việt là VAIS1000 medium, không phải giọng riêng đã đạt chất lượng.

Nguồn: [Piper](https://github.com/OHF-Voice/piper1-gpl), [train/export](https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/TRAINING.md), [checkpoint](https://huggingface.co/datasets/rhasspy/piper-checkpoints/tree/main/vi/vi_VN/vais1000/medium).
Piper runtime hiện tại GPL-3.0; model card VAIS1000 ghi dữ liệu CC BY 4.0. Lưu attribution đi kèm thử nghiệm; chưa tích hợp hay phát hành runtime này trong app.
''')
md('''## 1. Cài môi trường riêng
Có thể chạy bước setup bằng CPU. Để train: Runtime → Change runtime type → T4 GPU nếu được cấp. Không chọn TPU. Mỗi máy Colab mới cần chạy lại setup; không coi máy ảo là nơi lưu trữ lâu dài.
''')
code('''from pathlib import Path
import hashlib, json, os, shutil, subprocess, sys, urllib.request
ROOT = Path('/content/windi-small-voice')
ROOT.mkdir(exist_ok=True)
VENV = ROOT/'venv'
PY = VENV/'bin/python'
def run(command, **kwargs):
    p=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,**kwargs)
    for line in p.stdout: print(line,end='',flush=True)
    if p.wait(): raise RuntimeError('Lệnh setup thất bại: '+repr(command))
if not (VENV/'bin/pip').exists():
    run([sys.executable,'-m','pip','install','virtualenv==20.35.3'])
    run([sys.executable,'-m','virtualenv','--system-site-packages',str(VENV)])
run([str(PY),'-m','pip','install','--disable-pip-version-check',
    'piper-tts[train]==1.8.0','faster-whisper==1.2.1','av==16.0.1','soundfile==0.13.1'])
subprocess.run(['ffmpeg','-version'],check=True,stdout=subprocess.DEVNULL)
# Official wheel includes the training Python modules, but not the Cython aligner.
align_setup = r"""
import hashlib, importlib.util, shutil, subprocess, sys, urllib.request
from pathlib import Path
align=Path(importlib.util.find_spec('piper').origin).parent/'train/vits/monotonic_align'
target=align/'monotonic_align'; target.mkdir(exist_ok=True)
if not list(target.glob('core*.so')):
    url='https://raw.githubusercontent.com/OHF-Voice/piper1-gpl/619f513580c04dff5ef9a680f6f3f6979ed94d2e/src/piper/train/vits/monotonic_align/core.pyx'
    data=urllib.request.urlopen(url,timeout=60).read()
    if hashlib.sha256(data).hexdigest()!='8640b303683823a4a1259179547ef476999b1cbb2e46ff656b970763cfbc1157':
        raise RuntimeError('Mã aligner không đúng checksum.')
    (align/'core.pyx').write_bytes(data)
    subprocess.run([sys.executable,'-m','Cython.Build.Cythonize','-i','core.pyx'],cwd=align,check=True)
    for so in align.glob('core*.so'): shutil.copy2(so,target/so.name)
print('Cython aligner đã build.')
exporter=Path(importlib.util.find_spec('piper').origin).parent/'train/export_onnx.py'
source=exporter.read_text()
if 'dynamo=False' not in source:
    if source.count('opset_version=OPSET_VERSION,') != 1:
        raise RuntimeError('Exporter khác cấu trúc đã kiểm tra.')
    exporter.write_text(source.replace('opset_version=OPSET_VERSION,',
        'opset_version=OPSET_VERSION,\\n        dynamo=False,'))
print('Giữ legacy ONNX exporter cho kiến trúc Piper VITS trên Torch mới.')
"""
run([str(PY),'-c',align_setup])
print('Đã cài môi trường riêng. Chưa bắt đầu train.')
''')
md('## 2. Công cụ tách, duyệt và train — mã đi kèm notebook')
source = (HERE/'toolkit.py').read_text()
code('TOOLKIT = ' + repr(source) + '\n(ROOT/"toolkit.py").write_text(TOOLKIT, encoding="utf-8")\nprint("Đã ghi công cụ CapCut sạch, giữ giọng gốc. Không có bản thu trong notebook.")\n')
md('''## 3. Tải checkpoint cố định, xác minh và kiểm tra tương thích
Checkpoint train khoảng 846 MB; **không phải dung lượng model ONNX cuối cùng**. Chỉ tải trọng số, cấu hình và attribution, không tải dữ liệu thu âm gốc của bộ VAIS.
''')
code('''BASE = ROOT/'base'
BASE.mkdir(exist_ok=True)
REVISION = '37d1bea250e21ca0d617818d2bef1db724edb80c'
PREFIX = f'https://huggingface.co/datasets/rhasspy/piper-checkpoints/resolve/{REVISION}/vi/vi_VN/vais1000/medium/'
BASE_CKPT = BASE/'vais1000-medium.ckpt'
def fetch_verified(url,path,expected_sha=None):
    def sha(p):
        h=hashlib.sha256()
        with p.open('rb') as f:
            for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
        return h.hexdigest()
    if not path.exists() or (expected_sha and sha(path)!=expected_sha):
        tmp=path.with_name(path.name+'.partial')
        with urllib.request.urlopen(url,timeout=120) as incoming, tmp.open('wb') as out:
            while True:
                b=incoming.read(1024*1024)
                if not b: break
                out.write(b)
        if expected_sha and sha(tmp)!=expected_sha: raise RuntimeError('Checksum không khớp; không dùng checkpoint.')
        tmp.replace(path)
    return sha(path)
base_sha=fetch_verified(PREFIX+'epoch%3D4769-step%3D919580.ckpt', BASE_CKPT,
    'c3879268594a85b5133146e6a4709a5cc2f3014ef0eabf9280f67289054ba2bc')
fetch_verified(PREFIX+'config.json',BASE/'donor-config.json')
fetch_verified(PREFIX+'MODEL_CARD',BASE/'MODEL_CARD')
check = r"""
import torch, importlib.metadata, json
from pathlib import Path
from piper.train.vits.lightning import VitsModel
from piper.train.vits.dataset import VitsDataModule
from piper.train.vits.monotonic_align import maximum_path
p=Path('/content/windi-small-voice')
ck=torch.load(p/'base/vais1000-medium.ckpt',map_location='cpu',weights_only=False)
hp=ck['hyper_parameters']
architecture=['resblock','resblock_kernel_sizes','resblock_dilation_sizes','upsample_rates',
'upsample_initial_channel','upsample_kernel_sizes','filter_length','hop_length','win_length',
'mel_channels','mel_fmin','mel_fmax','inter_channels','hidden_channels','filter_channels',
'n_heads','n_layers','kernel_size','p_dropout','n_layers_q','use_spectral_norm','gin_channels',
'use_sdp','segment_size','num_symbols']
m=VitsModel(**{k:hp[k] for k in architecture if k in hp},sample_rate=22050,num_speakers=1,mos_metric=None)
m.load_state_dict(ck['state_dict'],strict=True)
report=dict(piper=importlib.metadata.version('piper-tts'),torch=torch.__version__,
    cudaAvailable=torch.cuda.is_available(),checkpointStrictLoad=True,
    checkpointEpoch=ck.get('epoch'),sampleRate=22050,modelBytes=(p/'base/vais1000-medium.ckpt').stat().st_size)
(p/'setup-proof.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
"""
subprocess.run([str(PY),'-c',check],check=True)
with (ROOT/'environment-lock.txt').open('w') as f:
    subprocess.run([str(PY),'-m','pip','freeze'],check=True,stdout=f)
print('Checkpoint khớp kiến trúc. Bắt đầu fine-tune mới, không tiếp tục epoch cũ của tác giả.')
''')
md('''## 4. Chuẩn bị model chép lời local trong Colab
Model ASR chỉ phục vụ chuẩn bị dữ liệu; không đưa vào app đọc sách. Bước này tải model từ Hugging Face lần đầu, không gửi audio tới API.
''')
code('''subprocess.run([str(PY),'-c',
    "from faster_whisper import WhisperModel; m=WhisperModel('small',device='cpu',compute_type='int8'); print('ASR small đã sẵn sàng.')"],check=True)
print((ROOT/'setup-proof.json').read_text())
if shutil.which('nvidia-smi'):
    print(subprocess.run(['nvidia-smi','--query-gpu=name,memory.total','--format=csv,noheader'],capture_output=True,text=True).stdout)
compile((ROOT/'toolkit.py').read_text(),str(ROOT/'toolkit.py'),'exec')
print('Công cụ hợp lệ. ASR đã tải. Chưa nhận file và chưa train.')
''')
md('''## 5. Nơi lưu bền vững — thực hiện khi có dữ liệu
Colab có thể xóa máy ảo. Trước khi train, cần lưu bản thu, lời duyệt và checkpoint vào thư mục riêng trên Drive. Ô này **mặc định tắt**; khi bật, Google yêu cầu bạn tự cho phép mount Drive. Quyền mount có thể cho mã notebook truy cập Drive, không chỉ thư mục huấn luyện. Không cần thực hiện ở giai đoạn chờ file.
''')
code('''MOUNT_DRIVE = False
if MOUNT_DRIVE:
    from google.colab import drive
    drive.mount('/content/drive')
WORK = Path('/content/drive/MyDrive/WindiSachNoi-Training/voice-001')
print('Thư mục dự kiến:', WORK)
print('Drive sẵn sàng:', Path('/content/drive/MyDrive').is_dir())
''')
md('''## 6. Nhận file bạn chọn
Bật khi đã có bản thu. Chỉ chọn một file WAV/M4A/MP3/FLAC. Audio sẽ được xử lý trên máy Colab của tài khoản này; không chia sẻ công khai. Giữ file gốc trên Mac nữa.
''')
code('''UPLOAD_RECORDING = False
if UPLOAD_RECORDING:
    if not Path('/content/drive/MyDrive').is_dir(): raise RuntimeError('Chọn nơi lưu bền vững ở bước 5 trước.')
    from google.colab import files
    incoming=files.upload()
    if len(incoming)!=1: raise RuntimeError('Chỉ chọn một bản thu.')
    import shutil
    name=next(iter(incoming))
    if Path(name).suffix.lower() not in {'.wav','.m4a','.mp3','.flac','.aac','.ogg'}: raise RuntimeError('Định dạng chưa hỗ trợ.')
    WORK.mkdir(parents=True,exist_ok=True)
    SOURCE=WORK/Path(name).name
    if SOURCE.exists(): raise RuntimeError('File đã tồn tại; không ghi đè bản gốc.')
    shutil.copy2(Path(name),SOURCE)
    print('Đã lưu bản thu được chọn:',SOURCE)
else:
    print('Đang chờ file của bạn. Không có audio nào được tải lên.')
''')
md('''## 7. Tách và chép lời
Xử lý trên máy Colab, lưu kết quả từng clip về Drive. Nếu ngắt, chạy lại với cùng file để tiếp tục; giữ các đoạn đã duyệt. Không tự khử nhạc hay tạo lại giọng gốc.
''')
code('''PREPARE_AUDIO = False
if PREPARE_AUDIO:
    if 'SOURCE' not in globals() or not SOURCE.is_file(): raise RuntimeError('Chưa chọn bản thu.')
    subprocess.run([str(PY),str(ROOT/'toolkit.py'),'prepare',str(SOURCE),'--root',str(WORK)],check=True)
else:
    print('Chưa tách audio: chờ bản thu được chọn.')
''')
md('''## 8. Nghe và duyệt lời từng clip
Giữ `originalText` riêng; sửa `text` cho đúng lời, đủ dấu tiếng Việt. Chỉ duyệt clip một người nói, không nhạc, không tiếng người khác. Không có nút tự duyệt toàn bộ.
''')
code('''import importlib.util
spec=importlib.util.spec_from_file_location('windi_training',ROOT/'toolkit.py')
kit=importlib.util.module_from_spec(spec); spec.loader.exec_module(kit)
if (WORK/'review.json').exists(): kit.review_ui(WORK)
else: print('Chưa có bản thu để duyệt.')
''')
md('''## 9. Chốt dataset
Chỉ lấy clip đã duyệt. Loại câu trùng, giữ 10% cuối bản thu làm bài nghe riêng, không đưa vào train. Piper giữ thêm 10% nội bộ cho validation. Chưa đủ 30 clip duyệt thì không tạo dataset.
''')
code('''BUILD_DATASET = False
if BUILD_DATASET: kit.make_dataset(WORK)
else: print('Chưa chốt dataset: chờ nghe và duyệt.')
''')
md('''## 10. Train thử có giới hạn
**Chỉ bật khi dữ liệu đã duyệt và bạn muốn bắt đầu dùng GPU.** Mặc định thử 300 bước, learning rate 3e-5, batch 4, FP32 để tương thích T4, tắt cắt khoảng lặng. Đây là pilot kiểm tra hướng học giọng, không phải số bước train đủ cho mọi bản thu. Lưu mỗi 100 bước và khi dừng có kiểm soát; ngắt đột ngột chỉ giữ checkpoint đã ghi xong. Chọn lại `RESUME` để tiếp tục. Đánh giá bằng nghe, không tự coi loss thấp là giọng đạt chất lượng.
''')
code('''START_TRAINING = False
MAX_STEPS = 300
RESUME = None  # ví dụ: str(WORK/'run/checkpoints/last.ckpt')
if START_TRAINING:
    if not Path('/content/drive/MyDrive').is_dir(): raise RuntimeError('Chưa có nơi lưu checkpoint bền vững.')
    if not (WORK/'dataset/report.json').is_file(): raise RuntimeError('Chưa có dataset đã duyệt.')
    command = ("import sys; sys.path.insert(0,"+repr(str(ROOT))+"); from toolkit import train; train("+
        repr(str(WORK))+","+repr(str(BASE_CKPT))+","+repr(str(WORK/'run'))+
        ",max_steps="+repr(MAX_STEPS)+",resume="+repr(RESUME)+")")
    subprocess.run([str(PY),'-c',command],check=True)
else:
    print('Train đang TẮT. Không dùng GPU để train khi chưa có dữ liệu.')
''')
md('''## 11. Xuất ONNX và đóng gói để thử trên Mac
Chọn checkpoint sau khi nghe; không tự chọn bản có loss thấp nhất. Gói gồm model, cấu hình, nguồn/giấy phép và bài nghe đối chiếu. Không có file thu gốc. Export chưa đồng nghĩa với đã kiểm thử chạy trong app.
''')
code('''EXPORT_MODEL = False
SELECTED_CKPT = WORK/'run/checkpoints/last.ckpt'
if EXPORT_MODEL:
    if not SELECTED_CKPT.is_file(): raise RuntimeError('Chưa có checkpoint để xuất.')
    OUT=WORK/'export'; OUT.mkdir(exist_ok=True)
    temp=OUT/'voice.partial.onnx'
    subprocess.run([str(PY),'-m','piper.train.export_onnx','--checkpoint',str(SELECTED_CKPT),
        '--output-file',str(temp)],check=True)
    subprocess.run([str(PY),'-c',"import onnx,sys; onnx.checker.check_model(sys.argv[1])",str(temp)],check=True)
    temp.replace(OUT/'voice.onnx')
    shutil.copy2(WORK/'run/voice.onnx.json',OUT/'voice.onnx.json')
    shutil.copy2(BASE/'MODEL_CARD',OUT/'DONOR_MODEL_CARD.txt')
    shutil.copy2(ROOT/'environment-lock.txt',OUT/'environment-lock.txt')
    (OUT/'ATTRIBUTION.txt').write_text('Piper: https://github.com/OHF-Voice/piper1-gpl (GPL-3.0)\\nDonor VAIS1000: '+PREFIX+'MODEL_CARD\\nDataset license in donor model card: CC BY 4.0\\nPrivate user recording not included.\\n')
    (OUT/'export-info.json').write_text(json.dumps(dict(sourceCheckpoint=str(SELECTED_CKPT.name),
        sha256=kit.digest(OUT/'voice.onnx'),bytes=(OUT/'voice.onnx').stat().st_size,
        checkpointRevision=REVISION,status='exported-not-yet-validated-on-mac'),indent=2))
    package=shutil.make_archive(str(WORK/'windi-voice-001'),'zip',OUT)
    print('Gói thử local:',package)
else:
    print('Chưa có model đã train để xuất.')
''')
md('''## 12. Nghe đối chiếu giọng gốc — chỉ sau khi có model
Tạo 5 cặp audio cùng lời từ phần holdout chưa đưa vào train. Nghe độ giống âm sắc, phát âm, giọng vùng miền và nhịp đọc. Bộ này có audio tham chiếu riêng tư, không nằm trong gói ONNX xuất ở trên. Không tự tăng/giảm tốc hay nâng cao độ để làm kết quả có vẻ giống. Chưa có file thật nên chưa đo độ giống giọng.
''')
code('''MAKE_COMPARISON = False
if MAKE_COMPARISON:
    kit.listening_pack(WORK, WORK/'export/voice.onnx', WORK/'private-comparison')
else:
    print('Chờ giọng đã train để tạo bài nghe A/B với bản gốc.')
''')
notebook = dict(nbformat=4, nbformat_minor=5, metadata=dict(
    colab=dict(name='Windi_SachNoi_Piper_CapCut.ipynb', provenance=[]),
    kernelspec=dict(name='python3',display_name='Python 3'), language_info=dict(name='python'),
    accelerator='GPU', gpuClass='standard'), cells=cells)
path=HERE/'Windi_SachNoi_GiongNho_Piper.ipynb'
path.write_text(json.dumps(notebook,ensure_ascii=False,indent=1)+'\n')
(HERE/'Windi_SachNoi_Piper_CapCut.ipynb').write_bytes(path.read_bytes())
print(path)
