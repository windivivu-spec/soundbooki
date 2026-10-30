import AppKit
import PDFKit
import Vision
import ImageIO

func emit(_ value: [String: Any]) {
    if let d = try? JSONSerialization.data(withJSONObject: value, options: [.sortedKeys]), let s = String(data:d, encoding:.utf8) { print(s); fflush(stdout) }
}
func ocr(_ image: CGImage, language:String="vi") throws -> (String, String) {
    let r = VNRecognizeTextRequest()
    r.recognitionLevel = .accurate
    r.usesLanguageCorrection = false
    let langs = try r.supportedRecognitionLanguages()
    if language == "en" {
        r.recognitionLanguages=["en-US"]
    } else {
        guard let vi = langs.first(where: {$0.hasPrefix("vi-")}) else { throw NSError(domain:"OCR", code:1, userInfo:[NSLocalizedDescriptionKey:"macOS này chưa có OCR tiếng Việt. Cập nhật macOS hoặc nhập PDF có chữ."]) }
        r.recognitionLanguages = [vi, "en-US"]
    }
    try VNImageRequestHandler(cgImage:image, options:[:]).perform([r])
    let lines = (r.results ?? []).sorted {
        if abs($0.boundingBox.midY - $1.boundingBox.midY) < 0.008 { return $0.boundingBox.minX < $1.boundingBox.minX }
        return $0.boundingBox.midY > $1.boundingBox.midY
    }
    let texts = lines.compactMap { $0.topCandidates(1).first }
    let low = texts.contains {$0.confidence < 0.7}
    return (texts.map(\.string).joined(separator:"\n"), low ? "Một số dòng OCR có độ tin cậy thấp. Hãy đối chiếu bản gốc." : "OCR cần được kiểm tra dấu và thứ tự cột trước khi nghe.")
}
func imageCG(_ url: URL) -> CGImage? {
    guard let s=CGImageSourceCreateWithURL(url as CFURL,nil) else {return nil}
    return CGImageSourceCreateThumbnailAtIndex(s,0,[kCGImageSourceCreateThumbnailFromImageAlways:true,kCGImageSourceCreateThumbnailWithTransform:true,kCGImageSourceThumbnailMaxPixelSize:2800] as CFDictionary)
}
// One selection per source line, rather than per glyph. Keep UTF-16 offsets so
// Python can anchor headings without guessing where a title occurs in prose.
func layoutLines(_ page: PDFPage, _ text: String) -> [[String: Any]] {
    let source=text as NSString
    let attributed=page.attributedString
    let bounds=page.bounds(for:.mediaBox)
    var result:[[String:Any]]=[]
    var offset=0
    while offset<source.length {
        let range=source.lineRange(for:NSRange(location:offset,length:0))
        let value=source.substring(with:range).trimmingCharacters(in:.newlines)
        offset=NSMaxRange(range)
        if value.trimmingCharacters(in:.whitespaces).isEmpty {continue}
        var size:CGFloat=0
        if let attr=attributed,range.location<attr.length {
            attr.enumerateAttribute(.font,in:NSRange(location:range.location,length:min(range.length,attr.length-range.location))) {font,_,_ in
                if let f=font as? NSFont {size=max(size,f.pointSize)}
            }
        }
        if let selection=page.selection(for:range) {
            let rect=selection.bounds(for:page)
            result.append(["text":value,"startUTF16":range.location,"lengthUTF16":range.length,
                           "x":rect.minX-bounds.minX,"y":bounds.maxY-rect.maxY,
                           "w":rect.width,"h":rect.height,"size":size])
        }
    }
    return result
}
let args=CommandLine.arguments
if args.count < 2 { emit(["error":"Thiếu tài liệu"]); exit(1) }
let url=URL(fileURLWithPath:args[1]); let start=args.count>2 ? (Int(args[2]) ?? 0) : 0
let force=args.contains("--ocr")
let language=args.contains("--language=en") ? "en" : "vi"
do {
    if url.pathExtension.lowercased() == "pdf" {
        guard let pdf=PDFDocument(url:url), !pdf.isLocked else {throw NSError(domain:"PDF",code:1,userInfo:[NSLocalizedDescriptionKey:"PDF không đọc được hoặc đang khóa bằng mật khẩu."])}
        var chapterItems:[[String:Any]]=[]
        var chapterPages=Set<Int>()
        func visit(_ node:PDFOutline) {
            if let title=node.label,let page=node.destination?.page {
                let index=pdf.index(for:page)
                if index != NSNotFound && !chapterPages.contains(index) {
                    chapterPages.insert(index);chapterItems.append(["title":title,"page":index])
                }
            }
            for n in 0..<node.numberOfChildren {if let child=node.child(at:n){visit(child)}}
        }
        if let outline=pdf.outlineRoot {visit(outline)}
        chapterItems.sort{($0["page"] as? Int ?? 0)<($1["page"] as? Int ?? 0)}
        for i in start..<pdf.pageCount {
            guard let p=pdf.page(at:i) else {continue}
            var text=p.string ?? ""; var method="text"; var warning=""
            if force || text.trimmingCharacters(in:.whitespacesAndNewlines).isEmpty {
                let bounds=p.bounds(for:.mediaBox)
                let ratio=2200/max(bounds.width,bounds.height)
                let img=p.thumbnail(of:NSSize(width:bounds.width*ratio,height:bounds.height*ratio),for:.mediaBox)
                guard let cg=img.cgImage(forProposedRect:nil,context:nil,hints:nil) else {throw NSError(domain:"PDF",code:2,userInfo:[NSLocalizedDescriptionKey:"Không dựng được trang \(i+1)"])}
                (text,warning)=try ocr(cg,language:language); method="ocr"
            }
            if text.trimmingCharacters(in:.whitespacesAndNewlines).isEmpty {warning="Trang trống hoặc không nhận được chữ. Hãy kiểm tra bản gốc."}
            emit(["page":i,"total":pdf.pageCount,"text":text,"method":method,"warning":warning,"chapters":chapterItems,
                  "layout":method=="text" ? layoutLines(p,text) : [],"pageWidth":p.bounds(for:.mediaBox).width])
        }
    } else {
        guard let cg=imageCG(url) else {throw NSError(domain:"Image",code:1,userInfo:[NSLocalizedDescriptionKey:"Ảnh không đọc được."])}
        let (text,warning)=try ocr(cg,language:language)
        emit(["page":0,"total":1,"text":text,"method":"ocr","warning":warning])
    }
} catch {emit(["error":error.localizedDescription]); exit(1)}
