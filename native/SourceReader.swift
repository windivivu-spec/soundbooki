import AppKit
import PDFKit
import Vision
import ImageIO

// Original pages are rendered on demand. Nothing is uploaded or converted into
// an intermediate book. All file access stays inside the selected library book.
final class SourcePageRenderer {
    let queue=DispatchQueue(label:"studio.windi.source-pages",qos:.userInitiated)
    private final class Bitmap:NSObject {
        let image:CGImage;let png:Data
        init(_ image:CGImage,_ png:Data){self.image=image;self.png=png}
    }
    private final class OCRText:NSObject {
        let text:String;let spans:[(NSRange,CGRect)]
        init(_ text:String,_ spans:[(NSRange,CGRect)]){self.text=text;self.spans=spans}
    }
    private let images=NSCache<NSString,Bitmap>()
    private let ocr=NSCache<NSString,OCRText>()
    let requestLock=NSLock();var latestRequest=UUID()
    var document:PDFDocument?;var documentKey=""
    init(){images.totalCostLimit=64*1024*1024;ocr.totalCostLimit=4*1024*1024}
    static func sourceURL(library:URL,bookID:String,page:Int)throws->(URL,Int){
        guard bookID.range(of:"^[a-f0-9]{32}$",options:.regularExpression) != nil,page>=0 else{throw failure("Trang sách không hợp lệ.")}
        let folder=library.appendingPathComponent(bookID).resolvingSymlinksInPath()
        guard folder.deletingLastPathComponent()==library.resolvingSymlinksInPath(),
              let book=try JSONSerialization.jsonObject(with:Data(contentsOf:folder.appendingPathComponent("book.json"))) as? [String:Any],
              let pages=book["pages"] as? [[String:Any]],page<pages.count,
              let sources=book["sources"] as? [[String:Any]],let source=pages[page]["source"] as? Int,source>=0,source<sources.count,
              let name=sources[source]["file"] as? String,name.range(of:"^source-[0-9]+\\.(pdf|png|jpg|jpeg|heic|tiff|tif|webp)$",options:.regularExpression) != nil,
              let number=pages[page]["sourcePage"] as? Int,number>=0 else{throw failure("Chưa mở được trang gốc của sách.")}
        let url=folder.appendingPathComponent(name).resolvingSymlinksInPath()
        guard url.deletingLastPathComponent()==folder else{throw failure("Đường dẫn bản gốc không hợp lệ.")}
        return (url,number)
    }
    static func failure(_ text:String)->NSError{NSError(domain:"SourceReader",code:1,userInfo:[NSLocalizedDescriptionKey:text])}
    static func folded(_ text:String)->(NSString,[Int]){
        var result="";var positions:[Int]=[];var offset=0
        for scalar in text.unicodeScalars {
            let count=scalar.value>0xffff ? 2:1
            if !CharacterSet.whitespacesAndNewlines.contains(scalar){result.unicodeScalars.append(scalar);positions.append(contentsOf:(offset..<offset+count))}
            offset+=count
        }
        return (result as NSString,positions)
    }
    static func uniqueRange(_ text:String,in source:String)->NSRange?{
        let (all,positions)=folded(source);let (target,_)=folded(text)
        guard target.length>0 else{return nil}
        let found=all.range(of:target as String)
        guard found.location != NSNotFound,NSMaxRange(found)<=positions.count else{return nil}
        let remaining=NSRange(location:NSMaxRange(found),length:all.length-NSMaxRange(found))
        guard all.range(of:target as String,options:[],range:remaining).location==NSNotFound else{return nil}
        return NSRange(location:positions[found.location],length:positions[NSMaxRange(found)-1]-positions[found.location]+1)
    }
    static func normalized(_ rect:CGRect,bounds:CGRect,rotation:Int)->[String:Double]{
        var points=[CGPoint(x:rect.minX,y:rect.minY),CGPoint(x:rect.maxX,y:rect.maxY)]
        points=points.map{point in
            let x=(point.x-bounds.minX)/bounds.width,y=(bounds.maxY-point.y)/bounds.height
            switch (rotation%360+360)%360 {
            case 90:return CGPoint(x:1-y,y:x)
            case 180:return CGPoint(x:1-x,y:1-y)
            case 270:return CGPoint(x:y,y:1-x)
            default:return CGPoint(x:x,y:y)
            }
        }
        let x=max(0,min(points[0].x,points[1].x)),y=max(0,min(points[0].y,points[1].y))
        return ["x":x,"y":y,"w":min(1-x,abs(points[0].x-points[1].x)),"h":min(1-y,abs(points[0].y-points[1].y))]
    }
    func render(url:URL,page index:Int,data:[String:Any])throws->[String:Any]{
        let attributes=try FileManager.default.attributesOfItem(atPath:url.path)
        let key=url.path+":"+String((attributes[.modificationDate] as? Date)?.timeIntervalSince1970 ?? 0)+":"+String(describing:attributes[.size])
        let imageKey=(key+":"+String(index)) as NSString
        var page:PDFPage?
        if url.pathExtension.lowercased()=="pdf" {
            if documentKey != key{document=PDFDocument(url:url);documentKey=key}
            guard let doc=document,!doc.isLocked,index<doc.pageCount,let p=doc.page(at:index) else{throw Self.failure("PDF đang khóa hoặc không còn trang này.")}
            page=p
        }
        let bitmap:Bitmap
        if let cached=images.object(forKey:imageKey){bitmap=cached}
        else{
            let image:CGImage
            if let p=page {
                let bounds=p.bounds(for:.mediaBox);let ratio=1500/max(bounds.width,bounds.height)
                let preview=p.thumbnail(of:NSSize(width:bounds.width*ratio,height:bounds.height*ratio),for:.mediaBox)
                guard let cg=preview.cgImage(forProposedRect:nil,context:nil,hints:nil) else{throw Self.failure("Không dựng được trang PDF.")};image=cg
            }else{
                guard let source=CGImageSourceCreateWithURL(url as CFURL,nil),let cg=CGImageSourceCreateThumbnailAtIndex(source,0,[kCGImageSourceCreateThumbnailFromImageAlways:true,kCGImageSourceCreateThumbnailWithTransform:true,kCGImageSourceThumbnailMaxPixelSize:1500] as CFDictionary) else{throw Self.failure("Không mở được ảnh gốc.")};image=cg
            }
            guard let png=NSBitmapImageRep(cgImage:image).representation(using:.png,properties:[:]) else{throw Self.failure("Không dựng được ảnh trang sách.")}
            bitmap=Bitmap(image,png);images.setObject(bitmap,forKey:imageKey,cost:image.bytesPerRow*image.height+png.count)
        }
        let image=bitmap.image,png=bitmap.png
        let cues=data["sentences"] as? [[String:Any]] ?? []
        var highlights:[String:Any]=[:]
        if let p=page,let text=p.string,!text.trimmingCharacters(in:.whitespacesAndNewlines).isEmpty {
            for cue in cues {
                guard let id=cue["id"] as? String,let value=cue["text"] as? String else{continue}
                var range: NSRange?
                if text==data["rawText"] as? String,let raw=cue["sourceRange"] as? [String:Int],let start=raw["location"],let length=raw["length"],start>=0,length>0,start+length<=(text as NSString).length{range=NSRange(location:start,length:length)}
                else{range=Self.uniqueRange(value,in:text)}
                if let range=range,let selection=p.selection(for:range){highlights[id]=selection.selectionsByLine().map{Self.normalized($0.bounds(for:p),bounds:p.bounds(for:.mediaBox),rotation:p.rotation)}}
            }
        } else if !cues.isEmpty {
            // Older scan imports have no stored boxes. OCR this displayed page
            // locally once, then anchor only uniquely matching source sentences.
            let ocrKey=(imageKey as String)+":"+(data["language"] as? String ?? "vi")
            let anchored:OCRText
            if let cached=ocr.object(forKey:ocrKey as NSString){anchored=cached}
            else{
                let request=VNRecognizeTextRequest();request.recognitionLevel = .accurate;request.usesLanguageCorrection=false
                let languages=try request.supportedRecognitionLanguages()
                if data["language"] as? String != "en",let vi=languages.first(where:{$0.hasPrefix("vi-")}){request.recognitionLanguages=[vi,"en-US"]}else{request.recognitionLanguages=["en-US"]}
                try VNImageRequestHandler(cgImage:image,options:[:]).perform([request])
                let lines=(request.results ?? []).sorted{abs($0.boundingBox.midY-$1.boundingBox.midY)<0.008 ? $0.boundingBox.minX<$1.boundingBox.minX:$0.boundingBox.midY>$1.boundingBox.midY}
                var raw="";var spans:[(NSRange,CGRect)]=[]
                for line in lines{if let text=line.topCandidates(1).first?.string{let start=(raw as NSString).length;raw+=text+"\n";spans.append((NSRange(location:start,length:(text as NSString).length),line.boundingBox))}}
                anchored=OCRText(raw,spans);ocr.setObject(anchored,forKey:ocrKey as NSString,cost:raw.utf8.count+spans.count*64)
            }
            let raw=anchored.text,spans=anchored.spans
            for cue in cues{guard let id=cue["id"] as? String,let text=cue["text"] as? String,let range=Self.uniqueRange(text,in:raw) else{continue};highlights[id]=spans.filter{NSIntersectionRange($0.0,range).length>0}.map{["x":Double($0.1.minX),"y":Double(1-$0.1.maxY),"w":Double($0.1.width),"h":Double($0.1.height)]}}
        }
        return ["image":"data:image/png;base64,"+png.base64EncodedString(),"width":image.width,"height":image.height,"highlights":highlights]
    }
    func receive(_ value:[String:Any],library:URL,completion:@escaping([String:Any])->Void){
        guard let bid=value["bookId"] as? String,let page=value["page"] as? Int else{return}
        let requestID=UUID();requestLock.lock();latestRequest=requestID;requestLock.unlock()
        if value["format"] as? String=="epub"{completion(value);return}
        queue.async{
            self.requestLock.lock();let current=self.latestRequest==requestID;self.requestLock.unlock();if !current{return}
            var result=value
            do{let (url,index)=try Self.sourceURL(library:library,bookID:bid,page:page);result.merge(try self.render(url:url,page:index,data:value)){_,new in new}}
            catch{result["imageError"]=error.localizedDescription}
            self.requestLock.lock();let stillCurrent=self.latestRequest==requestID;self.requestLock.unlock();if !stillCurrent{return}
            DispatchQueue.main.async{
                self.requestLock.lock();let current=self.latestRequest==requestID;self.requestLock.unlock()
                if current{completion(result)}
            }
        }
    }
}
