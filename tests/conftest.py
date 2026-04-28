"""Shared pytest fixtures."""

import pytest

from app.llm.mock_client import MockLLMClient
from app.schemas import Project, ProjectCreate
from app.schemas.project import CostMode, ProjectStatus, VerificationLevel
from app.storage.database import reset_repositories, get_repositories
from app.storage.repositories import Repositories


@pytest.fixture(autouse=True)
def fresh_repos():
    """Each test starts with an empty in-memory store."""
    reset_repositories()
    yield
    reset_repositories()


@pytest.fixture
def repos() -> Repositories:
    return get_repositories()


@pytest.fixture
def mock_llm() -> MockLLMClient:
    return MockLLMClient()


@pytest.fixture
def sample_project() -> Project:
    return Project(
        project_id="tm_test01",
        agenda="중국 AI 트레이너 시장 조사",
        purpose="커리어 확장 참고자료",
        cost_mode=CostMode.BALANCED,
        verification_level=VerificationLevel.STANDARD,
        max_retry=1,
        budget_cap=1500.0,
    )


@pytest.fixture
def sample_create() -> ProjectCreate:
    return ProjectCreate(
        agenda="중국 AI 트레이너 시장의 역할, 직무, 필요역량을 조사해줘.",
        purpose="커리어 확장 가능성 판단",
        conditions="금융 분야에 조금 더 가중치",
        cost_mode=CostMode.BALANCED,
    )
