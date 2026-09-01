import CoreGraphics
import CoreText
import Foundation
import ImageIO
import Vision

private let cliVersion = "pmj-vision-popup-roi-ocr/1.0.0"
private let ocrRevision = VNRecognizeTextRequestRevision3
private let decisionThreshold = 0.82
private let expansionFraction = 0.02

private struct Options {
    var imagePath: String?
    var witness = false
}

private enum EngineError: Error, CustomStringConvertible {
    case invalidArguments(String)
    case imageLoad(String)

    var description: String {
        switch self {
        case .invalidArguments(let message): return message
        case .imageLoad(let message): return message
        }
    }
}

private func fail(_ message: String) -> Never {
    FileHandle.standardError.write(Data((message + "\n").utf8))
    exit(2)
}

private func parseOptions() throws -> Options {
    var options = Options()
    let arguments = Array(CommandLine.arguments.dropFirst())
    var index = 0
    while index < arguments.count {
        switch arguments[index] {
        case "--image":
            index += 1
            guard index < arguments.count else {
                throw EngineError.invalidArguments("--image requires a path")
            }
            options.imagePath = arguments[index]
        case "--witness":
            options.witness = true
        case "--version":
            print(cliVersion)
            exit(0)
        default:
            throw EngineError.invalidArguments("unknown argument: \(arguments[index])")
        }
        index += 1
    }
    if options.witness == (options.imagePath != nil) {
        throw EngineError.invalidArguments("use exactly one of --image or --witness")
    }
    return options
}

private func loadImage(path: String) throws -> CGImage {
    let url = URL(fileURLWithPath: path)
    guard let source = CGImageSourceCreateWithURL(url as CFURL, nil),
          let image = CGImageSourceCreateImageAtIndex(source, 0, nil) else {
        throw EngineError.imageLoad("unable to decode image: \(path)")
    }
    return image
}

private func drawText(
    _ text: String,
    at point: CGPoint,
    size: CGFloat,
    context: CGContext
) {
    let font = CTFontCreateWithName("Helvetica-Bold" as CFString, size, nil)
    let attributes: [CFString: Any] = [
        kCTFontAttributeName: font,
        kCTForegroundColorAttributeName: CGColor(gray: 0.0, alpha: 1.0),
    ]
    let attributed = CFAttributedStringCreate(nil, text as CFString, attributes as CFDictionary)!
    let line = CTLineCreateWithAttributedString(attributed)
    context.textPosition = point
    CTLineDraw(line, context)
}

private func witnessImage() throws -> CGImage {
    let width = 800
    let height = 1200
    guard let colorSpace = CGColorSpace(name: CGColorSpace.sRGB),
          let context = CGContext(
              data: nil,
              width: width,
              height: height,
              bitsPerComponent: 8,
              bytesPerRow: 0,
              space: colorSpace,
              bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue
          ) else {
        throw EngineError.imageLoad("unable to create witness context")
    }
    context.setFillColor(CGColor(gray: 0.18, alpha: 1.0))
    context.fill(CGRect(x: 0, y: 0, width: width, height: height))
    let card = CGRect(x: 120, y: 330, width: 560, height: 540)
    context.setFillColor(CGColor(gray: 1.0, alpha: 1.0))
    context.fill(card)
    context.setStrokeColor(CGColor(gray: 0.0, alpha: 1.0))
    context.setLineWidth(8)
    context.stroke(card)
    context.textMatrix = .identity
    drawText("VISIBLE", at: CGPoint(x: 230, y: 620), size: 62, context: context)
    drawText("OFFER", at: CGPoint(x: 270, y: 515), size: 62, context: context)
    guard let image = context.makeImage() else {
        throw EngineError.imageLoad("unable to build witness image")
    }
    return image
}

private func expanded(_ box: CGRect) -> CGRect {
    let left = max(0.0, box.minX - expansionFraction)
    let bottom = max(0.0, box.minY - expansionFraction)
    let right = min(1.0, box.maxX + expansionFraction)
    let top = min(1.0, box.maxY + expansionFraction)
    return CGRect(x: left, y: bottom, width: right - left, height: top - bottom)
}

private func crop(_ image: CGImage, normalized box: CGRect) -> CGImage? {
    let width = CGFloat(image.width)
    let height = CGFloat(image.height)
    let pixels = CGRect(
        x: box.minX * width,
        y: (1.0 - box.maxY) * height,
        width: box.width * width,
        height: box.height * height
    ).integral
    return image.cropping(to: pixels)
}

private func shapeScore(_ observation: VNRectangleObservation) -> Double? {
    let box = observation.boundingBox
    let area = Double(box.width * box.height)
    guard area >= 0.06, area <= 0.72,
          box.minX >= 0.025, box.minY >= 0.025,
          box.maxX <= 0.975, box.maxY <= 0.975 else {
        return nil
    }
    let dx = Double(box.midX - 0.5)
    let dy = Double(box.midY - 0.5)
    let distance = sqrt(dx * dx + dy * dy)
    guard distance <= 0.36 else { return nil }
    let centrality = 1.0 - distance / 0.36
    let areaFit = 1.0 - min(abs(area - 0.28) / 0.28, 1.0)
    return 0.60 * Double(observation.confidence) + 0.25 * centrality + 0.15 * areaFit
}

