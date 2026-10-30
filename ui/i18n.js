'use strict';
// Translate app controls only. Book text, book/chapter titles and voice names
// are source data and must never pass through the interface translator.
(()=>{
const entries=[
['Tùy chọn khác','More options'],['Chọn sách để bắt đầu.','Choose a book to begin.'],['Chọn hoặc kéo sách vào đây để đọc và nghe.','Choose or drop a book here to read and listen.'],['Ảnh','Images'],['Ẩn ưu đãi ra mắt','Hide launch offer'],['Ẩn ưu đãi','Hide offer'],
['Trang chủ','Home'],['Về Trang chủ','Go home'],['Thông tin ứng dụng','About this app'],['Đóng thông tin ứng dụng','Close app information'],['Đọc sách','Read book'],['Chọn giọng, tạo bản nghe','Choose a voice, create audio'],['Mở trang sách, đọc & nghe','Open pages, read & listen'],['Kéo thả EPUB, PDF hoặc ảnh vào đây.','Drop an EPUB, PDF or image here.'],['Đọc sách hoặc tạo bản nghe theo cách của bạn.','Read or create an audiobook your way.'],['Ngôn ngữ','Language'],['Quản lý giọng','Manage voices'],['Sách được lưu trên Mac','Books are stored on your Mac'],['Lite miễn phí trên Mac. Pro thanh toán theo từng cuốn sách.','Lite is free on your Mac. Pro is paid per book.'],['Lite / Pro · Giá theo cuốn','Lite / Pro · Per-book pricing'],['Pro Cloud · Trả theo cuốn, nghe trên Mac','Pro Cloud · Pay per book, listen on Mac'],
['Nơi những trang sách hóa thanh âm','Where book pages turn into sound'],['Tìm sách trong thư viện','Search your library'],['Tìm trong thư viện','Search library'],['Thư viện của bạn','Your library'],['Không tìm thấy sách.','No books found.'],['Thêm sách mới','Add a book'],['Phông chữ','Font'],['Tùy chọn nhập','Import options'],['Ngôn ngữ sách mới','New book language'],['Ngôn ngữ sách','Book language'],['Ngôn ngữ giao diện','Interface language'],['Tiếng Việt','Vietnamese'],['OCR toàn bộ trang','OCR every page'],['Dùng khi PDF có lớp chữ lỗi hoặc thiếu nội dung.','Use when a PDF text layer is incomplete or incorrect.'],['Chỉ trên máy của bạn','On your device'],['Đang kiểm tra giọng đọc…','Checking voice resources…'],['Model giọng đọc','Voice models'],['Mở thư mục thư viện','Open library folder'],['Thư viện','Library'],['Sách của bạn','Your books'],['Góc nghe của bạn','Your listening space'],['Giao diện','Appearance'],['Theo hệ thống','System default'],['Sáng','Light'],['Sáng dịu','Soft light'],['Giấy ấm','Warm paper'],['Tối','Dark'],['Chuyển động','Motion'],['Bật','On'],['Giảm chuyển động','Reduce motion'],['Thiết lập được lưu trên máy.','Settings are saved on this device.'],['Đang kiểm tra cấu hình máy…','Checking this Mac…'],['Chưa có model · mở Model giọng đọc để tải','No model installed · open Voice models to download one'],
['Chỉ tải khi bạn chọn. Sau khi tải xong, chữ và giọng đọc được xử lý trên máy. Mức RAM bên trên là khuyến nghị của app; tốc độ còn tùy máy và độ dài câu.','Downloads start only when you choose. Once installed, text and speech are processed on your device. RAM values are app recommendations; speed depends on your Mac and sentence length.'],
['Một trang sách.','One page.'],['Một thế giới.','A whole world.'],['Sách của bạn. Giọng đọc của bạn.','Your books. Your voice.'],['Mở một cuốn sách.','Open a book.'],['Lắng nghe cả thế giới.','Listen to a whole world.'],['Biến EPUB, PDF và ảnh chụp thành những trang sách biết kể chuyện.','Turn EPUBs, PDFs and photos into audiobooks.'],['Chọn tài liệu, kiểm tra chữ và bắt đầu nghe.','Choose a document, check the text and start listening.'],['Chọn EPUB, PDF hoặc ảnh','Choose EPUB, PDF or images'],['PDF có chữ','Text PDF'],['PDF scan','Scanned PDF'],['Ảnh chụp','Photos'],['Giọng đọc cần tải một lần. Sau đó, bạn có thể nghe hoàn toàn trên máy.','Download a voice model once, then generate speech on your device.'],['Đang mở trong thư viện','Open in your library'],['Bản gốc','Original'],['Chọn chất lượng / tải thêm','Quality / downloads'],['Giọng đọc','Voice'],['Tốc độ','Speed'],['0,75×','0.75×'],['1,25×','1.25×'],['1,5×','1.5×'],['Tạo giọng','Generate speech'],['Nhạc nền','Background music'],['Tải về','Download'],['Nội dung sách','Book contents'],['Chuyển đến chương','Jump to chapter'],['Nội dung đoạn đang chọn','Selected segment text'],['Bạn có thể sửa chữ trước khi nghe.','You can edit the text before listening.'],['Khôi phục bản gốc','Restore original'],['Lưu chữ','Save text'],['Audio được tạo từng đoạn để bạn nghe sớm.','Speech is generated in segments so you can listen sooner.'],['Hủy tạo audio','Cancel generation'],['Hoàn thiện sách nói','Create your audiobook'],['Phạm vi','Scope'],['Tạo giọng đọc cho','Generate speech for'],['Toàn bộ sách','Whole book'],['Trang đang đọc','Current page'],['Mục đang đọc','Current section'],['Khoảng trang','Page range'],['Khoảng mục','Section range'],['Theo chương','By chapter'],['Từ trang','From page'],['Đến trang','To page'],['Từ mục','From section'],['Đến mục','To section'],['Chọn chương','Chapter'],['Tạo giọng đọc','Generate speech'],['Đặt hoặc sửa mốc chương','Add or edit chapter markers'],['Chương bắt đầu từ trang đang đọc.','The chapter starts on the current page.'],['Tên chương','Chapter title'],['Tên chương, ví dụ: Chương 1','Chapter title, e.g. Chapter 1'],['Lưu mốc ở trang này','Save marker on this page'],['Lưu mốc ở mục này','Save marker in this section'],['Bỏ mốc đã chọn','Remove selected marker'],['Nhạc không lời','Music track'],['Không dùng nhạc nền','No background music'],['Nhạc được trộn vào cả bản nghe và file tải về.','Music is included in playback and downloaded audio.'],['Âm lượng nhạc','Music volume'],['Âm lượng nhạc nền','Background music volume'],['Nghe thử nhạc','Preview music'],['Dừng nghe thử','Stop preview'],['Giữ nhạc nhỏ hơn lời đọc.','Keep music quieter than the narration.'],['Nhạc có sẵn trên máy, không cần tải thêm. Đổi nhạc không cần tạo lại giọng.','Tracks are stored locally. Changing music does not regenerate speech.'],['Định dạng','Format'],['M4A · Nhẹ, dùng trên điện thoại','M4A · Compact, for phones'],['WAV · Âm thanh chưa nén','WAV · Uncompressed audio'],['Gói nghe web · ZIP','Web player package · ZIP'],['Một file gồm lời đọc và nhạc nền đã chọn.','One file with narration and your selected background music.'],['Hủy xuất file','Cancel export'],['Sẵn sàng nghe','Ready to listen'],['Vị trí trong đoạn','Position in segment'],['đoạn trong sách','segments in this book'],['Hiển thị và chuyển động','Appearance and motion'],['Đóng model giọng đọc','Close voice models'],['Đóng tùy chọn','Close options'],['Các đoạn trong sách','Book segments'],['Thư viện sách','Book library'],['Các đoạn trước','Previous segments'],['↑ Các đoạn trước','↑ Earlier segments'],['Các đoạn sau ↓','Later segments ↓'],['Phát','Play'],['Tạm dừng','Pause'],['Đoạn trước','Previous segment'],['Đoạn tiếp theo','Next segment'],['Model đang dùng','Selected model'],['Chọn nhạc nền','Choose background music'],['Tùy chọn sách nói','Audiobook options'],['Tạo sách nói và tải về','Create and download audiobook'],
['Audio sẵn sàng','Audio ready'],['Chưa tạo audio','No audio yet'],['Audio được lưu trên máy. Đổi tốc độ không cần tạo lại.','Audio is stored locally. Changing speed does not regenerate it.'],['Chữ gốc được giữ lại để đối chiếu.','The original text is kept for comparison.'],['Chưa lưu · lưu trước khi nghe.','Unsaved · save before listening.'],['Đã tạo đủ giọng đọc','Speech complete'],['Đã lưu file có nhạc nền theo thiết lập hiện tại.','Saved with your current background music settings.'],['Đang hoàn tất file audio…','Finishing the audio file…'],['Đã nghe hết phạm vi đang chọn.','You have finished the selected scope.'],['Bạn đã nghe hết sách.','You have finished the book.'],['Đang chuẩn bị giọng đọc…','Preparing speech…'],['Lưu chữ đã sửa trước khi đổi đoạn hoặc bắt đầu nghe.','Save your edits before changing segments or listening.'],['Chưa nhận được đoạn chữ. Hãy kiểm tra bản gốc hoặc tiếp tục trích chữ.','No text found yet. Check the original or resume extraction.'],['Mỗi đoạn cần từ 1 đến 2.000 ký tự.','Each segment needs 1–2,000 characters.'],['Nhập tên chương trước khi lưu mốc.','Enter a chapter title before saving a marker.'],['Mục này chưa được trích chữ xong.','This section has not finished importing.'],['Chưa chọn chương','No chapter selected'],['Tiếp tục trích chữ','Resume extraction'],['Hủy trích chữ','Cancel extraction'],['Audio phát bị gián đoạn. Bấm nghe để thử lại.','Playback was interrupted. Press Play to try again.'],
['VieNeu Nano sẵn sàng · Không cần mạng','VieNeu Nano ready · Offline'],['VieNeu Turbo sẵn sàng · Không cần mạng','VieNeu Turbo ready · Offline'],['KittenTTS Mini sẵn sàng · Không cần mạng','KittenTTS Mini ready · Offline'],['Chọn Model giọng đọc để tải tài nguyên','Open Voice models to download resources'],['VieNeu Turbo · Chất lượng cao','VieNeu Turbo · High quality'],['Nhẹ và nhanh. Ngữ điệu đơn giản hơn, phù hợp nghe thử hoặc máy ít RAM.','Light and fast. Simpler intonation, suitable for previews or Macs with less RAM.'],['Bản FP32, giọng và ngữ điệu phong phú hơn. Có thể tạo chậm hơn Nano; nên nghe thử trước khi tạo cả sách.','FP32 model with richer voices and intonation. May generate more slowly than Nano; preview before creating a whole book.'],['Chuyên tiếng Anh, 8 giọng nam/nữ. Gói model nhỏ, chạy trên CPU và không cần PyTorch.','English model with 8 male and female voices. Small download, runs on CPU without PyTorch.'],['Phù hợp với máy này','Recommended for this Mac'],['Đã tải trên máy','Installed on this device'],['Dùng cho sách này','Use for this book'],['Đang dùng cho sách này','Selected for this book'],['Đã tải','Installed'],['Hủy tải · giữ phần đã tải','Cancel · keep downloaded data'],['Cần Mac Apple Silicon, RAM từ 8 GB','Requires Apple Silicon and at least 8 GB RAM'],['Cần thêm dung lượng trống trước khi tải.','Free up disk space before downloading.'],['Đã tải và xác minh','Downloaded and verified'],['Đang tải','Downloading'],['Kiểm tra tệp','Verifying file'],['Cần tải trước khi nghe','Download before listening'],['Chưa tải','Not downloaded'],['Tải / tiếp tục tải','Download / resume'],
['Một file gồm lời đọc và nhạc nền đã chọn. M4A dễ mang sang điện thoại và máy tính khác.','One file with narration and selected music. M4A works on phones and other computers.'],['Gồm audio M4A có nhạc, nội dung và trình nghe web. Có thể đưa lên hosting; chưa bao gồm tài khoản hoặc dịch vụ lưu trữ online.','Includes M4A audio with music, text and a web player. You can host these files; accounts and cloud storage are not included.'],['Một số dòng OCR có độ tin cậy thấp. Hãy đối chiếu bản gốc.','Some OCR lines have low confidence. Compare them with the original.'],['OCR cần được kiểm tra dấu và thứ tự cột trước khi nghe.','Check OCR spelling and column order before listening.'],['Trang trống hoặc không nhận được chữ. Hãy kiểm tra bản gốc.','Empty page or no recognized text. Check the original.'],['EPUB chia theo mục nội dung, không phải số trang của bản in.','EPUB sections follow the content structure, not printed page numbers.'],['EPUB này được lấy chữ trực tiếp, không OCR ảnh bên trong.','Text is extracted directly; images inside this EPUB are not OCR processed.'],['Ngôn ngữ sách không hợp lệ.','Invalid book language.'],['Hãy trích chữ xong trước khi đổi ngôn ngữ sách.','Finish extraction before changing the book language.'],['Hãy tải model này trước khi sử dụng.','Download this model before using it.'],['Hãy hủy tạo/xuất audio trước khi sửa chữ hoặc đổi giọng.','Cancel generation or export before changing text, model or voice.'],['Tài nguyên model thiếu hoặc checksum sai. Mở Model giọng đọc để tải lại.','Model files are missing or corrupted. Open Voice models to download them again.'],['Chỉ đổi cách nhận chữ và giọng đọc, không dịch nội dung sách.','Changes OCR and voice selection; it does not translate the book.']
];
entries.push(['Chọn phạm vi','Choose scope'],['Tạo toàn bộ sách','Create entire book'],['Chọn chương để tạo riêng, hoặc bấm “Tạo toàn bộ sách” để tạo cả cuốn.','Choose a chapter to generate separately, or create the entire book.']);
entries.push(['Dọn chữ · ghép dòng','Clean text · reflow lines'],['Đang tự dọn chữ và ghép dòng','Cleaning text and joining wrapped lines'],['Tự nối dòng, bỏ ký hiệu trang trí và nhận diện chương.','Joining wrapped lines, removing decorative marks and detecting chapters.']);
entries.push(...[
 [
  "Audio không hợp lệ.",
  "Invalid audio."
 ],
 [
  "Bản nhạc nền không có trong thư viện.",
  "This music track is not available."
 ],
 [
  "Chưa đủ dung lượng trống để tải model.",
  "Not enough disk space to download this model."
 ],
 [
  "Chương này chưa được trích chữ xong. Tiếp tục trích chữ trước khi tạo cả chương.",
  "This chapter has not finished importing. Resume extraction before generating the whole chapter."
 ],
 [
  "Chỉ chọn thư mục sách có đuôi .epub.",
  "Choose a book folder with the .epub extension."
 ],
 [
  "Chỉ hỗ trợ thư mục sách có đuôi .epub.",
  "Only folders with the .epub extension are supported."
 ],
 [
  "Chọn EPUB, PDF hoặc ảnh PNG/JPEG/HEIC/TIFF/WebP.",
  "Choose EPUB, PDF or PNG/JPEG/HEIC/TIFF/WebP images."
 ],
 [
  "Chọn M4A, WAV hoặc gói nghe web ZIP.",
  "Choose M4A, WAV or a web player ZIP."
 ],
 [
  "Chọn chương từ mục lục hoặc đặt mốc chương trước.",
  "Choose a chapter from the contents or add a marker first."
 ],
 [
  "Chọn lại giọng trong danh sách.",
  "Select a voice from the list."
 ],
 [
  "Chọn số trang hợp lệ.",
  "Enter valid page numbers."
 ],
 [
  "Chọn thư mục EPUB thật, không dùng liên kết symbolic.",
  "Choose the EPUB folder itself, not a symbolic link."
 ],
 [
  "Chọn từ 1 đến 2.000 ảnh hoặc một EPUB/PDF.",
  "Choose 1–2,000 images or one EPUB/PDF."
 ],
 [
  "Công việc này đang chạy. Hủy hoặc chờ hoàn tất.",
  "This job is already running. Cancel it or wait for it to finish."
 ],
 [
  "Cấu hình máy chưa phù hợp với model này.",
  "This Mac does not meet the model requirements."
 ],
 [
  "Cần trích chữ xong trước khi xuất cả sách.",
  "Finish extraction before exporting the whole book."
 ],
 [
  "EPUB chứa khai báo XML entity không được hỗ trợ.",
  "This EPUB contains unsupported XML entity declarations."
 ],
 [
  "EPUB chứa đường dẫn nằm ngoài sách.",
  "This EPUB contains a path outside the book."
 ],
 [
  "EPUB chứa đường dẫn tài nguyên không hợp lệ.",
  "This EPUB contains an invalid resource path."
 ],
 [
  "EPUB có mục đọc không phải HTML; chưa hỗ trợ loại nội dung này.",
  "This EPUB includes unsupported non-HTML content."
 ],
 [
  "EPUB có tên tài nguyên trùng nhau.",
  "This EPUB contains duplicate resource names."
 ],
 [
  "EPUB không có chữ đọc được. Sách chỉ chứa ảnh cần chuyển sang PDF/ảnh để OCR.",
  "This EPUB has no readable text. Convert an image-only book to PDF/images for OCR."
 ],
 [
  "EPUB quá lớn để nhập an toàn (tối đa 512 MB / 20.000 tệp).",
  "EPUB exceeds the import limit (512 MB / 20,000 files)."
 ],
 [
  "EPUB thiếu một mục trong manifest.",
  "An EPUB spine item is missing from the manifest."
 ],
 [
  "EPUB thiếu package document.",
  "EPUB package document is missing."
 ],
 [
  "EPUB thiếu thứ tự đọc (spine).",
  "EPUB reading order (spine) is missing."
 ],
 [
  "EPUB được mã hóa hoặc đặt mật khẩu; cần bản EPUB không khóa.",
  "This EPUB is encrypted or password protected. Use an unlocked copy."
 ],
 [
  "File EPUB không phải gói ZIP hợp lệ.",
  "This EPUB is not a valid ZIP package."
 ],
 [
  "File vượt giới hạn WAV 4 GB. Hãy xuất từng chương hoặc khoảng trang nhỏ hơn.",
  "The file exceeds the WAV 4 GB limit. Export a chapter or a smaller range."
 ],
 [
  "Giọng này không có trong model đang chọn.",
  "This voice is not available in the selected model."
 ],
 [
  "Giọng tiếng Anh không hợp lệ.",
  "Invalid English voice."
 ],
 [
  "HTML trong EPUB lồng quá sâu.",
  "HTML in this EPUB is nested too deeply."
 ],
 [
  "Hãy chờ hoặc hủy lần nhập hiện tại.",
  "Wait for the current import or cancel it."
 ],
 [
  "Hãy chờ hoặc hủy xuất file trước khi đổi nhạc.",
  "Wait for the export or cancel it before changing music."
 ],
 [
  "Hãy tạo đủ giọng đọc trong phạm vi đang chọn trước khi tải về.",
  "Generate all speech in the selected scope before downloading."
 ],
 [
  "Khoảng trang chưa được trích chữ hoặc không hợp lệ.",
  "The selected range is invalid or has not finished importing."
 ],
 [
  "Không trích được tài liệu. Hãy kiểm tra EPUB/PDF/ảnh.",
  "Could not extract this document. Check the EPUB/PDF/image."
 ],
 [
  "Không đọc được mã hóa chữ trong EPUB.",
  "Could not decode the text encoding in this EPUB."
 ],
 [
  "Model không hợp lệ.",
  "Invalid model."
 ],
 [
  "Model này cần Mac Apple Silicon với ít nhất 8 GB RAM.",
  "This model requires Apple Silicon with at least 8 GB RAM."
 ],
 [
  "Máy chủ trả vị trí tải không đúng. Hãy thử tải lại.",
  "The server returned an incorrect download range. Try downloading again."
 ],
 [
  "Mã sách không hợp lệ.",
  "Invalid book ID."
 ],
 [
  "Mỗi lần chọn một EPUB/PDF hoặc nhiều ảnh.",
  "Choose one EPUB/PDF or several images at a time."
 ],
 [
  "Mỗi đoạn cần từ 1 đến 2.000 ký tự. Chia đoạn dài hơn trước khi nhập.",
  "Each segment needs 1–2,000 characters. Split longer passages before entering them."
 ],
 [
  "Một model đang được tải. Hãy chờ hoặc hủy trước.",
  "A model download is already running. Wait or cancel it first."
 ],
 [
  "Nội dung EPUB bị mã hóa/DRM; cần bản EPUB không khóa.",
  "EPUB content is encrypted/DRM protected. Use an unlocked copy."
 ],
 [
  "Nội dung EPUB vượt giới hạn đọc (16 MB mỗi mục / 128 MB tổng).",
  "EPUB exceeds the reading limit (16 MB per resource / 128 MB total)."
 ],
 [
  "Phạm vi không hợp lệ.",
  "Invalid scope."
 ],
 [
  "Phạm vi này chưa có đoạn chữ để xuất.",
  "There is no text to export in this scope."
 ],
 [
  "Phạm vi đang chọn chưa có đoạn chữ.",
  "There is no text in the selected scope yet."
 ],
 [
  "Thao tác không hợp lệ.",
  "Invalid action."
 ],
 [
  "Thư mục EPUB chứa symbolic link không được hỗ trợ.",
  "EPUB folders containing symbolic links are not supported."
 ],
 [
  "Trang mở đầu chương không hợp lệ.",
  "Invalid chapter start page."
 ],
 [
  "Tên chương cần từ 1 đến 160 ký tự.",
  "Chapter titles need 1–160 characters."
 ],
 [
  "Tạo giọng bị gián đoạn. Bấm nghe để thử lại đoạn chưa xong.",
  "Speech generation was interrupted. Press Play to retry incomplete segments."
 ],
 [
  "Tải model bị gián đoạn. Bấm tải tiếp để giữ phần đã tải.",
  "The model download was interrupted. Resume to keep downloaded data."
 ],
 [
  "Tần số audio không khớp model đang chọn. Hãy tạo lại đoạn này.",
  "Audio sample rate does not match the selected model. Regenerate this segment."
 ],
 [
  "Tệp tải vượt dung lượng đã xác minh.",
  "The download exceeds its verified file size."
 ],
 [
  "Vị trí nghe không hợp lệ.",
  "Invalid playback position."
 ],
 [
  "Windi Sách Nói: kết nối mạng bị tắt khi đọc sách.",
  "Windi Sách Nói: network access is disabled during speech generation."
 ],
 [
  "Xuất ra ngoài thư viện để giữ an toàn dữ liệu.",
  "Export outside the library to protect your book data."
 ],
 [
  "Âm lượng nhạc cần từ 0 đến 50%.",
  "Music volume must be between 0 and 50%."
 ],
 [
  "Đoạn nghe không hợp lệ.",
  "Invalid playback segment."
 ],
 [
  "Đoạn này chưa tạo được tiếng hợp lệ. Hãy kiểm tra chữ rồi thử lại.",
  "This segment did not produce valid speech. Check the text and try again."
 ],
 [
  "Đoạn tiếng Anh tạo ra quá ngắn. Hãy thử lại.",
  "English audio was too short. Try generating it again."
 ],
 [
  "Đã hủy xuất audio.",
  "Audio export cancelled."
 ],
 [
  "Đường dẫn EPUB nằm ngoài sách.",
  "The EPUB path points outside the book."
 ]
]);
entries.push(...[["Chương sách", "Chapters"], ["Nội dung cả chương", "Full chapter text"], ["Sách nói của bạn", "Your audiobooks"], ["Không gian sách", "Book workspace"], ["Toàn bộ chương · có thể xóa bớt trước khi tạo.", "Full chapter · remove anything you do not want to narrate."], ["Dọn nội dung", "Clean up text"], ["Hủy sửa", "Discard edits"], ["Lưu nội dung", "Save content"], ["Tạo nhanh nội dung này", "Generate this text"], ["Đang lưu…", "Saving…"], ["Dọn nội dung trên máy", "Clean up text on your device"], ["Xem trước dọn nội dung", "Preview text cleanup"], ["Đóng", "Close"], ["Chỉ bỏ những dòng được liệt kê bên dưới. Hãy kiểm tra trước khi áp dụng; bản gốc luôn được giữ lại.", "Only the lines listed below will be removed. Review before applying; the original is always preserved."], ["Dòng chấm / ký hiệu trang trí", "Dot leaders / decorative lines"], ["Dòng chỉ có số trang", "Standalone page numbers"], ["Đầu / cuối trang lặp lại", "Repeated page headers / footers"], ["Mục lục có dòng chấm và số trang", "Table of contents with dot leaders and page numbers"], ["Áp dụng vào ô soạn thảo", "Apply to editor"], ["Đang kiểm tra các dòng thừa…", "Checking removable lines…"], ["Không tìm thấy dòng phù hợp với bộ lọc đã chọn.", "No lines match the selected filters."], ["Mỗi lần tạo được lưu riêng. Sửa nội dung hoặc đổi giọng vẫn giữ được bản đã tạo.", "Each generation is saved separately. Editing text or changing voices keeps earlier versions."], ["Định dạng tải", "Download format"], ["Nghe và tải về dùng nhạc nền đang chọn cho cuốn sách này.", "Playback and downloads use this book’s selected background music."], ["Chưa có sách nói. Chọn một chương, kiểm tra nội dung rồi bấm Tạo nhanh.", "No audiobooks yet. Choose a chapter, review the text, then generate it."], ["Nghe bản này", "Listen"], ["Chọn giọng bạn thích", "Find your voice"], ["Mẫu ngắn chạy trên máy, dùng cùng một câu để bạn dễ so sánh. Không dùng nội dung sách.", "Short local samples use the same sentence for easy comparison, without using book content."], ["Đóng nghe thử giọng", "Close voice previews"], ["Nghe thử", "Preview"], ["Đang chọn", "Selected"], ["Chọn giọng", "Choose voice"], ["Chưa có nội dung. Tiếp tục trích chữ để xem chương.", "No content yet. Resume extraction to view chapters."], ["Chưa lưu · Tạo nhanh sẽ lưu và tạo đúng nội dung trong ô này.", "Unsaved · Generate saves and narrates exactly the text in this editor."], ["Lưu nội dung hoặc hủy sửa trước khi đổi chương hay bắt đầu nghe.", "Save or discard your edits before switching chapters or listening."], ["Nội dung này chưa có chữ để tạo giọng.", "There is no text to narrate."], ["Đang tạo đúng nội dung chương. Bản tạo sẽ có trong Sách nói của bạn.", "Generating this chapter’s text. Find the result in Your audiobooks."], ["Hãy trích chữ xong trước khi sửa nội dung chương.", "Finish extraction before editing chapter content."], ["Mỗi chương tối đa 500.000 ký tự.", "Each chapter supports up to 500,000 characters."], ["Nội dung đã thay đổi ở nơi khác. Mở lại chương trước khi lưu.", "The content changed elsewhere. Reopen the chapter before saving."], ["Phần này chỉ có ký hiệu trang trí. Dọn nội dung trước khi tạo.", "This section only contains decorative symbols. Clean up the text before generating speech."], ["Chương không còn tồn tại. Mở lại sách để tiếp tục.", "This chapter no longer exists. Reopen the book to continue."], ["Hãy chờ hoặc hủy tạo audio trước khi nghe thử giọng.", "Wait for generation to finish or cancel it before previewing a voice."]]);
entries.push(
 ['Tùy chọn nghe','Listening options'],['Tốc độ nghe','Playback speed'],
 ['Nhận chữ từ ảnh trên mọi trang PDF','Recognize text from images on every PDF page'],
 ['OCR là nhận chữ từ ảnh. Mặc định, app lấy chữ có sẵn trong PDF và tự nhận chữ ở trang không có chữ. Chỉ bật khi PDF bị lỗi hoặc thiếu chữ; xử lý sẽ lâu hơn. Ảnh chụp luôn được nhận chữ; EPUB lấy chữ trực tiếp.','OCR recognizes text from images. By default, the app extracts existing PDF text and recognizes pages with no text automatically. Enable only for PDFs with broken or missing text; processing takes longer. Photos always use OCR; EPUB text is extracted directly.']
);
entries.push(...[["Đóng thanh toán", "Close payment"], ["Đang tạo mã QR…", "Creating QR code…"], ["Quét bằng ứng dụng ngân hàng", "Scan with your banking app"], ["QR đã điền số tiền và nội dung", "The amount and payment code are filled in"], ["cho máy của bạn.", "for this Mac."], ["Chuyển khoản ngân hàng · VietQR", "Bank transfer · VietQR"], ["THÊM TURBO VÀO THƯ VIỆN CỦA BẠN", "ADD TURBO TO YOUR LIBRARY"], ["Nghe sách với Turbo.", "Listen with Turbo."], ["Giọng đọc 48 kHz. Tạo và nghe audio trên máy sau khi tải model.", "48 kHz speech. Generate and listen on your Mac after downloading the model."], ["/ năm", "/ year"], ["Cho 1 máy · Không tự động gia hạn", "For 1 Mac · No automatic renewal"], ["Ngân hàng", "Bank"], ["Số tài khoản", "Account number"], ["Sao chép số tài khoản", "Copy account number"], ["Người nhận", "Recipient"], ["Nội dung chuyển khoản", "Payment code"], ["Sao chép nội dung chuyển khoản", "Copy payment code"], ["Giữ nguyên nội dung để nhận đúng bản quyền.", "Keep this code unchanged to receive your license."], ["Sau khi chuyển khoản, kiểm tra để nhận Pro.", "After transferring, check to activate Pro."], ["Đã chuyển khoản · Kiểm tra", "Transferred · Check payment"], ["Bản quyền chỉ được cấp sau khi tiền vào được xác nhận.", "A license is issued only after payment is confirmed."], ["Đang kiểm tra thanh toán…", "Checking payment…"], ["Đã sao chép số tài khoản.", "Account number copied."], ["Đã sao chép mã máy.", "Device code copied."], ["Pro đã sẵn sàng.", "Pro is ready."], ["Bạn có thể tải Turbo và tiếp tục nghe sách.", "Download Turbo and keep listening."], ["Tiếp tục với Pro", "Continue with Pro"], ["Chưa có bản quyền cho mã máy này. Sau khi tiền vào được xác nhận, hãy thử lại.", "No license for this Mac yet. Try again after your payment is confirmed."], ["Dịch vụ bản quyền đang chưa sẵn sàng. Hãy thử lại sau.", "The license service is unavailable. Please try again later."], ["Chưa kết nối được nơi cấp bản quyền. Hãy thử lại sau.", "Could not reach the license service. Please try again later."]]);
entries.push(...[["Thả sách vào đây", "Drop your book here"], ["Một EPUB, một PDF hoặc nhiều ảnh", "One EPUB, one PDF or several images"], ["Kéo thả EPUB, PDF hoặc ảnh vào cửa sổ", "Drag an EPUB, PDF or images into this window"], ["Đóng cửa sổ đang mở trước khi thêm sách.", "Close the open dialog before adding a book."]]);
entries.push(...[["Nhạc đã chọn · Chưa có trên máy này", "Selected music · Unavailable on this Mac"], ["Nhạc đã chọn không có trên máy này. Chọn nhạc khác trước khi nghe kèm hoặc xuất file.", "The selected music is unavailable on this Mac. Choose another track before mixing or exporting."], ["Thêm VieNeu Turbo 48 kHz và 8 giọng tiếng Việt đã train.", "Adds VieNeu Turbo at 48 kHz and eight trained Vietnamese voices."], ["Tám giọng tiếng Việt đã train, xử lý hoàn toàn trên máy. Có trong bản Pro.", "Eight trained Vietnamese voices, processed entirely on your Mac. Included with Pro."]]);
entries.push(['Thả EPUB, PDF hoặc ảnh vào đây','Drop an EPUB, PDF or images here'],['Thả để mở sách','Drop to open book']);
entries.push(...[
 [
  "Gói giọng đọc",
  "Voice packs"
 ],
 [
  "Gói giọng đang dùng",
  "Selected voice pack"
 ],
 [
  "Chọn gói giọng",
  "Choose voice pack"
 ],
 [
  "Đóng gói giọng đọc",
  "Close voice packs"
 ],
 [
  "Tạo bản đọc chương này",
  "Create chapter audio"
 ],
 [
  "Tạo sách nói",
  "Create audiobook"
 ],
 [
  "Dọn nội dung",
  "Clean up text"
 ],
 [
  "Gói Free / Pro",
  "Free / Pro plans"
 ],
 [
  "Mã kích hoạt cho Mac này:",
  "Activation code for this Mac:"
 ],
 [
  "Sao chép mã",
  "Copy code"
 ],
 [
  "Cập nhật Pro đã mua",
  "Restore purchased Pro"
 ],
 [
  "Đang cập nhật Pro…",
  "Updating Pro…"
 ],
 [
  "Bạn đang dùng bản trải nghiệm trên máy này.",
  "You are using a local preview."
 ],
 [
  "Chọn một gói giọng để bắt đầu nghe",
  "Choose a voice pack to start listening"
 ],
 [
  "Quét QR trong app. Pro tự mở khi giao dịch được xác nhận. Không cần tài khoản hoặc email.",
  "Scan the QR in the app. Pro activates after payment confirmation. No account or email needed."
 ],
 [
  "Pro sẽ sớm có mặt. Bạn vẫn có thể dùng Free hoặc khôi phục Pro đã mua.",
  "Pro is coming soon. Keep using Free or restore an existing purchase."
 ],
 [
  "Thêm các giọng Turbo cho tiếng Việt và tiếng Anh. Tải gói giọng một lần, tạo sách nói ngay trên Mac.",
  "Add Turbo voices for Vietnamese and English. Download a voice pack once and create audiobooks on your Mac."
 ],
 [
  "Thêm các giọng Turbo và 6 giọng đọc riêng. Tải gói giọng một lần, tạo sách nói ngay trên Mac.",
  "Add Turbo and six custom voices. Download a voice pack once and create audiobooks on your Mac."
 ],
 [
  "Đang chuẩn bị thanh toán…",
  "Preparing payment…"
 ],
 [
  "Đang chờ thanh toán · Tự động cập nhật",
  "Waiting for payment · Updates automatically"
 ],
 [
  "Kiểm tra ngay",
  "Check now"
 ],
 [
  "Chưa kết nối được. App đang thử lại…",
  "Could not connect. Retrying…"
 ],
 [
  "Đã tạm dừng cập nhật. Nếu đã chuyển khoản, bấm Kiểm tra ngay; không cần chuyển lại.",
  "Automatic checks are paused. If you have paid, select Check now; do not transfer again."
 ],
 [
  "Thanh toán tạm thời chưa sẵn sàng. Hãy đóng cửa sổ và thử lại sau.",
  "Payment is temporarily unavailable. Close this window and try again later."
 ],
 [
  "Giữ cửa sổ này mở. Pro sẽ tự cập nhật sau khi giao dịch được xác nhận.",
  "Keep this window open. Pro updates automatically after payment confirmation."
 ],
 [
  "THÊM LỰA CHỌN GIỌNG ĐỌC",
  "MORE VOICES FOR YOUR BOOKS"
 ],
 [
  "Chọn giọng Turbo bạn thích và tạo sách nói ngay trên Mac.",
  "Choose your favorite Turbo voice and create audiobooks on your Mac."
 ],
 [
  "Giữ nguyên nội dung để Pro được mở cho Mac này.",
  "Keep this payment code unchanged to activate Pro on this Mac."
 ],
 [
  "Khôi phục từ tệp",
  "Restore from file"
 ],
 [
  "Pro đã sẵn sàng. Bạn có thể chọn Turbo để bắt đầu nghe.",
  "Pro is ready. Choose Turbo to start listening."
 ],
 [
  "Bản đọc được lưu trên Mac. Đổi tốc độ nghe không cần tạo lại.",
  "Audio is saved on your Mac. Changing playback speed does not regenerate it."
 ],
 [
  "Nhiều lựa chọn giọng cho tiếng Việt và tiếng Anh. Hãy nghe thử để chọn giọng phù hợp với cuốn sách.",
  "More voice choices for Vietnamese and English. Preview them to find the right voice for your book."
 ],
 [
  "8 giọng nam và nữ cho sách tiếng Anh. Gói tải nhẹ, phù hợp để bắt đầu nghe.",
  "Eight male and female voices for English books. A small download to get started."
 ],
 [
  "6 giọng đọc riêng cho sách tiếng Việt. Tạo bản đọc ngay trên Mac với gói Pro.",
  "Six custom voices for Vietnamese books. Create audio on your Mac with Pro."
 ],
 [
  "Giọng đọc riêng",
  "Custom voices"
 ],
 [
  "Gói giọng riêng chưa có trên máy",
  "Custom voice pack is not installed"
 ],
 [
  "Gói giọng riêng chưa đầy đủ. Vui lòng cài lại gói giọng Pro đã nhận.",
  "The custom voice pack is incomplete. Reinstall the Pro voice pack you received."
 ],
 [
  "Gói giọng chưa đầy đủ hoặc bị lỗi. Mở Gói giọng đọc để tải lại.",
  "The voice pack is missing or damaged. Open Voice packs to download it again."
 ],
 [
  "Tệp giọng đọc tải về bị lỗi. Hãy thử tải lại.",
  "The voice download is damaged. Please try again."
 ],
 [
  "Chưa lưu được tệp M4A. Hãy thử lại hoặc chọn định dạng WAV.",
  "Could not save M4A. Try again or choose WAV."
 ],
 [
  "Chỉ bật khi chữ trong PDF bị thiếu hoặc sai. App sẽ đọc lại chữ từ ảnh từng trang nên có thể mất thêm thời gian. Ảnh chụp được nhận chữ tự động.",
  "Enable only when PDF text is missing or incorrect. Reading text from every page image may take longer. Photos are recognized automatically."
 ],
 [
  "Chọn và tải gói giọng bạn muốn dùng. Sau đó, bạn có thể tạo sách nói trên Mac mà không cần mạng. Tốc độ tạo tùy cấu hình máy.",
  "Download the voice pack you want. Then create audiobooks on your Mac offline. Generation speed depends on your Mac."
 ],
 [
  "Mẫu ngắn chạy trên máy, dùng cùng một câu để bạn dễ so sánh. Không dùng nội dung sách.",
  "Local samples use the same sentence for easy comparison."
 ],
 [
  "Nghe cùng một câu với các giọng khác nhau để chọn giọng bạn thích.",
  "Preview the same sentence with different voices to find your favorite."
 ]
]);
entries.push(...[["Chưa kết nối được. App sẽ thử lại khi có mạng.", "Could not connect. The app will retry when you are online."], ["Chưa cập nhật được Pro. App sẽ thử lại sau.", "Could not update Pro. The app will retry."], ["Chưa nhận được thông tin Pro hợp lệ. App sẽ thử lại sau.", "Could not verify Pro yet. The app will retry."], ["Chưa xác minh được Pro cho Mac này. App sẽ thử lại sau.", "Could not verify Pro for this Mac yet. The app will retry."], ["Chưa nhận được Pro cho Mac này. Nếu đã chuyển khoản, hãy chờ giao dịch được xác nhận.", "No Pro activation for this Mac yet. If you have paid, wait for payment confirmation."], ["Chưa có thay đổi với Pro trên Mac này. Nếu đã chuyển khoản, mở cửa sổ mua Pro để tự cập nhật.", "No Pro update yet. If you have paid, open the purchase window for automatic updates."], ["App đang cập nhật Pro. Vui lòng chờ một chút.", "The app is updating Pro. Please wait a moment."], ["Ứng dụng chưa mở được bộ đọc. Hãy đóng app, mở lại hoặc cài lại bản mới nhất.", "The reading service could not start. Restart the app or reinstall the latest version."], ["Chọn tệp kích hoạt Pro đã nhận cho Mac này.", "Choose the Pro activation file you received for this Mac."], ["Pro đã được mở cho Mac này.", "Pro is activated on this Mac."], ["Đang hoàn tất tệp âm thanh…", "Finishing the audio file…"], ["Gồm bản đọc, nhạc nền, nội dung sách và trình nghe. Bạn có thể mang sang máy khác hoặc đưa lên website của mình.", "Includes audio, background music, book text and a player. Use it on another device or on your website."], ["Toàn bộ chương · có thể xóa bớt trước khi tạo.", "Full chapter · remove anything you do not want to narrate."], ["Thêm các giọng Turbo. Tải gói giọng một lần, tạo sách nói ngay trên Mac.", "Add Turbo voices. Download a pack once and create audiobooks on your Mac."], ["Bản dùng thử", "Preview"], ["Giọng đọc", "Voice"], ["Đóng bản quyền", "Close plans"]]);
entries.push(...[["Giọng trước đây · Chọn giọng khác", "Previous voice · Choose another voice"], ["Chọn gói giọng có sẵn để tạo bản đọc mới.", "Choose an available voice pack to create new audio."]]);
entries.push(...[["Nghe thử giọng", "Preview voices"], ["Không dùng nhạc nền", "No background music"], ["Nghe theo cách bạn muốn", "Listen your way"], ["Free · Miễn phí", "Free · No charge"], ["Nano tiếng Việt và 8 giọng KittenTTS tiếng Anh. Đọc, sửa và nghe trên máy.", "Vietnamese with Nano and eight KittenTTS English voices. Read, edit and listen on your Mac."], ["Pro · 189.000đ/năm", "Pro · 189,000 VND/year"], ["Mua / gia hạn Pro", "Buy / renew Pro"], ["Chưa lưu · Tạo bản đọc sẽ lưu nội dung bạn đang chỉnh sửa.", "Unsaved · Create audio saves your current edits first."], ["Chưa có bản đọc. Chọn một chương rồi bấm Tạo bản đọc chương này.", "No audio yet. Choose a chapter, then select Create chapter audio."]]);
entries.push(...[
 ['Không gian cho lời kể','Set the mood for your story'],['Chọn nhạc nhẹ để lời đọc luôn nổi bật.','Keep the music gentle and the narration clear.'],['Thể loại','Category'],['Cách chọn nhạc','Music selection'],['Chọn bài','Choose a track'],['Ngẫu nhiên','Shuffle'],['Bài nhạc','Track'],['Thứ tự phát','Play order'],['Thứ tự bài nhạc','Track order'],['Đảo lại','Reshuffle'],['Lặp nhạc','Loop music'],['Tiếp tục nhạc đến hết lời đọc.','Keep the music going until narration ends.'],['Chỉ phát lời đọc, không kèm nhạc.','Play narration without background music.'],['Phát các bài theo thứ tự ngẫu nhiên đã chọn.','Play tracks in the saved shuffle order.'],['Lưu riêng cho từng sách. Đổi nhạc không cần tạo lại giọng.','Saved for each book. Change music without regenerating narration.'],['Thư giãn','Relaxation']
]);
entries.push(...[["Sách được lưu trên Mac", "Books are stored on your Mac"], ["Tạo sách bằng Clone Pro 2.1.", "Create audiobooks with Clone Pro 2.1."], ["Mua credit ngay trong app. Không cần tài khoản web Clone Pro, không thêm phí gói Pro Max.", "Buy credits in the app. No Clone Pro web account or extra Pro Max subscription."], ["Credit của bạn", "Your credits"], ["1 ký tự = 1 credit", "1 character = 1 credit"], ["Chỉ phần chữ bạn xác nhận mới được gửi để tạo giọng. Audio tải về được giữ trên Mac để nghe và xuất kèm nhạc.", "Only text you confirm is sent for speech generation. Downloaded audio stays on your Mac for listening and exports with music."], ["Cập nhật số dư", "Refresh balance"], ["Mua thêm credit", "Buy more credits"], ["Giá gói credit sẽ được công bố sau. Chưa mở bán.", "Credit pack prices will be announced later. Sales are not open."], ["Gói credit", "Credit pack"], ["Tạo QR mua credit", "Create payment QR"], ["Chuyển khoản mua credit", "Pay for credits by bank transfer"], ["Mã QR mua credit", "Credit payment QR code"], ["Nội dung chuyển khoản:", "Transfer reference:"], ["Sao chép nội dung", "Copy reference"], ["Chỉ cộng credit sau khi tiền vào được xác nhận. Mã thanh toán hoặc ảnh chuyển khoản không xác nhận thanh toán.", "Credits are added only after the bank receipt is verified. A reference or payment screenshot does not confirm payment."], ["Pro Max · Mua credit", "Pro Max · Buy credits"], ["Pro Max · Credit riêng trong app", "Pro Max · App credits"], ["Tạo sách nói bằng Clone Pro 2.1. Không cần tài khoản web, không thêm phí gói.", "Create audiobooks with Clone Pro 2.1. No web account or extra subscription."], ["Mua / quản lý credit", "Buy / manage credits"], ["Mua / quản lý credit Pro Max", "Buy / manage Pro Max credits"], ["Đóng Pro Max", "Close Pro Max"], ["Đang cập nhật ví credit trong app…", "Refreshing your app credit wallet…"], ["Chọn gói và quét QR. Credit được cộng khi tiền vào được xác nhận.", "Choose a pack and scan the QR. Credits are added after the bank receipt is verified."], ["Đã xác nhận tiền vào. Credit đã được cộng vào ví.", "Payment verified. Credits have been added to your wallet."], ["Đang chờ xác nhận tiền vào. Bạn có thể cập nhật số dư hoặc mở lại cửa sổ này sau.", "Waiting for payment verification. Refresh the balance or reopen this window later."], ["Hãy chờ cập nhật ví credit hoàn tất.", "Wait for the wallet refresh to finish."], ["Đang tạo yêu cầu mua credit…", "Creating a credit purchase order…"], ["Tạo sách với Clone Pro 2.1?", "Create audio with Clone Pro 2.1?"], ["Đóng xác nhận tạo sách", "Close audio confirmation"], ["Để sau", "Later"], ["Gửi chữ và dùng credit app", "Send text and use app credits"], ["Dùng audio đã có", "Use cached audio"], ["Tất cả đoạn đã có audio. Không cần gửi chữ hoặc dùng credit.", "All audio is cached. No text needs to be sent and no credits are needed."], ["Chữ trong phạm vi này sẽ được gửi tới WindiStudio để tạo giọng. Lượt tạo dùng credit mua riêng trong app. Hủy sẽ giữ audio hoàn tất; yêu cầu đã gửi có thể vẫn dùng credit.", "Text in this selection will be sent to WindiStudio for speech generation using app credits. Cancelling keeps completed audio; submitted requests may still use credits."], ["Đã cập nhật ví credit.", "App wallet refreshed."], ["Đã tạo yêu cầu mua credit. Chỉ cộng credit khi tiền vào được xác nhận.", "Credit purchase order created. Credits are added only after payment verification."], ["Dịch vụ credit trong app chưa được cấu hình. Giá gói sẽ được công bố sau.", "The app credit service is not configured yet. Pack prices will be announced later."], ["Pro Max · Credit app, tạo qua mạng, nghe trên Mac", "Pro Max · App credits, online generation, local listening"], ["Credit Clone Pro 2.1 · Không thêm phí gói", "App credits · No extra subscription"], ["Ví credit riêng trong app · Chọn để dùng cho sách", "Separate app wallet · Select to use for this book"], ["Cần mạng khi tạo · Nghe audio đã tải không cần mạng", "Internet needed for generation · Downloaded audio plays offline"], ["Chọn giọng rồi tạo một phần sách bằng credit để nghe.", "Choose a voice and generate a selection with credits to listen."], ["Tạo một phần sách để nghe", "Generate a selection to listen"], ["Bấm Tạo phạm vi đã chọn để xác nhận dùng credit Clone Pro 2.1.", "Create the selected scope to confirm using app credits."], ["Clone Pro 2.1 qua mạng", "Clone Pro 2.1 online"], ["Mở ví credit", "Open credit wallet"], ["Không đủ credit trong app. Mở Pro Max để mua thêm.", "Not enough app credits. Open Pro Max to buy more."], ["Tạo sách nói với giọng Clone Pro 2.1 qua mạng. Mua credit riêng trong app, không cần tài khoản web Clone Pro. Audio tải về nghe và xuất trên máy.", "Generate audiobooks with Clone Pro 2.1 online. Buy app credits separately without a Clone Pro web account. Listen and export downloaded audio locally."], ["Nano, Kitten, Turbo và giọng riêng tạo audio trên Mac sau khi tải. Pro Max dùng Clone Pro 2.1 qua mạng và trừ credit theo tài khoản.", "Nano, Kitten, Turbo and custom voices generate locally after download. Pro Max uses Clone Pro 2.1 online and charges your app credit wallet."]]);
entries.push(...[["Thêm giọng, thêm lựa chọn", "More voices to choose from"], ["Mở giọng Turbo với Pro.", "Unlock Turbo voices with Pro."], ["Turbo và 6 giọng F5 cho sách của bạn.", "Turbo and 6 F5 voices for your books."], ["Mua Pro · 189.000đ/năm", "Buy Pro · 189,000 VND/year"], ["Gia hạn Pro · 189.000đ/năm", "Renew Pro · 189,000 VND/year"], ["Quản lý gói Pro", "Manage Pro"], ["So sánh Free / Pro", "Compare Free / Pro"], ["Gói Pro", "Pro plan"], ["Mở Turbo với Pro", "Unlock Turbo with Pro"], ["Mở Turbo / F5 với Pro", "Unlock Turbo / F5 with Pro"], ["Giọng đọc riêng · F5", "Custom voices · F5"], ["Có sẵn Nano tiếng Việt và 8 giọng tiếng Anh. Tạo và nghe ngay trên Mac.", "Vietnamese Nano and 8 English voices included. Generate and listen on your Mac."], ["Có sẵn Nano tiếng Việt và 8 giọng KittenTTS tiếng Anh. Đọc, sửa và nghe ngay trên Mac.", "Vietnamese Nano and 8 KittenTTS English voices included. Read, edit and listen on your Mac."], ["Nano tiếng Việt và KittenTTS tiếng Anh có sẵn trong bản cài mới. Tải thêm Turbo khi đã mở Pro. Giọng đọc được tạo trên Mac; tốc độ tùy cấu hình máy.", "Vietnamese Nano and KittenTTS English are included with a fresh install. Download Turbo after unlocking Pro. Speech is generated on your Mac; speed depends on your hardware."]]);
entries.push(['Mua Pro','Buy Pro'],['189.000đ / năm','189,000 VND / year']);
entries.push(...[["Đang chuẩn bị giọng đọc…", "Preparing voice…"], ["Đang tạo bản đọc", "Generating narration"], ["Đã tạo xong bản đọc", "Narration complete"], ["Đã dừng · giữ phần đã tạo", "Stopped · completed audio kept"], ["Tạo bản đọc bị gián đoạn", "Narration interrupted"], ["Hủy tạo", "Cancel generation"], ["Ẩn tiến độ", "Hide progress"], ["Tiến độ tạo bản đọc", "Narration progress"], ["Bản đọc được lưu trong Sách nói của bạn.", "Your narration is saved in Your audiobooks."], ["Mở 6 giọng riêng F5 cho sách tiếng Việt. Tạo và nghe sách nói ngay trên Mac.", "Unlock 6 F5 voices for Vietnamese books. Generate and listen on your Mac."], ["Gói giọng riêng F5 chưa có trong bản cài này. Nano và tiếng Anh vẫn có sẵn miễn phí.", "F5 voices are not included in this edition. Nano and English voices remain free."], ["Chọn giọng riêng bạn thích.", "Choose your favorite voice."], ["Mở 6 giọng F5 tiếng Việt, tạo và nghe sách nói ngay trên Mac.", "Unlock 6 Vietnamese F5 voices. Generate and listen on your Mac."], ["Bạn có thể chọn giọng riêng F5 và tiếp tục tạo sách nói.", "Choose an F5 voice and continue creating audiobooks."], ["Pro đã sẵn sàng. Bạn có thể chọn giọng riêng F5.", "Pro is ready. You can choose an F5 voice."], ["Nano tiếng Việt và KittenTTS tiếng Anh có sẵn trong bản cài mới. Pro mở 6 giọng riêng F5. Giọng đọc được tạo trên Mac; tốc độ tùy cấu hình máy.", "Vietnamese Nano and KittenTTS English are included. Pro unlocks 6 F5 voices. Speech is generated on your Mac; speed depends on your hardware."], ["Turbo đã ngừng cung cấp. Chọn Nano để tạo nhanh hoặc giọng riêng F5 trong Pro.", "Turbo is retired. Choose Nano for faster generation or an F5 voice with Pro."]]);
entries.push(['Hãy thử tạo lại phần chưa hoàn tất.','Try generating the unfinished part again.']);
entries.push(['Chọn phạm vi có đoạn đang đọc trước khi nghe.','Choose a scope containing the current segment before playing.'],['Gói Nano chưa đầy đủ hoặc bị lỗi. Mở Gói giọng đọc để cài lại.','Nano resources are incomplete or corrupted. Open Voice packs to reinstall.']);
entries.push(['Đang đọc bản build…','Reading build information…'],['Bản đang chạy','Running version']);
const dictionary=new Map(entries), originals=new WeakMap(), attributes=new WeakMap();
let language='vi';try{language=localStorage.getItem('windi-language')==='en'?'en':'vi';}catch{}
const protectedData='#ebookFlow,#sourceReflow,#sourceHighlights,#editor,textarea,script,style,#title,#books strong,#readerChapter option,#musicTrack option:not([value="none"]),.user-text,#paymentCode,#paymentAccount,#paymentHolder';
function english(value){
 if(dictionary.has(value))return dictionary.get(value);
 const rules=[
 [/^(\d+) đoạn cần tạo · Dự kiến ([\d.]+) credit app\. (\d+) đoạn đã có được dùng lại\.$/,(_,n,c,r)=>`${n} segments to generate · Estimated ${c} app credits. Reuse ${r} cached segments.`],

 [/^(.+) · Chưa có trong gói này$/,(_,n)=>`${english(n)} · Not included in this pack`],
 [/^Pro · Dùng đến (.+)$/,(_,d)=>`Pro · Available until ${d}`],
 [/^Pro dùng đến (.+)\.$/,(_,d)=>`Pro is available until ${d}.`],
 [/^Giọng riêng (\d+)$/,(_,n)=>`Custom voice ${n}`],
 [/^(.+) sẵn sàng · Không cần mạng$/,(_,n)=>`${english(n)} ready · Offline`],
 [/^Đang lưu bản đọc · (\d+)%$/,(_,n)=>`Saving audio · ${n}%`],
 [/^Bản quyền đến (.+)\.$/,(_,date)=>`Licensed until ${date}.`],
 [/^(\d[\d.]*) ký tự$/,(_,n)=>`${n} characters`],
 [/^(\d[\d.]*) ký tự · (\d+)\/(\d+) phần (?:có audio|đã tạo)$/,(_,n,r,t)=>`${n} characters · ${r}/${t} parts with audio`],
 [/^(\d+)\/(\d+) phần (?:đã có audio|đã tạo)$/,(_,r,t)=>`${r}/${t} parts with audio`],
 [/^(\d+)\/(\d+) phần sẵn sàng$/,(_,r,t)=>`${r}/${t} parts ready`],
 [/^Có (\d+) dòng trang trí · Dọn nội dung để xem trước\.$/,(_,n)=>`${n} decorative lines · Preview text cleanup.`],
 [/^Sẽ bỏ (\d+) dòng\. Nội dung còn lại giữ nguyên\.$/,(_,n)=>`Remove ${n} lines. Keep the remaining text unchanged.`],
 [/^Dòng (\d+)$/,(_,n)=>`Line ${n}`],
 [/^Nghe thử · (.+)$/,(_,v)=>`Voice preview · ${v}`],
 [/^Sách nói · (.+)$/,(_,v)=>`Audiobook · ${v}`],
 [/^(Đang tải|Kiểm tra tệp|Đã tải và xác minh) · (\d+)% · (.+) MB$/,(_,stage,percent,size)=>`${english(stage)} · ${percent}% · ${size} MB`],
 [/^(\d+) (trang|mục) · (\d+) đoạn(.*)$/,(_,n,u,s,end)=>`${n} ${u==='trang'?(n==='1'?'page':'pages'):(n==='1'?'section':'sections')} · ${s} ${s==='1'?'segment':'segments'}${end.replace(' · Đã nghe xong',' · Finished').replace(/ · (\d+) đoạn (?:có audio|đã tạo)/,' · $1 with audio')}`],
 [/^(Trang|Mục) (\d+)\s*\/\s*Đoạn (\d+)$/,(_,u,n,s)=>`${u==='Trang'?'Page':'Section'} ${n} / Segment ${s}`],
 [/^(Trang|Mục) (\d+)(–\d+)?$/,(_,u,n,end)=>`${u==='Trang'?'Page':'Section'} ${n}${end||''}`],
 [/^(Trang|Mục) (\d+) · (Có audio|Chưa tạo)$/,(_,u,n,state)=>`${u==='Trang'?'Page':'Section'} ${n} · ${state==='Có audio'?'Audio ready':'Not generated'}`],
 [/^Đoạn (\d+)$/,(_,n)=>`Segment ${n}`],
 [/^(Sẵn sàng nghe|Đang chuẩn bị|Đang nghe|Tạm dừng) · Đoạn (\d+)$/,(_,s,n)=>`${{'Sẵn sàng nghe':'Ready','Đang chuẩn bị':'Preparing','Đang nghe':'Playing','Tạm dừng':'Paused'}[s]} · Segment ${n}`],
 [/^Đang trích chữ · (.+) (trang|mục)$/,(_,n,u)=>`Extracting text · ${n} ${u==='trang'?'pages':'sections'}`],
 [/^Đã lưu (\d+) (trang|mục)\. Có thể tiếp tục trích chữ\.$/,(_,n,u)=>`Saved ${n} ${u==='trang'?'pages':'sections'}. Extraction can be resumed.`],
 [/^Đang (đọc|chờ) (trang|mục) (đầu tiên|tiếp theo)…$/,(_,v,u,p)=>`${v==='đọc'?'Reading':'Waiting for'} the ${p==='đầu tiên'?'first':'next'} ${u==='trang'?'page':'section'}…`],
 [/^Đang tạo giọng · (.+) đoạn (?:có audio|đã tạo)$/,(_,n)=>`Generating speech · ${n} segments with audio`],
 [/^Đã tạo (.+) đoạn trong lượt này · có thể nghe ngay\.$/,(_,n)=>`Generated ${n} segments in this job · ready to listen.`],
 [/^Tạo (\d+)? ?đoạn trong phạm vi$/,(_,n)=>`Generate ${n||''} ${n==='1'?'segment':'segments'} in scope`],
 [/^(.+) · (\d+) đoạn · (\d+) đã có giọng đọc$/,(_,s,n,r)=>`${english(s)} · ${n} ${n==='1'?'segment':'segments'} · ${r} ready`],
 [/^(.+) · (\d+)\/(\d+) đoạn sẵn sàng\. Phạm vi được chọn ở tab Phạm vi\.$/,(_,s,r,n)=>`${english(s)} · ${r}/${n} segments ready. Choose the scope in the Scope tab.`],
 [/^Mốc chương bắt đầu từ (trang|mục) (\d+)\. Có thể đặt lại tên tại cùng (trang|mục)\.$/,(_,u,n)=>`The chapter starts at ${u==='trang'?'page':'section'} ${n}. Save a new title at the same position to rename it.`],
 [/^Sách chưa có mục lục chương\. Đặt mốc chương ở bên dưới hoặc chọn theo (trang|mục)\.$/,(_,u)=>`No chapter markers found. Add a marker below or select by ${u==='trang'?'page':'section'}.`],
 [/^Đang trộn\/xuất audio · (\d+)%$/,(_,n)=>`Mixing / exporting audio · ${n}%`],
 [/^Đã tải về: (.+)$/,(_,path)=>`Saved: ${path}`],
 [/^Nhạc demo bạn cung cấp · (.+)$/,(_,duration)=>`Your demo track · ${duration}`],
 [/^Mac (.+) · (.+) GB RAM · Trống (.+) GB$/,(_,arch,ram,disk)=>`Mac ${arch} · ${ram} GB RAM · ${disk} GB free`],
 [/^Nên dùng máy có RAM (\d+) GB trở lên$/,(_,n)=>`${n} GB RAM or more recommended`],
 [/^(\d+ MB · \d+ kHz · (?:VI|EN|VI \/ EN) · )Nên có (\d+) GB RAM$/,(_,prefix,n)=>`${prefix}${n} GB RAM recommended`],
 [/^(Tải \/ tiếp tục tải) · (\d+) MB$/,(_,s,n)=>`Download / resume · ${n} MB`]
 ];
 for(const [pattern,replace] of rules)if(pattern.test(value))return value.replace(pattern,replace);
 if(/^(\d+)\/(\d+) đoạn · (\d+)%$/.test(value))return value.replace(' đoạn · ',' segments · ');
 if(value.startsWith('Bản đang chạy: '))return 'Running version: '+value.slice('Bản đang chạy: '.length);
 if(value.includes(' · Mở khóa Pro'))return english(value.replace(' · Mở khóa Pro',''))+' · Unlock Pro';
 if(value.startsWith('Mua Pro để mở '))return 'Buy Pro to unlock '+english(value.slice(14).replace(' · 189.000đ/năm',''))+' · 189,000 VND/year';
 if(value.includes(' · Chưa tải'))return english(value.replace(' · Chưa tải',''))+' · Not downloaded';
 if(value.includes(' kHz · '))return value.replace(' · Đã tải',' · Installed').replace(' · Cần tải trước khi nghe',' · Download before listening');
 if(value.startsWith('EPUB chia theo mục'))return value.replace('EPUB chia theo mục nội dung, không phải số trang của bản in.','EPUB sections follow the content structure, not printed page numbers.').replace(/(\d+) mục trống hoặc chỉ có ảnh \(ví dụ bìa\) không được đưa vào lời đọc\./,'$1 empty or image-only sections (such as the cover) are excluded from narration.').replace('EPUB này được lấy chữ trực tiếp, không OCR ảnh bên trong.','Text is extracted directly; images inside this EPUB are not OCR processed.');
 return value;
}
function translated(source,element){
 const leading=source.match(/^\s*/)[0],trailing=source.match(/\s*$/)[0];let core=source.trim();
 if(!core)return source;
 if(element.closest('#chapterSelect'))core=core.replace(/ · (trang|mục) (\d+–\d+)$/,(_,u,n)=>` · ${u==='trang'?'pages':'sections'} ${n}`);
 else if(element.closest('#voice')){const parts=core.split(' · ');core=parts.map((p,i)=>i?(i===2&&p==='Nam'?'Southern':({'Nam':'Male','Nữ':'Female','Bắc':'Northern','Trung':'Central','Phong cách tự nhiên':'Natural','Giọng đọc tự nhiên':'Natural','Phong cách tin tức':'News','Phong cách kể chuyện':'Storytelling'}[p]||p)):p).join(' · ');}
 else core=english(core);
 return leading+core+trailing;
}
function translateText(node){
 const parent=node.parentElement;if(!parent||parent.closest(protectedData))return;
 const old=originals.get(node),source=old&&node.nodeValue===old.result?old.source:node.nodeValue;
 const result=language==='en'?translated(source,parent):source;
 originals.set(node,{source,result});if(node.nodeValue!==result)node.nodeValue=result;
}
function translateAttributes(element){
 if(element.closest(protectedData))return;
 const records=attributes.get(element)||{};
 for(const attr of ['aria-label','placeholder','title'])if(element.hasAttribute(attr)){
  const value=element.getAttribute(attr),old=records[attr],source=old&&value===old.result?old.source:value;
  const result=language==='en'?english(source):source;records[attr]={source,result};if(value!==result)element.setAttribute(attr,result);
 }
 attributes.set(element,records);
}
function translateSubtree(root){
 if(!root.isConnected||root.parentElement?.closest(protectedData))return;
 if(root.nodeType===Node.TEXT_NODE){translateText(root);return;}
 if(root.nodeType!==Node.ELEMENT_NODE||root.matches(protectedData))return;
 translateAttributes(root);
 // Reject protected book subtrees before walking their thousands of sentences.
 const walker=document.createTreeWalker(root,NodeFilter.SHOW_ELEMENT|NodeFilter.SHOW_TEXT,{acceptNode:node=>node.nodeType===Node.ELEMENT_NODE&&node.matches(protectedData)?NodeFilter.FILTER_REJECT:NodeFilter.FILTER_ACCEPT});
 let node;while(node=walker.nextNode()){if(node.nodeType===Node.TEXT_NODE)translateText(node);else translateAttributes(node);}
}
function observe(){observer.observe(document.body,{subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:['aria-label','placeholder','title']});}
function refresh(){observer.disconnect();document.documentElement.lang=language;translateSubtree(document.body);observe();}
const observer=new MutationObserver(changes=>{
 const roots=new Set(),attrs=new Set();
 for(const change of changes){
  if(change.type==='attributes')attrs.add(change.target);
  else if(change.type==='characterData')roots.add(change.target);
  else for(const node of change.addedNodes)roots.add(node);
 }
 observer.disconnect();
 for(const element of attrs)if(element.isConnected)translateAttributes(element);
 for(const root of roots){let parent=root.parentNode,covered=false;while(parent){if(roots.has(parent)){covered=true;break;}parent=parent.parentNode;}if(!covered)translateSubtree(root);}
 observe();
});
function select(value){language=value==='en'?'en':'vi';try{localStorage.setItem('windi-language',language);}catch{}refresh();window.webkit?.messageHandlers.app.postMessage({action:'locale',language});window.dispatchEvent(new Event('localechange'));}
window.i18n={get language(){return language;},english,refresh};
const control=document.getElementById('appLanguage');control.value=language;control.onchange=()=>select(control.value);
refresh();window.webkit?.messageHandlers.app.postMessage({action:'locale',language});
})();
