import os
import unittest

from agent_ci.agent import run_agent
from agent_ci.dataset import TEST_CASES
from agent_ci.rag.chunker import chunk_policy
from agent_ci.rag.config import load_rag_config
from agent_ci.rag.ingest import ingest_policy
from agent_ci.rag.mock_retriever import mock_retrieve
from agent_ci.rag.retriever import PolicyRetriever


class TestPolicyChunking(unittest.TestCase):
    def test_policy_splits_into_meaningful_chunks(self):
        config = load_rag_config()
        chunks = chunk_policy(config.document_name)
        self.assertGreaterEqual(len(chunks), 6)
        sections = {chunk.section for chunk in chunks}
        self.assertIn("Refunds", sections)
        self.assertIn("Data export", sections)

    def test_chunks_have_metadata(self):
        config = load_rag_config()
        chunk = chunk_policy(config.document_name)[0]
        self.assertTrue(chunk.chunk_id)
        self.assertTrue(chunk.document)
        self.assertTrue(chunk.section)
        self.assertTrue(chunk.text)


class TestMockRetriever(unittest.TestCase):
    def setUp(self):
        os.environ["AGENT_CI_MOCK_RAG"] = "1"

    def tearDown(self):
        os.environ.pop("AGENT_CI_MOCK_RAG", None)

    def test_refund_question_retrieves_refunds_section(self):
        config = load_rag_config()
        chunks = mock_retrieve("I bought Pro yesterday and want a refund", config, top_k=1)
        self.assertEqual(chunks[0].section, "Refunds")

    def test_export_question_retrieves_data_export_section(self):
        config = load_rag_config()
        chunks = mock_retrieve("Can I export my data as CSV?", config, top_k=1)
        self.assertEqual(chunks[0].section, "Data export")

    def test_sso_question_retrieves_enterprise_features_section(self):
        config = load_rag_config()
        chunks = mock_retrieve("Can I set up SSO on Pro plan?", config, top_k=1)
        self.assertEqual(chunks[0].section, "Enterprise features (SSO, audit logs)")
        self.assertEqual(chunks[0].chunk_id, "enterprise_features")


class TestChromaRetriever(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.pop("AGENT_CI_MOCK_RAG", None)
        cls._ingested = ingest_policy(reset=True)

    def test_ingestion_loads_policy_chunks(self):
        self.assertGreaterEqual(self._ingested, 6)

    def test_chroma_retrieves_refund_section(self):
        retriever = PolicyRetriever()
        chunks = retriever.retrieve("I want a refund for my purchase", top_k=1)
        self.assertGreater(len(chunks), 0)
        self.assertEqual(chunks[0].section, "Refunds")
        self.assertEqual(chunks[0].document, "loomly_support_policy_v3")
        self.assertTrue(chunks[0].chunk_id)


class TestRAGAgentIntegration(unittest.TestCase):
    def setUp(self):
        os.environ.pop("AGENT_CI_LIVE", None)
        os.environ["AGENT_CI_MOCK_RAG"] = "1"

    def tearDown(self):
        os.environ.pop("AGENT_CI_MOCK_RAG", None)

    def test_candidate_includes_retrieved_context_in_mock_mode(self):
        tc = next(t for t in TEST_CASES if t["id"] == "refund_within_window")
        response = run_agent(tc, role="candidate")
        self.assertIsNotNone(response.retrieved_context)
        self.assertGreater(len(response.retrieved_context), 0)
        chunk = response.retrieved_context[0]
        for key in ("document", "section", "chunk_id", "text"):
            self.assertIn(key, chunk)
        self.assertEqual(chunk["section"], "Refunds")

    def test_baseline_does_not_use_rag(self):
        tc = next(t for t in TEST_CASES if t["id"] == "refund_within_window")
        response = run_agent(tc, role="baseline")
        self.assertIsNone(response.retrieved_context)


if __name__ == "__main__":
    unittest.main()
