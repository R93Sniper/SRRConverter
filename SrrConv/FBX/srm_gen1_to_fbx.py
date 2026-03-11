from SrrConv.FBX.fbx_object import FbxObject
from SrrConv.CrystalDynamics.srm_gen1 import SrmFile
from SrrConv.CrystalDynamics.common import IMAGE_FMTS
from SrrConv.CrystalDynamics.common import do_texture_convert

from pathlib import Path
from logging import Logger

import fbx

def write_vertices(srm: SrmFile, mesh_node: fbx.FbxMesh, logger: Logger):
    logger.info("Writing vertices...")

    num_vertices = srm.display_buffer.num_vertices()
    logger.debug(f"\tVertices: {num_vertices}")
    mesh_node.InitControlPoints(num_vertices)
    for i, vert in enumerate(srm.get_vertices()):
        mesh_node.SetControlPointAt(fbx.FbxVector4(*vert), i)

    logger.info("\tSuccess!")

def write_normals(srm: SrmFile, mesh_node: fbx.FbxMesh, logger: Logger):
    logger.info("Writing normals...")
    mesh_layer = mesh_node.GetLayer(0)
    if mesh_layer == None:
        mesh_node.CreateLayer()
        mesh_layer = mesh_node.GetLayer(0)

    logger.debug("\tCreating normal layer")
    normals = fbx.FbxLayerElementNormal.Create(mesh_node, "normals")
    normals.SetMappingMode(fbx.FbxLayerElement.EMappingMode.eByControlPoint)
    normals.SetReferenceMode(fbx.FbxLayerElement.EReferenceMode.eDirect)

    logger.debug(f"\tNormals: {srm.display_buffer.num_vertices()}")
    for normal in srm.get_normals():
        fbx_norm = fbx.FbxVector4(*normal)
        fbx_norm.Normalize()
        normals.GetDirectArray().Add(fbx_norm)
    logger.info("\tSuccess!")
    
def process_materials(
        srm: SrmFile, 
        mesh_node: fbx.FbxMesh, 
        fbx_object: FbxObject, 
        fbx_path: Path,
        fmt: IMAGE_FMTS, 
        logger: Logger
    ):
    logger.info("Proccessing SRM Materials...")
    logger.debug(f"Material Count: {len(srm.material_palette.materials)}")

    for material in srm.material_palette.materials:
        logger.info(f"Material:  {material.name}")
        textures = material.get_texture_suffixes(extension=f".{fmt}")

        logger.debug(f"Expected Textures: {textures}")
        mesh_node.GetNode().AddMaterial( fbx_object.new_material(material.name, textures, fbx_path / "Textures", logger) )

def create_uv_layer(mesh_node: fbx.FbxMesh, logger: Logger):
    mesh_layer = mesh_node.GetLayer(0)
    if not mesh_layer:
        # Mesh layer should of already been created when normals were made...This is an error
        logger.error("Failed to get UV mesh layer")

    uv_layer = mesh_layer.GetUVs()
    if not uv_layer:
        uv_layer = mesh_node.CreateElementUV("UVSet")

    uv_layer.SetMappingMode(fbx.FbxLayerElement.EMappingMode.eByPolygonVertex) 
    uv_layer.SetReferenceMode(fbx.FbxLayerElement.EReferenceMode.eIndexToDirect) 

    return uv_layer

def create_triangles(srm: SrmFile, mesh_node: fbx.FbxMesh, logger: Logger):
    material_layer = mesh_node.CreateElementMaterial()
    material_layer.SetMappingMode(fbx.FbxLayerElement.EMappingMode.eByPolygon)
    material_layer.SetReferenceMode(fbx.FbxLayerElement.EReferenceMode.eIndexToDirect)

    seen_vertices = {}

    uv_layer = create_uv_layer(mesh_node, logger)
    uv_indices = uv_layer.GetIndexArray()
    uv_data = uv_layer.GetDirectArray()

    for face in srm.display_buffer.indices:
        material_index = srm.display_buffer.vertices[face[0]].texture_index - 1
        mesh_node.BeginPolygon(material_index)

        for index in face:
            vert = srm.display_buffer.vertices[index]

            if vert in seen_vertices:
                uv_index = seen_vertices[vert]
            else:
                uv_vector = fbx.FbxVector2(vert.u / 255.0, 1-(vert.v / 255.0))
                uv_index = uv_data.GetCount()
                uv_data.Add(uv_vector)
                seen_vertices[vert] = uv_index

            mesh_node.AddPolygon(index)
            uv_indices.Add(uv_index)
        mesh_node.EndPolygon()

def convert_textures(srm: SrmFile, fbx_path: Path, in_texture_path: Path, fmt: IMAGE_FMTS, logger: Logger):
    out_texture_path = fbx_path.parent / "Textures"
    material_texture_lists = [material.get_texture_suffixes() for material in srm.material_palette.materials]
    for material in material_texture_lists:
        for texture in material:
            if texture is None:
                continue
            do_texture_convert(in_texture_path / f"{texture}.dds", out_texture_path / f"{texture}.{fmt}", fmt, logger)

def srm_to_fbx(srm_path: str | Path, fbx_path: str | Path, fmt: IMAGE_FMTS, texture_path: str | Path, logger: Logger):
    """
        Load a SRM from `srm_path` and save it to `fbx_path`
    """

    srm_path     = Path(srm_path) if isinstance(srm_path, str) else srm_path
    fbx_path     = Path(fbx_path) if isinstance(fbx_path, str) else fbx_path
    texture_path = Path(texture_path) if isinstance(texture_path, str) else texture_path

    srm = SrmFile.from_file(srm_path)
    fbx_object = FbxObject()

    mesh_node = fbx_object.new_mesh(srm_path.stem, logger)
    if mesh_node == None:
        logger.error("Failed to convert srm to fbx!")
        return
    
    write_vertices(srm, mesh_node, logger)
    write_normals(srm, mesh_node, logger)
    process_materials(srm, mesh_node, fbx_object, fbx_path.parent, fmt, logger)
    create_triangles(srm, mesh_node, logger)
    convert_textures(srm, fbx_path, texture_path, fmt, logger)

    fbx_object.export(fbx_path, logger)