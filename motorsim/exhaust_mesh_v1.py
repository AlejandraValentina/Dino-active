"""Versioned conservative axial refinement for named linear-frustum exhaust sections."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path

from .engine_configuration import sha256, validate
from .gas1d.mesh import Mesh

IDENTITY = "EXHAUST_MESH_V1"
_ALLOWED = (1, 2, 4)

def _adapter_hash() -> str:
    return hashlib.sha256(Path(__file__).read_bytes().replace(b"\r\n", b"\n")).hexdigest()

def _section_mesh(section: dict, count: int, origin: float) -> Mesh:
    length = float(section["length_mm"]) * 1e-3
    d0 = float(section["inlet_diameter_mm"]) * 1e-3
    d1 = float(section["outlet_diameter_mm"]) * 1e-3
    faces = tuple(origin + length * i / count for i in range(count + 1))
    diameters = tuple(d0 + (d1 - d0) * i / count for i in range(count + 1))
    areas = tuple(math.pi * d * d / 4 for d in diameters)
    volumes, centers = [], []
    for i in range(count):
        h = faces[i + 1] - faces[i]
        left, right = diameters[i], diameters[i + 1]
        volume = math.pi * h * (left * left + left * right + right * right) / 12
        slope = (right - left) / h
        moment = math.pi / 4 * (left * left * h * h / 2 + 2 * left * slope * h**3 / 3 + slope * slope * h**4 / 4)
        volumes.append(volume)
        centers.append(faces[i] + moment / volume)
    return Mesh(faces, areas, tuple(volumes), tuple(centers))

def _combine_meshes(meshes: list[Mesh]) -> Mesh:
    faces = [meshes[0].faces[0]]
    areas = [meshes[0].areas[0]]
    volumes, centers = [], []
    for mesh in meshes:
        if not math.isclose(areas[-1], mesh.areas[0], rel_tol=2e-12, abs_tol=1e-18):
            raise ValueError("adjacent exhaust section areas are discontinuous")
        faces.extend(mesh.faces[1:])
        areas.extend(mesh.areas[1:])
        volumes.extend(mesh.volumes)
        centers.extend(mesh.centers)
    return Mesh(tuple(faces), tuple(areas), tuple(volumes), tuple(centers))

def refine_exhaust_configuration(document: dict, cells_per_section: list[int] | tuple[int, ...], *,
                                display_name: str | None = None) -> dict:
    """Return a new engine config with explicit 1/2/4 cells per named section.

    The old legacy adapter is untouched. Refinements map only from a recognized
    one-cell-per-section or EXHAUST_MESH_V1 configuration; extensive mass,
    species and total energy are conservatively remapped within each section.
    """
    validate(document)
    if not isinstance(cells_per_section, (list, tuple)) or any(type(n) is not int or n not in _ALLOWED for n in cells_per_section):
        raise ValueError("cells_per_section must contain only integer values 1, 2, or 4")
    native = deepcopy(document["native_configuration"])
    geometry = native["geometry_identity"]
    sections = deepcopy(geometry.get("chamber", {}).get("sections"))
    if not isinstance(sections, list) or not sections or len(cells_per_section) != len(sections):
        raise ValueError("one explicit refinement is required per named exhaust section")
    normalized=[]
    for i, row in enumerate(sections):
        required={"name","kind","length_mm","inlet_diameter_mm","outlet_diameter_mm","provenance"}
        if not isinstance(row,dict) or set(row)!=required:
            raise ValueError(f"exhaust section {i} schema is invalid")
        if row["kind"] not in {"header","diffuser","belly","baffle_cone","stinger","linear"}:
            raise ValueError(f"exhaust section {i} kind is unsupported")
        vals=[row[k] for k in ("length_mm","inlet_diameter_mm","outlet_diameter_mm")]
        if any(type(v) not in (int,float) or not math.isfinite(v) or v<=0 for v in vals):
            raise ValueError(f"exhaust section {i} dimensions must be finite positive mm")
        if not isinstance(row["provenance"],str) or not row["provenance"]:
            raise ValueError(f"exhaust section {i} provenance is required")
        if normalized and not math.isclose(normalized[-1]["outlet_diameter_mm"],row["inlet_diameter_mm"],rel_tol=1e-12,abs_tol=1e-12):
            raise ValueError(f"exhaust section {i} is discontinuous")
        normalized.append(deepcopy(row))
    sections=normalized
    geometry.setdefault("chamber",{})["sections"]=deepcopy(sections)
    exhaust = next((duct for duct in native["ducts"] if duct["id"] == "exhaust"), None)
    if exhaust is None:
        raise ValueError("exhaust duct is missing")
    old_mesh = exhaust["mesh"]
    old_meta = geometry.get("exhaust_mesh_discretization")
    if old_meta is None:
        old_counts = [1] * len(sections)
    else:
        required_meta={"schema","adapter_sha256","cells_per_section","section_names","discrete_geometry_sha256"}
        if not isinstance(old_meta,dict) or set(old_meta)!=required_meta or old_meta.get("schema") != IDENTITY:
            raise ValueError("unsupported exhaust mesh identity")
        if old_meta.get("adapter_sha256")!=_adapter_hash():
            raise ValueError("existing exhaust mesh adapter source hash mismatch")
        old_counts = old_meta.get("cells_per_section")
        if not isinstance(old_counts, list) or len(old_counts) != len(sections) or any(type(n) is not int or n not in _ALLOWED for n in old_counts):
            raise ValueError("existing exhaust mesh metadata is invalid")
        if old_meta.get("section_names")!=[s.get("name") for s in sections]:
            raise ValueError("existing exhaust section identity mismatch")
        existing_profile={"sections":deepcopy(sections),"cells_per_section":old_counts,"mesh":old_mesh}
        if old_meta.get("discrete_geometry_sha256")!=sha256(existing_profile):
            raise ValueError("existing discrete exhaust geometry hash mismatch")
    exhaust = next((duct for duct in native["ducts"] if duct["id"] == "exhaust"), None)
    if exhaust is None:
        raise ValueError("exhaust duct is missing")
    old_mesh = exhaust["mesh"]
    if len(old_mesh["volumes"]) != sum(old_counts):
        raise ValueError("existing exhaust topology is incompatible with section identity")
    if len(native["initial_duct_states"]["exhaust"]) != sum(old_counts) or len(native["duct_species"]["exhaust"]) != sum(old_counts):
        raise ValueError("existing exhaust state/species topology is incompatible")
    old_q = native["initial_duct_states"]["exhaust"]
    old_species = native["duct_species"]["exhaust"]
    gamma = native.get("eos", {}).get("gamma", 1.35)
    meshes=[]
    origin=float(old_mesh["faces"][0])
    cursor=origin
    for section, count in zip(sections, cells_per_section):
        mesh=_section_mesh(section, count, cursor);meshes.append(mesh);cursor=mesh.faces[-1]
    combined=_combine_meshes(meshes)
    new_q=[];new_species=[]
    old_index=new_index=0
    for old_count,new_count,mesh in zip(old_counts,cells_per_section,meshes):
        old_vols=old_mesh["volumes"][old_index:old_index+old_count]
        old_rows=old_q[old_index:old_index+old_count]
        old_sp=old_species[old_index:old_index+old_count]
        new_vols=mesh.volumes
        # Project each destination cell onto its containing source cell for split
        # refinements; nested 1/2/4 grids permit exact subcell overlap mapping.
        source_edges=[0.0]
        for v in old_vols: source_edges.append(source_edges[-1]+v)
        target_edges=[0.0]
        for v in new_vols: target_edges.append(target_edges[-1]+v)
        source_energy=[]
        for rho,u,p,_ in old_rows:
            source_energy.append((rho, rho*u, p/(gamma-1.0)+0.5*rho*u*u))
        for j, volume in enumerate(new_vols):
            lo,hi=target_edges[j],target_edges[j+1]
            accum=[0.0,0.0,0.0]; species=[0.0,0.0,0.0,0.0]
            for i in range(old_count):
                overlap=max(0.0,min(hi,source_edges[i+1])-max(lo,source_edges[i]))
                if overlap == 0: continue
                fraction=overlap/old_vols[i]
                for k in range(3): accum[k]+=source_energy[i][k]*overlap
                for k,value in enumerate(old_sp[i]): species[k]+=value*fraction
            rho,momentum,energy=(v/volume for v in accum)
            if rho<=0: raise ValueError("conservative remap produced nonpositive density")
            velocity=momentum/rho
            pressure=(gamma-1.0)*(energy-0.5*rho*velocity*velocity)
            if pressure<=0 or not math.isfinite(pressure): raise ValueError("conservative remap produced invalid pressure")
            new_q.append([rho,velocity,pressure,1.0])
            new_species.append(species)
        old_index+=old_count;new_index+=new_count
    mesh_dict=combined.as_dict()
    exhaust["mesh"]=mesh_dict
    native["initial_duct_states"]["exhaust"]=new_q
    native["duct_species"]["exhaust"]=new_species
    profile={"sections":deepcopy(sections),"cells_per_section":list(cells_per_section),"mesh":mesh_dict}
    geometry["exhaust_mesh_discretization"]={"schema":IDENTITY,"adapter_sha256":_adapter_hash(),
        "cells_per_section":list(cells_per_section),"section_names":[s["name"] for s in sections],
        "discrete_geometry_sha256":sha256(profile)}
    from .engine_configuration import create
    result=create(native_configuration=native, mechanical_loss_model=document["mechanical_loss_model"],
        operating_conditions=document["operating_conditions"],provenance=document["provenance"],
        display_name=display_name or document["display_name"])
    result["provenance"]={**result["provenance"],"exhaust_mesh_identity":IDENTITY,
                          "exhaust_mesh_adapter_sha256":_adapter_hash()}
    validate(result)
    return result
