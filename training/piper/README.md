# Thử model giọng sách nói nhỏ

Mục tiêu: fine-tune một giọng tiếng Việt trên Piper/VITS medium, xuất ONNX 22.050 Hz để đánh giá trên Mac. Không thay runtime, model hoặc dữ liệu của app hiện tại. Trạng thái hiện hành nằm trong `SETUP_STATUS.json`; các kết quả donor bên dưới là kiểm tra nền trước khi nhận bản thu.

## Pilot với bản thu thật ngày 18/10/2026

Đã nhận MP3 2 giờ 17 phút, giữ bản sao nguyên byte trong `data/voice-001/originals`. Gói riêng `data/voice-001/windi-pilot-input.zip` chứa 30 phút đầu bằng stream copy MP3, checksum/provenance và hai script. Không có khóa hay dữ liệu app trong gói.

`pilot.py` dùng large-v3 chép lời, small kiểm tra từng clip. Chỉ nhận clip không có cờ lỗi và hai model khớp toàn bộ từ có dấu, thêm ngưỡng confidence. Đây là chấp nhận tự động cho pilot được người dùng yêu cầu, **không phải đã nghe duyệt hoặc bảo đảm lời đúng**. Tối thiểu 60 clip khác nhau, tối đa 180 clip; giữ 10% riêng làm holdout, train giới hạn 300 global steps với optimizer mới. Piper dùng hai optimizer nên global steps không đồng nghĩa số batch/generator updates. Đã sửa lỗi decoder bằng `av==16.0.1`; PyAV 19.0.1 bỏ tham số `metadata_errors` mà faster-whisper 1.2.1 đang dùng.

Kết nối Drive gặp xác minh tài khoản. Pilot chuyển sang `/content/windi-pilot-private/voice-001`, phải tải model, preview và checkpoint về Mac trước khi máy ảo hết hạn. Không coi checkpoint trong `/content` là lưu trữ bền vững. Gói model tách khỏi gói nghe có bản thu tham chiếu riêng tư. Chưa chấm độ giống giọng trước khi nghe kết quả thật.

## Bản cập nhật cho audio đã làm sạch bằng CapCut

Notebook đang dùng: https://colab.research.google.com/drive/1x9WbNyHnPY6fRpSikH1AONqUKZpE0_kc — `Windi_SachNoi_Piper_CapCut.ipynb`, cấu hình T4 / runtime 2026.07, chưa kết nối GPU ở bản cập nhật này. Bản local được sinh cùng nội dung tại `Windi_SachNoi_Piper_CapCut.ipynb` và tên notebook cũ để tương thích các đường dẫn đã có.

- Không thêm denoise, lọc EQ, compressor, đổi cao độ hoặc tốc độ. Giữ bản gốc nguyên byte và chỉ chuyển bản làm việc sang mono PCM16 22.050 Hz theo kiến trúc donor.
- Tắt `trim_silence` của Piper để không tự cắt mất hơi thở và nghỉ trong từng clip. Tách clip ưu tiên câu/cụm có dấu câu và khoảng nghỉ, đánh dấu chỗ phải kiểm tra lại.
- Pilot learning rate 3e-5, batch 4, 300 bước, cache chuẩn bị riêng theo revision profile `capcut-clean-narration-v1`. Đây là cấu hình khởi đầu, chưa phải thông số tốt nhất cho bản thu chưa nhận.
- Dataset ghi checksum của từng clip; thay đổi audio/lời sau duyệt cần chốt lại. Dữ liệu không được chia sẻ công khai.
- Thêm `listening_pack`: tạo cặp bản gốc/bản sinh cùng lời từ holdout để nghe trực tiếp. Không chỉnh tốc độ/cao độ bản sinh để làm đẹp điểm so sánh. Audio tham chiếu riêng tư không nằm trong ZIP model.
- Đã qua 10 test công cụ và 26 core test. Bước A/B đã chạy với donor fixture offline: tạo WAV hợp lệ và bản tham chiếu giữ nguyên checksum. Chưa có file người dùng, chưa train theo profile này, chưa chấm độ giống giọng.

Notebook setup ban đầu: https://colab.research.google.com/drive/1shxz-Who6u3brsUW6VRq79jjrgceqqEh . Đã chạy setup trên runtime 2026.07 / Python 3.12, Tesla T4 15.360 MiB, Piper 1.8.0 và Torch 2.11.0+cu128. Checkpoint được xác minh checksum, nạp state dict strict thành công; ASR small khởi tạo thành công. Các bước nhận file, mount Drive, tạo dataset, train và export đều đang tắt. Notebook và đầu ra đã lưu, đã giải phóng máy GPU tạm sau kiểm tra; lần kết nối máy mới cần chạy lại setup. Drive chưa được cấp quyền và chưa chứa dữ liệu người dùng từ workflow này. Xem `SETUP_STATUS.json`.

