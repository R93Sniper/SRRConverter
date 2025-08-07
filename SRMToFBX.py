from pathlib import Path
from Source.srm import SrmFile
import fbx

'''
SRM To FBX Converter

This file is the "Converter" part of the pipeline. The files in the Source\ folder are the "Parser" parts of the pipeline.
We convert a given SRM file to an FBX File. Optionally, we feed the output logs into a string to be converted into a debug text file.
Because I'm petty as all hell, Everything is going to be written in PascalCase. I hate snake case. 
'''

#String for any logging statements. Just append to this so we can throw this at a file
OutputString = "Beginning Conversion of SRM File"

#Technically we don't need this because Python doesn't have truly private variables but I'm too hardcoded for this
def RetrieveOutputLog() -> str:
    return OutputString

"""
Convert Matrix Type
Converts a given aFBXMatrix to a regular FBXMatrix. Helper Function, since some python bindings don't accept AMatrixs as input.
Also I know the plural of Matrix is Matricies but that sounds weird to type here
"""
def ConvertMatrixType(MatrixToConvert: fbx.FbxAMatrix) -> fbx.FbxMatrix:
    ConvertedMatrix = fbx.FbxMatrix()
    for row in range(4):
        for col in range(4):
            ConvertedMatrix.Set(row, col, MatrixToConvert.Get(row, col))
    return ConvertedMatrix

"""
Parse Soul Reaver Model
Given a file path, look for a SRM file there.
If we can parse a SRM file, return it. Else return null.  
"""
def ParseSRM(PathToFile: Path) -> SrmFile | None:
    OutputString += "\nParsing SRM File"
    try:
        ParsedFile = SrmFile.from_file(PathToFile)
        OutputString += "\nSRM file successfully parsed."
        return ParsedFile
    except Exception as e:
        OutputString += f"\nFailed to parse SRM file: {e}"
        return None

"""
Initialize FBX Scene
Create the Scene in our FBXManager to start building the mesh
We return the Scene and our Mesh if we can build it. Else we return null
"""
def InitializeScene(PathToFile: Path, SceneManager: fbx.FbxManager) -> tuple[fbx.FbxScene, fbx.FbxNode, fbx.FbxMesh] | None:
    OurScene = fbx.FbxScene.Create(SceneManager, PathToFile.stem)
    
    #Validate our Scene so we don't work with malformed data.
    if OurScene:
        OutputString += "\nSuccessfully created FBX Scene"
    else:
        OutputString += "\nFailed to create FBX scene."
        return None
    
    #Get our scene root, create our mesh and to the root
    SceneRoot = OurScene.GetRootNode()
    MeshNode = fbx.FbxNode.Create(SceneManager, PathToFile.stem)
    WorkingMesh = fbx.FbxMesh.Create(SceneManager, "Mesh")

    #Validate that our mesh was created
    if WorkingMesh and MeshNode:
        MeshNode.SetNodeAttribute(WorkingMesh)
        SceneRoot.AddChild(MeshNode)
        OutputString += "\nMesh Created succesfully"
        return SceneRoot, MeshNode, WorkingMesh
    else:
        OutputString += "\nFailed to create mesh or mesh node."
        return None
    
        
"""
Create Vertices
Intialize the mesh's vertices, set their positions, and then apply their normals
The big gotcha with this is that vertex normals are bytes, so we need to normalize them
"""
def CreateVertices(SourceFile: SrmFile, WorkingMesh: fbx.FbxMesh) -> fbx.FbxLayer:
    
    #Initialize Vertex Array
    VertexCount = len(SourceFile.display_buffer.vertices)
    WorkingMesh.InitControlPoints(VertexCount)

    #Apply positions to each vertex. FBX requires this to be a Vector4 for some reason
    for i, vert in enumerate(SourceFile.display_buffer.vertices):
        WorkingMesh.SetControlPointAt(fbx.FbxVector4(vert.x, vert.y, vert.z), i)

    #Report back that the vertices have been created, in the event of a failure past this
    OutputString += "\nCreated Vertices. Processing Vertex Normals."

    #Create a Layer for the mesh so we can begin to apply the normals
    MeshLayer = WorkingMesh.GetLayer(0)
    if not MeshLayer:
        WorkingMesh.CreateLayer()
        MeshLayer = WorkingMesh.GetLayer(0)

    #Create Element Normals they don't already exist on this layer
    VertexNormals = MeshLayer.GetNormals()
    if not VertexNormals:
        VertexNormals = WorkingMesh.CreateElementNormal()

    VertexNormals.SetMappingMode(fbx.FbxLayerElement.EMappingMode.eByControlPoint) #One Normal Per Vert
    VertexNormals.SetReferenceMode(fbx.FbxLayerElement.EReferenceMode.eDirect) #Ordered Data

    #Normalize our Vertex Normals and apply them
    for vert in SourceFile.display_buffer.vertices:
        CompNormalX = (vert.normal_x / 255.0) * 2 - 1
        CompNormalY = (vert.normal_y / 255.0) * 2 - 1
        CompNormalZ = (vert.normal_z / 255.0) * 2 - 1
        VertexNormals.GetDirectArray().Add(fbx.FbxVector4(CompNormalX, CompNormalY, CompNormalZ))

    OutputString += "\nNormal Data applied to Vertices"
    return MeshLayer


