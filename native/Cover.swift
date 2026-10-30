import AppKit
import PDFKit
import ImageIO

// A bounded local thumbnail. stdout remains one JSON line, never diagnostics.
do {
    guard CommandLine.arguments.count == 2 else { throw CocoaError(.fileReadUnknown) }
    let url=URL(fileURLWithPath:CommandLine.arguments[1])
    let image:CGImage
    if url.pathExtension.lowercased() == "pdf" {
        guard let document=PDFDocument(url:url),!document.isLocked,let page=document.page(at:0) else { throw CocoaError(.fileReadCorruptFile) }
        let bounds=page.bounds(for:.mediaBox)
        guard bounds.width>0,bounds.height>0 else { throw CocoaError(.fileReadCorruptFile) }
        let ratio=480/max(bounds.width,bounds.height)
        let thumbnail=page.thumbnail(of:NSSize(width:bounds.width*ratio,height:bounds.height*ratio),for:.mediaBox)
        guard let cg=thumbnail.cgImage(forProposedRect:nil,context:nil,hints:nil) else { throw CocoaError(.fileReadCorruptFile) }
        image=cg
    } else {
        guard let source=CGImageSourceCreateWithURL(url as CFURL,nil),
              let cg=CGImageSourceCreateThumbnailAtIndex(source,0,[kCGImageSourceCreateThumbnailFromImageAlways:true,kCGImageSourceCreateThumbnailWithTransform:true,kCGImageSourceThumbnailMaxPixelSize:480] as CFDictionary) else { throw CocoaError(.fileReadCorruptFile) }
        image=cg
    }
    guard let data=NSBitmapImageRep(cgImage:image).representation(using:.jpeg,properties:[.compressionFactor:0.82]),data.count<250000 else { throw CocoaError(.fileReadTooLarge) }
    let json=try JSONSerialization.data(withJSONObject:["image":"data:image/jpeg;base64,"+data.base64EncodedString()])
    print(String(data:json,encoding:.utf8)!)
} catch { fputs("Không tạo được bìa sách: \(error)\n",stderr);exit(1) }
