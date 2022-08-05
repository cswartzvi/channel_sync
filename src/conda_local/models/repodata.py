from typing import Any, Dict, List
from pydantic import BaseModel, Field


class RepoData(BaseModel):
    info: Dict[str, str]
    packages: Dict[str, Dict[str, Any]]
    packages_conda: Dict[str, Dict[str, Any]] = Field(
        alias="conda.packages", default_factory=dict
    )
    removed: List[str]
    repodata_version: int