# Vibe Coding past this point. Beware hallucinations and weirdly named variables.
"""
Process Triangle Information
Apply Unwrap Data, Consolidate Materials, Create Triangles, and Assigns Materials to the triangles
This would have otherwise been four functions but they share so much data that its not worth it.
Luckily, we can be smart about how we write things out
"""
def ProcessTriangleInfo(SourceFile: SrmFile, SceneManager: fbx.FbxManager,WorkingMesh: fbx.FbxMesh, WorkingNode: fbx.FbxNode, WorkingLayer: fbx.FbxLayer):
    
    OutputString += "\nBeginning UV Processing"

    #Create a new layer for UVs
    UnwrapLayer = WorkingLayer.GetUVs()
    if not UnwrapLayer:
        UnwrapLayer = WorkingMesh.CreateElementUV("UVSet")

    #One UV Coordinate per vertex
    UnwrapLayer.SetMappingMode(fbx.FbxLayerElement.EMappingMode.eByPolygonVertex) 
    # Store UVs in a direct array, vertices can access the direct array through an Index array 
    UnwrapLayer.SetReferenceMode(fbx.FbxLayerElement.EReferenceMode.eIndexToDirect) 

    #Store the two arrays so we can access them later
    UnwrapArrayDirect = UnwrapLayer.GetDirectArray()
    UnwrapArrayIndexed = UnwrapLayer.GetIndexArray()

    UnwrapMap = {}

    """Consolidate Materials"""

    print("Collecting polygon material names...")

    polygon_material_names = []
    for tri in SourceFile.display_buffer.indices:
        raw_mat_id = SourceFile.display_buffer.vertices[tri[0]].texture_index - 1
        if raw_mat_id < 0 or raw_mat_id >= len(SourceFile.texture_palette.textures):
            print(f"Warning: Invalid material ID {raw_mat_id+1} on polygon, defaulting to 1")
            raw_mat_id = 0
        mat_name = SourceFile.texture_palette.textures[raw_mat_id].name.strip()
        polygon_material_names.append(mat_name)

    used_material_names = []
    for name in polygon_material_names:
        if name not in used_material_names:
            used_material_names.append(name)

    print(f"Added {len(used_material_names)} consolidated materials.")

    material_name_to_index = {}
    for mat_name in used_material_names:
        mat = fbx.FbxSurfacePhong.Create(SceneManager, mat_name)
        WorkingNode.AddMaterial(mat)
        material_name_to_index[mat_name] = len(material_name_to_index)

    """Create Tiangles"""

    print(f"Adding {len(SourceFile.display_buffer.indices)} triangles with standard winding and UVs...")

    for poly_idx, tri in enumerate(SourceFile.display_buffer.indices):
        WorkingMesh.BeginPolygon()
        for idx in tri:
            vert = SourceFile.display_buffer.vertices[idx]
            u = (vert.u / 255.0) % 1.0
            v = (vert.v / 255.0) % 1.0
            key = (idx, (u, v))

            if key in UnwrapMap:
                uv_index = UnwrapMap[key]
            else:
                uv_vector = fbx.FbxVector2(u, 1 - v)
                uv_index = UnwrapArrayDirect.GetCount()
                UnwrapArrayDirect.Add(uv_vector)
                UnwrapMap[key] = uv_index

            WorkingMesh.AddPolygon(idx)
            UnwrapArrayIndexed.Add(uv_index)
        WorkingMesh.EndPolygon()


    """Assign Materials"""
    print("Assigning materials to polygons...")

    material_element = WorkingMesh.CreateElementMaterial()
    material_element.SetMappingMode(fbx.FbxLayerElement.EMappingMode.eByPolygon)
    material_element.SetReferenceMode(fbx.FbxLayerElement.EReferenceMode.eIndexToDirect)

    for mat_name in polygon_material_names:
        mat_index = material_name_to_index.get(mat_name, 0)
        material_element.GetIndexArray().Add(mat_index)

    print("Material assignment completed.")

