"""Day-1 GPU gate and YOLO26 compatibility probe for RoadVision AI.

Implements TDD v1.1 Section 14 ("Installation order and gate") and the
compatibility probe defined as task S4-T1 in ROADVISION_STAGE_3_1_INSPECTION.md.

What this script does
---------------------
1.  Prints the Python / PyTorch / torchvision / CUDA / driver versions.
2.  Asserts that CUDA is available and identifies the GPU.
3.  Checks the device compute capability and that the installed torch build
    actually contains kernels (``sm_XX`` or ``compute_XX``) for it.
4.  Runs a real matrix multiplication on the GPU and validates the result is
    finite.
5.  Reports VRAM allocated / reserved / total.
6.  Compares the integer device id ``0`` with the string ``"0"``.
7.  Builds YOLO26n from the bundled ``yolo26n.yaml`` config - no weights are
    downloaded - and asserts that no ``*.pt`` file appeared on disk.
8.  Runs predictions with ``nms=False`` (end-to-end) and with default
    arguments (external NMS), plus a device-string acceptance check and a
    deprecated-``end2end`` diagnostic.
9.  Records warnings, execution errors, result object types and box shapes.
10. Reports ``YOLO_OFFLINE`` and the Ultralytics settings sync flag.

What this script deliberately does NOT do
-----------------------------------------
* It does not download datasets or model weights.
* It does not train anything.
* It does not modify dependencies, the application, the frontend, the API,
  the database, or any global Ultralytics setting.

Important limitation
--------------------
The YAML-built model has RANDOM, UNTRAINED weights. A forward pass on a blank
synthetic image proves only that the code path executes and that the tensor /
box shapes are as expected. It says NOTHING about detection accuracy, model
quality, FPS, or production latency. Any timing printed below is a smoke-test
number from random weights on a black image and must never be quoted as a
performance measurement.

Exit codes
----------
0  all required assertions passed -> prints ``GATE PASSED``
1  a required assertion failed     -> prints ``GATE FAILED: <reason>``
2  an unexpected exception occurred before the gate could be evaluated
"""

from __future__ import annotations

import argparse
import logging
import os
import platform
import shutil
import subprocess
import sys
import traceback
import warnings
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_YAML = "yolo26n.yaml"
DEFAULT_IMGSZ = 640


# --------------------------------------------------------------------------- #
# Gate bookkeeping
# --------------------------------------------------------------------------- #
class GateFailure(RuntimeError):
    """Raised when a required gate assertion fails."""


@dataclass
class Check:
    name: str
    status: str  # "PASS" | "INFO" | "FAIL"
    detail: str = ""


