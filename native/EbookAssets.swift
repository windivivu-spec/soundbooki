import AppKit
import PDFKit
import CoreGraphics

// Read image placement only. Render illustration crops from the source page so
// masks, color spaces and orientation remain PDFKit's responsibility.
final class Placements {
 var transform=CGAffineTransform.identity;var stack:[CGAffineTransform]=[];var boxes:[CGRect]=[]
 let content:CGPDFContentStreamRef;let depth:Int
 init(_ content:CGPDFContentStreamRef,_ transform:CGAffineTransform = .identity,_ depth:Int=0){self.content=content;self.transform=transform;self.depth=depth}
}
func state(_ pointer:UnsafeMutableRawPointer?)->Placements{Unmanaged<Placements>.fromOpaque(pointer!).takeUnretainedValue()}
let operators:CGPDFOperatorTableRef = {
 let table=CGPDFOperatorTableCreate()!
 CGPDFOperatorTableSetCallback(table,"q"){_,p in let s=state(p);s.stack.append(s.transform)}
 CGPDFOperatorTableSetCallback(table,"Q"){_,p in let s=state(p);s.transform=s.stack.popLast() ?? .identity}
 CGPDFOperatorTableSetCallback(table,"cm"){scanner,p in
  var v=[CGPDFReal](repeating:0,count:6)
  for i in (0..<6).reversed(){guard CGPDFScannerPopNumber(scanner,&v[i]) else{return}}
  let s=state(p);s.transform=CGAffineTransform(a:v[0],b:v[1],c:v[2],d:v[3],tx:v[4],ty:v[5]).concatenating(s.transform)
 }
 CGPDFOperatorTableSetCallback(table,"Do"){scanner,p in
  let s=state(p);var name:UnsafePointer<CChar>?
  guard CGPDFScannerPopName(scanner,&name),let name=name,let object=CGPDFContentStreamGetResource(s.content,"XObject",name) else{return}
  var stream:CGPDFStreamRef?;guard CGPDFObjectGetValue(object,.stream,&stream),let stream=stream,let dict=CGPDFStreamGetDictionary(stream) else{return}
  var type:UnsafePointer<CChar>?;guard CGPDFDictionaryGetName(dict,"Subtype",&type),let type=type else{return}
  if String(cString:type)=="Image"{s.boxes.append(CGRect(x:0,y:0,width:1,height:1).applying(s.transform))}
  else if String(cString:type)=="Form",s.depth<8 {
   var resources:CGPDFDictionaryRef?;CGPDFDictionaryGetDictionary(dict,"Resources",&resources)
   var matrix:CGPDFArrayRef?;var t=CGAffineTransform.identity
   if CGPDFDictionaryGetArray(dict,"Matrix",&matrix),let m=matrix,CGPDFArrayGetCount(m)==6{var v=[CGPDFReal](repeating:0,count:6);for i in 0..<6{CGPDFArrayGetNumber(m,i,&v[i])};t=CGAffineTransform(a:v[0],b:v[1],c:v[2],d:v[3],tx:v[4],ty:v[5])}
   let content=CGPDFContentStreamCreateWithStream(stream,resources ?? dict,s.content);let nested=Placements(content,t.concatenating(s.transform),s.depth+1)
   let child=CGPDFScannerCreate(content,operators,Unmanaged.passUnretained(nested).toOpaque());CGPDFScannerScan(child);s.boxes+=nested.boxes
  }
 }
 return table
}()
func images(_ page:PDFPage)->[CGRect]{
 guard let ref=page.pageRef,page.rotation==0 else{return []}
 let content=CGPDFContentStreamCreateWithPage(ref),s=Placements(content)
 let scanner=CGPDFScannerCreate(content,operators,Unmanaged.passUnretained(s).toOpaque());CGPDFScannerScan(scanner)
 let bounds=page.bounds(for:.mediaBox)
 var boxes:[CGRect]=[];let area=bounds.width*bounds.height
 for raw in s.boxes{let box=raw.intersection(bounds);let fraction=box.width*box.height/area;if !box.isNull && box.width>40 && box.height>40 && fraction>0.015 && fraction<0.85{boxes.append(box)}}
 // Related image tiles (for example a portrait beside two photos) form one figure.
 var groups:[CGRect]=[]
 for box in boxes {
  if let i=groups.firstIndex(where:{$0.insetBy(dx:-8,dy:-8).intersects(box)}){groups[i]=groups[i].union(box)}else{groups.append(box)}
 }
 return groups.sorted{$0.maxY>$1.maxY}
}
do {
 let args=CommandLine.arguments;guard args.count==3 else{throw NSError(domain:"Ebook",code:1)}
 let metadata=URL(fileURLWithPath:args[1]),destination=URL(fileURLWithPath:args[2]);try FileManager.default.createDirectory(at:destination,withIntermediateDirectories:true)
 let book=try JSONSerialization.jsonObject(with:Data(contentsOf:metadata)) as! [String:Any]
 let pages=book["pages"] as! [[String:Any]],sources=book["sources"] as! [[String:Any]];var docs:[Int:PDFDocument]=[:];var output:[[String:Any]]=[];var total=0
 for (at,item) in pages.enumerated() {
  guard output.count<500,total<24*1024*1024,item["method"] as? String=="text",let source=item["source"] as? Int,source>=0,source<sources.count,let name=sources[source]["file"] as? String,name.range(of:"^source-[0-9]+\\.pdf$",options:.regularExpression) != nil,let number=item["sourcePage"] as? Int else{continue}
  let url=metadata.deletingLastPathComponent().appendingPathComponent(name).resolvingSymlinksInPath()
  guard url.deletingLastPathComponent()==metadata.deletingLastPathComponent().resolvingSymlinksInPath() else{continue}
  if docs[source]==nil{docs[source]=PDFDocument(url:url)}
  guard let page=docs[source]?.page(at:number) else{continue};let bounds=page.bounds(for:.mediaBox);let boxes=images(page);if boxes.isEmpty{continue}
  let size=NSSize(width:bounds.width*2,height:bounds.height*2)
  guard let image=page.thumbnail(of:size,for:.mediaBox).cgImage(forProposedRect:nil,context:nil,hints:nil) else{continue}
  for (i,box) in boxes.enumerated(){
   let sx=CGFloat(image.width)/bounds.width,sy=CGFloat(image.height)/bounds.height
   let rect=CGRect(x:(box.minX-bounds.minX)*sx,y:(bounds.maxY-box.maxY)*sy,width:box.width*sx,height:box.height*sy).integral
   guard let crop=image.cropping(to:rect),let png=NSBitmapImageRep(cgImage:crop).representation(using:.jpeg,properties:[.compressionFactor:0.8]),total+png.count<24*1024*1024 else{continue}
   let name="p\(at)-\(i).jpg";try png.write(to:destination.appendingPathComponent(name),options:.atomic);total+=png.count
   output.append(["page":at,"file":name,"y":Double((bounds.maxY-box.maxY)/bounds.height),"bottom":Double((bounds.maxY-box.minY)/bounds.height),"height":Double(bounds.height),"width":crop.width,"pixelsHigh":crop.height])
  }
 }
 let data=try JSONSerialization.data(withJSONObject:output);try data.write(to:destination.appendingPathComponent("figures.json"),options:.atomic)
 print("{\"figures\":\(output.count)}")
} catch {fputs("Không trích được ảnh minh họa: \(error)\n",stderr);exit(1)}
