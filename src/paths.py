"""Where the study, the ledgers, and the trace files live.

On Johnny's machine that folder is the Google Drive copy. This session cannot
see the D: drive, so the repository folder is used until that path exists.
"""

from pathlib import Path

LOCAL_ROOT = Path(r"D:\Users\Johnny\Google Drive Mirror\Gex Tide\tasty-opt")


def project_root() -> Path:
    if LOCAL_ROOT.exists():
        return LOCAL_ROOT
    return Path(__file__).resolve().parents[1]
