import os
import tempfile

import pytest

from app.config import settings


@pytest.fixture(autouse=True)
def _rlm_archive_root():
    """Point both the module-level service and settings at the temp root so
    tempdir-based fixtures pass archive confinement."""
    import app.routers.research as research_router

    root = tempfile.gettempdir()
    settings.rlm_archive_root = root
    if research_router.rlm_service is not None:
        research_router.rlm_service._archive_root = os.path.realpath(root)
    yield


async def test_rlm_service_fallback_scan():
    from app.ai.rlm_service import RLMService
    service = RLMService()
    service._available = False
    import tempfile, os
    with tempfile.TemporaryDirectory() as tmpdir:
        fpath = os.path.join(tmpdir, "test.txt")
        with open(fpath, "w") as f:
            f.write("This file mentions oracle-lag and slippage-limit")
        result = await service.scan_directory(tmpdir, keywords=["oracle-lag", "slippage"])
        assert "alpha_vector" in result
        assert "findings" in result["alpha_vector"]



async def test_rlm_service_fallback_text_batch():
    from app.ai.rlm_service import RLMService
    service = RLMService()
    service._available = False
    result = await service.scan_text_batch(
        ["forum post about sentiment", "another post about momentum"],
        "Find alpha signals",
    )
    assert "alpha_vector" in result



async def test_rlm_service_drift_fallback():
    from app.ai.rlm_service import RLMService
    service = RLMService()
    service._available = False
    result = await service.detect_linguistic_drift(
        ["old post"], ["old post"], ["manager"]
    )
    assert "drift_scores" in result
    assert result["drift_scores"]["manager"]["drift_score"] == 0.0



async def test_rlm_service_source_hash():
    from app.ai.rlm_service import RLMService
    service = RLMService()
    h1 = service.compute_source_hash("path/to/data")
    h2 = service.compute_source_hash("path/to/data")
    assert h1 == h2
    h3 = service.compute_source_hash("different/path")
    assert h1 != h3



async def test_rlm_alpha_vector_model():
    from app.models.rlm_alpha_vector import RLMAlphaVector
    vec = RLMAlphaVector(
        source_type="forum",
        source_path="/data/forums",
        token_count=50000,
        alpha_vector={"findings": [{"signal": "sentiment_drop", "strength": 0.7}]},
    )
    assert vec.source_type == "forum"
    assert vec.used_in_sessions == 0 or vec.used_in_sessions is None



async def test_research_api_alpha_vectors(authenticated_client):
    response = await authenticated_client.get("/api/research/alpha-vectors")
    assert response.status_code == 200
    data = response.json()
    assert "vectors" in data



async def test_rlm_service_empty_directory():
    from app.ai.rlm_service import RLMService
    service = RLMService()
    service._available = False
    import tempfile, os
    with tempfile.TemporaryDirectory() as tmpdir:
        result = await service.scan_directory(tmpdir, keywords=["test"])
        assert "alpha_vector" in result
        assert result["alpha_vector"]["findings"] == []
        assert result["files_scanned"] == 0



async def test_rlm_service_no_keywords():
    from app.ai.rlm_service import RLMService
    service = RLMService()
    service._available = False
    import tempfile, os
    with tempfile.TemporaryDirectory() as tmpdir:
        fpath = os.path.join(tmpdir, "test.txt")
        with open(fpath, "w") as f:
            f.write("some content")
        result = await service.scan_directory(tmpdir, keywords=None)
        assert "alpha_vector" in result



async def test_rlm_service_linguistic_drift_no_change():
    from app.ai.rlm_service import RLMService
    service = RLMService()
    service._available = False
    result = await service.detect_linguistic_drift(
        ["same post content"], ["same post content"], ["manager", "analyst"]
    )
    assert "drift_scores" in result
    assert result["drift_scores"]["manager"]["drift_score"] == 0.0
    assert result["drift_scores"]["analyst"]["drift_score"] == 0.0



async def test_rlm_service_source_hash_deterministic():
    from app.ai.rlm_service import RLMService
    service = RLMService()
    h1 = service.compute_source_hash("forum/data")
    h2 = service.compute_source_hash("forum/data")
    h3 = service.compute_source_hash("forum/data")
    assert h1 == h2 == h3
    h4 = service.compute_source_hash("paper/data")
    assert h1 != h4



