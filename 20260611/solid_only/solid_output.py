# coding=utf-8
"""MED output helpers for the solid participant."""

from code_aster.Cata.Syntax import _F
from code_aster.Commands import DEFI_FICHIER, IMPR_RESU

from solid_config import SolidConfig


def write_window_med(config: SolidConfig, result, step, t, save_every=None):
    """Write one converged window as an independent ``solid_NNNN.med`` file."""
    if save_every is None:
        save_every = config.transient_save_every
    if step % save_every != 0:
        return

    out = config.case_dir / f"solid_{step:04d}.med"
    if out.exists():
        out.unlink()
    DEFI_FICHIER(
        ACTION="ASSOCIER",
        UNITE=config.result_unit,
        TYPE="BINARY",
        ACCES="NEW",
        FICHIER=str(out),
    )
    try:
        IMPR_RESU(
            FORMAT="MED",
            UNITE=config.result_unit,
            RESU=_F(
                RESULTAT=result,
                NOM_CHAM=("DEPL",),
                NOM_CHAM_MED=("DEPL",),
                INST=(float(t),),
                CRITERE="RELATIF",
                PRECISION=config.med_precision,
            ),
        )
    finally:
        DEFI_FICHIER(ACTION="LIBERER", UNITE=config.result_unit)


def stitch_med_series(config: SolidConfig, pattern="solid_*.med"):
    """Best-effort merge of window MED files into one time-series MED."""
    files = sorted(config.case_dir.glob(pattern))
    if not files:
        print(f"[Solid] stitch: {pattern} 매칭 없음", flush=True)
        return
    try:
        import medcoupling as mc
    except Exception as exc:
        print(f"[Solid] stitch: medcoupling 없음 ({exc}) — 개별 파일 유지", flush=True)
        return

    first = mc.MEDFileData.New(str(files[0]))
    field_names = list(first.getFields().getFieldsNames())
    if not field_names:
        print("[Solid] stitch: 첫 파일에 필드 없음", flush=True)
        return

    merged = mc.MEDFileData.New()
    merged.setMeshes(first.getMeshes())
    merged_fields = mc.MEDFileFields()
    for fname in field_names:
        mts = mc.MEDFileFieldMultiTS()
        new_iter = 0
        for path in files:
            src = mc.MEDFileData.New(str(path)).getFields().getFieldWithName(fname)
            for it_pair in src.getIterations():
                f1ts = src.getTimeStep(it_pair[0], it_pair[1])
                t_phys = f1ts.getTime()[2]
                new_iter += 1
                f1ts.setTime(new_iter, 0, t_phys)
                mts.pushBackTimeStep(f1ts)
        merged_fields.pushField(mts)
    merged.setFields(merged_fields)

    out = config.case_dir / config.result_file
    if out.exists():
        out.unlink()
    merged.write(str(out), 0)
    print(f"[Solid] stitch: {out.name} 생성 ({len(files)}개 병합)", flush=True)
