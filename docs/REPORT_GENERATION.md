# RoadVision — Report Generation & Data Export

RoadVision includes automated inspection reporting and audit data export capabilities.

---

## 1. Automated PDF Reports

Inspection sessions (images, videos, and live webcam streams) can be converted into standalone PDF documents.

### Key Content in Generated Reports:
- **Header**: RoadVision title, Inspection Session ID, creation timestamp, dynamic page count (`Page X of Y`).
- **Session Metadata**: Input type, source filename, execution status, detection model used (`YOLO26m`), confidence threshold, total defects, processing latency.
- **Classification Table**:
  - `D00`: Longitudinal Crack (Surface Crack)
  - `D10`: Transverse Crack (Surface Crack)
  - `D20`: Alligator Crack (Surface Crack)
  - `D40`: Pothole (Structural Defect)
- **Visual Evidence**: Automatically embeds high-resolution annotated damage images with proportional aspect scaling.
- **Footer**: Confidentiality notice and legal verification metadata.

### API Endpoint:
```http
GET /api/reports/inspection/{inspection_id}/pdf
```
Returns `application/pdf` with header `Content-Disposition: attachment; filename="roadvision_report_inspection_{id}.pdf"`.

---

## 2. Tabular CSV Exports

Inspection history can be exported in bulk for compliance audits and infrastructure tracking.

### Exported Columns:
1. `Inspection ID`
2. `Created At`
3. `Finished At`
4. `Input Type` (`image`, `video`, `webcam`)
5. `Filename`
6. `Model Used`
7. `Confidence Threshold`
8. `Status` (`completed`, `failed`, `cancelled`)
9. `Total Detections`
10. `D00 (Longitudinal Crack)`
11. `D10 (Transverse Crack)`
12. `D20 (Alligator Crack)`
13. `D40 (Pothole)`
14. `Frames Total`
15. `Frames Processed`
16. `Processing Time (ms)`
17. `Output File`

### API Endpoint:
```http
GET /api/reports/export/csv?limit=1000&offset=0
```
Returns `text/csv` conforming to RFC 4180.

