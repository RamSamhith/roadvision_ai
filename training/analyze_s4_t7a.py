"""
S4-T7A Master Analysis Script:
Dataset structure analysis, annotation quality inspection, validation error analysis,
and confidence threshold optimization for YOLO26m on RoadVision AI.
Strictly respects the test-set lock: operates ONLY on train and val splits.
"""
import json
import math
import os
import shutil
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import cv2
import numpy as np
import torch
from ultralytics import YOLO

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

CLASSES = {0: "D00", 1: "D10", 2: "D20", 3: "D40"}
CLASS_DESCRIPTIONS = {
    "D00": "Longitudinal Crack",
    "D10": "Transverse Crack",
    "D20": "Alligator Crack",
    "D40": "Pothole",
}

def box_iou(box1, box2):
    # box format: [x1, y1, x2, y2]
    xA = max(box1[0], box2[0])
    yA = max(box1[1], box2[1])
    xB = min(box1[2], box2[2])
    yB = min(box1[3], box2[3])
    inter = max(0, xB - xA) * max(0, yB - yA)
    area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
    union = area1 + area2 - inter
    return inter / union if union > 0 else 0.0

def xywh_to_xyxy(x, y, w, h):
    return [x - w / 2, y - h / 2, x + w / 2, y + h / 2]

def quantiles_dict(arr):
    if not arr:
        return {}
    a = np.array(arr)
    return {
        "min": float(np.min(a)),
        "p10": float(np.percentile(a, 10)),
        "p25": float(np.percentile(a, 25)),
        "median": float(np.median(a)),
        "p75": float(np.percentile(a, 75)),
        "p90": float(np.percentile(a, 90)),
        "p99": float(np.percentile(a, 99)),
        "max": float(np.max(a)),
        "mean": float(np.mean(a)),
        "std": float(np.std(a)),
    }

