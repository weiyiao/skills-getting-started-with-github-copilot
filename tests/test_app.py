"""
Tests for the Mergington High School API
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities data before each test"""
    # Store original state
    original_activities = {
        name: {
            "description": details["description"],
            "schedule": details["schedule"],
            "max_participants": details["max_participants"],
            "participants": details["participants"].copy()
        }
        for name, details in activities.items()
    }
    
    yield
    
    # Restore original state after test
    for name, details in original_activities.items():
        activities[name]["participants"] = details["participants"].copy()


class TestRootEndpoint:
    """Tests for the root endpoint"""
    
    def test_root_redirects_to_static(self, client):
        """Test that root redirects to static index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_returns_all_activities(self, client):
        """Test that all activities are returned"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) > 0
        assert "Chess Club" in data
        assert "Programming Class" in data
    
    def test_activity_structure(self, client):
        """Test that each activity has the correct structure"""
        response = client.get("/activities")
        data = response.json()
        
        for name, details in data.items():
            assert "description" in details
            assert "schedule" in details
            assert "max_participants" in details
            assert "participants" in details
            assert isinstance(details["participants"], list)
            assert isinstance(details["max_participants"], int)


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_success(self, client):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Art Studio/signup?email=test@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "test@mergington.edu" in data["message"]
        
        # Verify participant was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "test@mergington.edu" in activities_data["Art Studio"]["participants"]
    
    def test_signup_nonexistent_activity(self, client):
        """Test signup for a non-existent activity"""
        response = client.post(
            "/activities/Nonexistent Club/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]
    
    def test_signup_duplicate_participant(self, client):
        """Test that signing up twice returns an error"""
        email = "duplicate@mergington.edu"
        
        # First signup
        response1 = client.post(
            f"/activities/Drama Club/signup?email={email}"
        )
        assert response1.status_code == 200
        
        # Second signup (should fail)
        response2 = client.post(
            f"/activities/Drama Club/signup?email={email}"
        )
        assert response2.status_code == 400
        data = response2.json()
        assert "already signed up" in data["detail"]
    
    def test_signup_with_url_encoded_activity_name(self, client):
        """Test signup with URL-encoded activity name"""
        response = client.post(
            "/activities/Basketball%20Team/signup?email=player@mergington.edu"
        )
        assert response.status_code == 200


class TestUnregisterFromActivity:
    """Tests for DELETE /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_success(self, client):
        """Test successful unregistration from an activity"""
        email = "remove@mergington.edu"
        
        # First signup
        client.post(f"/activities/Science Club/signup?email={email}")
        
        # Then unregister
        response = client.delete(
            f"/activities/Science Club/unregister?email={email}"
        )
        assert response.status_code == 200
        data = response.json()
        assert "Removed" in data["message"]
        assert email in data["message"]
        
        # Verify participant was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email not in activities_data["Science Club"]["participants"]
    
    def test_unregister_nonexistent_activity(self, client):
        """Test unregister from a non-existent activity"""
        response = client.delete(
            "/activities/Fake Club/unregister?email=test@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]
    
    def test_unregister_not_signed_up(self, client):
        """Test unregistering when not signed up"""
        response = client.delete(
            "/activities/Debate Team/unregister?email=notsignedup@mergington.edu"
        )
        assert response.status_code == 400
        data = response.json()
        assert "not signed up" in data["detail"]
    
    def test_unregister_existing_participant(self, client):
        """Test unregistering an existing participant"""
        # Chess Club has existing participants
        response = client.delete(
            "/activities/Chess Club/unregister?email=michael@mergington.edu"
        )
        assert response.status_code == 200
        
        # Verify removal
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "michael@mergington.edu" not in activities_data["Chess Club"]["participants"]


class TestActivityParticipantLimits:
    """Tests for activity participant limits"""
    
    def test_participants_count_matches_list(self, client):
        """Test that participant count is accurate"""
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        
        for name, details in activities_data.items():
            participant_count = len(details["participants"])
            assert participant_count <= details["max_participants"]


class TestEmailValidation:
    """Tests for email parameter handling"""
    
    def test_signup_with_special_characters_in_email(self, client):
        """Test signup with special characters in email"""
        from urllib.parse import quote
        email = "test+special@mergington.edu"
        response = client.post(
            f"/activities/Swimming Club/signup?email={quote(email)}"
        )
        assert response.status_code == 200
        
        # Verify participant was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email in activities_data["Swimming Club"]["participants"]
