import Foundation
import Vision
import PDFKit
import AppKit

struct Segment: Codable { let text: String; let x: Double; let y: Double; let height: Double; let confidence: Float }
struct Page: Codable { let number: Int; let segments: [Segment] }
do {
    guard CommandLine.arguments.count == 2,
          let document = PDFDocument(url: URL(fileURLWithPath: CommandLine.arguments[1])),
          document.pageCount > 0, document.pageCount <= 12 else {
        throw NSError(domain: "OCR", code: 1, userInfo: [NSLocalizedDescriptionKey: "PDF must contain 1 to 12 pages"])
    }
    var pages = [Page]()
    for index in 0..<document.pageCount {
        guard let page = document.page(at: index) else { continue }
        let bounds = page.bounds(for: .mediaBox)
        guard bounds.width > 0, bounds.height > 0 else { throw NSError(domain: "OCR", code: 2) }
        let scale = min(2200 / bounds.width, 3000 / bounds.height)
        let size = CGSize(width: bounds.width * scale, height: bounds.height * scale)
        let thumbnail = page.thumbnail(of: size, for: .mediaBox)
        var rect = CGRect(origin: .zero, size: thumbnail.size)
        guard let cgImage = thumbnail.cgImage(forProposedRect: &rect, context: nil, hints: nil) else { throw NSError(domain: "OCR", code: 3) }
        let request = VNRecognizeTextRequest()
        request.recognitionLevel = .accurate
        request.recognitionLanguages = ["en-US", "ko-KR"]
        request.usesLanguageCorrection = false
        try VNImageRequestHandler(cgImage: cgImage).perform([request])
        let segments = (request.results ?? []).compactMap { observation -> Segment? in
            guard let candidate = observation.topCandidates(1).first else { return nil }
            let box = observation.boundingBox
            return Segment(text: candidate.string, x: box.minX, y: box.midY, height: box.height, confidence: candidate.confidence)
        }
        pages.append(Page(number: index + 1, segments: segments))
    }
    let data = try JSONEncoder().encode(pages)
    FileHandle.standardOutput.write(data)
} catch {
    FileHandle.standardError.write(Data("OCR failed: \(error.localizedDescription)\n".utf8))
    exit(1)
}