def analyze_dataset_structure():
    print("[TASK A] Analyzing dataset structure across train and val splits...")
    splits_data = {}
    
    for split in ["train", "val"]:
        img_dir = ROOT_DIR / "dataset" / "images" / split
        lbl_dir = ROOT_DIR / "dataset" / "labels" / split
        
        img_files = sorted(list(img_dir.glob("*.jpg")))
        total_images = len(img_files)
        
        class_instances = Counter()
        images_per_class = defaultdict(set)
        
        all_widths = []
        all_heights = []
        all_areas_norm = []
        all_aspect_ratios = [] # w / h
        
        per_class_widths = defaultdict(list)
        per_class_heights = defaultdict(list)
        per_class_areas = defaultdict(list)
        per_class_aspects = defaultdict(list)
        
        # Scale buckets (COCO definitions at 640x640: small < 1024 px^2, medium 1024-9216, large > 9216)
        # In normalized area: small < 0.0025, medium 0.0025-0.0225, large > 0.0225
        scale_counts = {"small": 0, "medium": 0, "large": 0}
        per_class_scales = defaultdict(lambda: {"small": 0, "medium": 0, "large": 0})
        
        image_class_counts = defaultdict(set)
        image_instance_counts = Counter()
        per_image_same_class_multi = defaultdict(lambda: Counter())
        
        for img_path in img_files:
            img_id = img_path.stem
            lbl_path = lbl_dir / f"{img_id}.txt"
            
            boxes_in_img = []
            if lbl_path.is_file():
                with open(lbl_path, "r", encoding="utf-8") as f:
                    for line in f:
                        parts = line.strip().split()
                        if len(parts) >= 5:
                            cid = int(parts[0])
                            x, y, w, h = map(float, parts[1:5])
                            boxes_in_img.append((cid, x, y, w, h))
            
            num_boxes = len(boxes_in_img)
            image_instance_counts[img_id] = num_boxes
            
            classes_in_this_img = set()
            for cid, x, y, w, h in boxes_in_img:
                cname = CLASSES[cid]
                class_instances[cname] += 1
                images_per_class[cname].add(img_id)
                classes_in_this_img.add(cname)
                per_image_same_class_multi[img_id][cname] += 1
                
                area = w * h
                aspect = w / h if h > 0 else 0.0
                
                all_widths.append(w)
                all_heights.append(h)
                all_areas_norm.append(area)
                all_aspect_ratios.append(aspect)
                
                per_class_widths[cname].append(w)
                per_class_heights[cname].append(h)
                per_class_areas[cname].append(area)
                per_class_aspects[cname].append(aspect)
                
                if area < 0.0025:
                    scale = "small"
                elif area <= 0.0225:
                    scale = "medium"
                else:
                    scale = "large"
                scale_counts[scale] += 1
                per_class_scales[cname][scale] += 1
                
            image_class_counts[img_id] = classes_in_this_img
            
        total_instances = sum(class_instances.values())
        
        # Co-occurrence matrix
        pair_counts = Counter()
        class_count_dist = Counter()
        for img_id, cset in image_class_counts.items():
            class_count_dist[len(cset)] += 1
            clist = sorted(list(cset))
            for i in range(len(clist)):
                for j in range(i + 1, len(clist)):
                    pair_counts[f"{clist[i]}+{clist[j]}"] += 1
                    
        # Multi-instance of same class
        multi_same_class = Counter()
        for img_id, ccounts in per_image_same_class_multi.items():
            for cname, cnt in ccounts.items():
                if cnt > 1:
                    multi_same_class[cname] += 1
                    
        # Density distribution
        density_bins = {
            "1_box": 0,
            "2_to_5_boxes": 0,
            "6_to_10_boxes": 0,
            "11_to_15_boxes": 0,
            "gt_15_boxes": 0,
        }
        for cnt in image_instance_counts.values():
            if cnt == 1:
                density_bins["1_box"] += 1
            elif 2 <= cnt <= 5:
                density_bins["2_to_5_boxes"] += 1
            elif 6 <= cnt <= 10:
                density_bins["6_to_10_boxes"] += 1
            elif 11 <= cnt <= 15:
                density_bins["11_to_15_boxes"] += 1
            else:
                density_bins["gt_15_boxes"] += 1

        splits_data[split] = {
            "total_images": total_images,
            "total_instances": total_instances,
            "instances_per_class": dict(class_instances),
            "class_shares_pct": {c: round(class_instances[c] / total_instances * 100, 2) for c in CLASSES.values()},
            "images_containing_class": {c: len(images_per_class[c]) for c in CLASSES.values()},
            "image_presence_pct": {c: round(len(images_per_class[c]) / total_images * 100, 2) for c in CLASSES.values()},
            "bbox_geometry": {
                "overall_width": quantiles_dict(all_widths),
                "overall_height": quantiles_dict(all_heights),
                "overall_area_normalized": quantiles_dict(all_areas_norm),
                "overall_aspect_ratio": quantiles_dict(all_aspect_ratios),
                "pixel_area_at_640": {k: v * (640 * 640) for k, v in quantiles_dict(all_areas_norm).items()},
            },
            "per_class_geometry": {
                c: {
                    "width": quantiles_dict(per_class_widths[c]),
                    "height": quantiles_dict(per_class_heights[c]),
                    "area_normalized": quantiles_dict(per_class_areas[c]),
                    "aspect_ratio": quantiles_dict(per_class_aspects[c]),
                }
                for c in CLASSES.values()
            },
            "scale_distribution": {
                "overall": {
                    "counts": scale_counts,
                    "percentages": {k: round(v / total_instances * 100, 2) for k, v in scale_counts.items()},
                },
                "per_class": {
                    c: {
                        "counts": per_class_scales[c],
                        "percentages": {
                            k: round(per_class_scales[c][k] / class_instances[c] * 100, 2)
                            for k in ["small", "medium", "large"]
                        },
                    }
                    for c in CLASSES.values()
                },
            },
            "multi_class_images": {
                "class_diversity_counts": dict(class_count_dist),
                "class_diversity_pct": {k: round(v / total_images * 100, 2) for k, v in class_count_dist.items()},
                "top_co_occurring_pairs": dict(pair_counts.most_common(10)),
            },
            "multi_instance_same_class_images": {
                c: {
                    "count": multi_same_class[c],
                    "pct_of_images_with_class": round(multi_same_class[c] / len(images_per_class[c]) * 100, 2),
                }
                for c in CLASSES.values()
            },
            "density_distribution": {
                "counts": density_bins,
                "percentages": {k: round(v / total_images * 100, 2) for k, v in density_bins.items()},
            },
        }

    return splits_data

