import pytest

from tests.conftest import unique_username


async def _login(client, username_prefix="import"):
    username = unique_username(username_prefix)
    payload = {
        "username": username,
        "email": f"{username}@example.com",
        "password": "correct-horse-battery-staple",
    }
    await client.post("/api/auth/register", json=payload)
    await client.post(
        "/api/auth/login",
        json={"username": username, "password": payload["password"], "rememberMe": False},
    )
    return username


@pytest.mark.asyncio
async def test_import_creates_folders_and_subscriptions(client):
    await _login(client)

    payload = {
        "folders": [{"id": 1, "name": "Tech", "parentId": None}],
        "subscriptions": [
            {"url": "https://example.test/feed.xml", "siteUrl": None, "customName": "Ex", "folderId": 1}
        ],
        "articleStates": [],
        "savedSearches": [],
        "mode": "merge",
    }
    response = await client.post("/api/import/my-data", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["foldersCreated"] == 1
    assert body["subscriptionsCreated"] == 1

    feeds = await client.get("/api/feeds")
    assert any(f["url"] == "https://example.test/feed.xml" and f["folderId"] for f in feeds.json())


@pytest.mark.asyncio
async def test_import_skips_already_subscribed_feed(client):
    await _login(client)
    payload = {
        "folders": [],
        "subscriptions": [{"url": "https://example.test/dup.xml", "siteUrl": None, "customName": None, "folderId": None}],
        "articleStates": [],
        "savedSearches": [],
        "mode": "merge",
    }
    first = await client.post("/api/import/my-data", json=payload)
    assert first.json()["subscriptionsCreated"] == 1

    second = await client.post("/api/import/my-data", json=payload)
    body = second.json()
    assert body["subscriptionsCreated"] == 0
    assert body["subscriptionsSkipped"] == 1


@pytest.mark.asyncio
async def test_import_article_states_matches_existing_articles_only(client, db_session):
    from app.db.models import Article
    from app.services import feed_discovery

    await _login(client)

    source = await feed_discovery.get_or_create_source_by_url(db_session, "https://example.test/matched.xml")
    article = Article(source_id=source.id, url="https://example.test/matched-article", title="Matched")
    db_session.add(article)
    await db_session.commit()

    payload = {
        "folders": [],
        "subscriptions": [],
        "articleStates": [
            {
                "articleUrl": "https://example.test/matched-article",
                "articleTitle": "Matched",
                "isRead": True,
                "starred": True,
                "readLater": False,
                "readAt": None,
            },
            {
                "articleUrl": "https://example.test/never-fetched",
                "articleTitle": "Missing",
                "isRead": True,
                "starred": False,
                "readLater": False,
                "readAt": None,
            },
        ],
        "savedSearches": [],
        "mode": "merge",
    }
    response = await client.post("/api/import/my-data", json=payload)
    body = response.json()
    assert body["articleStatesApplied"] == 1
    assert body["articleStatesSkipped"] == 1


@pytest.mark.asyncio
async def test_import_overwrite_mode_clears_existing_data_first(client):
    await _login(client)

    first = {
        "folders": [{"id": 1, "name": "Old", "parentId": None}],
        "subscriptions": [{"url": "https://example.test/old.xml", "siteUrl": None, "customName": None, "folderId": 1}],
        "articleStates": [],
        "savedSearches": [],
        "mode": "merge",
    }
    await client.post("/api/import/my-data", json=first)

    second = {
        "folders": [{"id": 2, "name": "New", "parentId": None}],
        "subscriptions": [{"url": "https://example.test/new.xml", "siteUrl": None, "customName": None, "folderId": 2}],
        "articleStates": [],
        "savedSearches": [],
        "mode": "overwrite",
    }
    response = await client.post("/api/import/my-data", json=second)
    assert response.status_code == 200

    folders = await client.get("/api/folders")
    folder_names = {f["name"] for f in folders.json()}
    assert folder_names == {"New"}

    feeds = await client.get("/api/feeds")
    feed_urls = {f["url"] for f in feeds.json()}
    assert feed_urls == {"https://example.test/new.xml"}


@pytest.mark.asyncio
async def test_import_rejects_malformed_body(client):
    await _login(client)
    response = await client.post("/api/import/my-data", json={"subscriptions": "not-a-list"})
    assert response.status_code == 422
