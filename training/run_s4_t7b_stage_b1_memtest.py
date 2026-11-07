"""
Stage B1: 832px Resolution Memory Test for YOLO26m on RoadVision AI.
Tests 2 epochs of training at 832x832 resolution with batch size 4, AMP enabled, 2 workers,
starting from S4-T5 best.pt checkpoint.
Monitors VRAM, GPU temperature, and confirms peak VRAM stays below 7.2 GB (7,372 MB) safety limit.
"""
import json
import os
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from training.monitor import HardwareMonitor
from ultralytics import YOLO

def run_stage_b1_memtest():
    print("=" * 80)
    print("ROADVISION AI — S4-T7B STAGE B1: 832px RESOLUTION MEMORY TEST")
    print("=" * 80)

    dataset_dir = ROOT_DIR / "dataset"
    data_yaml = dataset_dir / "data.yaml"
    runs_dir = ROOT_DIR / "runs" / "train"
    source_ckpt = runs_dir / "yolo26m_s4_t5_main_50ep" / "weights" / "best.pt"
    exp_name = "yolo26m_s4_t7b_mem832"
    exp_dir = runs_dir / exp_name

    assert data_yaml.is_file(), f"data.yaml not found at {data_yaml}"
    assert source_ckpt.is_file(), f"Source checkpoint not found at {source_ckpt}"
    assert not exp_dir.exists(), f"Target run directory already exists at {exp_dir}"

    mon_log = runs_dir / "s4_t7b_mem_hw_monitor.csv"
    monitor = HardwareMonitor(str(mon_log), interval=1.0)

    os.chdir(str(dataset_dir))
    print(f"[INFO] Working directory set to: {os.getcwd()}")
    print(f"[INFO] Starting weights: {source_ckpt}")
    print(f"[INFO] Resolution: 832x832 | Batch size: 4 | Epochs: 2 | AMP: True")
    print(f"[INFO] VRAM Safety Threshold: 7,200 MB (7.03 GB)")

    monitor.start()
    start_time = time.time()
    success = False
    error_msg = None
    vram_passed = False

    try:
        model = YOLO(str(source_ckpt))
        print("[INFO] Model loaded successfully. Commencing 2-epoch memory test...")

        results = model.train(
            data="data.yaml",
            epochs=2,
            batch=4,
            imgsz=832,
            device=0,
            workers=2,
            amp=True,
            seed=0,
            project=str(runs_dir),
            name=exp_name,
            exist_ok=False,
            verbose=True,
            plots=True,
            save=True,
        )
        success = True
        print("[SUCCESS] Stage B1 memory test completed without CUDA/OOM errors!")
    except Exception as e:
        error_msg = str(e)
        print(f"[ERROR] Stage B1 memory test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        end_time = time.time()
        monitor.stop()
        os.chdir(str(ROOT_DIR))

    elapsed = end_time - start_time
    hw_summary = monitor.get_summary()
    peak_vram = hw_summary.get("peak_vram_mb", 0.0)

    # Safety check: peak VRAM <= 7,200 MB
    if success and peak_vram <= 7200.0:
        vram_passed = True
    elif success:
        print(f"[WARNING] Run completed but peak VRAM {peak_vram:.1f} MB exceeded 7,200 MB safety threshold!")

    summary_data = {
        "stage": "S4-T7B Stage B1 Memory Test",
        "resolution": 832,
        "batch_size": 4,
        "epochs": 2,
        "success": success,
        "vram_safety_passed": vram_passed,
        "vram_threshold_mb": 7200.0,
        "peak_vram_mb": peak_vram,
        "avg_vram_mb": hw_summary.get("avg_vram_mb", 0.0),
        "peak_temp_c": hw_summary.get("peak_temp_c", 0.0),
        "avg_gpu_util_pct": hw_summary.get("avg_gpu_util_pct", 0.0),
        "elapsed_seconds": elapsed,
        "error": error_msg,
        "checkpoint_evaluated": str(source_ckpt),
        "exp_dir": str(exp_dir),
    }

    out_file = ROOT_DIR / "runs" / "s4_t7b_memtest_summary.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)

    print("\n" + "=" * 80)
    print("STAGE B1 MEMORY TEST SUMMARY:")
    print(f"Success: {success}")
    print(f"VRAM Safety Gate Passed: {vram_passed} (Peak: {peak_vram:.1f} MB / Limit: 7,200.0 MB)")
    print(f"Elapsed: {elapsed:.2f} s ({elapsed/60:.2f} min)")
    print(f"Avg GPU Util: {hw_summary.get('avg_gpu_util_pct', 0.0):.1f} %")
    print(f"Peak GPU Temp: {hw_summary.get('peak_temp_c', 0.0):.1f} °C")
    print("=" * 80)

    if not success or not vram_passed:
        sys.exit(1)

if __name__ == "__main__":
    run_stage_b1_memtest()

