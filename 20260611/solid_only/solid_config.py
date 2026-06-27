# coding=utf-8
"""Configuration for the Code_Aster solid-only run."""

import os
from dataclasses import dataclass
from pathlib import Path


# Edit this block for normal solid-only runs.
DIM = 2
MESH_FILE = "beam.med"
RESULT_FILE = "run_solid_result.med"

PROBE_X = 0.6
PROBE_Y = 0.2

TRANSIENT_DT = 0.002
TRANSIENT_STEPS = 1000
TRANSIENT_SAVE_EVERY = 50
TRANSIENT_CSV = "solid_only.csv"
TRANSIENT_CSV_FSYNC = False
PERTURB_VEL = 0.0

STEADY_SOLVER = "nonlinear"
STEADY_LOAD_LEVEL = 1.0
STEADY_STEPS = 20
STEADY_MED = "steady_result.med"
STEADY_CSV = "steady_probe.csv"

GRAVITY = 2.0
GRAVITY_DIR = (0.0, -1.0, 0.0)

VOLUME_GMA = "beam"
IFACE_GMA = "beam_wet"
CLAMP_GMA = "beam_fixed"
IFACE_GNO = "beam_wet_no"
MODELISATION = "D_PLAN"
CLAMP_DX = 0.0
CLAMP_DY = 0.0

E_MOD = 1.4e6
NU = 0.40
RHO = 1.0e3

MATERIAL_RELATION = "ELAS"
DEFORMATION = "GREEN_LAGRANGE"
TIME_SCHEME = "NEWMARK"
HHT_ALPHA = -0.1
NEWMARK_BETA = 0.25
NEWMARK_GAMMA = 0.5
NEWTON_MATRIX = "TANGENTE"
NEWTON_REAC_ITER = 1
SOLVER_METHOD = "MUMPS"
ITER_GLOB_MAXI = 80
RESI_GLOB_RELA = 1.0e-6
RESI_GLOB_MAXI = 1.0e-9
MED_PRECISION = 1.0e-6

MESH_UNIT = 20
RESULT_UNIT = 80
COMP = ("DX", "DY")


def _env_float(name: str, default: float) -> float:
    return float(os.environ.get(name, str(default)))


def _env_int(name: str, default: int) -> int:
    return int(os.environ.get(name, str(default)))


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_str(name: str, default: str) -> str:
    return os.environ.get(name, default)


def _env_tuple(name: str, default: tuple[float, ...]) -> tuple[float, ...]:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return tuple(float(x.strip()) for x in raw.split(","))


@dataclass(frozen=True)
class SolidConfig:
    case_dir: Path

    dim: int

    mesh_file: str
    result_file: str

    probe_x: float
    probe_y: float

    transient_dt: float
    transient_steps: int
    transient_save_every: int
    transient_csv: str
    transient_csv_fsync: bool

    steady_solver: str
    steady_load_level: float
    steady_steps: int
    steady_med: str
    steady_csv: str

    perturb_vel: float
    gravity: float
    gravity_dir: tuple[float, float, float]

    volume_gma: str
    iface_gma: str
    clamp_gma: str
    iface_gno: str
    modelisation: str
    clamp_dx: float
    clamp_dy: float

    e_mod: float
    nu: float
    rho: float

    material_relation: str
    deformation: str
    time_scheme: str
    hht_alpha: float
    newmark_beta: float
    newmark_gamma: float
    newton_matrix: str
    newton_reac_iter: int
    solver_method: str
    iter_glob_maxi: int
    resi_glob_rela: float
    resi_glob_maxi: float
    med_precision: float

    mesh_unit: int
    result_unit: int
    comp: tuple[str, str]

    @classmethod
    def from_env(cls) -> "SolidConfig":
        case_dir = Path(__file__).resolve().parent
        return cls(
            case_dir=case_dir,
            dim=DIM,
            mesh_file=_env_str("MESH_FILE", MESH_FILE),
            result_file=_env_str("RESULT_FILE", RESULT_FILE),
            probe_x=_env_float("SOLID_PROBE_X", PROBE_X),
            probe_y=_env_float("SOLID_PROBE_Y", PROBE_Y),
            transient_dt=_env_float("SOLID_DT", TRANSIENT_DT),
            transient_steps=_env_int("SOLID_STEPS", TRANSIENT_STEPS),
            transient_save_every=_env_int("SOLID_SAVE_EVERY", TRANSIENT_SAVE_EVERY),
            transient_csv=_env_str("SOLID_OUT", TRANSIENT_CSV),
            transient_csv_fsync=_env_bool("SOLID_CSV_FSYNC", TRANSIENT_CSV_FSYNC),
            steady_solver=_env_str("SOLID_STEAD_SOLVER", STEADY_SOLVER).strip().lower(),
            steady_load_level=_env_float("SOLID_STEAD_LOAD_LEVEL", STEADY_LOAD_LEVEL),
            steady_steps=_env_int("SOLID_STEAD_STEPS", STEADY_STEPS),
            steady_med=_env_str("SOLID_STEAD_MED", STEADY_MED),
            steady_csv=_env_str("SOLID_STEAD_OUT", STEADY_CSV),
            perturb_vel=_env_float("SOLID_PERTURB_VEL", PERTURB_VEL),
            gravity=_env_float("SOLID_GRAVITY", GRAVITY),
            gravity_dir=_env_tuple("SOLID_GRAVITY_DIR", GRAVITY_DIR),
            volume_gma=VOLUME_GMA,
            iface_gma=IFACE_GMA,
            clamp_gma=CLAMP_GMA,
            iface_gno=IFACE_GNO,
            modelisation=MODELISATION,
            clamp_dx=CLAMP_DX,
            clamp_dy=CLAMP_DY,
            e_mod=E_MOD,
            nu=NU,
            rho=RHO,
            material_relation=MATERIAL_RELATION,
            deformation=DEFORMATION,
            time_scheme=_env_str("SOLID_TIME_SCHEME", TIME_SCHEME).strip().upper(),
            hht_alpha=_env_float("SOLID_HHT_ALPHA", HHT_ALPHA),
            newmark_beta=_env_float("SOLID_NEWMARK_BETA", NEWMARK_BETA),
            newmark_gamma=_env_float("SOLID_NEWMARK_GAMMA", NEWMARK_GAMMA),
            newton_matrix=NEWTON_MATRIX,
            newton_reac_iter=NEWTON_REAC_ITER,
            solver_method=SOLVER_METHOD,
            iter_glob_maxi=ITER_GLOB_MAXI,
            resi_glob_rela=RESI_GLOB_RELA,
            resi_glob_maxi=RESI_GLOB_MAXI,
            med_precision=MED_PRECISION,
            mesh_unit=MESH_UNIT,
            result_unit=RESULT_UNIT,
            comp=COMP,
        )