def inspect_annotation_quality():
    print("[TASK B] Inspecting annotation quality across train and val splits...")
    anomalies = []
    
    for split in ["train", "val"]:
        lbl_dir = ROOT_DIR / "dataset" / "labels" / split
        img_dir = ROOT_DIR / "dataset" / "images" / split
        
        for lbl_path in lbl_dir.glob("*.txt"):
            img_id = lbl_path.stem
            boxes = []
            with open(lbl_path, "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 5:
                        boxes.append((int(parts[0]), float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])))
            
            # Check 1: Extremely tiny boxes (area < 0.00025, < 100 px^2 at 640)
            for i, (cid, x, y, w, h) in enumerate(boxes):
                area = w * h
                cname = CLASSES[cid]
                if area < 0.0003: # < 120 px^2
                    anomalies.append({
                        "image_id": img_id,
                        "split": split,
                        "class": cname,
                        "issue_type": "extremely_small_box",
                        "bbox_norm": [x, y, w, h],
                        "details": f"Area = {area:.6f} (~{area*640*640:.1f} px^2 at 640x640, w={w*640:.1f}px, h={h*640:.1f}px)",
                        "confidence": "confirmed",
                    })
                if area > 0.65:
                    anomalies.append({
                        "image_id": img_id,
                        "split": split,
                        "class": cname,
                        "issue_type": "giant_loose_box",
                        "bbox_norm": [x, y, w, h],
                        "details": f"Covers {area*100:.1f}% of image frame",
                        "confidence": "confirmed",
                    })
                if h > 0 and (w / h > 25.0 or w / h < 0.04):
                    anomalies.append({
                        "image_id": img_id,
                        "split": split,
                        "class": cname,
                        "issue_type": "extreme_aspect_ratio",
                        "bbox_norm": [x, y, w, h],
                        "details": f"Aspect ratio w/h = {w/h:.2f}",
                        "confidence": "confirmed",
                    })

            # Check 2: High overlap between boxes of same class or different classes
            n = len(boxes)
            for i in range(n):
                b1 = xywh_to_xyxy(boxes[i][1], boxes[i][2], boxes[i][3], boxes[i][4])
                for j in range(i + 1, n):
                    b2 = xywh_to_xyxy(boxes[j][1], boxes[j][2], boxes[j][3], boxes[j][4])
                    iou = box_iou(b1, b2)
                    if iou > 0.80 and boxes[i][0] == boxes[j][0]:
                        anomalies.append({
                            "image_id": img_id,
                            "split": split,
                            "class": CLASSES[boxes[i][0]],
                            "issue_type": "near_duplicate_box",
                            "bbox_norm": [boxes[i][1], boxes[i][2], boxes[i][3], boxes[i][4]],
                            "details": f"IoU = {iou:.3f} with box {j} of same class",
                            "confidence": "confirmed",
                        })
                    elif iou > 0.50 and boxes[i][0] != boxes[j][0]:
                        anomalies.append({
                            "image_id": img_id,
                            "split": split,
                            "class": f"{CLASSES[boxes[i][0]]} vs {CLASSES[boxes[j][0]]}",
                            "issue_type": "overlapping_different_classes",
                            "bbox_norm": [boxes[i][1], boxes[i][2], boxes[i][3], boxes[i][4]],
                            "details": f"IoU = {iou:.3f} between conflicting classes",
                            "confidence": "suspected_ambiguity",
                        })
                        
    # Group anomalies by issue type
    anomalies_by_type = defaultdict(list)
    for a in anomalies:
        anomalies_by_type[a["issue_type"]].append(a)
        
    summary = {
        "total_anomalies_flagged": len(anomalies),
        "anomalies_by_type_counts": {k: len(v) for k, v in anomalies_by_type.items()},
        "representative_curated_examples": [
            # Curate 8-10 distinct compelling examples across types
        ]
    }
    
    # Pick top distinct examples
    seen_images = set()
    curated = []
    for itype in ["extremely_small_box", "giant_loose_box", "extreme_aspect_ratio", "near_duplicate_box", "overlapping_different_classes"]:
        sample_list = anomalies_by_type[itype]
        for s in sample_list[:3]:
            if s["image_id"] not in seen_images and len(curated) < 10:
                seen_images.add(s["image_id"])
                curated.append(s)
    summary["representative_curated_examples"] = curated
    return summary

