import AppKit
import WebKit

// User-selected local documents only; Finder metadata/UTType is not authoritative.
enum DocumentImport {
    static let extensions:Set<String>=["epub","pdf","png","jpg","jpeg","heic","tiff","tif","webp"]
    static func validate(_ urls:[URL]) throws -> [URL] {
        func invalid(_ message:String)->NSError {NSError(domain:"WindiDocumentImport",code:1,userInfo:[NSLocalizedDescriptionKey:message])}
        guard !urls.isEmpty,urls.count<=2000 else{throw invalid("Chọn một EPUB/PDF hoặc từ 1 đến 2.000 ảnh.")}
        var unique=[URL](),seen=Set<String>()
        for url in urls {
            guard url.isFileURL else{throw invalid("Chỉ nhận tài liệu trên máy.")}
            let local=url.standardizedFileURL.resolvingSymlinksInPath(),ext=local.pathExtension.lowercased()
            var directory:ObjCBool=false
            guard extensions.contains(ext),FileManager.default.fileExists(atPath:local.path,isDirectory:&directory),FileManager.default.isReadableFile(atPath:local.path),(!directory.boolValue || ext=="epub") else {
                throw invalid("Chọn EPUB, PDF hoặc ảnh PNG/JPEG/HEIC/TIFF/WebP đọc được trên máy.")
            }
            if seen.insert(local.path).inserted {unique.append(local)}
        }
        if unique.count>1 && unique.contains(where:{["epub","pdf"].contains($0.pathExtension.lowercased())}) {throw invalid("Mỗi lần chọn một EPUB/PDF hoặc nhiều ảnh.")}
        return unique
    }
    static func urls(from pasteboard:NSPasteboard)->[URL] {
        (pasteboard.readObjects(forClasses:[NSURL.self],options:[.urlReadingFileURLsOnly:true]) as? [URL]) ?? []
    }
}

final class ImportPanelPolicy:NSObject,NSOpenSavePanelDelegate {
    func panel(_ sender:Any,shouldEnable url:URL)->Bool {
        // Folders remain navigable. Selection is validated before import.
        let directory=(try? url.resourceValues(forKeys:[.isDirectoryKey]).isDirectory) ?? false
        return directory || DocumentImport.extensions.contains(url.pathExtension.lowercased())
    }
    func panel(_ sender:Any,validate url:URL) throws { _ = try DocumentImport.validate([url]) }
}

final class ImportWebView:WKWebView {
    var onFiles:(([URL])->Void)?
    var onFileDrag:((Bool)->Void)?
    private func accepted(_ info:NSDraggingInfo)->[URL]? {
        guard info.draggingSourceOperationMask.contains(.copy) else{return nil}
        let urls=DocumentImport.urls(from:info.draggingPasteboard)
        return try? DocumentImport.validate(urls)
    }
    override func draggingEntered(_ sender:NSDraggingInfo)->NSDragOperation {
        if DocumentImport.urls(from:sender.draggingPasteboard).isEmpty{return super.draggingEntered(sender)}
        let valid=accepted(sender) != nil;onFileDrag?(valid);return valid ? .copy : []
    }
    override func draggingUpdated(_ sender:NSDraggingInfo)->NSDragOperation {
        if DocumentImport.urls(from:sender.draggingPasteboard).isEmpty{return super.draggingUpdated(sender)}
        let valid=accepted(sender) != nil;onFileDrag?(valid);return valid ? .copy : []
    }
    override func draggingExited(_ sender:NSDraggingInfo?) {onFileDrag?(false);super.draggingExited(sender)}
    override func prepareForDragOperation(_ sender:NSDraggingInfo)->Bool {
        if DocumentImport.urls(from:sender.draggingPasteboard).isEmpty{return super.prepareForDragOperation(sender)}
        return accepted(sender) != nil
    }
    override func performDragOperation(_ sender:NSDraggingInfo)->Bool {
        if DocumentImport.urls(from:sender.draggingPasteboard).isEmpty{return super.performDragOperation(sender)}
        onFileDrag?(false)
        guard let urls=accepted(sender) else{return false}
        onFiles?(urls);return true
    }
    override func concludeDragOperation(_ sender:NSDraggingInfo?) {onFileDrag?(false);super.concludeDragOperation(sender)}
}
