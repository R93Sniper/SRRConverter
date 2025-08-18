from pathlib import Path
from Source.srm import SrmFile
import fbx

# ================================================================================================================
# SRM To FBX Converter Class
#
# This file is the "Converter" part of the pipeline. The `srm.py` file is the "Parser" parts of the pipeline.
# We convert a given SRM file to an FBX File. Optionally, we feed the output logs into a string to be converted into a debug text file.
# Because I'm petty as all hell, Everything is going to be written in PascalCase. I hate snake case.
# TODO 1: Convert this into a class with all the core data being member variables
# TODO 2: Remove OutputString and do proper logging (Notice: I didn't know this was a thing) 
# ================================================================================================================

#String for any logging statements. Just append to this so we can throw this at a file
OutputString: str = ""

#Define our Scene manager so it can get accessed throughout the code
SceneManager: fbx.FbxManager


def ConvertMatrixType(MatrixToConvert: fbx.FbxAMatrix) -> fbx.FbxMatrix:
    """
    Convert Matrix Type Function
    Converts a given aFBXMatrix to a regular FBXMatrix. Helper Function, since some python bindings don't accept AMatrixs as input.
    Also I know the plural of Matrix is Matricies but that sounds weird in context here
    """
    ConvertedMatrix = fbx.FbxMatrix()
    for row in range(4):
        for col in range(4):
            ConvertedMatrix.Set(row, col, MatrixToConvert.Get(row, col))
    return ConvertedMatrix

def ParseSRM(PathToFile: Path) -> SrmFile | None:
    """
    Parse Soul Reaver Model Function
    Given a file path, look for a SRM file there.
    If we can parse a SRM file, return it. Else return null. 
    """
    global OutputString
    OutputString += "\nParsing SRM File"
    try:
        ParsedFile = SrmFile.from_file(PathToFile)
        OutputString += "\nSRM file successfully parsed."
        return ParsedFile
    except Exception as e:
        OutputString += f"\nFailed to parse SRM file: {e}"
        return None

def InitializeScene(PathToFile: Path) -> tuple[fbx.FbxScene, fbx.FbxNode, fbx.FbxNode, fbx.FbxMesh] | None:
    """
    Initialize FBX Scene Function
    Create the Scene in our FBXManager to start building the mesh
    We return the Scene and our Mesh if we can build it. Else we return null
    """
    global SceneManager, OutputString

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
        return OurScene, SceneRoot, MeshNode, WorkingMesh
    else:
        OutputString += "\nFailed to create mesh or mesh node."
        return None
    

def CreateVertices(SourceFile: SrmFile, WorkingMesh: fbx.FbxMesh) -> fbx.FbxLayer:
    """
    Create Vertices Function
    Intialize the mesh's vertices, set their positions, and then apply their normals
    The big gotcha with this is that vertex normals are bytes, so we need to normalize them
    """
    global OutputString

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


def ProcessTriangleInfo(SourceFile: SrmFile, WorkingMesh: fbx.FbxMesh, WorkingNode: fbx.FbxNode, WorkingLayer: fbx.FbxLayer):
    """
    Process Triangle Information Function
    Apply Unwrap Data, Consolidate Materials, Create Triangles, and Assigns Materials to the triangles
    This would have otherwise been four functions but they share so much data that its not worth it.
    Luckily, we can be smart about how we write things out
    """
    global SceneManager, OutputString

    # ============================= #
    # Create UV Data                #
    # ============================= #

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
    
    # ============================= #
    # Consolidate Materials         #
    # Note: This is very fragile    #
    # ============================= #

    OutputString += "\nPreprocessing Materials for Consolidation"

    #Get all the material names that exist per polygon and toss them into a list. 
    AllMaterials = []
    for tri in SourceFile.display_buffer.indices:
        MaterialId = SourceFile.display_buffer.vertices[tri[0]].texture_index - 1
        if MaterialId < 0 or MaterialId >= len(SourceFile.texture_palette.textures):
            OutputString += f"\nMaterial ID for {MaterialId+1} is Out of Range. Defaulting to 1"
            MaterialId = 0
        MatName = SourceFile.texture_palette.textures[MaterialId].name.strip()
        AllMaterials.append(MatName)

    #Build a list of all the UNIQUE material names in the order they appear 
    UniqueMaterials = []
    for name in AllMaterials:
        if name not in UniqueMaterials:
            UniqueMaterials.append(name)

    OutputString += f"\nModel has {len(UniqueMaterials)} unique materials."

    #Create a map of the unique materials and their indices. Create a phong material per unique mat 
    MaterialMap = {}
    for MatName in UniqueMaterials:
        mat = fbx.FbxSurfacePhong.Create(SceneManager, MatName)
        WorkingNode.AddMaterial(mat)
        MaterialMap[MatName] = len(MaterialMap)

    # ============================= #
    # Create Triangles              #
    # ============================= #

    OutputString += f"\nAttempting to create {len(SourceFile.display_buffer.indices)} Triangles"

    #Go through every triangle in the source file and create a polygon for it.
    for i, tri in enumerate(SourceFile.display_buffer.indices):
        WorkingMesh.BeginPolygon()
        
        #Every vertex in the created triangle
        for j in tri:
            vert = SourceFile.display_buffer.vertices[j]
            u = vert.u / 255.0
            v = vert.v / 255.0
           
            #Create a unique UV location per vertex. Prevents seam errors
            key = (j, (u, v))
            if key in UnwrapMap:
                uv_index = UnwrapMap[key]
            else:
                uv_vector = fbx.FbxVector2(u, 1 - v)
                uv_index = UnwrapArrayDirect.GetCount()
                UnwrapArrayDirect.Add(uv_vector)
                UnwrapMap[key] = uv_index

            #Map the triangle to the correct UV index
            WorkingMesh.AddPolygon(j)
            UnwrapArrayIndexed.Add(uv_index)
        WorkingMesh.EndPolygon()

    # ============================= #
    # Assign Materials              #
    # ============================= #
    
    OutputString += "\nTriangles Created, assigning materials."

    #Create a new layer for our materials and make it so we can have a multi-material
    MaterialLayer = WorkingMesh.CreateElementMaterial()
    MaterialLayer.SetMappingMode(fbx.FbxLayerElement.EMappingMode.eByPolygon)
    MaterialLayer.SetReferenceMode(fbx.FbxLayerElement.EReferenceMode.eIndexToDirect)

    #Actually assign the materials to each triangle
    for MatName in AllMaterials:
        MatIndex = MaterialMap.get(MatName, 0)
        MaterialLayer.GetIndexArray().Add(MatIndex)

    OutputString += "\nMaterials assigned successfully."

