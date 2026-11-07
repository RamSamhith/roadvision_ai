"""
Resume S4-T7B Stage B2 Fine-Tuning and Run Stage B3 Validation.
Resumes from runs/train/yolo26m_s4_t7b_832_finetune/weights/last.pt (epoch 11/20 completed).
Executes remaining 9 epochs (epochs 12 through 20) with full optimizer state intact.
Performs Stage B3 validation on validation split and saves runs/s4_t7b_832_summary.json.
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

def resume_finetuning():
    print("=" * 80)
    print("ROADVISION AI — S4-T7B: RESUMING 832px FINE-TUNING (EPOCHS 12–20)")
    print("=" * 80)

    dataset_dir = ROOT_DIR / "dataset"
    data_yaml = dataset_dir / "data.yaml"
    runs_dir = ROOT_DIR / "runs" / "train"
    exp_name = "yolo26m_s4_t7b_832_finetune"
    exp_dir = runs_dir / exp_name
    last_ckpt = exp_dir / "weights" / "last.pt"

    assert data_yaml.is_file(), f"data.yaml not found at {data_yaml}"
    assert last_ckpt.is_file(), f"last.pt not found at {last_ckpt}"

    mon_log = runs_dir / "s4_t7b_hw_monitor.csv"
    monitor = HardwareMonitor(str(mon_log), interval=2.0)

    os.chdir(str(dataset_dir))
    print(f"[INFO] Working directory set to: {os.getcwd()}")
    print(f"[INFO] Resuming from checkpoint: {last_ckpt}")

    monitor.start()
    start_time = time.time()
    success = False
    error_msg = None
    val_results = {}
    class_metrics = {}
    speed_metrics = {}

    try:
        model = YOLO(str(last_ckpt))
        print("[INFO] Checkpoint loaded with optimizer state. Resuming training...")

        train_results = model.train(resume=True)
        print("[SUCCESS] Training resumed and completed all 20 epochs!")

        best_ckpt = exp_dir / "weights" / "best.pt"
        assert best_ckpt.is_file(), f"best.pt not found at {best_ckpt}"

        print("\n" + "=" * 80)
        print("[STAGE B3] Running validation evaluation on validation split at 832px...")
        print("=" * 80)

        best_model = YOLO(str(best_ckpt))
        val_metrics = best_model.val(
            data="data.yaml",
            batch=4,
            imgsz=832,
            device=0,
            split="val",
            plots=True,
            save_json=False,
        )

        val_results = val_metrics.results_dict
        speed_metrics = val_metrics.speed

        class_names = {0: "D00", 1: "D10", 2: "D20", 3: "D40"}
        class_desc = {
            "D00": "Longitudinal Crack",
            "D10": "Transverse Crack",
            "D20": "Alligator Crack",
            "D40": "Pothole",
        }

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
        print(f"[ERROR] Resumed fine-tuning failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        end_time = time.time()
        monitor.stop()
        os.chdir(str(ROOT_DIR))

    elapsed = end_time - start_time
    hw_summary = monitor.get_summary()

    # Parse full results.csv
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
        "task": "S4-T7B 832px Resolution Fine-Tuning and Evaluation",
        "resumed_from_interruption": True,
        "interruption_reason": "System Modern Standby / Sleep suspended PyTorch IPC worker on Windows during epoch 12",
        "epochs_prior_to_resume": 11,
        "total_target_epochs": 20,
        "success": success,
        "error": error_msg,
        "elapsed_seconds": elapsed,
        "target_resolution": 832,
        "batch_size": 4,
        "hw_summary": hw_summary,
        "final_validation_metrics": val_results,
        "per_class_metrics": class_metrics,
        "speed_latencies_ms": speed_metrics,
        "epoch_results_count": len(epoch_results),
        "best_checkpoint": str(exp_dir / "weights" / "best.pt") if success else None,
        "last_checkpoint": str(exp_dir / "weights" / "last.pt") if success else None,
        "exp_dir": str(exp_dir),
    }

    out_file = ROOT_DIR / "runs" / "s4_t7b_832_summary.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)

    print("\n" + "=" * 80)
    print("S4-T7B SUMMARY (RESUMED RUN):")
    print(f"Success: {success}")
    print(f"Elapsed: {elapsed:.2f} s ({elapsed/3600:.2f} hours)")
    print(f"Peak VRAM: {hw_summary.get('peak_vram_mb', 0.0):.1f} MB")
    print(f"Avg GPU Util: {hw_summary.get('avg_gpu_util_pct', 0.0):.1f} %")
    if success:
        print(f"Validation mAP50: {val_results.get('metrics/mAP50(B)', 'N/A')}")
        print(f"Validation mAP50-95: {val_results.get('metrics/mAP50-95(B)', 'N/A')}")
    print("=" * 80)

    if not success:
        sys.exit(1)

if __name__ == "__main__":
    resume_finetuning()

