"""
Stage A: 2-Epoch GPU Memory Test for YOLO26m on RoadVision AI.
Runs YOLO26m for 2 epochs on the prepared RDD2022 dataset with batch=8, imgsz=640, device=0, workers=2, amp=True, seed=0.
Monitors VRAM, GPU utilization, temperature, epoch timings, and loss progression.
"""
import json
import os
import sys
import time
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from training.monitor import HardwareMonitor
from ultralytics import YOLO

def run_stage_a():
    print("=" * 80)
    print("RoadVision AI — S4-T4 Stage A: 2-Epoch GPU Memory Test (YOLO26m)")
    print("=" * 80)

    dataset_dir = ROOT_DIR / "dataset"
    data_yaml = dataset_dir / "data.yaml"
    runs_dir = ROOT_DIR / "runs" / "train"
    exp_name = "yolo26m_s4_t4_memory"
    exp_dir = runs_dir / exp_name
    model_weights = ROOT_DIR / "yolo26m.pt"

    assert data_yaml.is_file(), f"data.yaml not found at {data_yaml}"
    assert model_weights.is_file(), f"Pretrained weights not found at {model_weights}"

    mon_log = ROOT_DIR / "runs" / "train" / "stage_a_hw_monitor.csv"
    monitor = HardwareMonitor(str(mon_log), interval=1.0)

    # Change working directory to dataset directory for Ultralytics path resolution convention
    os.chdir(str(dataset_dir))
    print(f"[INFO] Working directory set to: {os.getcwd()}")
    print(f"[INFO] Model weights: {model_weights}")
    print(f"[INFO] Data config: {data_yaml}")
    print(f"[INFO] Target run dir: {exp_dir}")

    monitor.start()
    start_time = time.time()
    success = False
    error_msg = None

    try:
        model = YOLO(str(model_weights))
        print("[INFO] Model loaded successfully. Starting 2-epoch training...")
        
        results = model.train(
            data="data.yaml",
            epochs=2,
            batch=8,
            imgsz=640,
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
        print("[SUCCESS] Stage A training completed successfully!")
    except Exception as e:
        error_msg = str(e)
        print(f"[ERROR] Stage A failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        end_time = time.time()
        monitor.stop()
        os.chdir(str(ROOT_DIR))

    elapsed = end_time - start_time
    hw_summary = monitor.get_summary()

    stage_a_meta = {
        "success": success,
        "error": error_msg,
        "elapsed_seconds": elapsed,
        "batch_size": 8,
        "imgsz": 640,
        "epochs": 2,
        "workers": 2,
        "device": 0,
        "amp": True,
        "hw_summary": hw_summary,
        "exp_dir": str(exp_dir),
    }

    meta_file = ROOT_DIR / "runs" / "stage_a_summary.json"
    meta_file.parent.mkdir(parents=True, exist_ok=True)
    with open(meta_file, "w") as f:
        json.dump(stage_a_meta, f, indent=2)

    print("\n" + "=" * 80)
    print("STAGE A RUN SUMMARY:")
    print(f"Success: {success}")
    print(f"Elapsed: {elapsed:.2f} s")
    print(f"Peak VRAM: {hw_summary.get('peak_vram_mb', 0):.1f} MB")
    print(f"Avg GPU Util: {hw_summary.get('avg_gpu_util_pct', 0):.1f} %")
    print(f"Peak GPU Temp: {hw_summary.get('peak_temp_c', 0):.1f} °C")
    print("=" * 80)

    if not success:
        sys.exit(1)

if __name__ == "__main__":
    run_stage_a()

