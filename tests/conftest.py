import sys
from pathlib import Path

import pytest

TESTS = Path(__file__).resolve().parent
REPO = TESTS.parent
for p in (str(REPO), str(TESTS)):
    if p not in sys.path:
        sys.path.insert(0, p)


@pytest.fixture(scope="session")
def project_root(tmp_path_factory):
    from synthetic import make_project

    return make_project(tmp_path_factory.mktemp("project"))


@pytest.fixture(scope="session")
def project_cfg(project_root):
    from engine.config import Config
    from engine.paths import Paths

    return Config.load(Paths.default(project_root))


@pytest.fixture(scope="session")
def real_cfg():
    from engine.config import Config
    from engine.paths import Paths

    return Config.load(Paths.default(REPO))
