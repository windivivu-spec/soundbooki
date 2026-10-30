import AppKit
import WebKit

@main
struct VerifyImport {
    static func main() throws {
        let root=URL(fileURLWithPath:CommandLine.arguments[1]),fm=FileManager.default
        try fm.createDirectory(at:root,withIntermediateDirectories:true)
        let epub=root.appendingPathComponent("Sách có dấu.EPUB"),text=root.appendingPathComponent("invalid.txt"),folder=root.appendingPathComponent("unpacked.epub"),plain=root.appendingPathComponent("folder"),png=root.appendingPathComponent("page.png")
        try Data("fixture".utf8).write(to:epub);try Data("fixture".utf8).write(to:text);try Data().write(to:png)
        try fm.createDirectory(at:folder,withIntermediateDirectories:true);try fm.createDirectory(at:plain,withIntermediateDirectories:true)
        let policy=ImportPanelPolicy(),panel=NSOpenPanel()
        precondition(policy.panel(panel,shouldEnable:epub));precondition(!policy.panel(panel,shouldEnable:text));precondition(policy.panel(panel,shouldEnable:plain))
        let selected=try DocumentImport.validate([epub,epub]);precondition(selected.count==1)
        let unpacked=try DocumentImport.validate([folder]);precondition(unpacked.count==1)
        for bad in [[text],[plain],[epub,png],[URL(string:"https://example.com/book.epub")!],[root.appendingPathComponent("missing.epub")]] {
            do {_ = try DocumentImport.validate(bad);fatalError("Invalid selection accepted")}catch{}
        }
        let board=NSPasteboard.withUniqueName();defer{board.releaseGlobally()}
        precondition(board.writeObjects([epub as NSURL]))
        let dropped=try DocumentImport.validate(DocumentImport.urls(from:board));precondition(dropped==[epub.standardizedFileURL])
        print("PASS EPUB picker policy, uppercase/diacritics, unpacked EPUB, file pasteboard and rejected mixed/unsupported/remote selections")
    }
}
