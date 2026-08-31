import CoreGraphics
import Foundation
import ImageIO
import Vision

private let cliVersion = "pmj-vision-ocr-swift/1.0.0"
private let pinnedRevision = VNRecognizeTextRequestRevision3

private struct Options {
    var imagePath: String?
    var languages: [String] = []
    var recognitionLevel = "accurate"
    var usesLanguageCorrection = true
    var witness = false
    var seed: UInt64 = 17
}

private enum CLIError: Error, CustomStringConvertible {
    case invalidArguments(String)
    case imageLoad(String)
    case unsupportedLanguage(String)

    var description: String {
        switch self {
        case .invalidArguments(let message): return message
        case .imageLoad(let message): return message
        case .unsupportedLanguage(let message): return message
        }
    }
}

private func fail(_ message: String, code: Int32 = 2) -> Never {
    FileHandle.standardError.write(Data((message + "\n").utf8))
    exit(code)
}

private func parseOptions() throws -> Options {
    var options = Options()
    let arguments = Array(CommandLine.arguments.dropFirst())
    var index = 0
    while index < arguments.count {
        let argument = arguments[index]
        switch argument {
        case "--image":
            index += 1
            guard index < arguments.count else {
                throw CLIError.invalidArguments("--image requires a path")
            }
            options.imagePath = arguments[index]
        case "--language":
            index += 1
            guard index < arguments.count else {
                throw CLIError.invalidArguments("--language requires a BCP-47 tag")
            }
            options.languages.append(arguments[index])
        case "--recognition-level":
            index += 1
            guard index < arguments.count,
                  ["accurate", "fast"].contains(arguments[index]) else {
                throw CLIError.invalidArguments(
                    "--recognition-level must be accurate or fast"
                )
            }
            options.recognitionLevel = arguments[index]
        case "--uses-language-correction":
            index += 1
            guard index < arguments.count,
                  ["true", "false"].contains(arguments[index]) else {
                throw CLIError.invalidArguments(
                    "--uses-language-correction must be true or false"
                )
            }
            options.usesLanguageCorrection = arguments[index] == "true"
        case "--witness":
            options.witness = true
        case "--seed":
            index += 1
            guard index < arguments.count,
                  let seed = UInt64(arguments[index]) else {
                throw CLIError.invalidArguments("--seed requires an unsigned integer")
            }
            options.seed = seed
        case "--version":
            print(cliVersion)
            exit(0)
        default:
            throw CLIError.invalidArguments("unknown argument: \(argument)")
        }
        index += 1
    }
    if options.languages.isEmpty {
        options.languages = ["en-US"]
    }
    if !options.witness && options.imagePath == nil {
        throw CLIError.invalidArguments("exactly one --image path is required")
    }
    return options
}

private func loadImage(path: String) throws -> CGImage {
    let url = URL(fileURLWithPath: path)
    guard let source = CGImageSourceCreateWithURL(url as CFURL, nil),
          let image = CGImageSourceCreateImageAtIndex(source, 0, nil) else {
        throw CLIError.imageLoad("unable to decode image: \(path)")
    }
    return image
}

private func seededWitnessImage(seed: UInt64) throws -> CGImage {
    let width = 96
    let height = 64
    let bytesPerPixel = 4
    let bytesPerRow = width * bytesPerPixel
    var pixels = [UInt8](repeating: 255, count: height * bytesPerRow)
    var state = seed == 0 ? 0x9e3779b97f4a7c15 : seed
    for row in 20..<44 {
        for column in 18..<78 {
            state = state &* 6364136223846793005 &+ 1442695040888963407
            let bit = (state >> 63) & 1
            if bit == 1 && (row % 4 == 0 || column % 7 == 0) {
                let offset = row * bytesPerRow + column * bytesPerPixel
                pixels[offset] = 0
                pixels[offset + 1] = 0
                pixels[offset + 2] = 0
                pixels[offset + 3] = 255
            }
        }
    }
    guard let provider = CGDataProvider(data: Data(pixels) as CFData),
          let colorSpace = CGColorSpace(name: CGColorSpace.sRGB),
          let image = CGImage(
              width: width,
              height: height,
              bitsPerComponent: 8,
              bitsPerPixel: 32,
              bytesPerRow: bytesPerRow,
              space: colorSpace,
              bitmapInfo: CGBitmapInfo(rawValue: CGImageAlphaInfo.last.rawValue),
              provider: provider,
              decode: nil,
              shouldInterpolate: false,
              intent: .defaultIntent
          ) else {
        throw CLIError.imageLoad("unable to build deterministic witness image")
    }
    return image
}

