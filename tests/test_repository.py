from app.db.repository import MappingRepository, Mapping


def test_upsert_and_get_mapping_in_memory():
    repo = MappingRepository(":memory:")
    mapping = Mapping(
        linear_issue_id="lin_123",
        github_owner="octo",
        github_repo="repo",
        github_issue_number=42,
    )

    stored = repo.upsert_mapping(mapping)
    assert stored.linear_issue_id == mapping.linear_issue_id
    assert stored.github_issue_number == 42

    fetched = repo.get_by_linear_issue_id("lin_123")
    assert fetched is not None
    assert fetched.github_owner == "octo"

    # Upsert same id should be idempotent and return existing
    again = repo.upsert_mapping(mapping)
    assert again.github_issue_number == 42

