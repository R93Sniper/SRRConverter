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

    def new_mesh(self, name: str, logger: Logger) -> fbx.FbxMesh | None:
        logger.info(f"Creating new mesh: {name}")

        logger.debug(f"\tCreating mesh node: {name}_node")
        new_node = fbx.FbxNode.Create(self.scene, f"{name}_node")
        logger.debug(f"\tCreating mesh: {name}")
        new_mesh = fbx.FbxMesh.Create(self.scene, name)

        if new_node and self.new_mesh:
            logger.debug("\tAssigning mesh to node.")
            new_node.SetNodeAttribute(new_mesh)
            logger.debug("\tSetting scene root as new node's parent")
            self.scene.GetRootNode().AddChild(new_node)
        else:
            logger.error("\tFailed to create new mesh, aborting!")
            return None

        logger.info("\tSuccess!")
        return new_mesh

    def new_material(self, 
                     name: str, 
                     textures: list[str | None], 
                     outpath: Path, 
                     logger: Logger
    ) -> fbx.FbxSurfacePhong | None:
        logger.info(f"Creating new material: {name}")

        mat = fbx.FbxSurfacePhong.Create(self.scene, name)

        logger.debug(f"\tCreating mesh node: {name}_node")
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
        return mat
    
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