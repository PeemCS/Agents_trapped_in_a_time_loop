import Foundation
import Vision
var output = [[String: Any]]()
for item in CommandLine.arguments.dropFirst() {
    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.usesLanguageCorrection = false
    request.recognitionLanguages = ["en-US"]
    request.minimumTextHeight = 0.006
    try VNImageRequestHandler(url: URL(fileURLWithPath:item)).perform([request])
    let observations = (request.results ?? []).compactMap { item in item.topCandidates(1).first?.string }
    output.append(["path": item, "observations": observations])
}
let data = try JSONSerialization.data(withJSONObject:output)
FileHandle.standardOutput.write(data)
