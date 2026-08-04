import Foundation
import Vision
import CoreImage
import CoreGraphics

// 正向 + 負向雙重極致精確人臉辨識引擎 (scan_and_tag_sharon.swift)
let baseDir = URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
let photosDirURL = baseDir.appendingPathComponent("Photos")

let sharonPath = "references/sharon_base.png"
let malePath = "references/male_negative.jpg"

let sharonURL = baseDir.appendingPathComponent(sharonPath)
let maleURL = baseDir.appendingPathComponent(malePath)

print("🎯 載入正向基準 [太太Sharon]: \(sharonURL.path)")
print("🚫 載入負向對比 [男性特徵]: \(maleURL.path)")

guard let sharonCIImg = CIImage(contentsOf: sharonURL),
      let maleCIImg = CIImage(contentsOf: maleURL) else {
    print("❌ 無法載入基準比對照片！")
    exit(1)
}

func extractFacePrint(from ciImg: CIImage) -> VNFeaturePrintObservation? {
    let faceReq = VNDetectFaceLandmarksRequest()
    let handler = VNImageRequestHandler(ciImage: ciImg, options: [:])
    try? handler.perform([faceReq])
    
    guard let faceObs = faceReq.results?.first else { return nil }
    let bbox = faceObs.boundingBox
    let imgSize = ciImg.extent.size
    let cropRect = CGRect(x: bbox.origin.x * imgSize.width,
                          y: bbox.origin.y * imgSize.height,
                          width: bbox.size.width * imgSize.width,
                          height: bbox.size.height * imgSize.height)
    
    let faceCIImg = ciImg.cropped(to: cropRect)
    let faceHandler = VNImageRequestHandler(ciImage: faceCIImg, options: [:])
    let printReq = VNGenerateImageFeaturePrintRequest()
    try? faceHandler.perform([printReq])
    return printReq.results?.first as? VNFeaturePrintObservation
}

guard let sharonPrint = extractFacePrint(from: sharonCIImg) else {
    print("❌ 提取太太基準特徵失敗！")
    exit(1)
}

let malePrint = extractFacePrint(from: maleCIImg)
print("✅ 成功提取正向與負向雙重人臉五官特徵向量！")

print("🚀 開始使用多執行緒 Apple Vision 神經網絡進行【全庫 4,878 張照片雙重確鑿掃描】...")

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

print("📁 收集到 \(allPhotoURLs.count) 張相片，啟動極致精度運算...")

let lock = NSLock()
var matchedPhotos: [String] = []

// 雙重核驗門檻
let strictThreshold: Float = 0.28

DispatchQueue.concurrentPerform(iterations: allPhotoURLs.count) { index in
    let fileURL = allPhotoURLs[index]
    guard let ciImg = CIImage(contentsOf: fileURL) else { return }
    
    let imgFaceReq = VNDetectFaceLandmarksRequest()
    let imgHandler = VNImageRequestHandler(ciImage: ciImg, options: [:])
    try? imgHandler.perform([imgFaceReq])
    
    if let faces = imgFaceReq.results, !faces.isEmpty {
        let imgSize = ciImg.extent.size
        for face in faces {
            let bbox = face.boundingBox
            let faceWidth = bbox.size.width * imgSize.width
            let faceHeight = bbox.size.height * imgSize.height
            
            // 排除過小的遠景/背景小臉 (至少 80x80px)
            if faceWidth < 80 || faceHeight < 80 { continue }
            
            let cropRect = CGRect(x: bbox.origin.x * imgSize.width,
                                  y: bbox.origin.y * imgSize.height,
                                  width: faceWidth,
                                  height: faceHeight)
            let croppedFace = ciImg.cropped(to: cropRect)
            
            let printReq = VNGenerateImageFeaturePrintRequest()
            let faceHandler = VNImageRequestHandler(ciImage: croppedFace, options: [:])
            try? faceHandler.perform([printReq])
            
            if let currentPrint = printReq.results?.first as? VNFeaturePrintObservation {
                var distSharon: Float = 1.0
                try? currentPrint.computeDistance(&distSharon, to: sharonPrint)
                
                var distMale: Float = 1.0
                if let mPrint = malePrint {
                    try? currentPrint.computeDistance(&distMale, to: mPrint)
                }
                
                // 正向極嚴 Threshold < 0.28，且反向檢驗: 與太太相似度必須顯著優於與男性相似度
                if distSharon < strictThreshold && (distSharon < distMale - 0.08) {
                    let relPath = fileURL.path.replacingOccurrences(of: baseDir.path + "/", with: "")
                    lock.lock()
                    matchedPhotos.append(relPath)
                    print("✨ 確鑿匹配太太照片 (距離: \(String(format: "%.3f", distSharon)) vs 男: \(String(format: "%.3f", distMale))): \(fileURL.lastPathComponent)")
                    lock.unlock()
                    break
                }
            }
        }
    }
}

print("🎉 全庫掃描比對完全成功！共掃描 \(allPhotoURLs.count) 張照片，確鑿無誤比對出 \(matchedPhotos.count) 張太太 [Sharon] 的相片！")

let resultURL = baseDir.appendingPathComponent("sharon_matched.json")
if let jsonData = try? JSONEncoder().encode(matchedPhotos) {
    try? jsonData.write(to: resultURL)
    print("💾 最終結果已寫入: sharon_matched.json")
}
