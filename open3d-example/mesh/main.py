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
    mesh
    .remove_duplicated_vertices()         # 【重複頂点の除去】完全に同じ座標を持つ頂点を1つにまとめる → meshの軽量化と後続処理の安定化
    .remove_degenerate_triangles()        # 【縮退三角形の除去】頂点が重複していて面積がゼロに近い三角形（線または点状）を削除
    .remove_non_manifold_edges()         # 【非多様体エッジ処理】3面以上にまたがるエッジを検出し、最も面積の小さい三角形から順に削除してエッジを通常の形状に整える :contentReference[oaicite:1]{index=1}
    .remove_unreferenced_vertices()      # 【未参照頂点の除去】三角形に使われなくなった頂点を削除して、無駄な頂点を整理 :contentReference[oaicite:2]{index=2}
)


# --- 必要なら軽量化 --------------------------
mesh = mesh.simplify_vertex_clustering(voxel_size=0.0025)

o3d.io.write_triangle_mesh("clean_mesh.ply", mesh)
print("✅ clean_mesh.ply を出力しました")

