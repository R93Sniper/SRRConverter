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

    # Materials
    print("Creating materials from SRM texture palette...")

    materials = []
    for texture_entry in srm.texture_palette.textures:
        mat = fbx.FbxSurfaceLambert.Create(manager, texture_entry.name)
        mat.SetName(texture_entry.name)
        materials.append(mat)
        mesh_node.AddMaterial(mat)

    # Add an invalid material for out-of-range material IDs
    invalid_material = fbx.FbxSurfaceLambert.Create(manager, "InvalidMaterial")
    invalid_material.SetName("InvalidMaterial")
    materials.append(invalid_material)
    mesh_node.AddMaterial(invalid_material)
    invalid_material_index = len(materials) - 1

    print(f"Adding {len(srm.display_buffer.indices)} triangles with standard winding, UVs, and material IDs...")

    polygon_material_indices = []

    for tri in srm.display_buffer.indices:
        mesh.BeginPolygon()

        first_vertex_idx = tri[0]
        material_id = srm.display_buffer.vertices[first_vertex_idx].texture_index

        if material_id < 0 or material_id >= len(materials):
            print(f"Warning: Invalid material ID {material_id} on triangle, defaulting to InvalidMaterial")
            material_id = invalid_material_index

        for idx in tri:  # standard winding order: 0,1,2
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
        polygon_material_indices.append(material_id)

    # Assign material IDs per polygon
    material_element = mesh.CreateElementMaterial()
    material_element.SetMappingMode(fbx.FbxLayerElement.EMappingMode.eByPolygon)
    material_element.SetReferenceMode(fbx.FbxLayerElement.EReferenceMode.eIndexToDirect)

    for mat in materials:
        material_element.GetDirectArray().Add(mat)

    for mat_id in polygon_material_indices:
        material_element.GetIndexArray().Add(mat_id)

    print("Material assignment completed.")

    # Create skeleton and bones from SRM
    print("Creating skeleton...")

    skeleton_type_enum = None
    if hasattr(fbx.FbxSkeleton.EType, 'eLimbNode'):
        skeleton_type_enum = fbx.FbxSkeleton.EType.eLimbNode
    elif hasattr(fbx.FbxSkeleton.EType, 'eLimb'):
        skeleton_type_enum = fbx.FbxSkeleton.EType.eLimb
    else:
        print("[WARN] FBX skeleton limb enum not found, defaulting to eRoot")
        skeleton_type_enum = fbx.FbxSkeleton.EType.eRoot

    # Create root skeleton node
    skeleton_root = fbx.FbxNode.Create(manager, "RootSkeleton")
    skeleton_attr = fbx.FbxSkeleton.Create(manager, "SkeletonRoot")
    skeleton_attr.SetSkeletonType(skeleton_type_enum)
    skeleton_root.SetNodeAttribute(skeleton_attr)
    root_node.AddChild(skeleton_root)

    # Create a bone node for each active bone
    for i, active in enumerate(srm.bones.active_bones):
        if not active:
            continue

        bone_pos = srm.bones.bone_list[i]
        bone_name = f"Bone_{i}"

        bone_node = fbx.FbxNode.Create(manager, bone_name)
        bone_skel = fbx.FbxSkeleton.Create(manager, bone_name)
        bone_skel.SetSkeletonType(fbx.FbxSkeleton.EType.eLimbNode)
        bone_node.SetNodeAttribute(bone_skel)

        # Set bone position relative to root
        bone_node.LclTranslation.Set(fbx.FbxDouble3(*bone_pos))

        skeleton_root.AddChild(bone_node)

    print("Skeleton creation completed.")
    print("Conversion finished successfully.")

    return scene
