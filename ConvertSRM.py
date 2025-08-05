from pathlib import Path
from Source.srm import SrmFile
import fbx

def convert_srm_to_fbx(srm_path: Path, manager: fbx.FbxManager) -> fbx.FbxScene | None:
    print(f"Reading SRM file: {srm_path.name}")

    try:
        srm = SrmFile.from_file(srm_path)
        print("SRM file successfully parsed.")
    except Exception as e:
        print(f"Failed to parse SRM file: {e}")
        return None

    scene = fbx.FbxScene.Create(manager, srm_path.stem)
    if not scene:
        print("Failed to create FBX scene.")
        return None

    root_node = scene.GetRootNode()
    mesh_node = fbx.FbxNode.Create(manager, srm_path.stem)
    mesh = fbx.FbxMesh.Create(manager, "Mesh")

    if not mesh or not mesh_node:
        print("Failed to create mesh or mesh node.")
        return None

    mesh_node.SetNodeAttribute(mesh)
    root_node.AddChild(mesh_node)
    print("Mesh node attached to root.")

    vertex_count = len(srm.display_buffer.vertices)
    mesh.InitControlPoints(vertex_count)
    print(f"Setting {vertex_count} control points...")

    for i, vert in enumerate(srm.display_buffer.vertices):
        mesh.SetControlPointAt(fbx.FbxVector4(vert.x, vert.y, vert.z), i)

    print("Vertex data applied.")

    # Normals
    print("Adding normals...")
    layer = mesh.GetLayer(0)
    if not layer:
        mesh.CreateLayer()
        layer = mesh.GetLayer(0)

    normals_element = layer.GetNormals()
    if not normals_element:
        normals_element = mesh.CreateElementNormal()

    normals_element.SetMappingMode(fbx.FbxLayerElement.EMappingMode.eByControlPoint)
    normals_element.SetReferenceMode(fbx.FbxLayerElement.EReferenceMode.eDirect)

    def normalize_component(c):
        return (c / 255.0) * 2 - 1

    for vert in srm.display_buffer.vertices:
        nx = normalize_component(vert.normal_x)
        ny = normalize_component(vert.normal_y)
        nz = normalize_component(vert.normal_z)
        normals_element.GetDirectArray().Add(fbx.FbxVector4(nx, ny, nz))

    print("Normals applied.")

    # UVs
    print("Adding UV data with indexing reuse...")
    uv_element = layer.GetUVs()
    if not uv_element:
        uv_element = mesh.CreateElementUV("UVSet")

    uv_element.SetMappingMode(fbx.FbxLayerElement.EMappingMode.eByPolygonVertex)
    uv_element.SetReferenceMode(fbx.FbxLayerElement.EReferenceMode.eIndexToDirect)

    uv_direct_array = uv_element.GetDirectArray()
    uv_index_array = uv_element.GetIndexArray()

    uv_map = {}

    # --- MATERIAL CONSOLIDATION ---
    print("Collecting polygon material names...")

    polygon_material_names = []
    for tri in srm.display_buffer.indices:
        first_vertex_idx = tri[0]
        raw_mat_id = srm.display_buffer.vertices[first_vertex_idx].texture_index - 1
        if raw_mat_id < 0 or raw_mat_id >= len(srm.texture_palette.textures):
            print(f"Warning: Invalid material ID {raw_mat_id+1} on polygon, defaulting to 1")
            raw_mat_id = 0
        mat_name = srm.texture_palette.textures[raw_mat_id].name.strip()
        polygon_material_names.append(mat_name)

    used_material_names = []
    for name in polygon_material_names:
        if name not in used_material_names:
            used_material_names.append(name)

    print(f"Added {len(used_material_names)} consolidated materials.")

    material_name_to_index = {}
    for mat_name in used_material_names:
        mat = fbx.FbxSurfacePhong.Create(manager, mat_name)  # Using Phong per your previous fix
        mesh_node.AddMaterial(mat)
        material_name_to_index[mat_name] = len(material_name_to_index)

    print(f"Adding {len(srm.display_buffer.indices)} triangles with standard winding and UVs...")

    for poly_idx, tri in enumerate(srm.display_buffer.indices):
        mesh.BeginPolygon()
        for idx in tri:
            vert = srm.display_buffer.vertices[idx]
            u = (vert.u / 255.0) % 1.0
            v = (vert.v / 255.0) % 1.0
            key = (idx, (u, v))

            if key in uv_map:
                uv_index = uv_map[key]
            else:
                uv_vector = fbx.FbxVector2(u, 1 - v)
                uv_index = uv_direct_array.GetCount()
                uv_direct_array.Add(uv_vector)
                uv_map[key] = uv_index

            mesh.AddPolygon(idx)
            uv_index_array.Add(uv_index)
        mesh.EndPolygon()

    print("Assigning materials to polygons...")

    material_element = mesh.CreateElementMaterial()
    material_element.SetMappingMode(fbx.FbxLayerElement.EMappingMode.eByPolygon)
    material_element.SetReferenceMode(fbx.FbxLayerElement.EReferenceMode.eIndexToDirect)

    for mat_name in polygon_material_names:
        mat_index = material_name_to_index.get(mat_name, 0)
        material_element.GetIndexArray().Add(mat_index)

    print("Material assignment completed.")

    # Texture linking
    print("Linking textures to materials...")

    texture_types = {
        '_D': fbx.FbxSurfaceMaterial.sDiffuse,
        '_E': fbx.FbxSurfaceMaterial.sEmissive,
        '_S': fbx.FbxSurfaceMaterial.sSpecular,
        '_N': fbx.FbxSurfaceMaterial.sNormalMap,
    }

    textures_dir = srm_path.parent.parent / "Textures"

    for mat_name in used_material_names:
        mat = None
        for i in range(mesh_node.GetMaterialCount()):
            m = mesh_node.GetMaterial(i)
            if m.GetName() == mat_name:
                mat = m
                break
        if mat is None:
            continue

        for suffix, fbx_prop in texture_types.items():
            tex_filename = f"{mat_name}{suffix}.dds"
            tex_path = textures_dir / tex_filename
            if tex_path.exists():
                fbx_tex = fbx.FbxFileTexture.Create(manager, tex_path.stem)
                fbx_tex.SetFileName(str(tex_path))
                fbx_tex.SetSwapUV(False)
                fbx_tex.SetTranslation(0.0, 0.0)
                fbx_tex.SetScale(1.0, 1.0)
                fbx_tex.SetRotation(0.0, 0.0)
                prop = mat.FindProperty(fbx_prop)
                if prop.IsValid():
                    prop.ConnectSrcObject(fbx_tex)

    # Skeleton
    print("Creating skeleton...")
    skeleton_type_enum = getattr(fbx.FbxSkeleton.EType, 'eLimbNode', fbx.FbxSkeleton.EType.eRoot)
    skeleton_root = fbx.FbxNode.Create(manager, "RootSkeleton")
    skeleton_attr = fbx.FbxSkeleton.Create(manager, "SkeletonRoot")
    skeleton_attr.SetSkeletonType(skeleton_type_enum)
    skeleton_root.SetNodeAttribute(skeleton_attr)
    root_node.AddChild(skeleton_root)

    for i, active in enumerate(srm.bones.active_bones):
        if not active:
            continue

        bone_pos = srm.bones.bone_list[i]
        bone_name = f"Bone_{i}"

        bone_node = fbx.FbxNode.Create(manager, bone_name)
        bone_skel = fbx.FbxSkeleton.Create(manager, bone_name)
        bone_skel.SetSkeletonType(fbx.FbxSkeleton.EType.eLimbNode)
        bone_node.SetNodeAttribute(bone_skel)

        x, y, z = bone_pos
        fbx_pos = fbx.FbxDouble3(x, -z, -y)
        bone_node.LclTranslation.Set(fbx_pos)

        skeleton_root.AddChild(bone_node)

    print("Skeleton creation completed.")

    # Skinning weights & clusters
    print("Creating skinning clusters and assigning weights...")
    skin = fbx.FbxSkin.Create(manager, "Skin")
    mesh.AddDeformer(skin)

    for i, active in enumerate(srm.bones.active_bones):
        if not active:
            continue

        bone_name = f"Bone_{i}"
        bone_node = skeleton_root.FindChild(bone_name)
        if bone_node is None:
            print(f"Warning: Bone node '{bone_name}' not found for skin cluster.")
            continue

        cluster = fbx.FbxCluster.Create(manager, f"Cluster_{i}")
        cluster.SetLink(bone_node)

        for vert_index, vert in enumerate(srm.display_buffer.vertices):
            bone_ids = [vert.light_0, vert.light_1, vert.light_2]
            weights = [vert.r / 255.0, vert.g / 255.0, vert.b / 255.0]

            for bone_idx, weight in zip(bone_ids, weights):
                if bone_idx == i and weight > 0:
                    cluster.AddControlPointIndex(vert_index, weight)

        global_transform = mesh_node.EvaluateGlobalTransform()
        cluster.SetTransformMatrix(global_transform)

        global_link_transform = bone_node.EvaluateGlobalTransform()
        cluster.SetTransformLinkMatrix(global_link_transform)

        skin.AddCluster(cluster)

    print("Skinning clusters created and weights assigned.")

    print("Conversion finished successfully.")

    return scene
