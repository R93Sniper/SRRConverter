"""
This file was created for the SRRConverter project
License: GPLv3

Description: Convert SRM model data into FBX format using the Autodesk FBX SDK
Author: Zatarita
"""

from pathlib import Path
from logging import Logger
from shutil import rmtree

from SrrConv.CrystalDynamics import srm_gen1 as Gen1
from SrrConv.CrystalDynamics import srm_gen2 as Gen2
from SrrConv.CrystalDynamics.image import IMAGE_FMTS, convert_image_data
from SrrConv.CrystalDynamics.bigfile import BigFile
from SrrConv.FBX.fbx_object import FbxObject

try:
    import fbx
except ImportError as e:
    raise ImportError(
        "Failed to load the FBX library. Please download the 'FBX Python SDK' from: "
        "https://aps.autodesk.com/developer/overview/fbx-sdk"
    ) from e


def create_fbx_materials(
        srm: Gen1.SrmFile | Gen2.SrmEntry,
        mesh: fbx.FbxMesh,
        fbx_object: FbxObject,
        fbx_path: Path,
        fmt: IMAGE_FMTS,
        logger: Logger
    ) -> None:
    """Create FBX materials for the SRM material palette."""
    logger.info("Processing SRM Materials...")
    logger.debug(f"Material Count: {len(srm.material_palette.materials)}")

    for material in srm.material_palette.materials:
        logger.info(f"SRM Material: {material.name}")
        converted_textures = material.get_texture_suffixes(extension=f".{fmt}")

        logger.debug(f"Converted Textures: {converted_textures}")
        new_mat = fbx_object.new_material(material.name.lower(), converted_textures, fbx_path / "Textures", logger)
        if new_mat:
            mesh.GetNode().AddMaterial(new_mat)


def create_fbx_uvs(mesh: fbx.FbxMesh, logger: Logger) -> fbx.FbxLayerElementUV | None:
    """Convert SRM UVs into FBX UVs."""
    mesh_layer = mesh.GetLayer(0)
    if not mesh_layer:
        logger.error("Failed to get UV mesh layer")
        return None

    uv_layer = mesh_layer.GetUVs()
    if not uv_layer:
        uv_layer = mesh.CreateElementUV("UVSet")

    uv_layer.SetMappingMode(fbx.FbxLayerElement.EMappingMode.eByPolygonVertex)
    uv_layer.SetReferenceMode(fbx.FbxLayerElement.EReferenceMode.eIndexToDirect)

    return uv_layer


def create_triangles(srm: Gen1.SrmFile | Gen2.SrmEntry, mesh: fbx.FbxMesh, logger: Logger) -> None:
    """Convert SRM indices into FBX faces."""
    material_layer = mesh.CreateElementMaterial()
    material_layer.SetMappingMode(fbx.FbxLayerElement.EMappingMode.eByPolygon)
    material_layer.SetReferenceMode(fbx.FbxLayerElement.EReferenceMode.eIndexToDirect)

    seen_vertices = {}

    uv_layer = create_fbx_uvs(mesh, logger)
    if uv_layer is None:
        logger.error("Cannot create triangles without UV layer")
        return

    uv_indices = uv_layer.GetIndexArray()
    uv_data = uv_layer.GetDirectArray()

    for face in srm.display_buffer.indices:
        material_index = srm.display_buffer.vertices[face[0]].texture_index - 1
        mesh.BeginPolygon(material_index)

        for index in face:
            vert = srm.display_buffer.vertices[index]

            if vert in seen_vertices:
                uv_index = seen_vertices[vert]
            else:
                if isinstance(vert.u, int):
                    uv_vector = fbx.FbxVector2(vert.u / 255.0, 1 - (vert.v / 255.0))
                elif isinstance(vert.u, float):
                    uv_vector = fbx.FbxVector2(vert.u, -vert.v)
                uv_index = uv_data.GetCount()
                uv_data.Add(uv_vector)  # type: ignore
                seen_vertices[vert] = uv_index

            mesh.AddPolygon(index)
            uv_indices.Add(uv_index)
        mesh.EndPolygon()


def convert_textures_gen1(srm: Gen1.SrmFile, fbx_path: Path, in_texture_path: Path, fmt: IMAGE_FMTS, allow_overwrite: bool, logger: Logger) -> None:
    """Convert textures from the source directory to the output FBX texture directory."""
    out_texture_path = fbx_path.parent / "Textures"
    for material in srm.material_palette.materials:
        for texture in material.get_texture_suffixes():
            final_outpath = out_texture_path / f"{texture}.{fmt}"
            if final_outpath.exists() and not allow_overwrite:
                logger.warning(f"Texture `{final_outpath}` already exists and overwrite is disabled - skipping...")
                continue
            if final_outpath.exists():
                logger.info(f"Texture `{final_outpath}` already exists: overwriting")
            if not convert_image_data(in_texture_path / f"{texture}.dds", out_texture_path / f"{texture}.{fmt}", fmt, logger):
                logger.warning(f"Failed to convert texture `{texture}`")


