#!/usr/bin/env python3
"""
Build the coarse Turek-Hron fluid mesh with the Gmsh Python API.

This is the Python equivalent of fluid_coarse.geo. By default it only builds
and meshes the model in memory. Pass --output to write a mesh file.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import gmsh


def entity_tags(entities: list[tuple[int, int]]) -> list[int]:
    return [tag for _dim, tag in entities]


def first_tag(entities: list[tuple[int, int]], name: str) -> int:
    if not entities:
        raise RuntimeError(f"Could not find entity for {name}")
    return entities[0][1]


def curves_in_box(
    xmin: float,
    ymin: float,
    zmin: float,
    xmax: float,
    ymax: float,
    zmax: float,
) -> list[int]:
    return entity_tags(
        gmsh.model.getEntitiesInBoundingBox(xmin, ymin, zmin, xmax, ymax, zmax, 1)
    )


def points_in_box(
    xmin: float,
    ymin: float,
    zmin: float,
    xmax: float,
    ymax: float,
    zmax: float,
) -> list[int]:
    return entity_tags(
        gmsh.model.getEntitiesInBoundingBox(xmin, ymin, zmin, xmax, ymax, zmax, 0)
    )


def add_physical(dim: int, tags: list[int], name: str) -> int:
    if not tags:
        raise RuntimeError(f"No entities found for physical group {name!r}")
    phys_tag = gmsh.model.addPhysicalGroup(dim, tags)
    gmsh.model.setPhysicalName(dim, phys_tag, name)
    return phys_tag


def build_model() -> None:
    gmsh.model.add("fluid_coarse")
    gmsh.model.occ.synchronize()

    # 1. Parameters
    length = 2.5
    height = 0.41
    x_c = 0.2
    y_c = 0.2
    radius = 0.05

    x_bl = x_c
    x_br = 0.6
    y_bb = 0.19
    y_bt = 0.21

    lc_far = 0.04
    lc_wake = 0.016
    lc_near = 0.004
    lc_bl = 0.002

    eps = 1.0e-6

    # 2. Build geometry
    channel = gmsh.model.occ.addRectangle(0, 0, 0, length, height, tag=1)
    cylinder = gmsh.model.occ.addDisk(x_c, y_c, 0, radius, radius, tag=2)
    beam = gmsh.model.occ.addRectangle(x_bl, y_bb, 0, x_br - x_bl, y_bt - y_bb, tag=3)

    fluid_entities, _ = gmsh.model.occ.cut(
        [(2, channel)], [(2, cylinder), (2, beam)], tag=100, removeObject=True, removeTool=True
    )

    point_b = gmsh.model.occ.addPoint(0.15, 0.2, 0, lc_bl, tag=200)
    point_a = gmsh.model.occ.addPoint(0.6, 0.2, 0, lc_bl, tag=300)

    gmsh.model.occ.fragment(
        fluid_entities, [(0, point_b), (0, point_a)], removeObject=True, removeTool=True
    )
    gmsh.model.occ.synchronize()
    gmsh.model.occ.removeAllDuplicates()
    gmsh.model.occ.synchronize()

    fluid_surfaces = entity_tags(
        gmsh.model.getEntitiesInBoundingBox(
            -eps, -eps, -eps, length + eps, height + eps, eps, 2
        )
    )

    # 3. Identify boundaries by bounding box
    c_inlet = curves_in_box(-eps, -eps, -eps, eps, height + eps, eps)
    c_outlet = curves_in_box(length - eps, -eps, -eps, length + eps, height + eps, eps)
    c_bot = curves_in_box(-eps, -eps, -eps, length + eps, eps, eps)
    c_top = curves_in_box(-eps, height - eps, -eps, length + eps, height + eps, eps)

    c_cyl_all = curves_in_box(
        x_c - radius - eps,
        y_c - radius - eps,
        -eps,
        x_c + radius + eps,
        y_c + radius + eps,
        eps,
    )

    c_beam_top = curves_in_box(x_bl - eps, y_bt - eps, -eps, x_br + eps, y_bt + eps, eps)
    c_beam_bot = curves_in_box(x_bl - eps, y_bb - eps, -eps, x_br + eps, y_bb + eps, eps)
    c_beam_right = curves_in_box(x_br - eps, y_bb - eps, -eps, x_br + eps, y_bt + eps, eps)

    p_b = points_in_box(0.15 - eps, 0.2 - eps, -eps, 0.15 + eps, 0.2 + eps, eps)
    p_a = points_in_box(0.6 - eps, 0.2 - eps, -eps, 0.6 + eps, 0.2 + eps, eps)

    # 4. Mesh size fields
    distance = gmsh.model.mesh.field.add("Distance", 1)
    gmsh.model.mesh.field.setNumbers(
        distance, "CurvesList", c_cyl_all + c_beam_top + c_beam_bot + c_beam_right
    )
    gmsh.model.mesh.field.setNumber(distance, "Sampling", 400)

    threshold_bl = gmsh.model.mesh.field.add("Threshold", 2)
    gmsh.model.mesh.field.setNumber(threshold_bl, "InField", distance)
    gmsh.model.mesh.field.setNumber(threshold_bl, "SizeMin", lc_bl)
    gmsh.model.mesh.field.setNumber(threshold_bl, "SizeMax", lc_far)
    gmsh.model.mesh.field.setNumber(threshold_bl, "DistMin", 0.005)
    gmsh.model.mesh.field.setNumber(threshold_bl, "DistMax", 0.30)

    threshold_near = gmsh.model.mesh.field.add("Threshold", 3)
    gmsh.model.mesh.field.setNumber(threshold_near, "InField", distance)
    gmsh.model.mesh.field.setNumber(threshold_near, "SizeMin", lc_near)
    gmsh.model.mesh.field.setNumber(threshold_near, "SizeMax", lc_far)
    gmsh.model.mesh.field.setNumber(threshold_near, "DistMin", 0.02)
    gmsh.model.mesh.field.setNumber(threshold_near, "DistMax", 0.15)

    wake = gmsh.model.mesh.field.add("Box", 4)
    gmsh.model.mesh.field.setNumber(wake, "VIn", lc_wake)
    gmsh.model.mesh.field.setNumber(wake, "VOut", lc_far)
    gmsh.model.mesh.field.setNumber(wake, "XMin", 0.25)
    gmsh.model.mesh.field.setNumber(wake, "XMax", 1.5)
    gmsh.model.mesh.field.setNumber(wake, "YMin", 0.10)
    gmsh.model.mesh.field.setNumber(wake, "YMax", 0.30)
    gmsh.model.mesh.field.setNumber(wake, "Thickness", 0.05)

    minimum = gmsh.model.mesh.field.add("Min", 10)
    gmsh.model.mesh.field.setNumbers(minimum, "FieldsList", [threshold_bl, threshold_near, wake])
    gmsh.model.mesh.field.setAsBackgroundMesh(minimum)

    gmsh.option.setNumber("Mesh.MeshSizeFromPoints", 0)
    gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 0)
    gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 0)

    # 5. Physical groups, matching SU2 marker names from the .geo file.
    add_physical(1, c_inlet, "inlet")
    add_physical(1, c_outlet, "outlet")
    add_physical(1, c_top, "wall_top")
    add_physical(1, c_bot, "wall_bot")
    add_physical(1, c_cyl_all, "cylinder")
    add_physical(1, c_beam_top + c_beam_bot + c_beam_right, "beam_wet")
    add_physical(2, [first_tag([(2, tag) for tag in fluid_surfaces], "fluid surface")], "fluid")
    add_physical(0, [first_tag([(0, tag) for tag in p_b], "point_B")], "point_B")
    add_physical(0, [first_tag([(0, tag) for tag in p_a], "point_A")], "point_A")

    # 6. Mesh options
    gmsh.option.setNumber("Mesh.Algorithm", 6)
    gmsh.option.setNumber("Mesh.ElementOrder", 1)
    gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
    gmsh.option.setNumber("Mesh.SaveAll", 0)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Optional mesh output path, for example fluid_coarse_from_python.su2.",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Open the Gmsh GUI after building the mesh.",
    )
    parser.add_argument(
        "--no-mesh",
        action="store_true",
        help="Build the geometry and physical groups, but do not generate the 2D mesh.",
    )
    args, _unknown = parser.parse_known_args()
    return args


def main() -> None:
    args = parse_args()

    gmsh.initialize()
    try:
        build_model()
        if not args.no_mesh:
            gmsh.model.mesh.generate(2)
        if args.output:
            gmsh.write(str(args.output))
        if args.show:
            gmsh.fltk.run()
    finally:
        gmsh.finalize()


if __name__ == "__main__":
    main()