class Gate:
    """Collects PASS/INFO/FAIL lines and fails fast on required assertions."""

    def __init__(self) -> None:
        self.checks: list[Check] = []
        self.warnings: list[str] = []

    def info(self, name: str, value: object) -> None:
        text = str(value)
        self.checks.append(Check(name, "INFO", text))
        print(f"[INFO] {name}: {text}")

    def record(self, name: str, ok: bool, detail: str = "") -> bool:
        self.checks.append(Check(name, "PASS" if ok else "FAIL", detail))
        suffix = f"  ({detail})" if detail else ""
        print(f"[{'PASS' if ok else 'FAIL'}] {name}{suffix}")
        return ok

    def require(self, ok: bool, name: str, detail: str = "") -> None:
        if not self.record(name, ok, detail):
            raise GateFailure(f"{name}: {detail or 'condition not met'}")

    def add_warning(self, text: str) -> None:
        self.warnings.append(text)
        print(f"[WARN] {text}")


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #
def section(title: str) -> None:
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def nvidia_smi_report() -> str:
    """Return a one-line driver/GPU report from nvidia-smi, or a reason."""
    exe = shutil.which("nvidia-smi")
    if exe is None:
        return "nvidia-smi not found on PATH"
    query = "name,driver_version,memory.total,compute_cap"
    for fields in (query, "name,driver_version,memory.total"):
        try:
            proc = subprocess.run(
                [exe, f"--query-gpu={fields}", "--format=csv,noheader"],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:  # pragma: no cover
            return f"nvidia-smi failed: {exc}"
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip().replace("\n", " | ")
        last_error = (proc.stderr or proc.stdout).strip() or f"exit {proc.returncode}"
    return f"nvidia-smi query failed: {last_error}"


def weight_files_on_disk() -> set[str]:
    """All ``*.pt`` files inside the repository, excluding venv and node_modules."""
    found: set[str] = set()
    for path in REPO_ROOT.rglob("*.pt"):
        text = str(path)
        if f"{os.sep}.venv{os.sep}" in text or f"{os.sep}node_modules{os.sep}" in text:
            continue
        found.add(text)
    return found


class UltralyticsWarningSink(logging.Handler):
    """Captures Ultralytics LOGGER warnings (deprecation notices are logged)."""

    def __init__(self) -> None:
        super().__init__(level=logging.WARNING)
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.messages.append(f"{record.levelname}: {record.getMessage()}")
        except Exception:  # pragma: no cover - defensive only
            self.messages.append("<unformattable log record>")


def describe_result(result: object) -> dict[str, object]:
    """Collect type/shape evidence from an Ultralytics ``Results`` object."""
    boxes = getattr(result, "boxes", None)
    data = getattr(boxes, "data", None)
    xyxy = getattr(boxes, "xyxy", None)
    return {
        "result_type": type(result).__name__,
        "boxes_type": type(boxes).__name__,
        "num_boxes": int(len(boxes)) if boxes is not None else None,
        "boxes_data_shape": tuple(data.shape) if data is not None else None,
        "boxes_xyxy_shape": tuple(xyxy.shape) if xyxy is not None else None,
        "boxes_dtype": str(data.dtype) if data is not None else None,
        "boxes_device": str(data.device) if data is not None else None,
        "orig_shape": tuple(getattr(result, "orig_shape", ()) or ()),
        "speed_ms": dict(getattr(result, "speed", {}) or {}),
    }


# --------------------------------------------------------------------------- #
# Sections
# --------------------------------------------------------------------------- #
def report_versions(gate: Gate) -> None:
    section("1. Versions")
    import torchvision

    cv2_version = "not installed"
    try:
        import cv2

        cv2_version = cv2.__version__
    except Exception as exc:  # pragma: no cover - informational only
        cv2_version = f"import failed: {exc}"

    gate.info("python", sys.version.split()[0])
    gate.info("python_executable", sys.executable)
    gate.info("platform", platform.platform())
    gate.info("torch", torch.__version__)
    gate.info("torchvision", torchvision.__version__)
    gate.info("torch.version.cuda", torch.version.cuda)
    gate.info("torch.cuda.is_available", torch.cuda.is_available())
    gate.info("nvidia-smi", nvidia_smi_report())
    gate.info("opencv", cv2_version)

    gate.require(
        torch.version.cuda is not None,
        "torch is a CUDA build",
        f"torch.version.cuda={torch.version.cuda!r}",
    )
    gate.require(
        not torch.__version__.endswith("+cpu"),
        "torch is not a CPU-only build",
        torch.__version__,
    )


def check_cuda_device(gate: Gate) -> None:
    section("2-3. CUDA availability, GPU identity, compute capability, kernels")
    gate.require(torch.cuda.is_available(), "CUDA is available")

    device_count = torch.cuda.device_count()
    gate.require(device_count >= 1, "at least one CUDA device", f"count={device_count}")

    props = torch.cuda.get_device_properties(0)
    capability = torch.cuda.get_device_capability(0)
    arch_list = list(torch.cuda.get_arch_list())

    gate.info("gpu_name", props.name)
    gate.info("compute_capability", capability)
    gate.info("total_memory_bytes", props.total_memory)
    gate.info("total_memory_GiB", round(props.total_memory / 1024**3, 2))
    gate.info("total_memory_GB_decimal", round(props.total_memory / 1e9, 2))
    gate.info("multiprocessor_count", props.multi_processor_count)
    gate.info("arch_list", arch_list)

    need_sm = f"sm_{capability[0]}{capability[1]}"
    need_ptx = f"compute_{capability[0]}{capability[1]}"
    gate.info("required_kernel_arch", f"{need_sm} (or {need_ptx})")

    gate.require(
        need_sm in arch_list or need_ptx in arch_list,
        "torch build contains kernels for this GPU",
        f"{need_sm} in arch_list={need_sm in arch_list}, "
        f"{need_ptx} in arch_list={need_ptx in arch_list}",
    )

    # sm_120 is required by the RTX 5060 (Blackwell, compute capability 12.0).
    if capability == (12, 0):
        gate.require(
            "sm_120" in arch_list,
            "sm_120 kernels present for the RTX 5060",
            f"arch_list={arch_list}",
        )
    else:
        gate.add_warning(
            f"compute capability is {capability}, not the expected (12, 0) of the "
            "RTX 5060; arch assertion above used the detected capability instead"
        )

    if "5060" not in props.name:
        gate.add_warning(
            f"GPU name {props.name!r} does not contain '5060'; this may not be the "
            "documented target machine"
        )


def check_matmul_and_memory(gate: Gate) -> None:
    section("4-5. Real CUDA matrix multiplication and VRAM accounting")
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats(0)

    size = 2048
    x = torch.randn(size, size, device="cuda")
    y = x @ x
    torch.cuda.synchronize()

    finite = bool(torch.isfinite(y).all())
    expected = size * size
    gate.require(
        tuple(y.shape) == (size, size),
        "matmul output shape",
        f"shape={tuple(y.shape)}",
    )
    gate.require(finite, "matmul result is finite")
    gate.require(
        y.numel() == expected,
        "matmul output element count",
        f"numel={y.numel()} expected={expected}",
    )
    gate.info("matmul_sample", f"y[0,0]={float(y[0, 0]):.6f}")

    allocated = torch.cuda.memory_allocated(0)
    reserved = torch.cuda.memory_reserved(0)
    peak = torch.cuda.max_memory_allocated(0)
    total = torch.cuda.get_device_properties(0).total_memory

    gate.info("memory_allocated_bytes", allocated)
    gate.info("memory_reserved_bytes", reserved)
    gate.info("memory_peak_allocated_bytes", peak)
    gate.info("memory_allocated_MiB", round(allocated / 1024**2, 1))
    gate.info("memory_reserved_MiB", round(reserved / 1024**2, 1))
    gate.info("memory_peak_allocated_MiB", round(peak / 1024**2, 1))
    gate.info("memory_total_MiB", round(total / 1024**2, 1))

    gate.require(0 <= allocated <= reserved, "reserved >= allocated")
    gate.require(reserved <= total, "reserved does not exceed total VRAM")
    gate.require(peak > 0, "peak allocation recorded")

    del x, y
    torch.cuda.empty_cache()


def check_device_selection(gate: Gate) -> None:
    section('6. Device selection: integer 0 vs string "0"')
    from ultralytics.utils.torch_utils import select_device

    resolved_int = select_device(0, verbose=False)
    resolved_str = select_device("0", verbose=False)

    gate.info("select_device(0)", f"{resolved_int!s} type={resolved_int.type} index={resolved_int.index}")
    gate.info('select_device("0")', f"{resolved_str!s} type={resolved_str.type} index={resolved_str.index}")

    gate.require(
        resolved_int.type == "cuda" and resolved_int.index == 0,
        "integer device 0 resolves to cuda:0",
        str(resolved_int),
    )
    gate.require(
        resolved_str.type == "cuda" and resolved_str.index == 0,
        'string device "0" resolves to cuda:0',
        str(resolved_str),
    )
    gate.require(
        resolved_int == resolved_str,
        "integer 0 and string \"0\" resolve to the same device",
        f"{resolved_int} == {resolved_str}",
    )


def build_yaml_model(gate: Gate, yaml_name: str, log_details: bool = False) -> "object":
    """Build YOLO26n from the packaged YAML config (random weights, no download)."""
    from ultralytics import YOLO

    model = YOLO(yaml_name)
    head = model.model.model[-1]
    if log_details:
        gate.info("model_yaml", yaml_name)
        gate.info("head_class", type(head).__name__)
        gate.info("head_nc", getattr(head, "nc", None))
        gate.info("head_has_one2one_branch", hasattr(head, "one2one_cv2"))
        gate.info("head_end2end_before_any_predict", bool(getattr(head, "end2end", False)))
        gate.info("model_ckpt_path", getattr(model, "ckpt_path", None))
        gate.info("parameter_count", sum(p.numel() for p in model.model.parameters()))
    return model


def run_probe(
    gate: Gate,
    label: str,
    image: np.ndarray,
    device: object,
    imgsz: int,
    predict_kwargs: dict[str, object],
    expect_end2end: bool | None,
    log_model_details: bool = False,
) -> dict[str, object]:
    """Build a fresh model, run one prediction, and record full evidence."""
    print(f"\n-- probe {label} --")
    sink = UltralyticsWarningSink()
    logger = logging.getLogger("ultralytics")
    logger.addHandler(sink)

    model = None
    record: dict[str, object] = {"probe": label, "kwargs": dict(predict_kwargs)}
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            model = build_yaml_model(gate, DEFAULT_YAML, log_details=log_model_details)
            results = model.predict(
                image,
                device=device,
                imgsz=imgsz,
                verbose=False,
                **predict_kwargs,
            )
    except Exception as exc:  # recorded, re-raised as a gate failure below
        record["error"] = f"{type(exc).__name__}: {exc}"
        record["traceback"] = traceback.format_exc(limit=6)
        gate.record(f"probe {label} executed without exception", False, record["error"])
        logger.removeHandler(sink)
        raise GateFailure(f"probe {label} raised {record['error']}") from exc
    finally:
        logger.removeHandler(sink)

    python_warnings = [f"{w.category.__name__}: {w.message}" for w in caught]
    record["python_warnings"] = python_warnings
    record["ultralytics_log_warnings"] = list(sink.messages)

    gate.require(
        isinstance(results, list) and len(results) == 1,
        f"probe {label} returned a one-element list",
        f"type={type(results).__name__} len={len(results) if isinstance(results, list) else 'n/a'}",
    )

    result = results[0]
    evidence = describe_result(result)
    record.update(evidence)

    for key in (
        "result_type",
        "boxes_type",
        "num_boxes",
        "boxes_data_shape",
        "boxes_xyxy_shape",
        "boxes_dtype",
        "boxes_device",
        "orig_shape",
        "speed_ms",
    ):
        gate.info(f"{label}.{key}", evidence[key])

    gate.require(
        evidence["boxes_data_shape"] is not None and len(evidence["boxes_data_shape"]) == 2,
        f"probe {label} produced a 2-D boxes tensor",
        str(evidence["boxes_data_shape"]),
    )
    gate.require(
        evidence["boxes_data_shape"][1] == 6,
        f"probe {label} boxes have 6 columns (x1,y1,x2,y2,conf,cls)",
        str(evidence["boxes_data_shape"]),
    )
    gate.require(
        evidence["orig_shape"] == (image.shape[0], image.shape[1]),
        f"probe {label} preserved the original image shape",
        f"orig_shape={evidence['orig_shape']} input={image.shape[:2]}",
    )

    backend = model.predictor.model
    end2end = bool(getattr(backend, "end2end", False))
    record["backend_end2end"] = end2end
    gate.info(f"{label}.backend_end2end", end2end)
    if expect_end2end is not None:
        gate.require(
            end2end is expect_end2end,
            f"probe {label} selected the expected head",
            f"end2end={end2end} expected={expect_end2end}",
        )

    if python_warnings:
        for message in python_warnings:
            gate.add_warning(f"{label} python warning: {message}")
    if sink.messages:
        for message in sink.messages:
            gate.add_warning(f"{label} ultralytics log: {message}")

    record["models_used_debug"] = getattr(model, "ckpt_path", None)
    return record


def probe_order_dependence(gate: Gate, image: np.ndarray, device: object, imgsz: int) -> None:
    """Diagnostic: does an instance switched to end-to-end revert on default args?

    R-02 in the Stage 3.1 report claims the mode is applied per call. If a single
    model instance keeps the end-to-end head after a subsequent default-argument
    call, then reusing one instance across modes is unsafe. This is recorded as
    an observation, not a gate assertion.
    """
    section("9b. Diagnostic: NMS-mode persistence on a re-used model instance")
    print("Not a required assertion. Records whether the head mode is sticky.")

    from ultralytics import YOLO

    model = YOLO(DEFAULT_YAML)
    model.predict(image, device=device, imgsz=imgsz, nms=False, verbose=False)
    after_end2end = bool(model.predictor.model.end2end)

    model.predict(image, device=device, imgsz=imgsz, verbose=False)
    after_default = bool(model.predictor.model.end2end)

    gate.info("end2end_after_nms_False_call", after_end2end)
    gate.info("end2end_after_following_default_call", after_default)

    if after_end2end and after_default:
        gate.add_warning(
            "the end-to-end head is STICKY on a re-used model instance: a later "
            "default-argument predict() did not revert to external NMS. Use a fresh "
            "model instance per mode (see R-02)."
        )
    else:
        gate.info(
            "mode_reverted_on_reuse",
            "yes - a default call restored the external-NMS path on the same instance",
        )


def probe_input_independence(gate: Gate, image: np.ndarray, device: object, imgsz: int) -> None:
    """Diagnostic: confirm that untrained weights give input-independent output.

    A trained detector must react to image content. If a blank image and a noise
    image produce the same boxes and confidences, the network is effectively
    ignoring its input - which is exactly what random initialisation implies.
    This is recorded as evidence for the "no accuracy claim" statement.
    """
    section("9c. Diagnostic: untrained weights are input-independent")
    print("Not a required assertion. Confirms the random weights carry no signal.")

    from ultralytics import YOLO

    rng = np.random.default_rng(0)
    noise = rng.integers(0, 256, size=image.shape, dtype=np.uint8)

    model = YOLO(DEFAULT_YAML)
    blank_result = model.predict(
        image, device=device, imgsz=imgsz, nms=False, conf=0.0, verbose=False
    )[0]
    noise_result = model.predict(
        noise, device=device, imgsz=imgsz, nms=False, conf=0.0, verbose=False
    )[0]

    blank_conf = float(blank_result.boxes.conf.max()) if len(blank_result.boxes) else float("nan")
    noise_conf = float(noise_result.boxes.conf.max()) if len(noise_result.boxes) else float("nan")

    gate.info("blank.num_boxes", len(blank_result.boxes))
    gate.info("noise.num_boxes", len(noise_result.boxes))
    gate.info("blank.max_confidence", f"{blank_conf:.8f}")
    gate.info("noise.max_confidence", f"{noise_conf:.8f}")

    if len(blank_result.boxes) == len(noise_result.boxes) and abs(blank_conf - noise_conf) < 1e-9:
        gate.add_warning(
            "blank and noise images produced identical box counts and confidences. This is "
            "expected from random initialisation and proves the forward pass carries no "
            "detection signal: no accuracy, recall or precision may be inferred from it."
        )


def report_offline_state(gate: Gate) -> None:
    section("10. Offline / analytics state")
    yolo_offline = os.environ.get("YOLO_OFFLINE")
    gate.info("env YOLO_OFFLINE", yolo_offline if yolo_offline is not None else "<unset>")

    try:
        from ultralytics.utils import SETTINGS, SETTINGS_FILE, env_bool

        gate.info("env_bool(YOLO_OFFLINE)", env_bool("YOLO_OFFLINE"))
        gate.info("settings.sync", SETTINGS.get("sync"))
        gate.info("settings.datasets_dir", SETTINGS.get("datasets_dir"))
        gate.info("settings.weights_dir", SETTINGS.get("weights_dir"))
        gate.info("settings.runs_dir", SETTINGS.get("runs_dir"))
        gate.info("settings_file", SETTINGS_FILE)

        if SETTINGS.get("sync"):
            gate.add_warning(
                "Ultralytics settings sync is enabled (settings['sync']=True). This is the "
                "user-level setting shared by every project on this machine. AC-18 requires "
                "no external calls during inference, so the serving process must set "
                "YOLO_OFFLINE=1 and disable sync (or set YOLO_CONFIG_DIR to a project-local "
                "config) before claiming AC-18. No global setting was modified by this gate."
            )
    except Exception as exc:  # pragma: no cover - informational only
        gate.add_warning(f"could not read Ultralytics settings: {type(exc).__name__}: {exc}")

    if not yolo_offline:
        gate.info(
            "offline_note",
            "YOLO_OFFLINE is not set for this gate run; the gate performs no network I/O "
            "because it never resolves a remote weight path",
        )


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="RoadVision AI Day-1 GPU gate and YOLO26 compatibility probe.",
    )
    parser.add_argument(
        "--yaml",
        default=DEFAULT_YAML,
        help=f"model YAML built from the installed package (default: {DEFAULT_YAML}); "
        "no weights are downloaded",
    )
    parser.add_argument("--imgsz", type=int, default=DEFAULT_IMGSZ, help="probe image size")
    parser.add_argument("--device", default=0, help="device id for the probes (default: 0)")
    parser.add_argument(
        "--skip-deprecated-probe",
        action="store_true",
        help="skip the deprecated end2end= keyword diagnostic",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    global DEFAULT_YAML
    DEFAULT_YAML = args.yaml

    gate = Gate()

    print("RoadVision AI - Day-1 GPU gate and YOLO26 compatibility probe")
    print("TDD v1.1 Section 14 / Stage S4-T1")
    print("Random untrained weights only: no accuracy or performance claim is made.")

    weights_before = weight_files_on_disk()
    gate.info("pt_files_present_before", sorted(weights_before) or "<none>")

    report_versions(gate)
    check_cuda_device(gate)
    check_matmul_and_memory(gate)
    check_device_selection(gate)

    section("7-8. YOLO26 built from YAML, end-to-end vs external-NMS probes")
    print(
        "NOTE: yolo26n.yaml produces a randomly initialised network. The blank "
        f"{args.imgsz}x{args.imgsz} image below is a synthetic compatibility input, "
        "not a test image, and the timings are not benchmarks."
    )
    blank = np.zeros((args.imgsz, args.imgsz, 3), dtype=np.uint8)

    records: list[dict[str, object]] = []

    records.append(
        run_probe(
            gate,
            "A_nms_False",
            blank,
            args.device,
            args.imgsz,
            {"nms": False},
            expect_end2end=True,
            log_model_details=True,
        )
    )
    records.append(
        run_probe(
            gate,
            "B_default",
            blank,
            args.device,
            args.imgsz,
            {},
            expect_end2end=False,
        )
    )
    records.append(
        run_probe(
            gate,
            "C_device_string",
            blank,
            "0",
            args.imgsz,
            {},
            expect_end2end=False,
        )
    )
    if not args.skip_deprecated_probe:
        records.append(
            run_probe(
                gate,
                "D_deprecated_end2end_False",
                blank,
                args.device,
                args.imgsz,
                {"end2end": False},
                expect_end2end=False,
            )
        )

    # Evidence that the box tensor really can be populated. At the default
    # conf=0.25 a randomly initialised network produces nothing, so one pass at
    # conf=0.0 is used purely to prove the (N, 6) layout with rows present.
    low_conf = run_probe(
        gate,
        "E_low_conf_evidence",
        blank,
        args.device,
        args.imgsz,
        {"nms": False, "conf": 0.0},
        expect_end2end=True,
    )
    gate.require(
        int(low_conf["num_boxes"]) > 0,
        "low-threshold probe produced populated boxes",
        f"num_boxes={low_conf['num_boxes']}",
    )

    probe_order_dependence(gate, blank, args.device, args.imgsz)
    probe_input_independence(gate, blank, args.device, args.imgsz)

    section("No-download verification")
    weights_after = weight_files_on_disk()
    gate.info("pt_files_present_after", sorted(weights_after) or "<none>")
    gate.require(
        weights_before == weights_after,
        "no model weights were downloaded or created",
        f"before={len(weights_before)} after={len(weights_after)}",
    )

    report_offline_state(gate)

    section("Gate summary")
    passed = sum(1 for c in gate.checks if c.status == "PASS")
    failed = [c for c in gate.checks if c.status == "FAIL"]
    infos = sum(1 for c in gate.checks if c.status == "INFO")
    print(f"assertions passed : {passed}")
    print(f"assertions failed : {len(failed)}")
    print(f"informational     : {infos}")
    print(f"warnings          : {len(gate.warnings)}")

    if failed:
        for check in failed:
            print(f"  FAILED: {check.name} ({check.detail})")
        print("GATE FAILED")
        return 1

    print()
    print("GATE PASSED")
    print(
        "Reminder: this gate proves environment and API compatibility only. It does not "
        "establish detection accuracy, and the printed timings are not benchmarks."
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except GateFailure as failure:
        print()
        print(f"GATE FAILED: {failure}")
        sys.exit(1)
    except Exception as error:  # pragma: no cover - unexpected
        print()
        print(f"UNEXPECTED ERROR: {type(error).__name__}: {error}")
        traceback.print_exc()
        sys.exit(2)
