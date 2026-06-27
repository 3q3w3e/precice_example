# coding=utf-8
"""Configuration for the Code_Aster/preCICE solid participant."""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SolidConfig:
    case_dir: Path

    precice_config: str
    participant: str
    mesh_name: str
    read_data: str
    write_data: str
    dim: int
    zero_force_tol: float

    mesh_file: str
    result_file: str

    restart_dir: Path
    manifest_file: Path
    checkpoint_file: Path
    do_restart: bool
    ckpt_every: int
    ckpt_keep: int
    perturb_vel: float

    volume_gma: str
    iface_gma: str
    clamp_gma: str
    iface_gno: str

    e_mod: float
    nu: float
    rho: float

    time_scheme: str
    hht_alpha: float
    newmark_beta: float
    newmark_gamma: float

    mesh_unit: int
    result_unit: int
    comp: tuple[str, str]

    @classmethod
    def from_env(cls) -> "SolidConfig":
        case_dir = Path(__file__).resolve().parent
        restart_dir = Path(
            os.environ.get("SOLID_RESTART_DIR", str(case_dir.parent / "restart"))
        )
        return cls(
            case_dir=case_dir,
            precice_config=os.environ.get("PRECICE_CONFIG", "../precice-config.xml"),
            participant="Solid",
            mesh_name="Solid-Mesh",
            read_data="Force",
            write_data="Displacement",
            dim=2,
            zero_force_tol=1.0e-12,
            mesh_file=os.environ.get("MESH_FILE", "beam.med"),
            result_file=os.environ.get("RESULT_FILE", "run_solid_result.med"),
            restart_dir=restart_dir,
            manifest_file=restart_dir / "solid_manifest.json",
            checkpoint_file=restart_dir / "solid_ckpt.med",
            do_restart=os.environ.get("SOLID_RESTART", "0") == "1",
            ckpt_every=int(os.environ.get("SOLID_CKPT_EVERY", "1")),
            ckpt_keep=int(os.environ.get("SOLID_CKPT_KEEP", "2")),
            perturb_vel=float(os.environ.get("SOLID_PERTURB_VEL", "0")),
            volume_gma="beam",
            iface_gma="beam_wet",
            clamp_gma="beam_fixed",
            iface_gno="beam_wet_no",
            e_mod=1.4e6,
            nu=0.40,
            rho=1.0e4,
            time_scheme=os.environ.get("SOLID_TIME_SCHEME", "HHT").strip().upper(),
            hht_alpha=float(os.environ.get("SOLID_HHT_ALPHA", "-0.1")),
            newmark_beta=float(os.environ.get("SOLID_NEWMARK_BETA", "0.25")),
            newmark_gamma=float(os.environ.get("SOLID_NEWMARK_GAMMA", "0.5")),
            mesh_unit=20,
            result_unit=80,
            comp=("DX", "DY"),
        )
