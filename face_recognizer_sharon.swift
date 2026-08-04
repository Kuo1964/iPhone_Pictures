import Foundation
import Vision
import CoreImage
import CoreGraphics

// 太太 Sharon 極嚴格精準人臉辨識引擎 (face_recognizer_sharon.swift)
let baseDir = URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
let photosDirURL = baseDir.appendingPathComponent("Photos")
let targetPath = "references/sharon_base.png"

let targetURL = baseDir.appendingPathComponent(targetPath)
print("🎯 載入太太 [太太Sharon] 基準比對照片: \(targetURL.path)")

guard let targetCIImage = CIImage(contentsOf: targetURL) else {
    print("❌ 無法載入太太基準照片！")
    exit(1)
}

var baseFacePrints: [VNFeaturePrintObservation] = []

let faceReq = VNDetectFaceRectanglesRequest()
let handler = VNImageRequestHandler(ciImage: targetCIImage, options: [:])
try? handler.perform([faceReq])

if let faceObs = faceReq.results?.first {
    let bbox = faceObs.boundingBox
    let imgSize = targetCIImage.extent.size
    let cropRect = CGRect(x: bbox.origin.x * imgSize.width,
                          y: bbox.origin.y * imgSize.height,
                          width: bbox.size.width * imgSize.width,
                          height: bbox.size.height * imgSize.height)
    
    let faceCIImg = targetCIImage.cropped(to: cropRect)
    let faceHandler = VNImageRequestHandler(ciImage: faceCIImg, options: [:])
    let printReq = VNGenerateImageFeaturePrintRequest()
    try? faceHandler.perform([printReq])
    
    if let ob = printReq.results?.first as? VNFeaturePrintObservation {
        baseFacePrints.append(ob)
        print("✅ 成功提取太太人臉 Bounding Box 嚴格特徵向量！")
    }
}

print("🚀 開始使用多執行緒 Apple Vision 神經網路引擎進行【極嚴格 (閾值 0.48)】比對...")

let fileManager = FileManager.default
guard let enumerator = fileManager.enumerator(at: photosDirURL, includingPropertiesForKeys: nil) else {
    exit(1)
}

var allPhotoURLs: [URL] = []
let validExts = Set(["jpeg", "jpg"])

while let fileURL = enumerator.nextObject() as? URL {
    if validExts.contains(fileURL.pathExtension.lowercased()) {
        allPhotoURLs.append(fileURL)
    }
}

print("📁 收集到 \(allPhotoURLs.count) 張相片，啟動極高精度神經網絡計算...")

let lock = NSLock()
var matchedPhotos: [String] = []

// 多執行緒並行計算 (嚴格門檻 0.48)
DispatchQueue.concurrentPerform(iterations: allPhotoURLs.count) { index in
    let fileURL = allPhotoURLs[index]
    guard let ciImg = CIImage(contentsOf: fileURL) else { return }
    
    let imgFaceReq = VNDetectFaceRectanglesRequest()
    let imgHandler = VNImageRequestHandler(ciImage: ciImg, options: [:])
    try? imgHandler.perform([imgFaceReq])
    
    if let faces = imgFaceReq.results, !faces.isEmpty {
        let imgSize = ciImg.extent.size
        for face in faces {
            let bbox = face.boundingBox
            let cropRect = CGRect(x: bbox.origin.x * imgSize.width,
                                  y: bbox.origin.y * imgSize.height,
                                  width: bbox.size.width * imgSize.width,
                                  height: bbox.size.height * imgSize.height)
            let croppedFace = ciImg.cropped(to: cropRect)
            
            let printReq = VNGenerateImageFeaturePrintRequest()
            let faceHandler = VNImageRequestHandler(ciImage: croppedFace, options: [:])
            try? faceHandler.perform([printReq])
            
            if let currentPrint = printReq.results?.first as? VNFeaturePrintObservation {
                for baseOb in baseFacePrints {
                    var distance: Float = 1.0
                    try? currentPrint.computeDistance(&distance, to: baseOb)
                    
                    // 極嚴格比對門檻: 距離 < 0.48 排除其他類似女性相片
                    if distance < 0.48 {
                        let relPath = fileURL.path.replacingOccurrences(of: baseDir.path + "/", with: "")
                        lock.lock()
                        matchedPhotos.append(relPath)
                        print("✨ 確鑿精準匹配太太照片 (距離: \(String(format: "%.3f", distance))): \(fileURL.lastPathComponent)")
                        lock.unlock()
                        break
                    }
                }
            }
        }
    }
}

print("🎉 極嚴格比對完成！共掃描 \(allPhotoURLs.count) 張照片，精確辨識出 \(matchedPhotos.count) 張太太 [太太Sharon] 的確鑿相片！")

let resultURL = baseDir.appendingPathComponent("sharon_matched.json")
if let jsonData = try? JSONEncoder().encode(matchedPhotos) {
    try? jsonData.write(to: resultURL)
    print("💾 精準結果已寫入: sharon_matched.json")
}