private func detectRectangle(_ image: CGImage) throws -> (VNRectangleObservation, Double)? {
    let request = VNDetectRectanglesRequest()
    request.minimumConfidence = 0.8
    request.minimumAspectRatio = 0.3
    request.maximumAspectRatio = 1.0
    request.minimumSize = 0.12
    request.quadratureTolerance = 12.0
    request.maximumObservations = 16
    let handler = VNImageRequestHandler(cgImage: image, orientation: .up, options: [:])
    try handler.perform([request])
    let candidates = (request.results ?? []).compactMap { observation -> (VNRectangleObservation, Double)? in
        guard let score = shapeScore(observation) else { return nil }
        return (observation, score)
    }
    return candidates.sorted { left, right in
        if abs(left.1 - right.1) > 0.000_001 { return left.1 > right.1 }
        let leftBox = left.0.boundingBox
        let rightBox = right.0.boundingBox
        if abs(leftBox.maxY - rightBox.maxY) > 0.000_001 {
            return leftBox.maxY > rightBox.maxY
        }
        return leftBox.minX < rightBox.minX
    }.first
}

private func recognizeText(_ image: CGImage) throws -> ([String], Int) {
    let request = VNRecognizeTextRequest()
    request.revision = ocrRevision
    request.recognitionLevel = .accurate
    request.recognitionLanguages = ["zh-Hans", "en-US"]
    request.usesLanguageCorrection = true
    let handler = VNImageRequestHandler(cgImage: image, orientation: .up, options: [:])
    try handler.perform([request])
    let observations = request.results ?? []
    let sorted = observations.sorted { left, right in
        if abs(left.boundingBox.maxY - right.boundingBox.maxY) > 0.01 {
            return left.boundingBox.maxY > right.boundingBox.maxY
        }
        return left.boundingBox.minX < right.boundingBox.minX
    }
    let texts = sorted.compactMap { $0.topCandidates(1).first?.string }
    return (texts, observations.count)
}

private func engineIdentity() -> [String: Any] {
    return [
        "cli_version": cliVersion,
        "framework": "Vision",
        "rectangle_request": "VNDetectRectanglesRequest",
        "ocr_request": "VNRecognizeTextRequest",
        "ocr_revision": ocrRevision,
        "os_version": ProcessInfo.processInfo.operatingSystemVersionString,
        "decision_threshold": decisionThreshold,
    ]
}

private func emit(_ payload: [String: Any]) throws {
    let data = try JSONSerialization.data(withJSONObject: payload, options: [.sortedKeys])
    guard let line = String(data: data, encoding: .utf8) else {
        throw EngineError.invalidArguments("unable to encode result")
    }
    print(line)
}

private func abstain(reason: String, latencyMS: Double) throws {
    try emit([
        "status": "abstain",
        "block_reason": reason,
        "latency_ms": latencyMS,
        "engine": engineIdentity(),
    ])
}

private func run(_ image: CGImage) throws {
    let start = DispatchTime.now().uptimeNanoseconds
    guard let (rectangle, score) = try detectRectangle(image), score >= decisionThreshold else {
        let latency = Double(DispatchTime.now().uptimeNanoseconds - start) / 1_000_000.0
        try abstain(reason: "no_strong_popup_rectangle", latencyMS: latency)
        return
    }
    let box = expanded(rectangle.boundingBox)
    guard let roi = crop(image, normalized: box) else {
        let latency = Double(DispatchTime.now().uptimeNanoseconds - start) / 1_000_000.0
        try abstain(reason: "popup_roi_crop_failed", latencyMS: latency)
        return
    }
    let (texts, observationCount) = try recognizeText(roi)
    let message = texts.joined(separator: "\n").trimmingCharacters(in: .whitespacesAndNewlines)
    guard observationCount >= 1, message.count >= 4 else {
        let latency = Double(DispatchTime.now().uptimeNanoseconds - start) / 1_000_000.0
        try abstain(reason: "popup_roi_text_not_observed", latencyMS: latency)
        return
    }
    let latency = Double(DispatchTime.now().uptimeNanoseconds - start) / 1_000_000.0
    try emit([
        "status": "popup",
        "presence_confidence": score,
        "roi_normalized_xyxy": [
            Double(box.minX),
            Double(1.0 - box.maxY),
            Double(box.maxX),
            Double(1.0 - box.minY),
        ],
        "roi_confidence": Double(rectangle.confidence),
        "message_text": message,
        "critical_facts": [],
        "latency_ms": latency,
        "engine": engineIdentity(),
    ])
}

do {
    let options = try parseOptions()
    let image = options.witness ? try witnessImage() : try loadImage(path: options.imagePath!)
    try run(image)
} catch {
    fail("vision-popup-roi-ocr blocked: \(error)")
}
