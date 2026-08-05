import pytest

from tests.conftest import unique_username


async def _login(client, username_prefix="feeds"):
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
async def test_create_folder_and_list(client):
    await _login(client)

    create = await client.post("/api/folders", json={"name": "Tech"})
    assert create.status_code == 200
    folder_id = create.json()["id"]

    listing = await client.get("/api/folders")
    assert listing.status_code == 200
    assert any(f["id"] == folder_id for f in listing.json())


@pytest.mark.asyncio
async def test_delete_folder_orphans_subscriptions_not_cascades(client, monkeypatch):
    await _login(client)

    import app.services.feed_discovery as feed_discovery_module

    async def _fake_discover(url, auth=None):
        return url

    monkeypatch.setattr(feed_discovery_module, "discover_feed_url", _fake_discover)

    folder = await client.post("/api/folders", json={"name": "ToDelete"})
    folder_id = folder.json()["id"]

    create_feed = await client.post(
        "/api/feeds",
        json={"url": "https://feedcrud1.example.test/feed.xml", "folderId": folder_id},
    )
    assert create_feed.status_code == 200

    delete = await client.delete(f"/api/folders/{folder_id}")
    assert delete.status_code == 200

    feeds = await client.get("/api/feeds")
    matching = [f for f in feeds.json() if f["url"] == "https://feedcrud1.example.test/feed.xml"]
    assert len(matching) == 1
    assert matching[0]["folderId"] is None


@pytest.mark.asyncio
async def test_duplicate_subscription_rejected(client, monkeypatch):
    await _login(client)

    import app.services.feed_discovery as feed_discovery_module

    async def _fake_discover(url, auth=None):
        return url

    monkeypatch.setattr(feed_discovery_module, "discover_feed_url", _fake_discover)

    payload = {"url": "https://feedcrud2.example.test/feed.xml"}
    first = await client.post("/api/feeds", json=payload)
    assert first.status_code == 200

    second = await client.post("/api/feeds", json=payload)
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_opml_export_contains_subscribed_feed(client, monkeypatch):
    await _login(client)

    import app.services.feed_discovery as feed_discovery_module

    async def _fake_discover(url, auth=None):
        return url

    monkeypatch.setattr(feed_discovery_module, "discover_feed_url", _fake_discover)

    await client.post("/api/feeds", json={"url": "https://feedcrud3.example.test/feed.xml"})

    export = await client.get("/api/feeds/export-opml")
    assert export.status_code == 200
    assert b"feedcrud3.example.test" in export.content


@pytest.mark.asyncio
async def test_update_feed_summarize_flag(client, monkeypatch):
    await _login(client)

    import app.services.feed_discovery as feed_discovery_module

    async def _fake_discover(url, auth=None):
        return url

    monkeypatch.setattr(feed_discovery_module, "discover_feed_url", _fake_discover)

    create = await client.post("/api/feeds", json={"url": "https://feedcrud4.example.test/feed.xml"})
    subscription_id = create.json()["subscriptionId"]

    update = await client.patch(
        f"/api/feeds/{subscription_id}", json={"summarizeEnabled": True}
    )
    assert update.status_code == 200

    feeds = await client.get("/api/feeds")
    matching = next(f for f in feeds.json() if f["subscriptionId"] == subscription_id)
    assert matching["summarizeEnabled"] is True


@pytest.mark.asyncio
async def test_auto_read_pattern_rejects_catastrophic_backtracking_shape(client, monkeypatch):
    await _login(client)

    import app.services.feed_discovery as feed_discovery_module

    async def _fake_discover(url, auth=None):
        return url

    monkeypatch.setattr(feed_discovery_module, "discover_feed_url", _fake_discover)

    create = await client.post("/api/feeds", json={"url": "https://feedcrud5.example.test/feed.xml"})
    subscription_id = create.json()["subscriptionId"]

    update = await client.patch(
        f"/api/feeds/{subscription_id}", json={"autoReadPattern": "(a+)+$"}
    )
    assert update.status_code == 400

    ok = await client.patch(
        f"/api/feeds/{subscription_id}", json={"autoReadPattern": "breaking news"}
    )
    assert ok.status_code == 200
