from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


def prepare_funsr_input(point_cloud: Path, funsr_root: Path, dataname: str, refresh_cache: bool) -> Path:
    data_dir = funsr_root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    target = data_dir / f"{dataname}.ply"
    shutil.copy2(point_cloud, target)

    cached = data_dir / f"{dataname}.pt"
    if refresh_cache and cached.exists():
        cached.unlink()

    return target


def build_command(
    python_exe: Path,
    funsr_root: Path,
    conf: Path,
    dataname: str,
    output_name: str,
    gpu: int,
    threshold: float,
) -> list[str]:
    return [
        str(python_exe),
        str(funsr_root / "run_normalizedSpace.py"),
        "--gpu",
        str(gpu),
        "--conf",
        str(conf),
        "--dataname",
        dataname,
        "--dir",
        output_name,
        "--mcubes_threshold",
        str(threshold),
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare and optionally run FUNSR reconstruction.")
    parser.add_argument("--point-cloud", required=True, type=Path, help="Input .ply point cloud.")
    parser.add_argument("--funsr-root", default=Path("FUNSR/FUNSR"), type=Path)
    parser.add_argument("--python", default=Path(".venv-1/Scripts/python.exe"), type=Path)
    parser.add_argument("--dataname", default="ct_segmented")
    parser.add_argument("--output-name", default="ct_segmented")
    parser.add_argument("--gpu", default=0, type=int)
    parser.add_argument("--threshold", default=0.0, type=float)
    parser.add_argument("--refresh-cache", action="store_true")
    parser.add_argument("--run", action="store_true", help="Run FUNSR training/reconstruction after preparing input.")
    args = parser.parse_args(argv)

    prepared = prepare_funsr_input(args.point_cloud, args.funsr_root, args.dataname, args.refresh_cache)
    conf = args.funsr_root / "confs" / "conf.conf"
    command = build_command(args.python, args.funsr_root, conf, args.dataname, args.output_name, args.gpu, args.threshold)

    print(f"Prepared FUNSR input: {prepared}")
    print("FUNSR command:")
    print(" ".join(f'"{item}"' if " " in item else item for item in command))

    if args.run:
        subprocess.run(command, cwd=str(args.funsr_root), check=True)
    else:
        print("Not running FUNSR. Add --run when GPU/CUDA dependencies are ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