"""
Link Textures to Materials
"""
def LinkTexturesToMaterials():
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



"""
Create Skeleton
"""
def CreateSkeleton():
    # Skeleton
    print("Creating skeleton...")
    skeleton_type_enum = getattr(fbx.FbxSkeleton.EType, 'eLimbNode', fbx.FbxSkeleton.EType.eRoot)
    skeleton_root = fbx.FbxNode.Create(manager, "RootSkeleton")
    skeleton_attr = fbx.FbxSkeleton.Create(manager, "SkeletonRoot")
    skeleton_attr.SetSkeletonType(skeleton_type_enum)
    skeleton_root.SetNodeAttribute(skeleton_attr)
    root_node.AddChild(skeleton_root)

    bone_node_map = {}
    skipped_bones = 0

    for i, (active, bone_pos) in enumerate(zip(srm.bones.active_bones, srm.bones.bone_list)):
        if not active:
            skipped_bones += 1
            continue

        bone_pos = srm.bones.bone_list[i]
        bone_name = f"Bone_{i:03}"

        bone_node = fbx.FbxNode.Create(manager, bone_name)
        bone_skel = fbx.FbxSkeleton.Create(manager, bone_name)
        bone_skel.SetSkeletonType(fbx.FbxSkeleton.EType.eLimbNode)
        bone_node.SetNodeAttribute(bone_skel)

        x, y, z = bone_pos
        fbx_pos = fbx.FbxDouble3(-x, -z, -y)
        bone_node.LclTranslation.Set(fbx_pos)

        skeleton_root.AddChild(bone_node)
        bone_node_map[i-skipped_bones] = bone_node

    print(f"We skipped {skipped_bones} bones")
    print("Skeleton creation completed.")

"""
Skin Mesh
"""
def SkinMesh():
        # Skinning weights & clusters
    print("Creating skinning clusters and assigning weights...")
    skin = fbx.FbxSkin.Create(manager, "Skin")
    mesh.AddDeformer(skin)

    bone_clusters = {}
    for bone_idx, bone_node in bone_node_map.items():
        cluster = fbx.FbxCluster.Create(manager, f"Cluster_{bone_idx}")
        cluster.SetLink(bone_node)
        bone_clusters[bone_idx] = cluster


    for vert_index, vert in enumerate(srm.display_buffer.vertices):
        bone_ids = [vert.light_0, vert.light_1, vert.light_2]
        weights = [vert.r / 255.0, vert.g / 255.0, vert.b / 255.0]

        for bone_idx, weight in zip(bone_ids, weights):
            if weight > 0 and bone_idx in bone_clusters:
                bone_clusters[bone_idx].AddControlPointIndex(vert_index, weight)

    
    mesh_transform = mesh_node.EvaluateGlobalTransform()
    for bone_idx, cluster in bone_clusters.items():
        bone_node = bone_node_map[bone_idx]
        cluster.SetTransformMatrix(mesh_transform)
        cluster.SetTransformLinkMatrix(bone_node.EvaluateGlobalTransform())
        skin.AddCluster(cluster)

"""
Add Bind Pose
"""
def AddBindPose():
    # Add bind pose
    print("Adding bind pose...")
    pose = fbx.FbxPose.Create(scene, "BindPose")
    pose.SetIsBindPose(True)

    pose.Add(mesh_node, amatrix_to_fbxmatrix(mesh_transform))
    for bone_node in bone_node_map.values():
        pose.Add(bone_node, amatrix_to_fbxmatrix(bone_node.EvaluateGlobalTransform()))
    scene.AddPose(pose)

    print("Skinning clusters created and weights assigned.")


"""
SRM To FBX
"""
def SrmToFBX(ReaverFilePath: Path, FileManager: fbx.FBXManager) -> fbx.FbxScene | None:
    
    #Get our File and put it into a Variable
    OurFile = ParseSRM(ReaverFilePath)
    if OurFile is None:
        return None
    
    #Initialize the FBX Scene and retrieve the Scene Root and Mesh 
    TheScene = InitializeScene(ReaverFilePath, FileManager)
    if TheScene is not None:
        OurSceneRoot, SceneNode, SceneMesh = TheScene
    else:
        return None
    
    #Create Vertices on the Mesh
    OurMeshLayer = CreateVertices(OurFile,SceneMesh)

    #Add the UV Data 

    #Consolidate Materials to prevent duplicates

    #Create the triangles for the mesh

    #Apply The Materials to the triangles

    #Create the Skeleton

    #Bind the Mesh to the Skeleton and Apply Weights

    #Add the Bind Pose for the Mesh

    #We have our new FBX File!