"""
# ================================================================================================================
# Link Textures to Materials Function
# TODO: This section is incomplete and unused. Cannot figure out why it doesn't work.
# TODO: This is directly ported from the old Converter. Clean it up to be less vibe-coded
# ================================================================================================================
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
        for i in range(SceneNode.GetMaterialCount()):
            m = SceneNode.GetMaterial(i)
            if m.GetName() == mat_name:
                mat = m
                break
        if mat is None:
            continue

        for suffix, fbx_prop in texture_types.items():
            tex_filename = f"{mat_name}{suffix}.dds"
            tex_path = textures_dir / tex_filename
            if tex_path.exists():
                fbx_tex = fbx.FbxFileTexture.Create(SceneManager, tex_path.stem)
                fbx_tex.SetFileName(str(tex_path))
                fbx_tex.SetSwapUV(False)
                fbx_tex.SetTranslation(0.0, 0.0)
                fbx_tex.SetScale(1.0, 1.0)
                fbx_tex.SetRotation(0.0, 0.0)
                prop = mat.FindProperty(fbx_prop)
                if prop.IsValid():
                    prop.ConnectSrcObject(fbx_tex)
"""


def CreateSkeleton(SourceFile: SrmFile, WorkingRoot: fbx.FbxScene) -> dict[int, fbx.FbxNode]:
    """
    Create Skeleton Function
    Create a Root skeleton node and then only add bones that actually have skinning data.
    Currently parents everything to the root. SRM files don't seem to store the heirarchy information at all.
    TODO: Read Zata's YAML file system to build the heirarchy.
    """
    global SceneManager, OutputString

    OutputString += "\nCreating Skeleton"
    
    #Create the root skeleton node and assign its attributes
    SkeletonType = getattr(fbx.FbxSkeleton.EType, 'eLimbNode', fbx.FbxSkeleton.EType.eRoot)
    SkeletonRoot = fbx.FbxNode.Create(SceneManager, "RootSkeleton")
    RootType = fbx.FbxSkeleton.Create(SceneManager, "SkeletonRoot")
    RootType.SetSkeletonType(SkeletonType)
    SkeletonRoot.SetNodeAttribute(RootType)
    WorkingRoot.AddChild(SkeletonRoot)

    #Create a Map of the bones to their indices.
    NodeMap = {}
    SkippedBones = 0

    #Loop through every bone in the srm file
    for i, (active, BonePos) in enumerate(zip(SourceFile.bones.active_bones, SourceFile.bones.bone_list)):
        if not active:
            SkippedBones += 1 #Increment skip counter for correct indexing offset
            continue

        #Set the bone name based on its index from the list
        BonePos = SourceFile.bones.bone_list[i]
        BoneName = f"Bone_{i:03}"

        #Create the node and set its attributes
        BoneNode = fbx.FbxNode.Create(SceneManager, BoneName)
        MainSkel = fbx.FbxSkeleton.Create(SceneManager, BoneName)
        MainSkel.SetSkeletonType(fbx.FbxSkeleton.EType.eLimbNode)
        BoneNode.SetNodeAttribute(MainSkel)

        #Convert Coordinate Space. FBX = Y-Up/Right-Handed. SRM = Z-Up/Left-Handed.
        x, y, z = BonePos
        fbx_pos = fbx.FbxDouble3(-x, -z, -y)
        BoneNode.LclTranslation.Set(fbx_pos)

        #Make the bone a child of the root bone and index it for skinning later
        SkeletonRoot.AddChild(BoneNode)
        NodeMap[i-SkippedBones] = BoneNode
    
    OutputString += f"\nSkeleton successfully created with {SkippedBones} null bones skipped"
    return NodeMap


