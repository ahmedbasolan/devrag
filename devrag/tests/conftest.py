"""Keep every retriever the tests build out of the app's index.

The app loads whatever index it finds at src.retriever.CHROMA_DIR on startup.
Tests used to build HybridRetriever() with that default, so running the suite
left a handful of fake chunks there and the next app launch answered from them.
"""

import pytest


@pytest.fixture(autouse=True, scope="session")
def _isolated_chroma_dir(tmp_path_factory):
    mp = pytest.MonkeyPatch()
    mp.setenv("DEVRAG_CHROMA_DIR", str(tmp_path_factory.mktemp("chroma")))
    yield
    mp.undo()
