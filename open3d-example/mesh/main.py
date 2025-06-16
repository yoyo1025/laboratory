import open3d as o3d

# 1. 点群を読み込む
pcd = o3d.io.read_point_cloud("input.pcd")     # .pcd や 点群 .ply

# 2. 法線推定（半径や近傍点数は点群密度に応じて調整）
pcd.estimate_normals(
    search_param=o3d.geometry.KDTreeSearchParamHybrid(
        radius=0.02,       # 近傍探索半径 [m]
        max_nn=30          # 近傍点数
    )
)

# 3. ポアソン再構成でメッシュ化
mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
    pcd,
    depth=9               # 解像度（深いほど細かい）
)

# 4. 後処理（重複除去・小さな三角形除去など）
mesh = (
    mesh.remove_duplicated_vertices()
        .remove_degenerate_triangles()
        .remove_non_manifold_edges()
        .remove_unreferenced_vertices()
)

simplifed_mesh = mesh.simplify_vertex_clustering(voxel_size=0.001)

# 5. メッシュを書き出し
o3d.io.write_triangle_mesh("output_mesh5.ply", simplifed_mesh)
print("✅ 点群から生成したメッシュを output_mesh.ply に保存しました")
