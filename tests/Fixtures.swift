import AppKit
import PDFKit
let dir=URL(fileURLWithPath:CommandLine.arguments[1]); try FileManager.default.createDirectory(at:dir,withIntermediateDirectories:true)
let lines=["Mỗi ngày, tôi dành một giờ để đọc sách.","Tiếng Việt có dấu: ă â ê ô ơ ư đ.","Sách mở ra những chân trời mới."]
func drawText(_ n:Int){
    NSColor.black.setFill()
    let attrs:[NSAttributedString.Key:Any]=[.font:NSFont.systemFont(ofSize:30),.foregroundColor:NSColor.black]
    for (i,s) in lines.enumerated(){(s as NSString).draw(at:NSPoint(x:55,y:480-CGFloat(i)*65),withAttributes:attrs)}
    ("Trang \(n)" as NSString).draw(at:NSPoint(x:55,y:200),withAttributes:attrs)
}
let image=NSImage(size:NSSize(width:900,height:600));image.lockFocus();NSColor.white.setFill();NSRect(x:0,y:0,width:900,height:600).fill();drawText(1);image.unlockFocus()
let bitmap=NSBitmapImageRep(data:image.tiffRepresentation!)!;try bitmap.representation(using:.png,properties:[:])!.write(to:dir.appendingPathComponent("chu-viet.png"))
func pdf(_ name:String,scan:Bool,pages:Int){
 var rect=CGRect(x:0,y:0,width:900,height:600)
 let c=CGContext(dir.appendingPathComponent(name) as CFURL,mediaBox:&rect,nil)!
 for n in 1...pages {
  c.beginPDFPage(nil);NSGraphicsContext.saveGraphicsState();NSGraphicsContext.current=NSGraphicsContext(cgContext:c,flipped:false)
  if scan{image.draw(in:NSRect(x:0,y:0,width:900,height:600))}else{drawText(n)}
  NSGraphicsContext.restoreGraphicsState();c.endPDFPage()
 }
 c.closePDF()
}
pdf("text-viet.pdf",scan:false,pages:3);pdf("scan-viet.pdf",scan:true,pages:2);pdf("long-scan.pdf",scan:true,pages:10)
let doc=PDFDocument(url:dir.appendingPathComponent("text-viet.pdf"))!
let thumb=doc.page(at:0)!.thumbnail(of:NSSize(width:900,height:600),for:.mediaBox)
try NSBitmapImageRep(data:thumb.tiffRepresentation!)!.representation(using:.png,properties:[:])!.write(to:dir.appendingPathComponent("text-preview.png"))
print("Đã tạo fixtures PDF text, PDF scan và ảnh tiếng Việt.")

let chapterRoot=PDFOutline()
for (i,page) in [0,2].enumerated() {
 let node=PDFOutline();node.label="Chương \(i+1)";node.destination=PDFDestination(page:doc.page(at:page)!,at:NSPoint(x:0,y:600));chapterRoot.insertChild(node,at:i)
}
doc.outlineRoot=chapterRoot;doc.write(to:dir.appendingPathComponent("chapters-viet.pdf"))

let englishLines=["Every book opens a new window on the world.","Take your time, listen carefully, and let the story come to life."]
let englishImage=NSImage(size:NSSize(width:1200,height:600));englishImage.lockFocus();NSColor.white.setFill();NSRect(x:0,y:0,width:1200,height:600).fill()
for (i,line) in englishLines.enumerated(){(line as NSString).draw(at:NSPoint(x:55,y:450-CGFloat(i)*80),withAttributes:[.font:NSFont.systemFont(ofSize:28),.foregroundColor:NSColor.black])}
englishImage.unlockFocus()
try NSBitmapImageRep(data:englishImage.tiffRepresentation!)!.representation(using:.png,properties:[:])!.write(to:dir.appendingPathComponent("english-scan.png"))
var enRect=CGRect(x:0,y:0,width:1200,height:600)
let englishPDF=CGContext(dir.appendingPathComponent("english-text.pdf") as CFURL,mediaBox:&enRect,nil)!
englishPDF.beginPDFPage(nil);NSGraphicsContext.saveGraphicsState();NSGraphicsContext.current=NSGraphicsContext(cgContext:englishPDF,flipped:false)
for (i,line) in englishLines.enumerated(){(line as NSString).draw(at:NSPoint(x:55,y:450-CGFloat(i)*80),withAttributes:[.font:NSFont.systemFont(ofSize:28),.foregroundColor:NSColor.black])}
NSGraphicsContext.restoreGraphicsState();englishPDF.endPDFPage();englishPDF.closePDF()
