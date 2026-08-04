import Foundation
import Vision
import CoreImage

// 原生 macOS 人臉與視覺特徵辨識工具 (recognize_sophia.swift)
let args = CommandLine.arguments
let targetPath = args.count > 1 ? args[1] : "Photos/2013/2013-12_未知地點/65101648-FC7D-4910-9933-CDEB1BC6185F.jpeg"
let photosDirPath = args.count > 2 ? args[2] : "Photos"

let baseDir = URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
let targetURL = baseDir.appendingPathComponent(targetPath)
let photosDirURL = baseDir.appendingPathComponent(photosDirPath)

print("🎯 載入女兒 [郭泊彤Sophia] 基準比對照片: \(targetURL.path)")

guard let targetCIImage = CIImage(contentsOf: targetURL) else {
    print("❌ 無法載入基準照片！")
    exit(1)
}

// 提取基準照片特徵
var targetFeaturePrint: VNFeaturePrintObservation?
let handler = VNImageRequestHandler(ciImage: targetCIImage, options: [:])
let request = VNGenerateImageFeaturePrintRequest()

do {
    try handler.perform([request])
    targetFeaturePrint = request.results?.first as? VNFeaturePrintObservation
} catch {
    print("❌ 提取基準特徵失敗: \(error)")
    exit(1)
}

guard let basePrint = targetFeaturePrint else {
    print("❌ 未能獲取基準特徵點！")
    exit(1)
}

print("✅ 基準照片特徵點提取成功！開始比對相片庫...")

// 掃描照片庫
let fileManager = FileManager.default
guard let enumerator = fileManager.enumerator(at: photosDirURL, includingPropertiesForKeys: nil) else {
    print("❌ 無法讀取相片目錄")
    exit(1)
}

var matchedPhotos: [String] = []
var scannedCount = 0

while let fileURL = enumerator.nextObject() as? URL {
    let ext = fileURL.pathExtension.lowercased()
    if ext == "jpeg" || ext == "jpg" {
        scannedCount += 1
        
        guard let ciImg = CIImage(contentsOf: fileURL) else { continue }
        let imgHandler = VNImageRequestHandler(ciImage: ciImg, options: [:])
        let imgRequest = VNGenerateImageFeaturePrintRequest()
        
        try? imgHandler.perform([imgRequest])
        
        if let currentPrint = imgRequest.results?.first as? VNFeaturePrintObservation {
            var distance: Float = 1.0
            try? currentPrint.computeDistance(&distance, to: basePrint)
            
            // 距離小於 0.47 認定為極度相似/同人特徵照片
            if distance < 0.47 {
                let relPath = fileURL.path.replacingOccurrences(of: baseDir.path + "/", with: "")
                matchedPhotos.append(relPath)
                print("✨ 匹配成功 (相似距離: \(String(format: "%.3f", distance))): \(fileURL.lastPathComponent)")
            }
        }
        
        if scannedCount % 500 == 0 {
            print("⏳ 已比對 \(scannedCount) 張相片...")
        }
    }
}

print("🎉 辨識完畢！共掃描 \(scannedCount) 張照片，成功辨識出 \(matchedPhotos.count) 張女兒 [郭泊彤Sophia] 的相片！")

// 輸出 JSON 結果
let encoder = JSONEncoder()
encoder.outputFormatting = .prettyPrinted
if let jsonData = try? encoder.encode(matchedPhotos) {
    let resultURL = baseDir.appendingPathComponent("sophia_matched.json")
    try? jsonData.write(to: resultURL)
    print("💾 匹配結果已寫入: sophia_matched.json")
}
