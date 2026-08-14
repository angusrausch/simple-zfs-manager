def test_get_google_maps_key(client):
    response = client.get('/health')
    assert response.status_code == 200
    data = response.get_json()
    assert 'status' in data
    assert data['status'] == "pass"