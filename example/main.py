# example/main.py
import argparse, open3d as o3d
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--no-view", action="store_true", help="GUI を開かない")
args = ap.parse_args()

pcd_path = Path(__file__).with_name("bun.pcd")
pcd = o3d.io.read_point_cloud(str(pcd_path))

if not args.no_view:
    o3d.visualization.draw_geometries([pcd])

o3d.io.write_point_cloud("output.pcd", pcd)
print("✅ bun.pcd を output.pcd にコピーしました")
