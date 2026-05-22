from __future__ import annotations

import argparse

from src.medical3d_pipeline import ct_to_pointcloud, funsr_reconstruct, make_web_viewer, manual_mask_segment


def main() -> int:
    parser = argparse.ArgumentParser(
        description="CT image -> point cloud -> Open3D segmentation -> FUNSR reconstruction -> web viewer pipeline."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_ct = subparsers.add_parser("ct-to-pointcloud", help="Convert CT images/DICOM slices to .ply point cloud.")
    p_ct.add_argument("--input", required=True)
    p_ct.add_argument("--output", default="outputs/pointclouds/ct_pointcloud.ply")
    p_ct.add_argument("--threshold", default=None, type=float)
    p_ct.add_argument("--percentile", default=75.0, type=float)
    p_ct.add_argument("--slice-step", default=1, type=int)
    p_ct.add_argument("--pixel-step", default=2, type=int)
    p_ct.add_argument("--xy-spacing", default=1.0, type=float)
    p_ct.add_argument("--z-spacing", default=1.0, type=float)
    p_ct.add_argument("--max-points", default=300000, type=int)
    p_ct.add_argument("--include-zero-background", action="store_true")

    p_seg = subparsers.add_parser("segment", help="Launch Open3D and draw a 2D mask for manual point-cloud segmentation.")
    p_seg.add_argument("--input", required=True)
    p_seg.add_argument("--output-dir", default="outputs/segmentation")
    p_seg.add_argument("--prefix", default="segment_001")
    p_seg.add_argument("--width", default=1000, type=int)
    p_seg.add_argument("--height", default=760, type=int)

    p_fun = subparsers.add_parser("funsr", help="Prepare and optionally run FUNSR reconstruction.")
    p_fun.add_argument("--point-cloud", required=True)
    p_fun.add_argument("--funsr-root", default="FUNSR/FUNSR")
    p_fun.add_argument("--python", default=".venv-1/Scripts/python.exe")
    p_fun.add_argument("--dataname", default="ct_segmented")
    p_fun.add_argument("--output-name", default="ct_segmented")
    p_fun.add_argument("--gpu", default=0, type=int)
    p_fun.add_argument("--threshold", default=0.0, type=float)
    p_fun.add_argument("--refresh-cache", action="store_true")
    p_fun.add_argument("--run", action="store_true")

    p_web = subparsers.add_parser("web", help="Generate a static web viewer for point clouds.")
    p_web.add_argument("--inputs", nargs="+", required=True)
    p_web.add_argument("--names", nargs="*", default=None)
    p_web.add_argument("--output-dir", default="outputs/web")

    args = parser.parse_args()

    if args.command == "ct-to-pointcloud":
        return ct_to_pointcloud.main(
            [
                "--input",
                args.input,
                "--output",
                args.output,
                "--percentile",
                str(args.percentile),
                "--slice-step",
                str(args.slice_step),
                "--pixel-step",
                str(args.pixel_step),
                "--xy-spacing",
                str(args.xy_spacing),
                "--z-spacing",
                str(args.z_spacing),
                "--max-points",
                str(args.max_points),
            ]
            + ([] if args.threshold is None else ["--threshold", str(args.threshold)])
            + ([] if not args.include_zero_background else ["--include-zero-background"])
        )

    if args.command == "segment":
        return manual_mask_segment.main(
            [
                "--input",
                args.input,
                "--output-dir",
                args.output_dir,
                "--prefix",
                args.prefix,
                "--width",
                str(args.width),
                "--height",
                str(args.height),
            ]
        )

    if args.command == "funsr":
        fun_args = [
            "--point-cloud",
            args.point_cloud,
            "--funsr-root",
            args.funsr_root,
            "--python",
            args.python,
            "--dataname",
            args.dataname,
            "--output-name",
            args.output_name,
            "--gpu",
            str(args.gpu),
            "--threshold",
            str(args.threshold),
        ]
        if args.refresh_cache:
            fun_args.append("--refresh-cache")
        if args.run:
            fun_args.append("--run")
        return funsr_reconstruct.main(fun_args)

    if args.command == "web":
        web_args = ["--inputs", *args.inputs, "--output-dir", args.output_dir]
        if args.names:
            web_args.extend(["--names", *args.names])
        return make_web_viewer.main(web_args)

    raise ValueError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