Mở `Windi_SachNoi_GiongNho_Piper.ipynb` trong Colab bằng tài khoản của bạn. Notebook tự chứa công cụ và ghi chú; không phụ thuộc repo công khai của dự án này. Bước 1–4 cài dependency, tải checkpoint đã khóa/checksum và model chép lời. Chúng có thể chạy trên CPU. Chọn T4 GPU cho bước train sau khi có dữ liệu.

1. Cung cấp bản thu WAV/M4A/MP3 khoảng một giờ, một người nói. Chưa cần tự cắt. Giữ bản gốc trên Mac.
2. Khi thực sự dùng dữ liệu, tự cho phép mount Drive và dùng thư mục riêng `WindiSachNoi-Training/voice-001`. Không có dữ liệu nào tự upload trong setup. Không tạo public link hoặc push model lên Hub.
3. Chọn file cụ thể, chạy tách/chuyển lời. Whisper chạy trong máy Colab, không dùng API chép lời; processing trên Colab là cloud compute, không phải processing trên Mac. Giữ bản gốc, lưu từng clip hoàn tất và `originalText` riêng. Chạy lại tiếp tục mà không xóa lựa chọn đã duyệt.
4. Nghe từng clip, sửa `text`, duyệt những đoạn sạch và khớp lời. Không tự duyệt transcript. File `review.json` lưu sau mỗi lần duyệt.
5. Chốt dataset. Tối thiểu 30 clip khác nhau đã duyệt chỉ là điều kiện bắt đầu, không bảo đảm đủ dữ liệu/chất lượng. Giữ 10% cuối riêng làm bài nghe; Piper chia thêm validation nội bộ. Dữ liệu bị sửa sau khi chốt phải chốt lại.
6. Bắt đầu pilot 300 bước, batch 4, FP32; lưu mỗi 100 bước vào Drive. Chỉ checkpoint đã ghi xong mới dùng để resume. Dừng có kiểm soát lưu thêm `interrupted.ckpt`; bị xóa máy ảo đột ngột chỉ giữ các checkpoint hoàn tất trên Drive. Checkpoint nền dùng khởi tạo trọng số với optimizer mới; không resume epoch 4769 của tác giả.
7. Nghe các checkpoint trên lời mới và bài đọc dài. Chọn checkpoint rồi xuất ONNX + config + provenance/attribution. Kiểm tra ONNX, audio, tốc độ và RAM trên Mac trước khi quyết định tích hợp app. Chưa coi export là bằng chứng app tương thích hoặc giọng đạt chất lượng.

Dung lượng ONNX donor khoảng 63 MB, checkpoint train 845.898.392 bytes. Model riêng sau train chưa đo. Thư viện train/Whisper/checkpoint không thuộc gói runtime đọc sách.

## Nguồn và quyền sử dụng

- Piper hiện tại: https://github.com/OHF-Voice/piper1-gpl — runtime/code GPL-3.0; không tự suy diễn rằng model hoặc app hiện tại cùng giấy phép.
- PyPI: `piper-tts[train]==1.8.0`; `faster-whisper==1.2.1`; `soundfile==0.13.1`. Notebook ghi `pip freeze` cho đúng môi trường đã cài; dependency gián tiếp có thể thay đổi giữa máy mới.
- Checkpoint: https://huggingface.co/datasets/rhasspy/piper-checkpoints/tree/37d1bea250e21ca0d617818d2bef1db724edb80c/vi/vi_VN/vais1000/medium
- SHA-256 checkpoint: `c3879268594a85b5133146e6a4709a5cc2f3014ef0eabf9280f67289054ba2bc`.
- Model card VAIS1000 ghi một giọng, 22.050 Hz, dữ liệu CC BY 4.0, fine-tune từ lessac medium. Giữ attribution trong gói xuất. Thử nghiệm này chưa phải quyết định phát hành/phân phối.

## Kiểm tra local

```sh
python3 training/piper/build_notebook.py
python3 -m unittest discover -s training/piper -p 'test_*.py'
```

Fixture nằm trong `.qa/training-tests`, không chứng minh chất lượng giọng thật. Không cài PyTorch/Piper vào `.runtime` của app.

## Kiểm tra suy luận donor trên Mac

Đã cài `piper-tts==1.8.0` trong `.qa/piper-probe/venv`, tải donor ONNX 63.201.294 bytes từ revision `c10ece1aade47bb51c153c893d14e5bf8e5b7117` và đối chiếu SHA-256. `probe_local.py` chặn kết nối mạng trước khi load/suy luận, tạo WAV mono PCM16 22.050 Hz. Bài mẫu 10,147 giây tạo trong 0,600 giây, load 1,229 giây; peak process khoảng 245 MB trong bài ngắn này. Môi trường QA cài khoảng 181 MiB, model khoảng 60 MiB; không phải đo bộ nhớ của cả app hoặc model giọng người dùng. Kết quả ở `.qa/piper-probe/local-proof.json` và `.qa/piper-probe/sample-vietnamese.wav`.
