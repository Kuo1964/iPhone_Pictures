import Foundation
import Vision
import CoreImage
import CoreGraphics

// 原生 macOS 專業人臉辨識引擎 (face_recognizer_v2.swift)
let baseDir = URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
let photosDirURL = baseDir.appendingPathComponent("Photos")

// 搜尋全庫中所有可能屬於女兒郭泊彤的照片或由使用者設定的樣本
let targetPaths = [
    "Photos/2013/2013-12_未知地點/65101648-FC7D-4910-9933-CDEB1BC6185F.jpeg"
]

var baseFacePrints: [VNFeaturePrintObservation] = []

print("📸 正在解析基準照片人臉特徵點...")
for relPath in targetPaths {
    let imgURL = baseDir.appendingPathComponent(relPath)
    guard let ciImg = CIImage(contentsOf: imgURL) else { continue }
    
    // 檢測人臉矩形並剪裁人臉
    let faceReq = VNDetectFaceRectanglesRequest()
    let handler = VNImageRequestHandler(ciImage: ciImg, options: [:])
    try? handler.perform([faceReq])
    
    guard let faceObs = faceReq.results?.first else {
        // 若未檢測出單獨人臉矩形，使用全圖 print
        let printReq = VNGenerateImageFeaturePrintRequest()
        try? handler.perform([printReq])
        if let ob = printReq.results?.first as? VNFeaturePrintObservation {
            baseFacePrints.append(ob)
        }
        continue
    }
    
    // 依據人臉 Bounding Box 剪裁人臉區域
    let bbox = faceObs.boundingBox
    let imgSize = ciImg.extent.size
    let cropRect = CGRect(x: bbox.origin.x * imgSize.width,
                          y: bbox.origin.y * imgSize.height,
                          width: bbox.size.width * imgSize.width,
                          height: bbox.size.height * imgSize.height)
    
    let faceCIImg = ciImg.cropped(to: cropRect)
    let faceHandler = VNImageRequestHandler(ciImage: faceCIImg, options: [:])
    let facePrintReq = VNGenerateImageFeaturePrintRequest()
    try? faceHandler.perform([facePrintReq])
    
    if let ob = facePrintReq.results?.first as? VNFeaturePrintObservation {
        baseFacePrints.append(ob)
        print("  └─ 成功擷取人臉特徵向量！")
    }
}

print("🚀 開始使用 Apple Vision 人臉辨識引擎全庫比對 4,800+ 張照片...")

let fileManager = FileManager.default
guard let enumerator = fileManager.enumerator(at: photosDirURL, includingPropertiesForKeys: nil) else {
    exit(1)
}

var matchedPhotos: Set<String> = []
var scannedCount = 0

while let fileURL = enumerator.nextObject() as? URL {
    let ext = fileURL.pathExtension.lowercased()
    if ext == "jpeg" || ext == "jpg" {
        scannedCount += 1
        
        guard let ciImg = CIImage(contentsOf: fileURL) else { continue }
        
        // 人臉檢測
        let faceReq = VNDetectFaceRectanglesRequest()
        let imgHandler = VNImageRequestHandler(ciImage: ciImg, options: [:])
        try? imgHandler.perform([faceReq])
        
        if let faces = faceReq.results, !faces.isEmpty {
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
                        
                        // 人臉區域比對距離閾值 (人臉剪裁後 0.65 即可高度匹配同一人)
                        if distance < 0.65 {
                            let relPath = fileURL.path.replacingOccurrences(of: baseDir.path + "/", with: "")
                            matchedPhotos.insert(relPath)
                            print("✨ 辨識成功女兒照片 (距離: \(String(format: "%.3f", distance))): \(fileURL.lastPathComponent)")
                            break
                        }
                    }
                }
            }
        }
        
        if scannedCount % 500 == 0 {
            print("⏳ 已完成人臉辨識 \(scannedCount) / 4878 張相片...")
        }
    }
}

print("🎉 辨識完全成功！共發現 \(matchedPhotos.count) 張女兒 [郭泊彤Sophia] 的相片。")

// 更新 photos_db.json 標籤
let matchedArray = Array(matchedPhotos)
let resultURL = baseDir.appendingPathComponent("sophia_matched.json")
if let jsonData = try? JSONEncoder().encode(matchedArray) {
    try? jsonData.write(to: resultURL)
}
