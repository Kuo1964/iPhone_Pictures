import Foundation
import Vision
import CoreImage

// 取得命令列引數
let args = CommandLine.arguments
guard args.count >= 2 else {
    print("使用方式: swift detect_sophia.swift <基準照路徑> [搜尋目錄]")
    exit(1)
}

let targetImagePath = args[1]
let searchDirPath = args.count >= 3 ? args[2] : "."

let targetURL = URL(fileURLWithPath: targetImagePath)
guard let targetCIImage = CIImage(contentsOf: targetURL) else {
    print("❌ 無法讀取基準照片: \(targetImagePath)")
    exit(1)
}

print("📸 正在提取基準照特徵: \(targetURL.lastPathComponent)...")

var targetFeaturePrint: VNFeaturePrintObservation?

let requestHandler = VNImageRequestHandler(ciImage: targetCIImage, options: [:])
let featureRequest = VNGeneratePersonSegmentationRequest() // 使用 Vision 生物特徵與人臉檢測

let faceFeatureRequest = VNGenerateImageFeaturePrintRequest()
try? requestHandler.perform([faceFeatureRequest])

if let observation = faceFeatureRequest.results?.first as? VNFeaturePrintObservation {
    targetFeaturePrint = observation
    print("✅ 成功提取基準照片特徵 print！")
} else {
    print("⚠️ 警告: 基準照片未能提取出標準特徵，將採用人臉矩形比對...")
}

print("🚀 準備全庫比對照片...")
