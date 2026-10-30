import AppKit
import CoreImage

// EMV/VietQR transfer-to-account payload. No network or secret is needed to render it.
enum VietQR {
    static func field(_ tag:String,_ value:String)->String {
        precondition(value.utf8.count <= 99 && value.utf8.allSatisfy{$0 < 128})
        return tag + String(format:"%02d",value.utf8.count) + value
    }
    static func payload(bin:String,account:String,amount:Int,content:String)->String {
        let beneficiary=field("00",bin)+field("01",account)
        let merchant=field("00","A000000727")+field("01",beneficiary)+field("02","QRIBFTTA")
        let raw=field("00","01")+field("01","12")+field("38",merchant)+field("53","704")+field("54",String(amount))+field("58","VN")+field("62",field("08",content))+"6304"
        var crc:UInt16=0xFFFF
        for byte in raw.utf8 {
            crc ^= UInt16(byte)<<8
            for _ in 0..<8 {crc = (crc & 0x8000 != 0) ? (crc &<< 1)^0x1021 : crc &<< 1}
        }
        return raw+String(format:"%04X",crc)
    }
    static func image(_ payload:String)->String? {
        guard let filter=CIFilter(name:"CIQRCodeGenerator") else{return nil}
        filter.setValue(Data(payload.utf8),forKey:"inputMessage");filter.setValue("M",forKey:"inputCorrectionLevel")
        guard let qr=filter.outputImage else{return nil}
        // Integer-size modules plus an opaque four-module quiet zone for reliable scanning.
        let scale=8,quiet=4,modules=Int(qr.extent.width),size=(modules+quiet*2)*scale
        guard let cg=CIContext().createCGImage(qr,from:qr.extent),
              let bitmap=NSBitmapImageRep(bitmapDataPlanes:nil,pixelsWide:size,pixelsHigh:size,bitsPerSample:8,samplesPerPixel:4,hasAlpha:true,isPlanar:false,colorSpaceName:.deviceRGB,bytesPerRow:0,bitsPerPixel:0),
              let graphics=NSGraphicsContext(bitmapImageRep:bitmap) else{return nil}
        NSGraphicsContext.saveGraphicsState();NSGraphicsContext.current=graphics
        let context=graphics.cgContext;context.setFillColor(NSColor.white.cgColor);context.fill(CGRect(x:0,y:0,width:size,height:size))
        context.interpolationQuality = .none
        context.draw(cg,in:CGRect(x:quiet*scale,y:quiet*scale,width:modules*scale,height:modules*scale))
        NSGraphicsContext.restoreGraphicsState()
        guard let png=bitmap.representation(using:.png,properties:[:]) else{return nil}
        return "data:image/png;base64,"+png.base64EncodedString()
    }
    static func vector(_ payload:String)->(path:String,size:Int)? {
        guard let filter=CIFilter(name:"CIQRCodeGenerator") else{return nil}
        filter.setValue(Data(payload.utf8),forKey:"inputMessage");filter.setValue("M",forKey:"inputCorrectionLevel")
        guard let qr=filter.outputImage,let cg=CIContext().createCGImage(qr,from:qr.extent),
              let data=cg.dataProvider?.data,let bytes=CFDataGetBytePtr(data) else{return nil}
        let stride=cg.bitsPerPixel/8
        guard stride>0 else{return nil}
        var path=""
        for y in 0..<cg.height {for x in 0..<cg.width {
            if bytes[y*cg.bytesPerRow+x*stride]<128 {path += "M\(x+4) \(y+4)h1v1h-1z"}
        }}
        return (path,cg.width+8)
    }
    static func checkout(_ config:[String:Any],device:String)->[String:Any]? {
        guard device.range(of:"^SN[A-F0-9]{12}$",options:.regularExpression) != nil,
              let raw=config["checkoutURL"] as? String,let url=URL(string:raw),url.scheme=="https",url.host=="img.vietqr.io",
              let parts=URLComponents(url:url,resolvingAgainstBaseURL:false),let items=parts.queryItems else{return nil}
        let path=url.lastPathComponent.components(separatedBy:"-")
        guard path.count==3,["TPB","970423"].contains(path[0]),
              path[1].range(of:"^[0-9]{6,32}$",options:.regularExpression) != nil,
              items.filter({$0.name=="amount"}).count==1,items.first(where:{$0.name=="amount"})?.value=="189000",
              let holder=items.first(where:{$0.name=="accountName"})?.value,!holder.isEmpty,holder.count<=64,
              let image=image(payload(bin:"970423",account:path[1],amount:189000,content:device)),
              let vector=vector(payload(bin:"970423",account:path[1],amount:189000,content:device)) else{return nil}
        return ["event":"purchaseReady","qrImage":image,"qrPath":vector.path,"qrSize":vector.size,"bank":"TPBank","account":path[1],"holder":holder.replacingOccurrences(of:"+",with:" "),"amount":189000,"content":device]
    }
}