async def test_research_api_rlm_scan(authenticated_client):
    import tempfile, os

    with tempfile.TemporaryDirectory() as tmpdir:
        fpath = os.path.join(tmpdir, "test.txt")
        with open(fpath, "w") as f:
            f.write("This file mentions oracle-lag and slippage-limit")
        response = await authenticated_client.post(
            "/api/research/rlm-scan",
            params={"source_path": tmpdir, "keywords": "oracle-lag,slippage"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert "alpha_vector_id" in data

        vec_response = await authenticated_client.get("/api/research/alpha-vectors")
        assert vec_response.status_code == 200
        vec_data = vec_response.json()
        assert len(vec_data["vectors"]) >= 1
        created_ids = [v["id"] for v in vec_data["vectors"]]
        assert data["alpha_vector_id"] in created_ids



async def test_research_api_rlm_scan_no_keywords(authenticated_client):
    import tempfile, os

    with tempfile.TemporaryDirectory() as tmpdir:
        fpath = os.path.join(tmpdir, "data.txt")
        with open(fpath, "w") as f:
            f.write("some random content")
        response = await authenticated_client.post(
            "/api/research/rlm-scan",
            params={"source_path": tmpdir},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert "alpha_vector_id" in data



async def test_rlm_linguistic_drift_detector_keyword():
    from app.ai.rlm_service import LinguisticDriftDetector
    detector = LinguisticDriftDetector()
    detector._embed_available = False
    scores = await detector.compute_drift(
        historical=["old post about manager", "another old one"],
        recent=["new post about manager bad performance", "manager criticism growing"],
        entities=["manager", "analyst"],
    )
    assert "manager" in scores
    assert "analyst" in scores
    assert scores["manager"]["drift_score"] > 0
    assert scores["analyst"]["drift_score"] == 0.0



async def test_rlm_linguistic_drift_detector_empty():
    from app.ai.rlm_service import LinguisticDriftDetector
    detector = LinguisticDriftDetector()
    detector._embed_available = False
    scores = await detector.compute_drift(
        historical=[],
        recent=[],
        entities=["test"],
    )
    assert scores["test"]["drift_score"] == 0.0
    assert scores["test"]["direction"] == "neutral"



async def test_rlm_linguistic_drift_detector_no_entity_mention():
    from app.ai.rlm_service import LinguisticDriftDetector
    detector = LinguisticDriftDetector()
    detector._embed_available = False
    scores = await detector.compute_drift(
        historical=["completely unrelated text"],
        recent=["also unrelated content"],
        entities=["missing_entity"],
    )
    assert scores["missing_entity"]["drift_score"] == 0.0



async def test_rlm_service_scan_directory_with_keywords():
    from app.ai.rlm_service import RLMService
    service = RLMService()
    service._available = False
    import tempfile, os
    with tempfile.TemporaryDirectory() as tmpdir:
        for fname in ["a.txt", "b.txt", "c.log"]:
            with open(os.path.join(tmpdir, fname), "w") as f:
                f.write(f"content about oracle-lag and slippage in {fname}")
        result = await service.scan_directory(tmpdir, keywords=["oracle-lag"])
        assert result["alpha_vector"]["findings"]
        assert result["files_scanned"] == 3
        assert result["files_matched"] == 3



async def test_rlm_service_scan_directory_file_pattern():
    from app.ai.rlm_service import RLMService
    service = RLMService()
    service._available = False
    import tempfile, os
    with tempfile.TemporaryDirectory() as tmpdir:
        for fname in ["data.txt", "data.csv", "notes.log"]:
            with open(os.path.join(tmpdir, fname), "w") as f:
                f.write("some content")
        result = await service.scan_directory(tmpdir, keywords=["content"], file_pattern="*.txt")
        assert result["files_matched"] == 1
        assert result["files_scanned"] == 1
        alpha = result["alpha_vector"]
        assert alpha["total_files_with_signals"] == 1



async def test_rlm_service_scan_directory_token_budget():
    from app.ai.rlm_service import RLMService
    service = RLMService()
    service._available = False
    import tempfile, os
    with tempfile.TemporaryDirectory() as tmpdir:
        for i in range(10):
            with open(os.path.join(tmpdir, f"file_{i}.txt"), "w") as f:
                f.write("a" * 50000)
        result = await service.scan_directory(
            tmpdir, keywords=None, max_tokens=100_000
        )
        assert result["files_scanned"] == 10
        assert result["files_matched"] > 0



async def test_rlm_service_scan_directory_no_readable_files():
    from app.ai.rlm_service import RLMService
    service = RLMService()
    service._available = False
    import tempfile, os
    with tempfile.TemporaryDirectory() as tmpdir:
        result = await service.scan_directory(tmpdir, keywords=["test"])
        assert result["alpha_vector"]["findings"] == []



async def test_rlm_service_scan_directory_nonexistent():
    import pytest
    from app.ai.rlm_service import RLMService
    service = RLMService()
    result = await service.scan_directory("nonexistent-subdir", keywords=["test"])
    assert "error" in result["alpha_vector"]
    assert result["files_scanned"] == 0


async def test_rlm_service_scan_directory_outside_archive_rejected():
    import pytest
    from app.ai.rlm_service import RLMService
    service = RLMService()
    with pytest.raises(ValueError, match="outside the RLM archive root"):
        await service.scan_directory("/etc", keywords=["test"])



async def test_rlm_service_text_batch_empty():
    from app.ai.rlm_service import RLMService
    service = RLMService()
    service._available = False
    result = await service.scan_text_batch([], "test query")
    assert result["documents_processed"] == 0
    assert result["token_estimate"] == 0



async def test_rlm_service_text_batch_filtered():
    from app.ai.rlm_service import RLMService
    service = RLMService()
    service._available = False
    texts = ["short text", "another short one", "third document"]
    result = await service.scan_text_batch(texts, "find signals")
    assert result["documents_processed"] == 3
    assert result["documents_filtered"] == 3
    assert result["alpha_vector"]["filtered_count"] == 3



async def test_rlm_service_drift_with_embedding():
    from app.ai.rlm_service import RLMService
    service = RLMService()
    result = await service.detect_linguistic_drift(
        texts_historical=["old manager post", "old analyst post"],
        texts_recent=["new manager post criticism", "new analyst post praise"],
        target_entities=["manager", "analyst"],
        use_dspy=False,
    )
    assert "drift_scores" in result
    assert "manager" in result["drift_scores"]
    assert "analyst" in result["drift_scores"]
    assert "top_drift_entities" in result
    assert result["historical_docs"] == 2
    assert result["recent_docs"] == 2



async def test_rlm_service_drift_no_entities():
    from app.ai.rlm_service import RLMService
    service = RLMService()
    result = await service.detect_linguistic_drift(
        texts_historical=["old content"],
        texts_recent=["new content"],
        target_entities=[],
        use_dspy=False,
    )
    assert result["drift_scores"] == {}
    assert result["total_entities_analyzed"] == 0



async def test_rlm_service_sub_agent_fallback():
    from app.ai.rlm_service import RLMService
    service = RLMService()
    service._available = False
    result = await service.spawn_sub_agent(
        document="This is a test document about oracle-lag risks in lending protocols",
        instruction="Extract all risk signals",
    )
    assert "keyword_matches" in result or "Fallback" in result



async def test_rlm_service_sub_agent_depth_limit():
    from app.ai.rlm_service import RLMService
    service = RLMService()
    service._available = False
    result = await service.spawn_sub_agent(
        document="test " * 10000,
        instruction="analyze",
        max_depth=1,
        depth=1,
    )
    assert "max depth" in result



async def test_rlm_service_run_pipeline():
    from app.ai.rlm_service import RLMService
    service = RLMService()
    service._available = False
    import tempfile, os
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "forum.txt"), "w") as f:
            f.write("Forum post about manager changes and team sentiment")
        with open(os.path.join(tmpdir, "news.txt"), "w") as f:
            f.write("News article about market oracle volatility")
        result = await service.run_pipeline(
            directory=tmpdir,
            keywords=["manager", "oracle"],
            historical_texts=["old manager post", "old analyst post"],
            recent_texts=["new manager post criticism"],
            entities=["manager", "analyst"],
        )
        assert "alpha_vector" in result
        assert result["pipeline_complete"]
        assert result["scan"]["files_scanned"] == 2
        assert result["drift"] is not None
        assert result["drift"]["top_drift_entities"]



async def test_rlm_service_run_pipeline_no_drift():
    from app.ai.rlm_service import RLMService
    service = RLMService()
    service._available = False
    import tempfile, os
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "data.txt"), "w") as f:
            f.write("simple data")
        result = await service.run_pipeline(
            directory=tmpdir,
            keywords=["data"],
        )
        assert result["pipeline_complete"]
        assert result["drift"] is None



