"""
Unit & integration tests for Public Showcase and Media Gallery endpoints.
"""


def test_public_explore_page_accessible_without_auth(client):
    """General visitors can access /explore without needing any session cookie."""
    response = client.get("/explore")
    assert response.status_code == 200
    assert "Temple Fitness" in response.text
    assert "Zero Wait-Time" in response.text
    assert "Four Worlds of Training" in response.text


def test_public_media_page_accessible_without_auth(client):
    """General visitors can access /media gallery without needing any session cookie."""
    response = client.get("/media")
    assert response.status_code == 200
    assert "THE TEMPLE" in response.text
    assert "gallery-grid" in response.text
    assert "lightbox-modal" in response.text


def test_public_info_api(client, db_session):
    """Safe public API returns today's checkin count and plans list."""
    response = client.get("/api/public/info")
    assert response.status_code == 200
    data = response.json()
    assert "today_checkins" in data
    assert "plans" in data
    assert len(data["plans"]) == 4