def run_validation_error_analysis_and_thresholding():
    print("[TASK C & G] Running validation error analysis and threshold sweep with YOLO26m best.pt...")
    
    ckpt_path = ROOT_DIR / "runs" / "train" / "yolo26m_s4_t5_main_50ep" / "weights" / "best.pt"
    assert ckpt_path.is_file(), f"Model checkpoint not found at {ckpt_path}"
    
    model = YOLO(str(ckpt_path))
    val_img_dir = ROOT_DIR / "dataset" / "images" / "val"
    val_lbl_dir = ROOT_DIR / "dataset" / "labels" / "val"
    
    val_images = sorted(list(val_img_dir.glob("*.jpg")))
    print(f"[INFO] Evaluating {len(val_images)} validation images for error taxonomy...")
    
    # Threshold sweep: evaluate confidence thresholds 0.10 to 0.70 in 0.05 increments
    thresholds = [round(t, 2) for t in np.arange(0.10, 0.75, 0.05)]
    threshold_metrics = {
        t: {
            "overall": {"tp": 0, "fp": 0, "fn": 0},
            "per_class": {c: {"tp": 0, "fp": 0, "fn": 0} for c in CLASSES.values()},
        }
        for t in thresholds
    }
    
    # Error taxonomy at standard conf = 0.25, iou = 0.50
    EVAL_CONF = 0.25
    EVAL_IOU = 0.50
    
    error_cases = {
        "false_positives": [],
        "false_negatives": [],
        "class_confusion": [],
        "missed_small_objects": [],
    }
    
    confusion_counts = defaultdict(lambda: defaultdict(int)) # true_class -> pred_class -> count
    fp_by_background_type = Counter()
    
    total_gt_count = Counter()
    
    # Run batch prediction or sequential prediction on val set
    # Using model.predict on val images directly
    batch_size = 16
    n_images = len(val_images)
    
    for start_idx in range(0, n_images, batch_size):
        batch_paths = val_images[start_idx : start_idx + batch_size]
        results = model.predict(
            source=[str(p) for p in batch_paths],
            conf=0.10, # low conf to enable sweep
            iou=0.50,
            imgsz=640,
            device=0,
            verbose=False,
            save=False,
        )
        
        for p, res in zip(batch_paths, results):
            img_id = p.stem
            lbl_file = val_lbl_dir / f"{img_id}.txt"
            
            # Load ground truth
            gt_boxes = []
            if lbl_file.is_file():
                with open(lbl_file, "r", encoding="utf-8") as f:
                    for line in f:
                        parts = line.strip().split()
                        if len(parts) >= 5:
                            cid = int(parts[0])
                            x, y, w, h = map(float, parts[1:5])
                            gt_boxes.append({
                                "cid": cid,
                                "cname": CLASSES[cid],
                                "xywh": [x, y, w, h],
                                "xyxy": xywh_to_xyxy(x, y, w, h),
                                "area": w * h,
                                "matched": False,
                            })
            
            for gt in gt_boxes:
                total_gt_count[gt["cname"]] += 1
                
            # Extract predictions
            pred_boxes = []
            if res.boxes is not None and len(res.boxes) > 0:
                xyxy_preds = res.boxes.xyxy.cpu().numpy()
                # Normalize xyxy to 0-1
                img_h, img_w = res.orig_shape
                confs = res.boxes.conf.cpu().numpy()
                clss = res.boxes.cls.cpu().numpy()
                
                for i in range(len(confs)):
                    box_norm = [
                        xyxy_preds[i][0] / img_w,
                        xyxy_preds[i][1] / img_h,
                        xyxy_preds[i][2] / img_w,
                        xyxy_preds[i][3] / img_h,
                    ]
                    cid = int(clss[i])
                    pred_boxes.append({
                        "cid": cid,
                        "cname": CLASSES[cid],
                        "conf": float(confs[i]),
                        "xyxy": box_norm,
                        "matched_gt": False,
                    })

            # Threshold sweep calculations
            for t in thresholds:
                t_preds = [pb for pb in pred_boxes if pb["conf"] >= t]
                matched_gt_ids = set()
                
                # Match preds to GT (greedy IoU matching)
                # Sort preds by conf descending
                t_preds_sorted = sorted(t_preds, key=lambda x: x["conf"], reverse=True)
                for pb in t_preds_sorted:
                    best_iou = 0.0
                    best_gt_idx = -1
                    for gt_idx, gt in enumerate(gt_boxes):
                        if gt_idx in matched_gt_ids:
                            continue
                        iou = box_iou(pb["xyxy"], gt["xyxy"])
                        if iou > best_iou:
                            best_iou = iou
                            best_gt_idx = gt_idx
                            
                    if best_iou >= EVAL_IOU and best_gt_idx >= 0 and gt_boxes[best_gt_idx]["cid"] == pb["cid"]:
                        # True Positive
                        matched_gt_ids.add(best_gt_idx)
                        threshold_metrics[t]["overall"]["tp"] += 1
                        threshold_metrics[t]["per_class"][pb["cname"]]["tp"] += 1
                    else:
                        # False Positive
                        threshold_metrics[t]["overall"]["fp"] += 1
                        threshold_metrics[t]["per_class"][pb["cname"]]["fp"] += 1
                        
                # False Negatives for this threshold
                unmatched_gt_count = len(gt_boxes) - len(matched_gt_ids)
                threshold_metrics[t]["overall"]["fn"] += unmatched_gt_count
                for gt_idx, gt in enumerate(gt_boxes):
                    if gt_idx not in matched_gt_ids:
                        threshold_metrics[t]["per_class"][gt["cname"]]["fn"] += 1

            # Detailed error collection at EVAL_CONF (0.25)
            eval_preds = [pb for pb in pred_boxes if pb["conf"] >= EVAL_CONF]
            matched_gts_eval = set()
            
            for pb in sorted(eval_preds, key=lambda x: x["conf"], reverse=True):
                best_iou = 0.0
                best_gt_idx = -1
                for gt_idx, gt in enumerate(gt_boxes):
                    iou = box_iou(pb["xyxy"], gt["xyxy"])
                    if iou > best_iou:
                        best_iou = iou
                        best_gt_idx = gt_idx
                        
                if best_iou >= EVAL_IOU and best_gt_idx >= 0 and gt_boxes[best_gt_idx]["cid"] == pb["cid"]:
                    matched_gts_eval.add(best_gt_idx)
                elif best_iou >= 0.30 and best_gt_idx >= 0 and gt_boxes[best_gt_idx]["cid"] != pb["cid"]:
                    # Class confusion
                    true_c = gt_boxes[best_gt_idx]["cname"]
                    pred_c = pb["cname"]
                    confusion_counts[true_c][pred_c] += 1
                    if len(error_cases["class_confusion"]) < 30:
                        error_cases["class_confusion"].append({
                            "image_id": img_id,
                            "true_class": true_c,
                            "pred_class": pred_c,
                            "conf": pb["conf"],
                            "iou": best_iou,
                            "img_path": str(p),
                            "gt_box": gt_boxes[best_gt_idx]["xywh"],
                            "pred_box": pb["xyxy"],
                        })
                else:
                    # Pure false positive / background hallucination
                    if len(error_cases["false_positives"]) < 30:
                        error_cases["false_positives"].append({
                            "image_id": img_id,
                            "pred_class": pb["cname"],
                            "conf": pb["conf"],
                            "max_gt_iou": best_iou,
                            "img_path": str(p),
                            "pred_box": pb["xyxy"],
                        })
                        
            # Unmatched GTs are False Negatives
            for gt_idx, gt in enumerate(gt_boxes):
                if gt_idx not in matched_gts_eval:
                    is_small = gt["area"] < 0.0025
                    fn_record = {
                        "image_id": img_id,
                        "class": gt["cname"],
                        "area": gt["area"],
                        "is_small": is_small,
                        "img_path": str(p),
                        "gt_box": gt["xywh"],
                    }
                    if is_small and len(error_cases["missed_small_objects"]) < 30:
                        error_cases["missed_small_objects"].append(fn_record)
                    elif len(error_cases["false_negatives"]) < 30:
                        error_cases["false_negatives"].append(fn_record)

    # Compute precision, recall, F1 across thresholds
    sweep_table = []
    best_f1 = 0.0
    optimal_thresh = 0.25
    
    for t in thresholds:
        tp = threshold_metrics[t]["overall"]["tp"]
        fp = threshold_metrics[t]["overall"]["fp"]
        fn = threshold_metrics[t]["overall"]["fn"]
        
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
        
        if f1 > best_f1:
            best_f1 = f1
            optimal_thresh = t
            
        row = {
            "threshold": t,
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1_score": round(f1, 4),
            "per_class": {}
        }
        for cname in CLASSES.values():
            c_tp = threshold_metrics[t]["per_class"][cname]["tp"]
            c_fp = threshold_metrics[t]["per_class"][cname]["fp"]
            c_fn = threshold_metrics[t]["per_class"][cname]["fn"]
            c_p = c_tp / (c_tp + c_fp) if (c_tp + c_fp) > 0 else 0.0
            c_r = c_tp / (c_tp + c_fn) if (c_tp + c_fn) > 0 else 0.0
            c_f1 = (2 * c_p * c_r) / (c_p + c_r) if (c_p + c_r) > 0 else 0.0
            row["per_class"][cname] = {
                "precision": round(c_p, 4),
                "recall": round(c_r, 4),
                "f1": round(c_f1, 4),
            }
        sweep_table.append(row)

    # Generate representative visual error images under runs/analysis/s4_t7a_validation_errors/
    out_vis_dir = ROOT_DIR / "runs" / "analysis" / "s4_t7a_validation_errors"
    out_vis_dir.mkdir(parents=True, exist_ok=True)
    
    generated_visuals = []
    
    # 1. Background False Positives (Shadow/Tar line)
    if error_cases["false_positives"]:
        for idx, fp in enumerate(error_cases["false_positives"][:3]):
            img = cv2.imread(fp["img_path"])
            h, w = img.shape[:2]
            box = fp["pred_box"]
            x1, y1, x2, y2 = int(box[0]*w), int(box[1]*h), int(box[2]*w), int(box[3]*h)
            # Draw red pred box
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 255), 2)
            cv2.putText(img, f"FP: {fp['pred_class']} {fp['conf']:.2f}", (x1, max(20, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            fname = f"fp_background_{idx+1}_{fp['image_id']}.jpg"
            save_path = out_vis_dir / fname
            cv2.imwrite(str(save_path), img)
            generated_visuals.append({
                "type": "false_positive_background",
                "image_id": fp["image_id"],
                "file_name": fname,
                "description": f"Model hallucinated {fp['pred_class']} (conf={fp['conf']:.2f}) on road surface with no ground truth damage",
            })
            
    # 2. Missed Small Object (Pothole or Narrow Crack)
    if error_cases["missed_small_objects"]:
        for idx, fn in enumerate(error_cases["missed_small_objects"][:3]):
            img = cv2.imread(fn["img_path"])
            h, w = img.shape[:2]
            x, y, bw, bh = fn["gt_box"]
            x1, y1, x2, y2 = int((x - bw/2)*w), int((y - bh/2)*h), int((x + bw/2)*w), int((y + bh/2)*h)
            # Draw green GT box
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(img, f"FN (Missed): {fn['class']}", (x1, max(20, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            fname = f"fn_missed_small_{idx+1}_{fn['image_id']}.jpg"
            save_path = out_vis_dir / fname
            cv2.imwrite(str(save_path), img)
            generated_visuals.append({
                "type": "false_negative_small_object",
                "image_id": fn["image_id"],
                "file_name": fname,
                "description": f"Ground-truth {fn['class']} (area={fn['area']:.5f}) missed by model due to low contrast / small scale",
            })

    # 3. Class Confusion (e.g. D00 vs D20 or D00 vs D10)
    if error_cases["class_confusion"]:
        for idx, cc in enumerate(error_cases["class_confusion"][:3]):
            img = cv2.imread(cc["img_path"])
            h, w = img.shape[:2]
            # GT green
            gx, gy, gw, gh = cc["gt_box"]
            gx1, gy1, gx2, gy2 = int((gx - gw/2)*w), int((gy - gh/2)*h), int((gx + gw/2)*w), int((gy + gh/2)*h)
            cv2.rectangle(img, (gx1, gy1), (gx2, gy2), (0, 255, 0), 2)
            cv2.putText(img, f"GT: {cc['true_class']}", (gx1, max(20, gy1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            # Pred red
            pbox = cc["pred_box"]
            px1, py1, px2, py2 = int(pbox[0]*w), int(pbox[1]*h), int(pbox[2]*w), int(pbox[3]*h)
            cv2.rectangle(img, (px1, py1), (px2, py2), (0, 0, 255), 2)
            cv2.putText(img, f"Pred: {cc['pred_class']} {cc['conf']:.2f}", (px1, min(h-5, py2 + 15)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            fname = f"class_confusion_{idx+1}_{cc['image_id']}.jpg"
            save_path = out_vis_dir / fname
            cv2.imwrite(str(save_path), img)
            generated_visuals.append({
                "type": "class_confusion",
                "image_id": cc["image_id"],
                "file_name": fname,
                "description": f"True {cc['true_class']} classified as {cc['pred_class']} with conf {cc['conf']:.2f} (IoU={cc['iou']:.2f})",
            })

    return {
        "threshold_sweep": sweep_table,
        "optimal_threshold_overall": optimal_thresh,
        "optimal_f1_overall": best_f1,
        "confusion_pairs": {k: dict(v) for k, v in confusion_counts.items()},
        "generated_visual_errors": generated_visuals,
    }

def main():
    print("=" * 80)
    print("ROADVISION AI — S4-T7A MASTER DATASET & VALIDATION ERROR ANALYSIS")
    print("=" * 80)
    start_t = time.time()
    
    # Task A
    dataset_structure = analyze_dataset_structure()
    
    # Task B
    annotation_quality = inspect_annotation_quality()
    
    # Tasks C & G
    val_analysis = run_validation_error_analysis_and_thresholding()
    
    elapsed = time.time() - start_t
    print(f"\n[INFO] Comprehensive analysis completed in {elapsed:.2f} seconds.")
    
    findings = {
        "task": "S4-T7A Dataset and Validation Error Analysis",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "elapsed_seconds": elapsed,
        "dataset_structure": dataset_structure,
        "annotation_quality": annotation_quality,
        "validation_analysis": val_analysis,
    }
    
    out_json = ROOT_DIR / "runs" / "s4_t7a_improvement_findings.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(findings, f, indent=2)
        
    print(f"[SUCCESS] Findings written to: {out_json}")
    print("=" * 80)

if __name__ == "__main__":
    main()

