from __future__ import annotations

import argparse
import re
from pathlib import Path

import numpy as np
import open3d as o3d
from PIL import Image


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}
DICOM_EXTENSIONS = {".dcm", ""}


def natural_key(path: Path) -> list[object]:
    parts = re.split(r"(\d+)", path.name)
    return [int(part) if part.isdigit() else part.lower() for part in parts]


def list_input_files(input_path: Path) -> list[Path]:
    if input_path.is_file():
        return [input_path]
    files = [
        path
        for path in input_path.iterdir()
        if path.is_file()
        and (path.suffix.lower() in IMAGE_EXTENSIONS or path.suffix.lower() in DICOM_EXTENSIONS)
    ]
    return sorted(files, key=natural_key)


def read_grayscale(path: Path) -> np.ndarray:
    if path.suffix.lower() in IMAGE_EXTENSIONS:
        return np.asarray(Image.open(path).convert("L"), dtype=np.float32)

    try:
        import pydicom
    except ImportError as exc:
        raise RuntimeError(
            "Reading DICOM requires pydicom. Install it or convert DICOM to PNG first."
        ) from exc

    ds = pydicom.dcmread(str(path))
    image = ds.pixel_array.astype(np.float32)
    slope = float(getattr(ds, "RescaleSlope", 1.0))
    intercept = float(getattr(ds, "RescaleIntercept", 0.0))
    image = image * slope + intercept
    image -= np.nanmin(image)
    max_value = np.nanmax(image)
    if max_value > 0:
        image = image / max_value * 255.0
    return image


def estimate_threshold(
    images: list[np.ndarray],
    percentile: float,
    sample_limit: int = 2_000_000,
    ignore_zero: bool = True,
) -> float:
    samples: list[np.ndarray] = []
    remaining = sample_limit
    for image in images:
        flat = image.reshape(-1)
        if ignore_zero:
            flat = flat[flat > 0]
        if flat.size == 0:
            continue
        if flat.size > remaining:
            idx = np.linspace(0, flat.size - 1, remaining, dtype=np.int64)
            samples.append(flat[idx])
            break
        samples.append(flat)
        remaining -= flat.size
        if remaining <= 0:
            break
    if not samples:
        return 0.0
    return float(np.percentile(np.concatenate(samples), percentile))


def build_point_cloud(
    files: list[Path],
    *,
    threshold: float | None,
    percentile: float,
    slice_step: int,
    pixel_step: int,
    xy_spacing: float,
    z_spacing: float,
    max_points: int | None,
    ignore_zero_background: bool,
) -> tuple[o3d.geometry.PointCloud, dict[str, object]]:
    if not files:
        raise ValueError("No CT image or DICOM files found.")

    slice_step = max(1, slice_step)
    pixel_step = max(1, pixel_step)
    selected_files = files[::slice_step]
    images = [read_grayscale(path) for path in selected_files]
    if threshold is None:
        threshold = estimate_threshold(images, percentile, ignore_zero=ignore_zero_background)

    points: list[np.ndarray] = []
    colors: list[np.ndarray] = []
    slice_counts: list[int] = []

    for slice_index, image in enumerate(images):
        sampled = image[::pixel_step, ::pixel_step]
        mask = sampled >= threshold
        rows, cols = np.nonzero(mask)
        if rows.size == 0:
            slice_counts.append(0)
            continue

        height, width = image.shape[:2]
        x = (cols * pixel_step - width / 2.0) * xy_spacing
        y = (height / 2.0 - rows * pixel_step) * xy_spacing
        z = np.full_like(x, slice_index * slice_step * z_spacing, dtype=np.float32)
        values = sampled[rows, cols] / 255.0

        points.append(np.column_stack([x, y, z]).astype(np.float32))
        colors.append(np.column_stack([values, values, values]).astype(np.float32))
        slice_counts.append(int(rows.size))

    if not points:
        raise ValueError(
            f"No foreground points were produced. Lower --threshold or --percentile. Current threshold: {threshold:.3f}"
        )

    all_points = np.vstack(points)
    all_colors = np.vstack(colors)

    if max_points and all_points.shape[0] > max_points:
        rng = np.random.default_rng(42)
        indices = rng.choice(all_points.shape[0], size=max_points, replace=False)
        all_points = all_points[indices]
        all_colors = all_colors[indices]

    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(all_points.astype(np.float64))
    pcd.colors = o3d.utility.Vector3dVector(all_colors.astype(np.float64))

    meta = {
        "input_count": len(files),
        "used_slice_count": len(selected_files),
        "threshold": threshold,
        "percentile": percentile,
        "slice_step": slice_step,
        "pixel_step": pixel_step,
        "xy_spacing": xy_spacing,
        "z_spacing": z_spacing,
        "point_count": int(all_points.shape[0]),
        "ignore_zero_background": ignore_zero_background,
        "slice_point_counts": slice_counts,
    }
    return pcd, meta


def save_point_cloud(pcd: o3d.geometry.PointCloud, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not o3d.io.write_point_cloud(str(output_path), pcd):
        raise RuntimeError(f"Failed to write point cloud: {output_path}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Convert a CT slice folder or DICOM folder to a point cloud.")
    parser.add_argument("--input", required=True, type=Path, help="Input CT image/DICOM file or folder.")
    parser.add_argument("--output", default=Path("outputs/pointclouds/ct_pointcloud.ply"), type=Path)
    parser.add_argument("--threshold", type=float, default=None, help="Foreground threshold in 0-255 scale.")
    parser.add_argument("--percentile", type=float, default=75.0, help="Auto threshold percentile when --threshold is omitted.")
    parser.add_argument("--slice-step", type=int, default=1, help="Use every Nth slice.")
    parser.add_argument("--pixel-step", type=int, default=2, help="Use every Nth pixel in x/y.")
    parser.add_argument("--xy-spacing", type=float, default=1.0)
    parser.add_argument("--z-spacing", type=float, default=1.0)
    parser.add_argument("--max-points", type=int, default=300_000)
    parser.add_argument(
        "--include-zero-background",
        action="store_true",
        help="Include zero-valued background pixels when estimating the auto threshold.",
    )
    args = parser.parse_args(argv)

    files = list_input_files(args.input)
    pcd, meta = build_point_cloud(
        files,
        threshold=args.threshold,
        percentile=args.percentile,
        slice_step=args.slice_step,
        pixel_step=args.pixel_step,
        xy_spacing=args.xy_spacing,
        z_spacing=args.z_spacing,
        max_points=args.max_points,
        ignore_zero_background=not args.include_zero_background,
    )
    save_point_cloud(pcd, args.output)
    print(f"Wrote {args.output}")
    print(f"Point count: {meta['point_count']}")
    print(f"Threshold: {meta['threshold']:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