def SkinMesh(SourceFile: SrmFile, WorkingScene: fbx.FbxScene, WorkingMesh: fbx.FbxMesh, WorkingNode: fbx.FbxNode, NodeMap: dict[int, fbx.FbxNode]):
    """
    Skin Mesh Function
    Take the mesh and apply weights based on information from SRM file. Add the bind pose once mesh is skinned.
    For skinned meshes, weight information is actually handled in the vertex color attributes. Must have been an efficiency measure from Crystal Dynamics that Aspyr used
    This information is more readily present once you look at the shader. Level Geometry uses a different shader and uses the information for other purposes
    """
    global SceneManager, OutputString

    OutputString += "\nBeginning skinning process. Adding Skin Clusters"
    
    #Create the Skin Deformer. It's not actually a layer but it follows our earlier naming convention.
    SkinLayer = fbx.FbxSkin.Create(SceneManager, "Skin")
    WorkingMesh.AddDeformer(SkinLayer)

    #Make a cluster for each bone
    SkinClusterMap = {}
    for BoneIndex, BoneNode in NodeMap.items():
        Cluster = fbx.FbxCluster.Create(SceneManager, f"Cluster_{BoneIndex}")
        Cluster.SetLink(BoneNode)
        SkinClusterMap[BoneIndex] = Cluster

    #Assign Vertices to each bone cluster
    for vert_index, vert in enumerate(SourceFile.display_buffer.vertices):
        #Bone Influence Index dictated by light attribute. Weights by color components
        bone_ids = [vert.light_0, vert.light_1, vert.light_2]
        weights = [vert.r / 255.0, vert.g / 255.0, vert.b / 255.0] #Normalize weights 

        #Apply weight to vertex (assuming non-zero)
        for BoneIndex, weight in zip(bone_ids, weights):
            if weight > 0 and BoneIndex in SkinClusterMap:
                SkinClusterMap[BoneIndex].AddControlPointIndex(vert_index, weight)

    OutputString += "\nSkin Clusters added and weights assigned. Attaching weights to skin"

    #Set the bind matrix and add each cluster to the skin
    BindMatrix = WorkingNode.EvaluateGlobalTransform()
    for BoneIndex, Cluster in SkinClusterMap.items():
        BoneNode = NodeMap[BoneIndex]
        Cluster.SetTransformMatrix(BindMatrix)
        Cluster.SetTransformLinkMatrix(BoneNode.EvaluateGlobalTransform())
        SkinLayer.AddCluster(Cluster)

    # ============================= #
    # Add Bind Pose                 #
    # ============================= #

    OutputString += "\nCreating Bind Pose for Mesh"
    
    #Create a new bind pose and add mesh to it
    BindPose = fbx.FbxPose.Create(WorkingScene, "BindPose")
    BindPose.SetIsBindPose(True)
    BindPose.Add(WorkingNode, ConvertMatrixType(BindMatrix))
    
    #Add each bone and its transform to the bind pose
    for BoneNode in NodeMap.values():
        BindPose.Add(BoneNode, ConvertMatrixType(BoneNode.EvaluateGlobalTransform()))
    
    #Assign bind pose
    WorkingScene.AddPose(BindPose)

    OutputString += "\nBind Pose assigned, Skinning complete."


def SrmToFBX(ReaverFilePath: Path, FileManager: fbx.FbxManager, GiveOutput: bool) -> tuple[fbx.FbxScene | None, str]:
    """
    SRM To FBX Function
    Main function to actually convert files
    We need a path to the file and the FBX Scene Manager to process the data
    Returns an FBX Scene on success, null on failure
    Optionally returns the Output String
    """
    global SceneManager, OutputString 
    SceneManager = FileManager
    OutputString = "Beginning Conversion of SRM File"

    #Get our File and put it into a Variable
    OurFile = ParseSRM(ReaverFilePath)
    if OurFile is None:
        return None, OutputString
    
    #Initialize the FBX Scene and retrieve the Scene Root and Mesh 
    TheScene = InitializeScene(ReaverFilePath)
    if TheScene is not None:
        OurScene, OurSceneRoot, SceneNode, SceneMesh = TheScene
    else:
        return None, OutputString
    
    #Create Vertices on the Mesh
    OurMeshLayer = CreateVertices(OurFile,SceneMesh)

    #Create triangles, add their UVs and materials
    ProcessTriangleInfo(OurFile,SceneMesh,SceneNode,OurMeshLayer)

    #Create the Skeleton
    BoneNodeMap = CreateSkeleton(OurFile,OurSceneRoot)
    if not BoneNodeMap:
        OutputString += "\nCouldn't find any bones"
        return None, OutputString

    #Skin the mesh and add its bind pose
    SkinMesh(OurFile,OurScene,SceneMesh,SceneNode,BoneNodeMap)

    #We have our new FBX File!
    if GiveOutput:
        return OurScene, OutputString
    else:
        return OurScene, None