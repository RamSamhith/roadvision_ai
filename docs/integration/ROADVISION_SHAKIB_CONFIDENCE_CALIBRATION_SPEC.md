# RoadVision AI — Shakib Integration Specification: Calibrated Confidence Modes & Metadata Propagation

- **Author:** Ram Samhith (Senior Computer Vision Engineer)
- **Recipient:** Shakib (Application Backend & Frontend Lead)
- **Authority:** TDD v1.1 §6, §7, §8, §10; PRD v1.1 §4; `ROADVISION_CONFIDENCE_CALIBRATION_REPORT.md`
- **CV Implementation Status:** Implemented, verified, 101/101 automated tests passing.
- **Date:** 8 November 2026

---

## 1. Executive Summary

Empirical diagnostic evaluation on China_Drone road scenes has demonstrated that road damage detection performance is strongly dependent on the operational context:
- **Balanced Mode (`conf = 0.25`, Default):** Delivers peak F1 score (0.833–0.848), maximum precision (84.8%–88.0%), and minimizes false alarms (curb shadows, oil stains, pavement joints). Pothole (`D40`) detection is exceptionally reliable (94.0% precision, 90.7% recall).
- **High-Recall Mode (`conf = 0.15`, Optional):** Increases overall damage detection recall to **87.3%** (recovering faint, hairline, and distant cracks that score below 0.25, such as the `D10` sample at 0.1819 and `D00` sample at 0.1475). The operational trade-off is an increase in candidate detections and background false alarms (precision drops from 88.0% to 78.2%).

To provide a smooth, professional user experience without overwhelming inspectors with false positives, the application should provide a simple UI toggle between these two calibrated modes, while allowing power users to specify custom numeric values between `0.10` and `0.90`.

---

## 2. Calibrated Confidence Modes & Thresholds

| Mode Name | Float Value | UI Display Label | Recommended Use Case | Expected Trade-off |
| :--- | :---: | :--- | :--- | :--- |
| **`balanced`** (Default) | `0.25` | **Balanced (25%)** | Routine municipal road audits, production video monitoring | Peak accuracy, minimal false alarms; may miss faint hairline cracks |
| **`high_recall`** | `0.15` | **High Sensitivity / High Recall (15%)** | Critical road screening, safety-critical asset audits | Catches faint, low-contrast cracks; user must expect ~20% more false candidates |
| **Custom** | `[0.10, 0.90]` | **Custom Slider** | Advanced inspection engineers | User-defined precision/recall trade-off |

---

## 3. API Contract & Validation Rules

### 3.1 Parameter Specification
Both `POST /api/v1/detect/image` and `POST /api/v1/detect/video` must accept:
- **Field Name:** `confidence` (query parameter or multipart form field).
- **Accepted Types:**
  - `float`: Any numeric value in `[0.10, 0.90]` (e.g., `0.25`, `0.15`, `0.30`).
  - `string`: Predefined mode string (`"balanced"` or `"high_recall"`), or numeric string (`"0.25"`).
- **Default Value:** `0.25` (or `"balanced"`).
- **HTTP 422 Error Handling:** If the user supplies an out-of-range value (`< 0.10` or `> 0.90`) or invalid mode string, return `HTTP 422 Unprocessable Entity` with a clear message:
  ```json
  {
    "detail": [
      {
        "loc": ["query", "confidence"],
        "msg": "Confidence threshold must be between 0.10 and 0.90, or one of ['balanced', 'high_recall'].",
        "type": "value_error"
      }
    ]
  }
  ```

### 3.2 FastAPI Implementation Example
Shakib should implement parameter parsing using `app.config.validate_confidence`:

```python
from fastapi import APIRouter, UploadFile, File, Query, HTTPException, Depends
from starlette.concurrency import run_in_threadpool
from app.config import validate_confidence, DEFAULT_CONFIDENCE
from app.services.vision.service import VisionService

router = APIRouter(prefix="/api/v1")

@router.post("/detect/image")
async def detect_image(
    file: UploadFile = File(...),
    confidence: str = Query(
        default="balanced",
        description="Confidence threshold [0.10, 0.90] or mode ('balanced', 'high_recall')"
    ),
    service: VisionService = Depends(get_vision_service)
):
    try:
        resolved_conf = validate_confidence(confidence)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    contents = await file.read()
    inspection = await run_in_threadpool(
        service.detect_image,
        image_input=contents,
        conf=resolved_conf,
        filename=file.filename
    )
    return inspection.to_dict()
```