def convert_textures_gen2(srm: Gen2.SrmEntry, fbx_path: Path, in_texture_path: Path, fmt: IMAGE_FMTS, allow_overwrite: bool, prevent_cleanup: bool, logger: Logger) -> None:
    """Extract textures from bigfile and convert them to the output format."""
    out_texture_path_raw = fbx_path.parent / "Raw"
    out_texture_path_raw.mkdir(parents=True, exist_ok=True)
    out_texture_path = fbx_path.parent / "Textures"
    for material in srm.material_palette.materials:
        for texture in material.get_texture_suffixes():
            raw_final_outpath = out_texture_path_raw / f"{texture}.dds"
            if raw_final_outpath.exists() and not allow_overwrite:
                logger.warning(f"Raw texture `{raw_final_outpath}` already extracted and overwrite is disabled - skipping...")
            else:
                logger.debug(f"Extracting {texture}.dds from bigfile to {raw_final_outpath}")
                if in_texture_path.stem == "bigfilehd":
                    logger.debug("Getting data from bigfile")
                    try:
                        bigfile = BigFile.from_file(in_texture_path)
                        data = bigfile.get_data_from_string(f"tex_hd/{texture}.dds")
                    except (KeyError, ValueError):
                        logger.warning(f"Texture `{texture}.dds` not found in archive, skipping...")
                        continue
                    logger.debug(f"Writing data to {raw_final_outpath}")
                    with open(raw_final_outpath, "wb") as raw_out:
                        raw_out.write(data)
                logger.debug("Setting conversion target to last extracted texture")

            final_outpath = out_texture_path / f"{texture}.{fmt}"
            if final_outpath.exists() and not allow_overwrite:
                logger.warning(f"Texture `{final_outpath}` already exists and overwrite is disabled - skipping...")
                continue

            if final_outpath.exists():
                logger.info(f"Texture `{final_outpath}` already exists: overwriting")
            logger.debug(f"Converting {raw_final_outpath} to {final_outpath}")
            if not convert_image_data(raw_final_outpath, final_outpath, fmt, logger):
                logger.warning(f"Failed to convert texture `{texture}`")
    if not prevent_cleanup:
        rmtree(fbx_path.parent / "Raw")


def srm_to_fbx_gen2(
            srm_path: Path,
            fbx_path: Path,
            fmt: IMAGE_FMTS,
            texture_path: Path,
            allow_overwrite: bool,
            prevent_cleanup: bool,
            logger: Logger
        ) -> None:
    fbx_object = FbxObject()

    srm = Gen2.SrmFile.from_file(srm_path)

    for i, srm_entry in enumerate(srm.entries):
        if i == 0:
            mesh_name = srm_path.stem
        else:
            mesh_name = f"{srm_path.stem}_lod_{i}"

        logger.debug(f"Creating Mesh: {mesh_name}")
        mesh = fbx_object.new_mesh(f"{mesh_name}", logger, srm_entry.get_vertices(), srm_entry.get_normals())
        if mesh is None:
            logger.error("Failed to create new mesh srm_entry to fbx!")
            return

        create_fbx_materials(srm_entry, mesh, fbx_object, fbx_path.parent, fmt, logger)
        create_triangles(srm_entry, mesh, logger)
        convert_textures_gen2(srm_entry, fbx_path, texture_path, fmt, allow_overwrite, prevent_cleanup, logger)

        fbx_object.rig(mesh, mesh_name, srm_entry.get_bone_positions(), srm_entry.get_vertex_bone_ids(), srm_entry.get_vertex_weights(), logger)

    fbx_object.export(fbx_path, logger)


def srm_to_fbx_gen1(
            srm_path: str | Path,
            fbx_path: str | Path,
            fmt: IMAGE_FMTS,
            texture_path: str | Path,
            allow_overwrite: bool,
            logger: Logger
        ) -> None:
    """Load an SRM from *srm_path* and save it as FBX to *fbx_path*."""

    srm_path     = Path(srm_path)
    fbx_path     = Path(fbx_path)
    texture_path = Path(texture_path)

    logger.info(f"Loading SRM from path: {srm_path}")
    srm = Gen1.SrmFile.from_file(srm_path)

    fbx_object = FbxObject()

    logger.debug(f"Creating Mesh: {srm_path.stem}")
    mesh = fbx_object.new_mesh(srm_path.stem, logger, srm.get_vertices(), srm.get_normals())
    if mesh is None:
        logger.error("Failed to create new mesh srm to fbx!")
        return

    create_fbx_materials(srm, mesh, fbx_object, fbx_path.parent, fmt, logger)
    create_triangles(srm, mesh, logger)
    convert_textures_gen1(srm, fbx_path, texture_path, fmt, allow_overwrite, logger)

    fbx_object.rig(mesh, srm_path.stem, srm.get_bone_positions(), srm.get_vertex_bone_ids(), srm.get_vertex_weights(), logger)

    fbx_object.export(fbx_path, logger)
