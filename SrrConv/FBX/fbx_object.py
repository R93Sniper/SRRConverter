try:
    import fbx
except:
    print("Failed to load the FBX library. Please download the 'FBX Python SDK' from: https://aps.autodesk.com/developer/overview/fbx-sdk")
    exit()

from logging import Logger
from pathlib import Path

class FbxObject:
    def __init__(self) -> None:
        self.manager = fbx.FbxManager.Create()
        self.scene = fbx.FbxScene.Create(self.manager, "SRM Data")

    def _create_fbx_verts(self, verts: list[tuple[float, float, float]], mesh: fbx.FbxMesh, logger: Logger):
        logger.info("Writing vertices...")

        num_vertices = len(verts)
        logger.debug(f"Vertices: {num_vertices}")
        mesh.InitControlPoints(num_vertices)
        for i, vert in enumerate(verts):
            mesh.SetControlPointAt(fbx.FbxVector4(*vert), i)

        logger.info("Success!")

    def _create_fbx_norms(self, norms: list[tuple[float, float, float]], mesh: fbx.FbxMesh, logger: Logger):
        logger.info("Writing normals...")
        mesh_layer = mesh.GetLayer(0)
        if mesh_layer == None:
            mesh.CreateLayer()
            mesh_layer = mesh.GetLayer(0)

        logger.debug("Creating normal layer")
        normals = fbx.FbxLayerElementNormal.Create(mesh, "normals")
        normals.SetMappingMode(fbx.FbxLayerElement.EMappingMode.eByControlPoint)
        normals.SetReferenceMode(fbx.FbxLayerElement.EReferenceMode.eDirect)

        logger.debug(f"Normals: {len(norms)}")
        for normal in norms:
            fbx_norm = fbx.FbxVector4(*normal)
            fbx_norm.Normalize()
            normals.GetDirectArray().Add(fbx_norm)
        logger.info("Success!")

    def new_mesh(self, 
                 name: str, 
                 logger: Logger, 
                 verts: list[tuple[float, float, float]],
                 normals: list[tuple[float, float, float]]
                ) -> fbx.FbxMesh | None:
        logger.info(f"Creating new mesh: {name}")

        logger.debug(f"Creating mesh node: {name}_node")
        mesh_node = fbx.FbxNode.Create(self.scene, f"{name}_node")
        logger.debug(f"Creating mesh: {name}")
        new_mesh = fbx.FbxMesh.Create(self.scene, name)

        if mesh_node and self.new_mesh:
            logger.debug("Assigning mesh to node.")
            mesh_node.SetNodeAttribute(new_mesh)
            logger.debug("Setting scene root as new node's parent")
            self.scene.GetRootNode().AddChild(mesh_node)
        else:
            logger.error("Failed to create new mesh, aborting!")
            return None

        logger.info("Success!")

        self._create_fbx_verts(verts, new_mesh, logger)
        self._create_fbx_norms(normals, new_mesh, logger)
        return new_mesh

    def new_material(self, 
                     name: str, 
                     textures: list[str | None], 
                     outpath: Path, 
                     logger: Logger
    ) -> fbx.FbxSurfacePhong | None:
        logger.info(f"Creating new FBX phong material: {name}")

        mat = fbx.FbxSurfacePhong.Create(self.scene, name)
        
        # 0% shininess is PDB 100% roughness
        mat.Shininess.Set(0.0)

        logger.debug(f"Creating mesh node: {name}_node")
        for i, texture in enumerate(textures):
            if texture is not None:
                texture_path = str(outpath / texture)
                logger.debug(f"Using final texture path of: {texture_path}")
                fbx_tex  = fbx.FbxFileTexture.Create(self.scene, texture)
                fbx_tex.SetFileName(texture_path)

                match i:
                    case 0: 
                        logger.debug(f"Linking texture {texture} to material diffuse channel")
                        mat.Diffuse.ConnectSrcObject(fbx_tex)
                    case 1: 
                        logger.debug(f"Linking texture {texture} to material normal channel")
                        mat.NormalMap.ConnectSrcObject(fbx_tex)
                    case 2: 
                        logger.debug(f"Linking texture {texture} to material specular channel")
                        mat.Specular.ConnectSrcObject(fbx_tex)
                    case 3: 
                        logger.debug(f"Linking texture {texture} to material emissive channel")
                        mat.Emissive.ConnectSrcObject(fbx_tex)

        logger.info(f"Success: Created material {name}!")
        return mat
    
    def _create_bones(
            self,
            mesh: fbx.FbxMesh, 
            bone_positions: list[tuple[float, float, float]], 
            logger: Logger
        ):
        skeleton_attribute = fbx.FbxSkeleton.Create(self.scene, "skeleton")
        skeleton_attribute.SetSkeletonType(fbx.FbxSkeleton.EType.eRoot)
        skeleton_attribute.LimbLength.Set(5.0)

        skeleton_root = fbx.FbxNode.Create(self.scene, "skeleton_root")
        skeleton_root.SetNodeAttribute(skeleton_attribute)
        skeleton_root.LclTranslation.Set(fbx.FbxDouble3(0, 0, 0))

        clusters = []
        bind_mtx = mesh.GetNode().EvaluateGlobalTransform()
        
        for index, position in enumerate(bone_positions):
            skeleton_limb_attribute = fbx.FbxSkeleton.Create(self.scene, "SkeletonLimb")
            skeleton_limb_attribute.SetSkeletonType(fbx.FbxSkeleton.EType.eLimb)
            skeleton_limb_attribute.LimbLength.Set(3.0)

            skeleton_limb_node = fbx.FbxNode.Create(self.scene, f"bone_{index}")
            skeleton_limb_node.SetNodeAttribute(skeleton_limb_attribute)
            skeleton_limb_node.LclTranslation.Set(fbx.FbxDouble3(-position[0], -position[2], position[1]))

            cluster = fbx.FbxCluster.Create(self.scene, f"cluster_{index}")
            cluster.SetLink(skeleton_limb_node)
            cluster.SetTransformMatrix(bind_mtx)
            cluster.SetTransformLinkMatrix(skeleton_limb_node.EvaluateGlobalTransform())
            clusters.append(cluster)

            skeleton_root.AddChild(skeleton_limb_node)
        
        self.scene.GetRootNode().AddChild(skeleton_root)
        return clusters
    
    def _create_skin(
            self, 
            mesh: fbx.FbxMesh, 
            clusters,
            vertex_bone_id: list[tuple[int, int, int]], 
            vertex_weights: list[tuple[float, float, float]], 
            logger: Logger
        ):
        skin = fbx.FbxSkin.Create(self.scene, "Skin")
        mesh.AddDeformer(skin)

        # For each collection of bone & weight vertex attributes. [(int, int, int), (float, float, float)]
        for i, (bones, weights) in enumerate(zip(vertex_bone_id, vertex_weights)):
            # For each bone and weight in the collection [(int, float), (int, float), (int, float)]
            for bone, weight in zip(bones, weights):
                if weight > 0 and bone < len(clusters):
                    clusters[bone].AddControlPointIndex(i, weight)
        
        for cluster in clusters:
            skin.AddCluster(cluster)
    
    def rig( 
            self, 
            mesh: fbx.FbxMesh, 
            bone_positions: list[tuple[float, float, float]], 
            vertex_bone_id: list[tuple[int, int, int]], 
            vertex_weights: list[tuple[float, float, float]],
            logger: Logger
        ):
        clusters = self._create_bones(mesh, bone_positions, logger)
        self._create_skin(mesh, clusters, vertex_bone_id, vertex_weights, logger)
        
    def export(self, path: str | Path, logger: Logger):
        logger.info(f"Attempting to export to location: {path}")
        path = Path(path) if isinstance(path, str) else path

        if path.parent:
            path.parent.mkdir(exist_ok=True, parents=True)

        exporter = fbx.FbxExporter.Create(self.manager, "")

        if not exporter.Initialize(str(path)):
            logger.error(f"Failed to create FBX file!")

        if exporter.Export(self.scene):
            logger.info(f"Success!")
        else:
            logger.error(f"Failed to export FBX scene!")

        exporter.Destroy()
