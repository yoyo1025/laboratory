import open3d as o3d
import numpy as np

pcd = o3d.io.read_point_cloud("input.pcd")

# --- 法線推定と向き揃え ----------------------
pcd.estimate_normals(
    search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=0.05, max_nn=30)
)
pcd.orient_normals_consistent_tangent_plane(k=30)

# --- Poisson 再構成 --------------------------
mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
    pcd, depth=9
)

# --- 低密度頂点を除去 ------------------------
densities = np.asarray(densities)
th = np.quantile(densities, 0.025)   # 下位 2.5% をカット
mesh.remove_vertices_by_mask(densities < th)

mesh = (
    mesh.remove_duplicated_vertices()
        .remove_degenerate_triangles()
        .remove_non_manifold_edges()
        .remove_unreferenced_vertices()
)

# --- 必要なら軽量化 --------------------------
mesh = mesh.simplify_vertex_clustering(voxel_size=0.0025)

o3d.io.write_triangle_mesh("clean_mesh.ply", mesh)
print("✅ clean_mesh.ply を出力しました")

