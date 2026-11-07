"""
Stage B: 10-Epoch Training Pilot for YOLO26m on RoadVision AI.
Continues training from Stage A's last checkpoint (runs/train/yolo26m_s4_t4_memory/weights/last.pt)
to reach a cumulative total of 12 epochs (2 from Stage A + 10 additional in Stage B).
Monitors VRAM, GPU utilization, temperature, epoch timings, and comprehensive validation metrics.
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

def run_stage_b():
    print("=" * 80)
    print("RoadVision AI — S4-T4 Stage B: 10-Epoch Training Pilot (YOLO26m)")
    print("=" * 80)

    dataset_dir = ROOT_DIR / "dataset"
    data_yaml = dataset_dir / "data.yaml"
    runs_dir = ROOT_DIR / "runs" / "train"
    stage_a_ckpt = runs_dir / "yolo26m_s4_t4_memory" / "weights" / "last.pt"
    
    exp_name = "yolo26m_s4_t4_pilot"
    exp_dir = runs_dir / exp_name

    assert data_yaml.is_file(), f"data.yaml not found at {data_yaml}"
    assert stage_a_ckpt.is_file(), f"Stage A checkpoint not found at {stage_a_ckpt}"

    mon_log = ROOT_DIR / "runs" / "train" / "stage_b_hw_monitor.csv"
    monitor = HardwareMonitor(str(mon_log), interval=1.0)

    os.chdir(str(dataset_dir))
    print(f"[INFO] Working directory set to: {os.getcwd()}")
    print(f"[INFO] Initializing model from Stage A checkpoint: {stage_a_ckpt}")
    print(f"[INFO] Data config: {data_yaml}")
    print(f"[INFO] Target run dir: {exp_dir}")

    monitor.start()
    start_time = time.time()
    success = False
    error_msg = None

    try:
        # Load weights from Stage A checkpoint
        model = YOLO(str(stage_a_ckpt))
        print("[INFO] Model checkpoint loaded. Starting 10-epoch training pilot...")
        
        # In Ultralytics, when fine-tuning/continuing from a checkpoint under a new run name,
        # we train for epochs=10 starting from stage_a_ckpt weights.
        results = model.train(
            data="data.yaml",
            epochs=10,
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
        print("[SUCCESS] Stage B pilot training completed successfully!")
    except Exception as e:
        error_msg = str(e)
        print(f"[ERROR] Stage B failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        end_time = time.time()
        monitor.stop()
        os.chdir(str(ROOT_DIR))

    elapsed = end_time - start_time
    hw_summary = monitor.get_summary()

    stage_b_meta = {
        "success": success,
        "error": error_msg,
        "elapsed_seconds": elapsed,
        "batch_size": 8,
        "imgsz": 640,
        "epochs": 10,
        "stage_a_epochs": 2,
        "total_epochs": 12,
        "workers": 2,
        "device": 0,
        "amp": True,
        "hw_summary": hw_summary,
        "source_checkpoint": str(stage_a_ckpt),
        "exp_dir": str(exp_dir),
    }

    meta_file = ROOT_DIR / "runs" / "stage_b_summary.json"
    meta_file.parent.mkdir(parents=True, exist_ok=True)
    with open(meta_file, "w") as f:
        json.dump(stage_b_meta, f, indent=2)

    print("\n" + "=" * 80)
    print("STAGE B RUN SUMMARY:")
    print(f"Success: {success}")
    print(f"Elapsed: {elapsed:.2f} s ({elapsed/60:.2f} min)")
    print(f"Peak VRAM: {hw_summary.get('peak_vram_mb', 0):.1f} MB")
    print(f"Avg GPU Util: {hw_summary.get('avg_gpu_util_pct', 0):.1f} %")
    print(f"Peak GPU Temp: {hw_summary.get('peak_temp_c', 0):.1f} °C")
    print("=" * 80)

    if not success:
        sys.exit(1)

if __name__ == "__main__":
    run_stage_b()

