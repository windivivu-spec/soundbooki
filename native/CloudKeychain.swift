import Foundation
import Security

// Secrets travel over stdin/stdout pipes, never process arguments or app events.
do {
    let data = FileHandle.standardInput.readDataToEndOfFile()
    guard data.count < 8192,
          let value = try JSONSerialization.jsonObject(with:data) as? [String:String],
          let action = value["action"] else {throw NSError(domain:"Keychain",code:1)}
    let books = value["domain"] == "books"
    let query:[String:Any] = [kSecClass as String:kSecClassGenericPassword,
        kSecAttrService as String:(books ? "studio.windi.sachnoi.books" : "studio.windi.sachnoi.credits"),
        kSecAttrAccount as String:(books ? "Book purchase device" : "App credit wallet")]
    var result:[String:Any] = [:]
    switch action {
    case "read", "create":
        var request=query;request[kSecReturnData as String]=true;request[kSecMatchLimit as String]=kSecMatchLimitOne
        var item:CFTypeRef?
        let status=SecItemCopyMatching(request as CFDictionary,&item)
        if status==errSecItemNotFound && action=="create" {
            var bytes=[UInt8](repeating:0,count:32)
            guard SecRandomCopyBytes(kSecRandomDefault,bytes.count,&bytes)==errSecSuccess else {throw NSError(domain:"Keychain",code:4)}
            let token=(books ? "wsn_book_" : "wsn_credit_")+bytes.map{String(format:"%02x",$0)}.joined()
            var create=query;create[kSecValueData as String]=Data(token.utf8);create[kSecAttrAccessible as String]=kSecAttrAccessibleWhenUnlockedThisDeviceOnly
            guard SecItemAdd(create as CFDictionary,nil)==errSecSuccess else {throw NSError(domain:"Keychain",code:5)}
            result=["token":token]
        } else {
            guard status==errSecSuccess,let secret=item as? Data,let token=String(data:secret,encoding:.utf8) else {throw NSError(domain:"Keychain",code:Int(status))}
            result=["token":token]
        }
    default:throw NSError(domain:"Keychain",code:3)
    }
    FileHandle.standardOutput.write(try JSONSerialization.data(withJSONObject:result))
} catch {
    print("{\"error\":\"Không truy cập được Keychain. Hãy mở khóa Mac rồi kết nối lại.\"}")
    exit(1)
}
