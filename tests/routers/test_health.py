def test_read_health(client):
    response = client.get('/health')
    assert response.status_code == 200
    data = response.json()
    assert 'status' in data
    assert data['status'] == "ok"