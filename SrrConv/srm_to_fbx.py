from pathlib import Path

try:
    import fbx
except:
    print("Failed to load the FBX library. Please download the 'FBX Python SDK' from: https://aps.autodesk.com/developer/overview/fbx-sdk")

# ================================================================================================================
# TODO 1: Convert this into a class with all the core data being member variables
# TODO 2: Remove OutputString and do proper logging (Notice: I didn't know this was a thing) 
# ================================================================================================================

class FbxConverter:

    def __init__(self):
        #String for any logging statements. Just append to this so we can throw this at a file
        self.OutputString: str = ""

        #Define common variables that get used throughout the code
        self.SceneManager: fbx.FbxManager = None        # FBX Scene manager 
        self.PathToFile: Path                           # Path to the SRM File
        self.SourceFile: SrmFile = None                 # The actual SRM file that gets parsed
        self.OurScene: fbx.FbxScene = None              # The "Scene" that is created for our FBX
        self.RootNode: fbx.FbxNode = None               # The object that defines the origin of the scene
        self.MeshNode: fbx.FbxNode = None               #
        self.MeshLayer: fbx.FbxLayer = None             # The layers of the mesh. Needed for different elements (ie vertex normals)
        self.WorkingMesh: fbx.FbxMesh = None            # The actual mesh we're creating and working on
        self.NodeMap: dict[int, fbx.FbxNode] = {}       # Mapping the Index of the bones to their FBX node. Required for skinning 


    @staticmethod
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


    def ParseSRM(self):
        """
        Parse Soul Reaver Model Function
        Given a file path, look for a SRM file there.
        If we can parse a SRM file, return it. Else return null. 
        """
        self.OutputString += "\nParsing SRM File"
        try:
            self.SourceFile = SrmFile.from_file(self.PathToFile)
            self.OutputString += "\nSRM file successfully parsed."
        except Exception as e:
            self.OutputString += f"\nFailed to parse SRM file: {e}"
            return None


    def InitializeScene(self):
        """
        Initialize FBX Scene Function
        Create the Scene in our FBXManager to start building the mesh
        We return the Scene and our Mesh if we can build it. Else we return null
        """

        self.OurScene = fbx.FbxScene.Create(self.SceneManager, self.PathToFile.stem)
        
        #Validate our Scene so we don't work with malformed data.
        if self.OurScene:
            self.OutputString += "\nSuccessfully created FBX Scene"
        else:
            self.OutputString += "\nFailed to create FBX scene."
            return None
        
        #Get our scene root, create our mesh and to the root
        self.RootNode = self.OurScene.GetRootNode()
        self.MeshNode = fbx.FbxNode.Create(self.SceneManager, self.PathToFile.stem)
        self.WorkingMesh = fbx.FbxMesh.Create(self.SceneManager, "Mesh")

        #Validate that our mesh was created
        if self.WorkingMesh and self.MeshNode:
            self.MeshNode.SetNodeAttribute(self.WorkingMesh)
            self.RootNode.AddChild(self.MeshNode)
            self.OutputString += "\nMesh Created succesfully"
        else:
            self.OutputString += "\nFailed to create mesh or mesh node."
            return None
        

    def CreateVertices(self):
        """
        Create Vertices Function
        Intialize the mesh's vertices, set their positions, and then apply their normals
        The big gotcha with this is that vertex normals are bytes, so we need to normalize them
        """

        #Initialize Vertex Array
        VertexCount = len(self.SourceFile.display_buffer.vertices)
        self.WorkingMesh.InitControlPoints(VertexCount)

        #Apply positions to each vertex. FBX requires this to be a Vector4 for some reason
        for i, vert in enumerate(self.SourceFile.display_buffer.vertices):
            self.WorkingMesh.SetControlPointAt(fbx.FbxVector4(vert.x, vert.y, vert.z), i)

        #Report back that the vertices have been created, in the event of a failure past this
        self.OutputString += "\nCreated Vertices. Processing Vertex Normals."

        #Create a Layer for the mesh so we can begin to apply the normals
        self.MeshLayer = self.WorkingMesh.GetLayer(0)
        if not self.MeshLayer:
            self.WorkingMesh.CreateLayer()
            self.MeshLayer = self.WorkingMesh.GetLayer(0)

        #Create Element Normals they don't already exist on this layer
        VertexNormals = self.MeshLayer.GetNormals()
        if not VertexNormals:
            VertexNormals = self.WorkingMesh.CreateElementNormal()

        VertexNormals.SetMappingMode(fbx.FbxLayerElement.EMappingMode.eByControlPoint) #One Normal Per Vert
        VertexNormals.SetReferenceMode(fbx.FbxLayerElement.EReferenceMode.eDirect) #Ordered Data

        #Normalize our Vertex Normals and apply them
        for vert in self.SourceFile.display_buffer.vertices:
            normal = fbx.FbxVector4(vert.normal_x, vert.normal_y, vert.normal_z)
            normal.Normalize()
            VertexNormals.GetDirectArray().Add(normal)

        self.OutputString += "\nNormal Data applied to Vertices"


    def ProcessMaterials(self, texture_format):
        texture_converter = TextureConverter()
        for Material in self.SourceFile.material_palette.materials:
            mat = fbx.FbxSurfacePhong.Create(self.SceneManager, Material.name)
            for texture in Material.get_texture_suffixes():
                try:
                    converted_tex = f"Output/Textures/{texture.upper()}.{texture_converter.format.upper()}"
                    texture_converter.convertTexture(
                        f"Input/Textures/{texture.upper()}.DDS", 
                        converted_tex,texture_format
                    )
                    fbx_tex = fbx.FbxFileTexture.Create(self.SceneManager, texture)
                    fbx_tex.SetFileName(str(converted_tex))
                    if "_D" in texture:
                        mat.Diffuse.ConnectSrcObject(fbx_tex)
                    if "_S" in texture:
                        mat.Specular.ConnectSrcObject(fbx_tex)
                    if "_E" in texture:
                        mat.Emissive.ConnectSrcObject(fbx_tex)
                    if "_N" in texture:
                        mat.NormalMap.ConnectSrcObject(fbx_tex)
                except Exception as e:
                    print(f"failed to parse texture {texture} - Reason {e}")
            self.MeshNode.AddMaterial(mat)


    def ProcessTriangleInfo(self):
        """
        Process Triangle Information Function
        Apply Unwrap Data, Consolidate Materials, Create Triangles, and Assigns Materials to the triangles
        This would have otherwise been four functions but they share so much data that its not worth it.
        Luckily, we can be smart about how we write things out
        """

        # ============================= #
        # Create UV Data                #
        # ============================= #

        self.OutputString += "\nBeginning UV Processing"

        #Create a new layer for UVs
        UnwrapLayer = self.MeshLayer.GetUVs()
        if not UnwrapLayer:
            UnwrapLayer = self.WorkingMesh.CreateElementUV("UVSet")

        #One UV Coordinate per vertex
        UnwrapLayer.SetMappingMode(fbx.FbxLayerElement.EMappingMode.eByPolygonVertex) 
        # Store UVs in a direct array, vertices can access the direct array through an Index array 
        UnwrapLayer.SetReferenceMode(fbx.FbxLayerElement.EReferenceMode.eIndexToDirect) 

        #Store the two arrays so we can access them later
        UnwrapArrayDirect = UnwrapLayer.GetDirectArray()
        UnwrapArrayIndexed = UnwrapLayer.GetIndexArray()

        UnwrapMap = {}
        
        self.ProcessMaterials("PNG")

        # ============================= #
        # Create Triangles              #
        # ============================= #

        self.OutputString += f"\nAttempting to create {len(self.SourceFile.display_buffer.indices)} Triangles"

        MaterialLayer = self.WorkingMesh.CreateElementMaterial()
        MaterialLayer.SetMappingMode(fbx.FbxLayerElement.EMappingMode.eByPolygon)
        MaterialLayer.SetReferenceMode(fbx.FbxLayerElement.EReferenceMode.eIndexToDirect)

        #Go through every triangle in the source file and create a polygon for it.
        for i, tri in enumerate(self.SourceFile.display_buffer.indices):
            self.WorkingMesh.BeginPolygon(self.SourceFile.display_buffer.vertices[tri[0]].texture_index - 1)
            
            #Every vertex in the created triangle
            for j in tri:
                vert = self.SourceFile.display_buffer.vertices[j]
                u = vert.u / 255.0
                v = vert.v / 255.0
            
                #Create a unique UV location per vertex. Prevents seam errors
                key = (j, (u, v))
                if key in UnwrapMap:
                    uv_index = UnwrapMap[key]
                else:
                    uv_vector = fbx.FbxVector2(u, 1-v)
                    uv_index = UnwrapArrayDirect.GetCount()
                    UnwrapArrayDirect.Add(uv_vector)
                    UnwrapMap[key] = uv_index

                #Map the triangle to the correct UV index
                self.WorkingMesh.AddPolygon(j)
                UnwrapArrayIndexed.Add(uv_index)
            self.WorkingMesh.EndPolygon()


    def CreateSkeleton(self):
        """
        Create Skeleton Function
        Create a Root skeleton node and then only add bones that actually have skinning data.
        Currently parents everything to the root. SRM files don't seem to store the heirarchy information at all.
        TODO: Read Zata's YAML file system to build the heirarchy.
        """

        self.OutputString += "\nCreating Skeleton"
        
        #Create the root skeleton node and assign its attributes
        SkeletonType = getattr(fbx.FbxSkeleton.EType, 'eLimbNode', fbx.FbxSkeleton.EType.eRoot)
        SkeletonRoot = fbx.FbxNode.Create(self.SceneManager, "RootSkeleton")
        RootType = fbx.FbxSkeleton.Create(self.SceneManager, "SkeletonRoot")
        RootType.SetSkeletonType(SkeletonType)
        SkeletonRoot.SetNodeAttribute(RootType)
        self.RootNode.AddChild(SkeletonRoot)

        #Create a Map of the bones to their indices.
        SkippedBones = 0

        #Loop through every bone in the srm file
        for i, (active, BonePos) in enumerate(zip(self.SourceFile.bones.active_bones, self.SourceFile.bones.bone_list)):
            if not active:
                SkippedBones += 1 #Increment skip counter for correct indexing offset
                continue

            #Set the bone name based on its index from the list
            BonePos = self.SourceFile.bones.bone_list[i]
            BoneName = f"Bone_{i:03}"

            #Create the node and set its attributes
            BoneNode = fbx.FbxNode.Create(self.SceneManager, BoneName)
            MainSkel = fbx.FbxSkeleton.Create(self.SceneManager, BoneName)
            MainSkel.SetSkeletonType(fbx.FbxSkeleton.EType.eLimbNode)
            BoneNode.SetNodeAttribute(MainSkel)

            #Convert Coordinate Space. FBX = Y-Up/Right-Handed. SRM = Z-Up/Left-Handed.
            x, y, z = BonePos
            fbx_pos = fbx.FbxDouble3(-x, -z, -y)
            BoneNode.LclTranslation.Set(fbx_pos)

            #Make the bone a child of the root bone and index it for skinning later
            SkeletonRoot.AddChild(BoneNode)
            self.NodeMap[i-SkippedBones] = BoneNode
        
        self.OutputString += f"\nSkeleton successfully created with {SkippedBones} null bones skipped"


    def SkinMesh(self):
        """
        Skin Mesh Function
        Take the mesh and apply weights based on information from SRM file. Add the bind pose once mesh is skinned.
        For skinned meshes, weight information is actually handled in the vertex color attributes. Must have been an efficiency measure from Crystal Dynamics that Aspyr used
        This information is more readily present once you look at the shader. Level Geometry uses a different shader and uses the information for other purposes
        """

        self.OutputString += "\nBeginning skinning process. Adding Skin Clusters"
        
        #Create the Skin Deformer. It's not actually a layer but it follows our earlier naming convention.
        SkinLayer = fbx.FbxSkin.Create(self.SceneManager, "Skin")
        self.WorkingMesh.AddDeformer(SkinLayer)

        #Make a cluster for each bone
        SkinClusterMap = {}
        for BoneIndex, BoneNode in self.NodeMap.items():
            Cluster = fbx.FbxCluster.Create(self.SceneManager, f"Cluster_{BoneIndex}")
            Cluster.SetLink(BoneNode)
            SkinClusterMap[BoneIndex] = Cluster

        #Assign Vertices to each bone cluster
        for vert_index, vert in enumerate(self.SourceFile.display_buffer.vertices):
            #Bone Influence Index dictated by light attribute. Weights by color components
            bone_ids = [vert.light_0, vert.light_1, vert.light_2]
            weights = [vert.r / 255.0, vert.g / 255.0, vert.b / 255.0] #Normalize weights 

            #Apply weight to vertex (assuming non-zero)
            for BoneIndex, weight in zip(bone_ids, weights):
                if weight > 0 and BoneIndex in SkinClusterMap:
                    SkinClusterMap[BoneIndex].AddControlPointIndex(vert_index, weight)

        self.OutputString += "\nSkin Clusters added and weights assigned. Attaching weights to skin"

        #Set the bind matrix and add each cluster to the skin
        BindMatrix = self.MeshNode.EvaluateGlobalTransform()
        for BoneIndex, Cluster in SkinClusterMap.items():
            BoneNode = self.NodeMap[BoneIndex]
            Cluster.SetTransformMatrix(BindMatrix)
            Cluster.SetTransformLinkMatrix(BoneNode.EvaluateGlobalTransform())
            SkinLayer.AddCluster(Cluster)

        # ============================= #
        # Add Bind Pose                 #
        # ============================= #

        self.OutputString += "\nCreating Bind Pose for Mesh"
        
        #Create a new bind pose and add mesh to it
        BindPose = fbx.FbxPose.Create(self.OurScene, "BindPose")
        BindPose.SetIsBindPose(True)
        BindPose.Add(self.MeshNode, self.ConvertMatrixType(BindMatrix))
        
        #Add each bone and its transform to the bind pose
        for BoneNode in self.NodeMap.values():
            BindPose.Add(BoneNode, self.ConvertMatrixType(BoneNode.EvaluateGlobalTransform()))
        
        #Assign bind pose
        self.OurScene.AddPose(BindPose)

        self.OutputString += "\nBind Pose assigned, Skinning complete."


    def SrmToFBX(self, ReaverFilePath: Path, FileManager: fbx.FbxManager, GiveOutput: bool) -> tuple[fbx.FbxScene | None, str]:
        """
        SRM To FBX Function
        Main function to actually convert files
        We need a path to the file and the FBX Scene Manager to process the data
        Returns an FBX Scene on success, null on failure
        Optionally returns the Output String
        """

        self.SceneManager = FileManager
        self.OutputString = "Beginning Conversion of SRM File"
        self.PathToFile = ReaverFilePath

        #Get our File and put it into a Variable
        self.ParseSRM()
        if self.SourceFile is None:
            return None, self.OutputString
        
        #Initialize the FBX Scene and retrieve the Scene Root and Mesh 
        self.InitializeScene()
        if self.OurScene is None:
            return None, self.OutputString
        
        #Create Vertices on the Mesh
        self.CreateVertices()

        #Create triangles, add their UVs and materials
        self.ProcessTriangleInfo()

        #Create the Skeleton
        self.CreateSkeleton()
        if not self.NodeMap:
            self.OutputString += "\nCouldn't find any bones"
            return None, self.OutputString

        #Skin the mesh and add its bind pose
        self.SkinMesh()

        #We have our new FBX File!
        if GiveOutput:
            return self.OurScene, self.OutputString
        else:
            return self.OurScene, None