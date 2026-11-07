"""
GPU and Training Monitor for RoadVision AI S4-T4.
Monitors nvidia-smi stats and system memory in a background thread while training runs.
"""
import csv
import os
import subprocess
import threading
import time
from datetime import datetime

class HardwareMonitor:
    def __init__(self, log_path: str, interval: float = 2.0):
        self.log_path = log_path
        self.interval = interval
        self.stop_event = threading.Event()
        self.thread = None
        self.records = []
        os.makedirs(os.path.dirname(os.path.abspath(log_path)), exist_ok=True)

    def _query_nvidia_smi(self):
        try:
            cmd = [
                "nvidia-smi",
                "--query-gpu=memory.total,memory.used,memory.free,utilization.gpu,utilization.memory,temperature.gpu",
                "--format=csv,noheader,nounits"
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            parts = [p.strip() for p in res.stdout.strip().split(",")]
            if len(parts) >= 6:
                return {
                    "vram_total_mb": float(parts[0]),
                    "vram_used_mb": float(parts[1]),
                    "vram_free_mb": float(parts[2]),
                    "gpu_util_pct": float(parts[3]),
                    "mem_util_pct": float(parts[4]),
                    "temp_c": float(parts[5]),
                }
        except Exception as e:
            pass
        return None

    def _run(self):
        with open(self.log_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "timestamp",
                    "vram_total_mb",
                    "vram_used_mb",
                    "vram_free_mb",
                    "gpu_util_pct",
                    "mem_util_pct",
                    "temp_c"
                ]
            )
            writer.writeheader()
            while not self.stop_event.is_set():
                stats = self._query_nvidia_smi()
                if stats:
                    row = {
                        "timestamp": datetime.now().isoformat(),
                        **stats
                    }
                    writer.writerow(row)
                    f.flush()
                    self.records.append(row)
                self.stop_event.wait(self.interval)

    def start(self):
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        if self.thread:
            self.stop_event.set()
            self.thread.join(timeout=5.0)

    def get_summary(self):
        if not self.records:
            return {}
        vram_used = [r["vram_used_mb"] for r in self.records]
        gpu_util = [r["gpu_util_pct"] for r in self.records]
        temps = [r["temp_c"] for r in self.records]
        return {
            "peak_vram_mb": max(vram_used),
            "min_vram_mb": min(vram_used),
            "avg_vram_mb": sum(vram_used) / len(vram_used),
            "peak_gpu_util_pct": max(gpu_util),
            "avg_gpu_util_pct": sum(gpu_util) / len(gpu_util),
            "peak_temp_c": max(temps),
            "avg_temp_c": sum(temps) / len(temps),
            "samples_count": len(self.records),
        }

