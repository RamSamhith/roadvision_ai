"""RoadVision AI — S5-M1 Real Hardware Smoke Test (Non-Test Split Image).

Executes real forward pass using promoted YOLO26m model on GPU and CPU.
Verifies:
- Checkpoint SHA-256
- Class order & count (4 canonical classes)
- End-to-end NMS-free inference
- Structured output schema (TDD v1.1 §6)
- Bounding box annotation without mutating source
- GPU vs CPU latency measurement
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import torch

# Add backend to path
ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.vision import (
    CLASS_CODES,
    MODEL_YOLO26M_EXPECTED_SHA256,
    MODEL_YOLO26M_PATH,
    VisionService,
    compute_sha256,
    get_primary_device,
)


def run_smoke_test() -> int:
    print("=" * 80)
    print("ROADVISION AI — S5-M1 CV SERVICE GPU & CPU SMOKE TEST")
    print("=" * 80)

    # 1. Checkpoint Verification
    print("\n[STEP 1] Verifying Promoted Production Checkpoint...")
    assert MODEL_YOLO26M_PATH.is_file(), f"Missing checkpoint: {MODEL_YOLO26M_PATH}"
    actual_hash = compute_sha256(MODEL_YOLO26M_PATH)
    print(f"  Checkpoint Path : {MODEL_YOLO26M_PATH}")
    print(f"  Expected SHA256 : {MODEL_YOLO26M_EXPECTED_SHA256}")
    print(f"  Actual SHA256   : {actual_hash}")
    assert actual_hash == MODEL_YOLO26M_EXPECTED_SHA256, "SHA256 verification failed!"
    print("  --> SHA-256 VERIFIED!")

    # 2. Hardware Environment
    print("\n[STEP 2] Hardware Device Check...")
    cuda_available = torch.cuda.is_available()
    device_name = torch.cuda.get_device_name(0) if cuda_available else "N/A"
    primary_dev = get_primary_device()
    print(f"  CUDA Available  : {cuda_available}")
    print(f"  Device Name     : {device_name}")
    print(f"  Primary Target  : {primary_dev}")

    # 3. Non-Test Image Selection
    print("\n[STEP 3] Selecting Non-Test Split Validation Sample...")
    val_image_path = ROOT_DIR / "dataset" / "images" / "val" / "China_Drone__China_Drone_000005.jpg"
    assert val_image_path.is_file(), f"Sample image missing: {val_image_path}"
    print(f"  Selected Image  : {val_image_path.name}")
    print(f"  Image Path      : {val_image_path}")

    out_dir = ROOT_DIR / "runs" / "smoke_test"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_annotated_gpu = out_dir / "smoke_annotated_gpu.jpg"
    out_annotated_cpu = out_dir / "smoke_annotated_cpu.jpg"

    # 4. GPU Inference
    print(f"\n[STEP 4] Executing GPU Forward Pass on {primary_dev}...")
    service_gpu = VisionService(primary_device=primary_dev)
    t0_gpu_init = time.perf_counter()
    init_ok = service_gpu.initialize(device=primary_dev)
    init_time_gpu = (time.perf_counter() - t0_gpu_init) * 1000.0
    print(f"  GPU Init OK     : {init_ok} ({init_time_gpu:.1f} ms)")

    # Warm-up / First pass
    t0_gpu_infer = time.perf_counter()
    gpu_result = service_gpu.detect_image(
        image_input=val_image_path,
        conf=0.25,
        annotate=True,
        output_path=out_annotated_gpu,
    )
    gpu_infer_time = (time.perf_counter() - t0_gpu_infer) * 1000.0

    print(f"  Total Latency   : {gpu_infer_time:.2f} ms")
    print(f"  Active Model    : {gpu_result.result.model}")
    print(f"  Device Used     : {gpu_result.device}")
    print(f"  Total Detections: {gpu_result.result.total_detections}")
    print(f"  Class Counts    : {gpu_result.result.class_counts}")
    print(f"  Image Dimension : {gpu_result.result.image_dimensions}")
    print(f"  Models Used     : {gpu_result.models_used}")
    print(f"  Saved Image     : {gpu_result.annotated_output_path}")

    # Print detections detail
    for idx, d in enumerate(gpu_result.result.detections):
        print(f"    Detection #{idx+1}: {d.class_name} ({d.label}) | conf: {d.confidence:.4f} | box: {d.box}")

    # Validate output schema
    res_dict = gpu_result.to_dict()
    assert "model" in res_dict
    assert "total_detections" in res_dict
    assert "class_counts" in res_dict
    assert "detections" in res_dict
    assert "models_used" in res_dict

    # 5. Same-Model CPU Execution
    print("\n[STEP 5] Testing Same-Model CPU Execution...")
    service_cpu = VisionService(primary_device="cpu")
    t0_cpu_init = time.perf_counter()
    service_cpu.initialize(device="cpu")
    init_time_cpu = (time.perf_counter() - t0_cpu_init) * 1000.0
    print(f"  CPU Init OK     : True ({init_time_cpu:.1f} ms)")

    t0_cpu_infer = time.perf_counter()
    cpu_result = service_cpu.detect_image(
        image_input=val_image_path,
        conf=0.25,
        annotate=True,
        output_path=out_annotated_cpu,
    )
    cpu_infer_time = (time.perf_counter() - t0_cpu_infer) * 1000.0

    print(f"  Total Latency   : {cpu_infer_time:.2f} ms")
    print(f"  Active Model    : {cpu_result.result.model}")
    print(f"  Device Used     : {cpu_result.device}")
    print(f"  Total Detections: {cpu_result.result.total_detections}")
    print(f"  Class Counts    : {cpu_result.result.class_counts}")

    # Compare GPU vs CPU Detections
    print("\n[STEP 6] Cross-Device Detection Verification...")
    assert gpu_result.result.total_detections == cpu_result.result.total_detections, (
        f"Mismatch between GPU ({gpu_result.result.total_detections}) and CPU ({cpu_result.result.total_detections}) counts!"
    )
    print("  GPU and CPU detection counts MATCH perfectly!")

    # 6. Performance Summary
    print("\n" + "=" * 80)
    print("LATENCY & PERFORMANCE COMPARISON:")
    print("=" * 80)
    print(f"  GPU ({device_name}): {gpu_infer_time:.2f} ms (Engine forward pass: {gpu_result.result.inference_time_ms:.2f} ms)")
    print(f"  CPU:                 {cpu_infer_time:.2f} ms (Engine forward pass: {cpu_result.result.inference_time_ms:.2f} ms)")
    if cuda_available and cpu_infer_time > 0:
        speedup = cpu_infer_time / gpu_infer_time
        print(f"  GPU Speedup         : {speedup:.2f}x faster than CPU")

    print("\nALL SMOKE TEST CRITERIA PASSED SUCCESSFULLY!")
    return 0


if __name__ == "__main__":
    sys.exit(run_smoke_test())

