import Foundation
import CryptoKit
import IOKit

// Small offline verifier: JSON-lines stdout, no network or private signing key.
do {
    let args = CommandLine.arguments
    if args.count == 2 && args[1] == "--device-code" {
        let service=IOServiceGetMatchingService(kIOMainPortDefault,IOServiceMatching("IOPlatformExpertDevice"))
        guard service != 0 else {throw NSError(domain:"Device",code:1)}
        defer {IOObjectRelease(service)}
        guard let value=IORegistryEntryCreateCFProperty(service,"IOPlatformUUID" as CFString,kCFAllocatorDefault,0)?.takeRetainedValue() as? String,!value.isEmpty else {throw NSError(domain:"Device",code:2)}
        let hash=SHA256.hash(data:Data(("studio.windi.sachnoi/device/v1/"+value).utf8))
        let code="SN"+hash.prefix(6).map{String(format:"%02X",$0)}.joined()
        print("{\"deviceCode\":\"\(code)\"}")
        exit(0)
    }
    guard args.count == 4,
          let key = Data(base64Encoded: args[1]),
          let payload = Data(base64Encoded: args[2]),
          let signature = Data(base64Encoded: args[3]) else { throw NSError(domain:"License",code:1) }
    let publicKey = try Curve25519.Signing.PublicKey(rawRepresentation:key)
    guard publicKey.isValidSignature(signature,for:payload) else { throw NSError(domain:"License",code:2) }
    print("{\"valid\":true}")
} catch {
    print("{\"valid\":false}")
    exit(1)
}