---

## 4. Metadata Reporting & Persistence

Both image detection results and recorded video job summaries now explicitly record the effective confidence threshold in their payload:

### 4.1 Image Inspection Result Schema (`VisionInspectionResult.to_dict()`)
```json
{
  "model": "YOLO26m",
  "total_detections": 3,
  "class_counts": {"D00": 1, "D10": 2, "D20": 0, "D40": 0},
  "class_summary": {"D00": 1, "D10": 2, "D20": 0, "D40": 0},
  "conf_threshold": 0.25,
  "inference_time_ms": 14.82,
  "image_dimensions": [512, 512],
  "models_used": ["YOLO26m"],
  "device": "cuda:0",
  "success": true,
  "detections": [
    {
      "class_id": 1,
      "class_name": "D10",
      "label": "Transverse crack",
      "confidence": 0.5802,
      "box": [0.0, 70.6, 204.3, 101.4]
    }
  ]
}
```

### 4.2 SQLite Database Column Recommendation
In the SQLite database table (`inspections` and `video_jobs`), Shakib should store the effective threshold:
```sql
ALTER TABLE inspections ADD COLUMN conf_threshold REAL DEFAULT 0.25;
ALTER TABLE video_jobs ADD COLUMN conf_threshold REAL DEFAULT 0.25;
```

---

## 5. React Frontend User Experience Guidelines

### 5.1 Mode Selector Component
In the dashboard upload modal and video processing settings, provide a clear segmented control or radio group:

```tsx
import React, { useState } from 'react';

export const ConfidenceSelector: React.FC<{
  value: string;
  onChange: (mode: string) => void;
}> = ({ value, onChange }) => {
  return (
    <div className="flex flex-col space-y-2">
      <label className="text-sm font-semibold text-gray-700">Detection Sensitivity</label>
      <div className="grid grid-cols-2 gap-3">
        <button
          type="button"
          onClick={() => onChange("balanced")}
          className={`p-3 text-left border rounded-lg transition-colors ${
            value === "balanced"
              ? "border-blue-600 bg-blue-50 text-blue-900"
              : "border-gray-200 hover:bg-gray-50 text-gray-700"
          }`}
        >
          <div className="font-medium text-sm">Balanced (25%)</div>
          <div className="text-xs text-gray-500 mt-1">Recommended for standard audits. Minimal false alarms.</div>
        </button>

        <button
          type="button"
          onClick={() => onChange("high_recall")}
          className={`p-3 text-left border rounded-lg transition-colors ${
            value === "high_recall"
              ? "border-blue-600 bg-blue-50 text-blue-900"
              : "border-gray-200 hover:bg-gray-50 text-gray-700"
          }`}
        >
          <div className="font-medium text-sm">High Recall (15%)</div>
          <div className="text-xs text-gray-500 mt-1">Detects faint/hairline cracks. May include more false candidates.</div>
        </button>
      </div>
      {value === "high_recall" && (
        <div className="text-xs text-amber-600 flex items-center space-x-1 mt-1">
          <span>⚠️ High Recall mode prioritizes finding all defects; review candidates carefully.</span>
        </div>
      )}
    </div>
  );
};
```

---

## 6. Integration Checklist for Shakib

1. [ ] Import `validate_confidence` from `app.config`.
2. [ ] Support both string modes (`"balanced"`, `"high_recall"`) and floats (`0.10` to `0.90`) in endpoint schemas.
3. [ ] Return `HTTP 422` on validation failure.
4. [ ] Pass resolved confidence float to `service.detect_image(..., conf=resolved_conf)` and `service.detect_video(..., conf=resolved_conf)`.
5. [ ] Store `conf_threshold` in SQLite table rows for every inspection and job.
6. [ ] Render the sensitivity toggle in the React UI with clear warning text for High Recall mode.

