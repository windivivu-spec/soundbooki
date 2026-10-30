import AppKit
import Vision

@main
struct PaymentVerification {
    static func main() throws {
        // Published VietQR API example: independent golden payload, including CRC.
        // https://www.vietqr.io/danh-sach-api/link-tao-ma-nhanh/api-tao-ma-qr
        let expected="00020101021238560010A0000007270126000697041501121133666688880208QRIBFTTA53037045405790005802VN62220818Ung Ho Quy Vac Xin63043ACF"
        precondition(VietQR.payload(bin:"970415",account:"113366668888",amount:79000,content:"Ung Ho Quy Vac Xin")==expected,"Official fixture mismatch")
        let code="SN123456ABCDEF"
        let config:[String:Any]=["checkoutURL":"https://img.vietqr.io/image/TPB-55111685555-compact2.png?amount=189000&addInfo=&accountName=BUI+QUOC+HUNG"]
        let result=VietQR.checkout(config,device:code)!
        precondition(result["amount"] as? Int == 189000 && result["content"] as? String == code && result["account"] as? String == "55111685555" && result["holder"] as? String == "BUI QUOC HUNG")
        let image=result["qrImage"] as! String
        let bytes=Data(base64Encoded:String(image.split(separator:",",maxSplits:1)[1]))!
        let request=VNDetectBarcodesRequest();request.symbologies=[.qr]
        try VNImageRequestHandler(data:bytes).perform([request])
        let payload=request.results?.first?.payloadStringValue
        precondition(payload==VietQR.payload(bin:"970423",account:"55111685555",amount:189000,content:code),"PNG QR does not decode to intended transfer")
        // Rasterize the emitted SVG path with SVG's top-left coordinate system,
        // then scan it independently. This catches a mirrored or transposed matrix.
        let svgPath=result["qrPath"] as! String,svgSize=result["qrSize"] as! Int
        let bitmap=NSBitmapImageRep(bitmapDataPlanes:nil,pixelsWide:svgSize*8,pixelsHigh:svgSize*8,bitsPerSample:8,samplesPerPixel:4,hasAlpha:true,isPlanar:false,colorSpaceName:.deviceRGB,bytesPerRow:0,bitsPerPixel:0)!
        NSGraphicsContext.saveGraphicsState();NSGraphicsContext.current=NSGraphicsContext(bitmapImageRep:bitmap)
        let context=NSGraphicsContext.current!.cgContext
        context.setFillColor(NSColor.white.cgColor);context.fill(CGRect(x:0,y:0,width:svgSize*8,height:svgSize*8))
        context.setFillColor(NSColor.black.cgColor)
        let regex=try NSRegularExpression(pattern:"M([0-9]+) ([0-9]+)h1v1h-1z"),source=svgPath as NSString
        for match in regex.matches(in:svgPath,range:NSRange(location:0,length:source.length)) {
            let x=Int(source.substring(with:match.range(at:1)))!,y=Int(source.substring(with:match.range(at:2)))!
            context.fill(CGRect(x:x*8,y:(svgSize-y-1)*8,width:8,height:8))
        }
        NSGraphicsContext.restoreGraphicsState()
        let vectorPNG=bitmap.representation(using:.png,properties:[:])!
        let vectorRequest=VNDetectBarcodesRequest();vectorRequest.symbologies=[.qr]
        try VNImageRequestHandler(data:vectorPNG).perform([vectorRequest])
        precondition(vectorRequest.results?.first?.payloadStringValue==payload,"SVG transfer payload mismatch")
        var wrong=config;wrong["checkoutURL"]=(config["checkoutURL"] as! String).replacingOccurrences(of:"189000",with:"1")
        precondition(VietQR.checkout(wrong,device:code)==nil)
        precondition(VietQR.checkout(config,device:"SN123")==nil)
        wrong["checkoutURL"]="https://example.com/image/TPB-55111685555-compact2.png?amount=189000&accountName=BUI"
        precondition(VietQR.checkout(wrong,device:code)==nil)
        let output=CommandLine.arguments.dropFirst().first
        if let output=output {try bytes.write(to:URL(fileURLWithPath:output))}
        print("PASS official VietQR payload, CRC, PNG and SVG scans, pinned amount/account/device and invalid configuration")
    }
}
