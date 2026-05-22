from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
import open3d as o3d


class ManualPointCloudSegmenter:
    def __init__(self, input_path: Path, output_dir: Path, width: int, height: int, prefix: str):
        self.input_path = input_path
        self.output_dir = output_dir
        self.width = width
        self.height = height
        self.prefix = prefix
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.pcd = o3d.io.read_point_cloud(str(input_path))
        if self.pcd.is_empty():
            raise ValueError(f"Point cloud is empty or unreadable: {input_path}")

        self.vis: o3d.visualization.VisualizerWithKeyCallback | None = None
        self.view_image: np.ndarray | None = None
        self.camera: dict[str, object] | None = None
        self.mask: np.ndarray | None = None

    def run(self) -> None:
        print("Open3D window controls:")
        print("  Rotate/zoom to the target view.")
        print("  Press C to capture the current view and draw a 2D polygon mask.")
        print("  Press Q or ESC to close.")
        self.vis = o3d.visualization.VisualizerWithKeyCallback()
        self.vis.create_window(width=self.width, height=self.height, window_name="Manual point cloud segmentation")
        self.vis.add_geometry(self.pcd)
        opt = self.vis.get_render_option()
        opt.point_size = 2.0
        opt.background_color = np.array([0.05, 0.05, 0.05])
        self.vis.register_key_callback(ord("C"), self.capture_and_mask)
        self.vis.run()
        self.vis.destroy_window()

    def capture_and_mask(self, _vis: o3d.visualization.Visualizer) -> bool:
        if self.vis is None:
            return False
        params = self.vis.get_view_control().convert_to_pinhole_camera_parameters()
        image = np.asarray(self.vis.capture_screen_float_buffer(do_render=True))
        self.view_image = (image * 255).astype(np.uint8)
        self.camera = {
            "intrinsic": np.asarray(params.intrinsic.intrinsic_matrix),
            "extrinsic": np.asarray(params.extrinsic),
            "width": self.width,
            "height": self.height,
        }

        view_path = self.output_dir / f"{self.prefix}_view.png"
        camera_path = self.output_dir / f"{self.prefix}_camera.json"
        cv2.imwrite(str(view_path), cv2.cvtColor(self.view_image, cv2.COLOR_RGB2BGR))
        with camera_path.open("w", encoding="utf-8") as file:
            json.dump(
                {
                    "intrinsic": self.camera["intrinsic"].tolist(),
                    "extrinsic": self.camera["extrinsic"].tolist(),
                    "width": self.width,
                    "height": self.height,
                },
                file,
                indent=2,
            )
        print(f"Captured view: {view_path}")
        self.draw_polygon_mask()
        self.segment()
        return False

    def draw_polygon_mask(self) -> None:
        if self.view_image is None:
            raise RuntimeError("No captured view image.")

        points: list[tuple[int, int]] = []
        mask = np.zeros(self.view_image.shape[:2], dtype=np.uint8)
        window_name = "Draw polygon mask: left click points, S save, C clear, Q cancel"

        def on_mouse(event: int, x: int, y: int, _flags: int, _param: object) -> None:
            if event == cv2.EVENT_LBUTTONDOWN:
                points.append((x, y))

        cv2.namedWindow(window_name)
        cv2.setMouseCallback(window_name, on_mouse)

        while True:
            display = self.view_image.copy()
            for point in points:
                cv2.circle(display, point, 4, (255, 255, 0), -1)
            if len(points) > 1:
                cv2.polylines(display, [np.array(points, np.int32)], len(points) > 2, (0, 255, 0), 2)
            cv2.imshow(window_name, cv2.cvtColor(display, cv2.COLOR_RGB2BGR))
            key = cv2.waitKey(20) & 0xFF
            if key == ord("s"):
                if len(points) < 3:
                    print("Need at least three points.")
                    continue
                cv2.fillPoly(mask, [np.array(points, np.int32)], 255)
                break
            if key == ord("c"):
                points.clear()
                mask.fill(0)
            if key == ord("q") or key == 27:
                cv2.destroyWindow(window_name)
                raise RuntimeError("Mask drawing cancelled.")

        cv2.destroyWindow(window_name)
        self.mask = mask
        mask_path = self.output_dir / f"{self.prefix}_mask.png"
        cv2.imwrite(str(mask_path), mask)
        print(f"Saved mask: {mask_path}")

    def project_points(self) -> np.ndarray:
        if self.camera is None or self.mask is None:
            raise RuntimeError("Missing camera or mask.")

        points = np.asarray(self.pcd.points)
        ones = np.ones((points.shape[0], 1), dtype=np.float64)
        homogeneous = np.hstack([points, ones])
        extrinsic = np.asarray(self.camera["extrinsic"], dtype=np.float64)
        intrinsic = np.asarray(self.camera["intrinsic"], dtype=np.float64)
        camera_points = (extrinsic @ homogeneous.T).T[:, :3]

        z = camera_points[:, 2]
        valid_z = np.abs(z) > 1e-8
        projected = np.full((points.shape[0], 2), np.nan, dtype=np.float64)
        uvw = (intrinsic @ camera_points[valid_z].T).T
        projected[valid_z] = uvw[:, :2] / uvw[:, 2:3]
        return projected

    def segment(self) -> None:
        if self.mask is None:
            raise RuntimeError("No mask to segment.")

        points_2d = self.project_points()
        height, width = self.mask.shape
        valid_indices: list[int] = []
        for idx, (u_float, v_float) in enumerate(points_2d):
            if not np.isfinite(u_float) or not np.isfinite(v_float):
                continue
            u = int(round(u_float))
            v = int(round(v_float))
            if 0 <= u < width and 0 <= v < height and self.mask[v, u] > 0:
                valid_indices.append(idx)

        if not valid_indices:
            raise RuntimeError("Mask did not select any 3D points. Try another view or a larger polygon.")

        selected = self.pcd.select_by_index(valid_indices)
        remaining = self.pcd.select_by_index(valid_indices, invert=True)

        selected_ply = self.output_dir / f"{self.prefix}_segmented.ply"
        selected_pcd = self.output_dir / f"{self.prefix}_segmented.pcd"
        remaining_ply = self.output_dir / f"{self.prefix}_remaining.ply"
        o3d.io.write_point_cloud(str(selected_ply), selected)
        o3d.io.write_point_cloud(str(selected_pcd), selected)
        o3d.io.write_point_cloud(str(remaining_ply), remaining)
        print(f"Selected points: {len(valid_indices)}")
        print(f"Saved segmented point cloud: {selected_ply}")
        print(f"Saved remaining point cloud: {remaining_ply}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Manual polygon-mask segmentation for an Open3D point cloud.")
    parser.add_argument("--input", required=True, type=Path, help="Input .ply/.pcd point cloud.")
    parser.add_argument("--output-dir", default=Path("outputs/segmentation"), type=Path)
    parser.add_argument("--prefix", default="segment_001")
    parser.add_argument("--width", default=1000, type=int)
    parser.add_argument("--height", default=760, type=int)
    args = parser.parse_args(argv)

    ManualPointCloudSegmenter(args.input, args.output_dir, args.width, args.height, args.prefix).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

