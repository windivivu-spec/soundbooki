import AppKit
import CoreImage
@main struct VerifyPaidQR {
 static func main() throws {
  let root=URL(fileURLWithPath:FileManager.default.currentDirectoryPath)
  let info=try JSONSerialization.jsonObject(with:Data(contentsOf:root.appendingPathComponent(".qa/paid-cloud/mac-order.json"))) as! [String:Any]
  let bank=info["bank"] as! [String:Any]
  let image=NSImage(contentsOf:root.appendingPathComponent(".qa/paid-cloud/mac-live-payment.png"))!
  let bitmap=NSBitmapImageRep(data:image.tiffRepresentation!)!
  let detector=CIDetector(ofType:CIDetectorTypeQRCode,context:nil,options:[CIDetectorAccuracy:CIDetectorAccuracyHigh])!
  let codes=detector.features(in:CIImage(cgImage:bitmap.cgImage!)).compactMap{($0 as? CIQRCodeFeature)?.messageString}
  let expected=VietQR.payload(bin:bank["bin"] as! String,account:bank["account"] as! String,amount:info["amountVND"] as! Int,content:info["paymentCode"] as! String)
  guard codes.contains(expected) else{fputs("FAIL: actual Mac QR differs from its server order\n",stderr);exit(1)}
  print("PASS: actual Mac QR scans to the exact server-quoted amount, receiving account and unique payment code")
 }
}