private func recognitionLevel(_ value: String) -> VNRequestTextRecognitionLevel {
    value == "fast" ? .fast : .accurate
}

private func validateLanguages(_ options: Options) throws {
    let probe = VNRecognizeTextRequest()
    probe.revision = pinnedRevision
    probe.recognitionLevel = recognitionLevel(options.recognitionLevel)
    let supported: [String]
    do {
        supported = try probe.supportedRecognitionLanguages()
    } catch {
        throw CLIError.unsupportedLanguage(
            "unable to query supported OCR languages for revision "
                + "\(pinnedRevision): \(error)"
        )
    }
    for language in options.languages where !supported.contains(language) {
        throw CLIError.unsupportedLanguage(
            "unsupported language \(language) for revision \(pinnedRevision); "
                + "supported=\(supported.sorted().joined(separator: ","))"
        )
    }
}

private func recognize(
    image: CGImage,
    options: Options
) throws -> ([VNRecognizedTextObservation], Double) {
    try validateLanguages(options)
    let request = VNRecognizeTextRequest()
    request.revision = pinnedRevision
    request.recognitionLevel = recognitionLevel(options.recognitionLevel)
    request.recognitionLanguages = options.languages
    request.usesLanguageCorrection = options.usesLanguageCorrection
    let start = DispatchTime.now().uptimeNanoseconds
    let handler = VNImageRequestHandler(cgImage: image, orientation: .up, options: [:])
    try handler.perform([request])
    let elapsed = DispatchTime.now().uptimeNanoseconds - start
    return (request.results ?? [], Double(elapsed) / 1_000_000.0)
}

private func jsonObservation(
    _ observation: VNRecognizedTextObservation
) -> [String: Any]? {
    guard let candidate = observation.topCandidates(1).first else { return nil }
    let box = observation.boundingBox
    return [
        "text": candidate.string,
        "confidence": Double(candidate.confidence),
        "bounding_box": [
            "x": Double(box.origin.x),
            "y": Double(box.origin.y),
            "width": Double(box.size.width),
            "height": Double(box.size.height),
        ],
    ]
}

private func emitJSON(
    observations: [VNRecognizedTextObservation],
    latencyMS: Double,
    options: Options
) throws {
    let sorted = observations.sorted { left, right in
        let verticalDifference = abs(left.boundingBox.maxY - right.boundingBox.maxY)
        if verticalDifference > 0.01 {
            return left.boundingBox.maxY > right.boundingBox.maxY
        }
        return left.boundingBox.minX < right.boundingBox.minX
    }
    let rows = sorted.compactMap(jsonObservation)
    let texts = rows.compactMap { $0["text"] as? String }
    let confidences = rows.compactMap { $0["confidence"] as? Double }
    let meanConfidence: Any = confidences.isEmpty
        ? NSNull()
        : confidences.reduce(0.0, +) / Double(confidences.count)
    let payload: [String: Any] = [
        "status": rows.isEmpty ? "no_text" : "ok",
        "text": rows.isEmpty ? NSNull() : texts.joined(separator: "\n"),
        "confidence": meanConfidence,
        "observations": rows,
        "latency_ms": latencyMS,
        "engine": [
            "framework": "Vision",
            "request": "VNRecognizeTextRequest",
            "request_revision": pinnedRevision,
            "recognition_level": options.recognitionLevel,
            "languages": options.languages,
            "uses_language_correction": options.usesLanguageCorrection,
            "swift_cli_version": cliVersion,
            "os_version": ProcessInfo.processInfo.operatingSystemVersionString,
        ],
    ]
    let data = try JSONSerialization.data(withJSONObject: payload, options: [.sortedKeys])
    guard let line = String(data: data, encoding: .utf8) else {
        throw CLIError.invalidArguments("unable to encode OCR result")
    }
    print(line)
}

do {
    let options = try parseOptions()
    if options.witness {
        let image = try seededWitnessImage(seed: options.seed)
        let (observations, _) = try recognize(image: image, options: options)
        print(
            "WITNESS vision_ocr seed=\(options.seed) "
                + "observations=\(observations.count) revision=\(pinnedRevision)"
        )
    } else {
        let image = try loadImage(path: options.imagePath!)
        let (observations, latency) = try recognize(image: image, options: options)
        try emitJSON(observations: observations, latencyMS: latency, options: options)
    }
} catch {
    fail("vision-ocr blocked: \(error)")
}
