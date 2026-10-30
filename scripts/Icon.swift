import AppKit

// Compose the supplied artwork; keep the originals in media-kit/logo.
// Source rectangles exclude the transparent export margins, not the artwork.
guard CommandLine.arguments.count == 4 else {
    fatalError("Usage: make-icon output.iconset source-directory ui-brand-directory")
}
let directory = URL(fileURLWithPath: CommandLine.arguments[1])
let source = URL(fileURLWithPath: CommandLine.arguments[2])
let brand = URL(fileURLWithPath: CommandLine.arguments[3])
for folder in [directory, brand] {
    try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
}
func load(_ name: String, crop: CGRect? = nil) -> NSImage {
    guard let data = try? Data(contentsOf: source.appendingPathComponent(name)),
          let rep = NSBitmapImageRep(data: data),
          let full = rep.cgImage,
          let image = crop.map({ full.cropping(to: $0) }) ?? full else {
        fatalError("Missing brand artwork: \(name)")
    }
    return NSImage(cgImage: image, size: NSSize(width: image.width, height: image.height))
}
let logo = load("logo.png", crop: CGRect(x: 209, y: 169, width: 876, height: 917))
let wordmark = load("typo.png", crop: CGRect(x: 81, y: 188, width: 2010, height: 334))
let background = load("background.png")

func png(width: Int, height: Int, draw: () -> Void) -> Data {
    guard let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: width, pixelsHigh: height,
                                    bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true,
                                    isPlanar: false, colorSpaceName: .deviceRGB,
                                    bytesPerRow: 0, bitsPerPixel: 0) else { fatalError("Cannot allocate brand image") }
    rep.size = NSSize(width: width, height: height)
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)
    NSGraphicsContext.current?.imageInterpolation = .high
    draw()
    NSGraphicsContext.restoreGraphicsState()
    guard let data = rep.representation(using: .png, properties: [:]) else { fatalError("Cannot encode brand image") }
    return data
}
func fit(_ image: NSImage, in rect: NSRect) {
    let scale = min(rect.width / image.size.width, rect.height / image.size.height)
    let size = NSSize(width: image.size.width * scale, height: image.size.height * scale)
    image.draw(in: NSRect(x: rect.midX - size.width / 2, y: rect.midY - size.height / 2,
                         width: size.width, height: size.height),
               from: .zero, operation: .sourceOver, fraction: 1)
}
let master = png(width: 1024, height: 1024) {
    // One macOS tile with a background that runs to its rounded edge.
    // Only the outer transparent Dock alignment canvas remains.
    let tile = NSRect(x: 56, y: 56, width: 912, height: 912)
    NSBezierPath(roundedRect: tile, xRadius: 204, yRadius: 204).addClip()
    background.draw(in: tile, from: .zero, operation: .copy, fraction: 1)
    let markInset = tile.width * 0.15
    fit(logo, in: tile.insetBy(dx: markInset, dy: markInset))
}
let icon = NSImage(data: master)!
for size in [16, 32, 128, 256, 512] {
    for scale in [1, 2] {
        let pixels = size * scale
        let data = png(width: pixels, height: pixels) {
            icon.draw(in: NSRect(x: 0, y: 0, width: pixels, height: pixels),
                      from: .zero, operation: .copy, fraction: 1)
        }
        let suffix = scale == 2 ? "@2x" : ""
        try data.write(to: directory.appendingPathComponent("icon_\(size)x\(size)\(suffix).png"))
    }
}
try master.write(to: brand.appendingPathComponent("app-icon-master.png"))
try png(width: 512, height: 536) {
    fit(logo, in: NSRect(x: 0, y: 0, width: 512, height: 536))
}.write(to: brand.appendingPathComponent("logo.png"))
try png(width: 1206, height: 200) {
    fit(wordmark, in: NSRect(x: 0, y: 0, width: 1206, height: 200))
}.write(to: brand.appendingPathComponent("wordmark.png"))
