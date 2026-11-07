"""
Main Training Run for RoadVision AI: YOLO26m 50 Cumulative Epochs (S4-T5).
Continues from Stage B pilot checkpoint (runs/train/yolo26m_s4_t4_pilot/weights/last.pt),
which completed 12 cumulative epochs (2 in Stage A + 10 in Stage B).
Trains for 38 additional epochs to reach exactly 50 cumulative epochs.
Captures GPU telemetry, validation metrics, per-class metrics, and saves results to runs/s4_t5_summary.json.
"""
import csv
import json
import os
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from training.monitor import HardwareMonitor
from ultralytics import YOLO

def run_main_training():
    print("=" * 80)
    print("ROADVISION AI — S4-T5: MAIN YOLO26m TRAINING (50 CUMULATIVE EPOCHS)")
    print("=" * 80)

    dataset_dir = ROOT_DIR / "dataset"
    data_yaml = dataset_dir / "data.yaml"
    runs_dir = ROOT_DIR / "runs" / "train"
    source_ckpt = runs_dir / "yolo26m_s4_t4_pilot" / "weights" / "last.pt"
    exp_name = "yolo26m_s4_t5_main_50ep"
    exp_dir = runs_dir / exp_name

    assert data_yaml.is_file(), f"data.yaml not found at {data_yaml}"
    assert source_ckpt.is_file(), f"Source checkpoint not found at {source_ckpt}"
    assert not exp_dir.exists(), f"Target experiment directory already exists at {exp_dir}"

    mon_log = runs_dir / "s4_t5_hw_monitor.csv"
    monitor = HardwareMonitor(str(mon_log), interval=2.0)

    os.chdir(str(dataset_dir))
    print(f"[INFO] Working directory set to: {os.getcwd()}")
    print(f"[INFO] Initializing model from S4-T4 pilot checkpoint: {source_ckpt}")
    print(f"[INFO] Data config: {data_yaml}")
    print(f"[INFO] Target run dir: {exp_dir}")
    print("[INFO] Additional epochs to train: 38 (Cumulative total: 12 + 38 = 50 epochs)")

    monitor.start()
    start_time = time.time()
    success = False
    error_msg = None
    train_results = None
    val_results_dict = {}
    class_metrics = {}
    speed_metrics = {}

    try:
        model = YOLO(str(source_ckpt))
        print("[INFO] Checkpoint successfully loaded. Commencing 38-epoch training run...")

        train_results = model.train(
            data="data.yaml",
            epochs=38,
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
            save_period=5,
        )
        print("[SUCCESS] 38 additional epochs completed successfully!")

        best_ckpt = exp_dir / "weights" / "best.pt"
        last_ckpt = exp_dir / "weights" / "last.pt"
        assert best_ckpt.is_file(), f"best.pt not found at {best_ckpt}"
        assert last_ckpt.is_file(), f"last.pt not found at {last_ckpt}"

        print("\n" + "=" * 80)
        print("[INFO] Running comprehensive post-training validation on validation split...")
        print("=" * 80)

        best_model = YOLO(str(best_ckpt))
        val_metrics = best_model.val(
            data="data.yaml",
            batch=8,
            imgsz=640,
            device=0,
            split="val",
            plots=True,
            save_json=False,
        )

        val_results_dict = val_metrics.results_dict
        speed_metrics = val_metrics.speed

        class_names = {0: "D00", 1: "D10", 2: "D20", 3: "D40"}
        class_desc = {
            "D00": "Longitudinal Crack",
            "D10": "Transverse Crack",
            "D20": "Alligator Crack",
            "D40": "Pothole",
        }

        # Extract per-class metrics
        for cid, cname in class_names.items():
            try:
                c_res = val_metrics.box.class_result(cid)
                class_metrics[cname] = {
                    "class_id": cid,
                    "description": class_desc[cname],
                    "precision": float(c_res[0]),
                    "recall": float(c_res[1]),
                    "mAP50": float(c_res[2]),
                    "mAP50-95": float(c_res[3]),
                }
            except Exception as e:
                print(f"[WARN] Failed to extract per-class metric for {cname}: {e}")

        success = True
    except Exception as e:
        error_msg = str(e)
        print(f"[ERROR] Main training failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        end_time = time.time()
        monitor.stop()
        os.chdir(str(ROOT_DIR))

    elapsed = end_time - start_time
    hw_summary = monitor.get_summary()

    # Parse results.csv if available
    epoch_results = []
    results_csv_path = exp_dir / "results.csv"
    if results_csv_path.is_file():
        try:
            with open(results_csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    cleaned_row = {k.strip(): float(v.strip()) if v.strip() else None for k, v in row.items()}
                    epoch_results.append(cleaned_row)
        except Exception as e:
            print(f"[WARN] Failed to parse results.csv: {e}")

    summary_data = {
        "task": "S4-T5 Main YOLO26m Training (50 Cumulative Epochs)",
        "success": success,
        "error": error_msg,
        "start_time": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(start_time)),
        "end_time": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(end_time)),
        "elapsed_seconds": elapsed,
        "elapsed_hours": elapsed / 3600.0,
        "source_checkpoint": str(source_ckpt),
        "previous_cumulative_epochs": 12,
        "additional_epochs_trained": 38,
        "final_cumulative_epochs": 50,
        "configuration": {
            "model": "YOLO26m",
            "imgsz": 640,
            "batch_size": 8,
            "device": 0,
            "workers": 2,
            "amp": True,
            "seed": 0,
            "save_period": 5,
        },
        "hw_summary": hw_summary,
        "final_validation_metrics": val_results_dict,
        "per_class_metrics": class_metrics,
        "speed_latencies_ms": speed_metrics,
        "epoch_results_count": len(epoch_results),
        "best_checkpoint": str(exp_dir / "weights" / "best.pt") if success else None,
        "last_checkpoint": str(exp_dir / "weights" / "last.pt") if success else None,
        "exp_dir": str(exp_dir),
    }

    summary_file = ROOT_DIR / "runs" / "s4_t5_summary.json"
    summary_file.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)

    print("\n" + "=" * 80)
    print("S4-T5 MAIN TRAINING RUN COMPLETE:")
    print(f"Success: {success}")
    print(f"Total Elapsed Time: {elapsed:.2f} s ({elapsed/3600:.2f} hours)")
    print(f"Peak VRAM: {hw_summary.get('peak_vram_mb', 0):.1f} MB")
    print(f"Average GPU Utilization: {hw_summary.get('avg_gpu_util_pct', 0):.1f} %")
    print(f"Peak GPU Temperature: {hw_summary.get('peak_temp_c', 0):.1f} °C")
    if success:
        print(f"Final Validation mAP50: {val_results_dict.get('metrics/mAP50(B)', 'N/A')}")
        print(f"Final Validation mAP50-95: {val_results_dict.get('metrics/mAP50-95(B)', 'N/A')}")
        print(f"Best Checkpoint: {summary_data['best_checkpoint']}")
    print("=" * 80)

    if not success:
        sys.exit(1)

if __name__ == "__main__":
    run_main_training()

