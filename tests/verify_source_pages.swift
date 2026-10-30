import AppKit
import Foundation

@main struct SourceQA {
 static func main()throws {
  let file=URL(fileURLWithPath:CommandLine.arguments[1]);let cases=try JSONSerialization.jsonObject(with:Data(contentsOf:file)) as! [[String:Any]]
  let renderer=SourcePageRenderer();var report:[[String:Any]]=[]
  for test in cases {
   let data=test["data"] as! [String:Any],library=URL(fileURLWithPath:test["library"] as! String),bid=test["bookID"] as! String
   let (url,page)=try SourcePageRenderer.sourceURL(library:library,bookID:bid,page:0)
   let result=try renderer.render(url:url,page:page,data:data)
   let highlights=result["highlights"] as! [String:Any]
   guard !highlights.isEmpty,(result["image"] as? String)?.hasPrefix("data:image/png;base64,")==true else{throw SourcePageRenderer.failure("Missing scan/image highlights")}
   for raw in highlights.values{for rect in raw as! [[String:Double]]{guard rect.values.allSatisfy({$0>=0 && $0<=1}) else{throw SourcePageRenderer.failure("Invalid bounds")}}}
   do{_=try SourcePageRenderer.sourceURL(library:library,bookID:"../escape",page:0);throw SourcePageRenderer.failure("Path escaped")}catch let error as NSError{if error.localizedDescription=="Path escaped"{throw error}}
   report.append(["file":url.lastPathComponent,"highlightedSentences":highlights.count,"page":page])
  }
  print(String(data:try JSONSerialization.data(withJSONObject:["result":"PASS","cases":report],options:[.prettyPrinted,.sortedKeys]),encoding:.utf8)!)
 }
}