async def test_rlm_service_token_budget_tracking():
    from app.ai.rlm_service import RLMService
    service = RLMService()
    service._reset_budget(500_000)
    assert service._token_budget == 500_000
    assert service._consume_token_budget(100)
    assert service._token_budget == 499_900
    assert not service._consume_token_budget(499_900)
    assert service._token_budget == 0
    assert not service._consume_token_budget(1)



async def test_rlm_service_accumulated_state():
    from app.ai.rlm_service import RLMService
    service = RLMService()
    state = service.get_accumulated_state()
    assert state == []
    assert isinstance(state, list)



async def test_rlm_service_estimate_tokens():
    from app.ai.rlm_service import _estimate_tokens
    assert _estimate_tokens("hello world") == 2
    assert _estimate_tokens("a" * 400) == 100
    assert _estimate_tokens("") == 1



async def test_rlm_service_fallback_scan_directory_method():
    from app.ai.rlm_service import RLMService
    service = RLMService()
    import tempfile, os
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "test.txt"), "w") as f:
            f.write("oracle-lag signal found")
        result = await service.fallback_scan_directory(tmpdir, keywords=["oracle-lag"])
        assert result["files_scanned"] == 1
        assert result["files_matched"] == 1



async def test_rlm_drift_api_endpoint(authenticated_client):
    response = await authenticated_client.post(
        "/api/research/rlm-drift",
        params={
            "historical_texts": ["old manager post"],
            "recent_texts": ["new manager criticism"],
            "entities": "manager,analyst",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "drift_scores" in data
    assert "top_drift_entities" in data



async def test_rlm_text_batch_api_endpoint(authenticated_client):
    response = await authenticated_client.post(
        "/api/research/rlm-text-batch",
        params={
            "texts": ["first document", "second document"],
            "query": "find alpha signals",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "alpha_vector" in data
    assert "documents_processed" in data



async def test_rlm_trajectory_api_endpoint(authenticated_client):
    response = await authenticated_client.get("/api/research/rlm-trajectory")
    assert response.status_code == 200
    data = response.json()
    assert "trajectory" in data
    assert "available" in data



async def test_rlm_state_api_endpoint(authenticated_client):
    response = await authenticated_client.get("/api/research/rlm-state")
    assert response.status_code == 200
    data = response.json()
    assert "state" in data
    assert "count" in data



async def test_rlm_pipeline_api_endpoint(authenticated_client):
    import tempfile, os
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "data.txt"), "w") as f:
            f.write("test signal data")
        fpath = tmpdir.replace("\\", "/")
        response = await authenticated_client.post(
            "/api/research/rlm-pipeline",
            params={
                "directory": fpath,
                "keywords": "signal",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "alpha_vector_id" in data
        assert data["pipeline_complete"]



async def test_rlm_pipeline_api_full(authenticated_client):
    import tempfile, os
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "forum.txt"), "w") as f:
            f.write("forum post about manager changes")
        fpath = tmpdir.replace("\\", "/")
        response = await authenticated_client.post(
            "/api/research/rlm-pipeline",
            params={
                "directory": fpath,
                "keywords": "manager",
                "historical_texts": ["old post about manager"],
                "recent_texts": ["new post criticizing manager"],
                "entities": "manager",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "linguistic_signals" in data
        assert data["pipeline_complete"]



async def test_rlm_keyword_match_edge_cases():
    from app.ai.rlm_service import RLMService
    service = RLMService()
    service._available = False
    assert service._keyword_match("Hello World", ["hello"]) is True
    assert service._keyword_match("Hello World", ["world"]) is True
    assert service._keyword_match("Hello World", ["xyz"]) is False
    assert service._keyword_match("", ["test"]) is False



async def test_rlm_extract_keyword_findings():
    from app.ai.rlm_service import RLMService
    service = RLMService()
    findings = service._extract_keyword_findings("The oracle-lag is 2 seconds", ["oracle-lag"])
    assert len(findings) == 1
    assert findings[0]["keyword"] == "oracle-lag"
    assert findings[0]["position"] == 4
    empty = service._extract_keyword_findings("no match", ["keyword"])
    assert empty == []
    all_content = service._extract_keyword_findings("content", None)
    assert len(all_content) == 1
    assert all_content[0]["keyword"] == "any"



async def test_rlm_linguistic_drift_embedding_fallback():
    from app.ai.rlm_service import LinguisticDriftDetector
    detector = LinguisticDriftDetector()
    detector._embed_available = False
    scores = await detector.compute_drift(
        historical=["a" * 1000, "b" * 1000],
        recent=["c" * 1000, "d" * 1000],
        entities=["entity1", "entity2"],
    )
    assert len(scores) == 2
    for s in scores.values():
        assert "drift_score" in s
        assert "direction" in s
        assert "keyword_score" in s
        assert "global_drift" in s



async def test_rlm_source_hash_consistency():
    from app.ai.rlm_service import RLMService
    service = RLMService()
    h1 = service.compute_source_hash("/data/archives/forum_2024.json")
    h2 = service.compute_source_hash("/data/archives/forum_2024.json")
    h3 = service.compute_source_hash("/DATA/ARCHIVES/FORUM_2024.JSON")
    assert h1 == h2
    assert h1 != h3



async def test_rlm_inspect_trajectory_none():
    from app.ai.rlm_service import RLMService
    service = RLMService()
    assert service.inspect_last_trajectory() is None


