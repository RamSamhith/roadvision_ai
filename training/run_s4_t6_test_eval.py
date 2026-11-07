"""
S4-T6: Final Held-Out Test Evaluation of YOLO26m (50 Cumulative Epochs).
Evaluates the best checkpoint from S4-T5 (runs/train/yolo26m_s4_t5_main_50ep/weights/best.pt)
on the untouched RDD2022 test split (2,349 images, 5,424 ground-truth instances).
Preserves all test outputs under runs/val/yolo26m_s4_t6_test_eval/.
"""
import hashlib
import json
import os
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from ultralytics import YOLO

def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def run_test_evaluation():
    print("=" * 80)
    print("ROADVISION AI — S4-T6: FINAL HELD-OUT TEST EVALUATION (YOLO26m 50-EPOCH MODEL)")
    print("=" * 80)

    dataset_dir = ROOT_DIR / "dataset"
    data_yaml = dataset_dir / "data.yaml"
    ckpt_path = ROOT_DIR / "runs" / "train" / "yolo26m_s4_t5_main_50ep" / "weights" / "best.pt"
    runs_val_dir = ROOT_DIR / "runs" / "val"
    exp_name = "yolo26m_s4_t6_test_eval"
    exp_dir = runs_val_dir / exp_name

    assert data_yaml.is_file(), f"data.yaml not found at {data_yaml}"
    assert ckpt_path.is_file(), f"Checkpoint not found at {ckpt_path}"
    assert not exp_dir.exists(), f"Target evaluation directory already exists at {exp_dir}"

    ckpt_sha256 = compute_sha256(ckpt_path)
    print(f"[INFO] Evaluating checkpoint: {ckpt_path}")
    print(f"[INFO] Checkpoint SHA-256: {ckpt_sha256}")
    print(f"[INFO] Dataset config: {data_yaml}")
    print(f"[INFO] Evaluation output directory: {exp_dir}")

    # Set working directory to dataset to resolve data.yaml relative paths correctly
    os.chdir(str(dataset_dir))
    print(f"[INFO] Working directory set to: {os.getcwd()}")

    start_time = time.time()
    success = False
    error_msg = None
    results_summary = {}

    try:
        model = YOLO(str(ckpt_path))
        print("[INFO] Model loaded successfully. Commencing validation on 'test' split...")

        metrics = model.val(
            data="data.yaml",
            split="test",
            batch=8,
            imgsz=640,
            device=0,
            plots=True,
            save_json=False,
            project=str(runs_val_dir),
            name=exp_name,
            exist_ok=False,
            verbose=True,
        )

        end_time = time.time()
        elapsed = end_time - start_time
        print(f"[SUCCESS] Test evaluation completed in {elapsed:.2f} seconds.")

        class_names = {0: "D00", 1: "D10", 2: "D20", 3: "D40"}
        class_desc = {
            "D00": "Longitudinal Crack",
            "D10": "Transverse Crack",
            "D20": "Alligator Crack",
            "D40": "Pothole",
        }
        gt_counts = {"D00": 2575, "D10": 1165, "D20": 1047, "D40": 637}

        per_class_results = {}
        for cid, cname in class_names.items():
            c_res = metrics.box.class_result(cid)
            per_class_results[cname] = {
                "class_id": cid,
                "description": class_desc[cname],
                "ground_truth_instances": gt_counts[cname],
                "precision": float(c_res[0]),
                "recall": float(c_res[1]),
                "mAP50": float(c_res[2]),
                "mAP50-95": float(c_res[3]),
            }

        # Confusion matrix
        cm_matrix = metrics.confusion_matrix.matrix.tolist() if metrics.confusion_matrix else None

        results_summary = {
            "task": "S4-T6 Final Held-Out Test Evaluation",
            "model_path": str(ckpt_path),
            "model_sha256": ckpt_sha256,
            "dataset_split": "test",
            "test_images_count": 2349,
            "test_instances_total": 5424,
            "evaluation_duration_seconds": elapsed,
            "configuration": {
                "imgsz": 640,
                "batch_size": 8,
                "device": 0,
                "split": "test",
            },
            "overall_metrics": {
                "precision": float(metrics.box.mp),
                "recall": float(metrics.box.mr),
                "mAP50": float(metrics.box.map50),
                "mAP50-95": float(metrics.box.map),
            },
            "per_class_metrics": per_class_results,
            "speed_ms": metrics.speed,
            "confusion_matrix": cm_matrix,
            "confusion_matrix_labels": ["D00", "D10", "D20", "D40", "background"],
            "output_directory": str(exp_dir),
        }

        success = True
    except Exception as e:
        end_time = time.time()
        elapsed = end_time - start_time
        error_msg = str(e)
        print(f"[ERROR] Test evaluation failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        os.chdir(str(ROOT_DIR))

    summary_file = ROOT_DIR / "runs" / "s4_t6_test_summary.json"
    summary_file.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(results_summary, f, indent=2)

    print("\n" + "=" * 80)
    print("S4-T6 TEST EVALUATION SUMMARY:")
    print(f"Success: {success}")
    print(f"Elapsed: {elapsed:.2f} s")
    if success:
        ov = results_summary["overall_metrics"]
        print(f"Test Precision: {ov['precision']:.4f}")
        print(f"Test Recall:    {ov['recall']:.4f}")
        print(f"Test mAP50:     {ov['mAP50']:.4f}")
        print(f"Test mAP50-95:  {ov['mAP50-95']:.4f}")
        print("\nPer-Class Results:")
        for cname, cdata in results_summary["per_class_metrics"].items():
            print(f"  {cname} ({cdata['description']}): P={cdata['precision']:.3f}, R={cdata['recall']:.3f}, mAP50={cdata['mAP50']:.3f}, mAP50-95={cdata['mAP50-95']:.3f} (GT={cdata['ground_truth_instances']})")
        print("\nSpeed Latencies (ms/image):")
        for k, v in results_summary["speed_ms"].items():
            print(f"  {k}: {v:.2f} ms")
    print("=" * 80)

    if not success:
        sys.exit(1)

if __name__ == "__main__":
    run_test_evaluation()

