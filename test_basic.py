import json
import os
import pytest
import datetime 
from assistant import get_routine, get_task_by_time, ROUTINE_FILE_PATH, parse_time 

# --- Setup Fixtures (Mock Data) ---

@pytest.fixture
def mock_routine_data():
    """Provides a sample routine structure for testing."""
    return [
        {"start": "09:00", "end": "10:00", "activity": "Wake up and meditate"}, 
        {"start": "10:00", "end": "11:00", "activity": "Breakfast and check emails"},
        {"start": "11:00", "end": "12:30", "activity": "Morning walk or yoga"}, 
        {"start": "12:30", "end": "13:30", "activity": "Lunch break"}, 
        {"start": "13:30", "end": "15:30", "activity": "Work on personal project X"}, 
    ]

@pytest.fixture(autouse=True)
def mock_json_file(tmp_path, mock_routine_data, monkeypatch):
    """
    CRITICAL FIX: Creates a temporary routine.json file for tests to use in the FLAT structure.
    Uses monkeypatch to directly override the variable in assistant.py.
    """
    # Create the mock routine.json file directly in the temporary root path
    file_path = tmp_path / "routine.json"
    with open(file_path, "w") as f:
        json.dump(mock_routine_data, f, indent=4)
    
    # 1. Patch the ROUTINE_FILE_PATH variable in assistant.py to point to the mock file
    # This ensures the assistant uses the mock file instead of the real one.
    monkeypatch.setattr('assistant.ROUTINE_FILE_PATH', str(file_path))
    
    # 2. Mock the favorites file path similarly for safety
    favorites_path = tmp_path / "favorites.json"
    monkeypatch.setattr('assistant.FAVORITES_FILE_PATH', str(favorites_path))

    yield


# --- Test Cases ---

def test_get_routine_success():
    """Test that get_routine loads data successfully."""
    routine_json_string = get_routine()
    
    routine = json.loads(routine_json_string) 
    
    assert isinstance(routine, list)
    assert len(routine) > 0
    assert "activity" in routine[0]


def test_get_task_by_time_current_task(mocker):
    """Test finding a task currently in progress."""
    
    # Setup mock for datetime.now() to return a time within the 10:00-11:00 slot (10:30)
    mock_dt_class = mocker.MagicMock(spec=datetime.datetime)
    mock_now_dt = datetime.datetime.combine(datetime.date.today(), datetime.time(10, 30))
    
    # Configure the Mock Class
    mock_dt_class.now.return_value = mock_now_dt
    mock_dt_class.today.return_value = mock_now_dt
    mock_dt_class.combine = datetime.datetime.combine # Use real combine method
    
    # Patch the imported 'datetime' object in assistant.py
    mocker.patch('assistant.datetime', mock_dt_class)
    
    # get_task_by_time() with no argument uses the mocked current time (10:30)
    result = get_task_by_time() 
    result_data = json.loads(result)
    
    assert result_data["status"] == "found"
    assert "Breakfast and check emails" in result_data["activity"]


def test_get_task_by_time_next_task(mocker):
    """Test finding a task by explicit time, and a next task."""
    
    # --- Test 1: Querying a time *inside* an activity ---
    result_in_task = get_task_by_time(query_time="10:00") 
    result_data_in_task = json.loads(result_in_task)
    
    assert result_data_in_task["status"] == "found"
    assert "Breakfast and check emails" in result_data_in_task["activity"]
    
    # --- Test 2: Querying a time *between* activities (to find the next one) ---
    
    # Setup mock environment for explicit query (required for the datetime.combine path)
    mock_dt_class = mocker.MagicMock(spec=datetime.datetime)
    mock_today_date = datetime.date(2025, 12, 13)
    
    mock_dt_class.today.return_value = mocker.MagicMock(date=lambda: mock_today_date)
    mock_dt_class.combine = datetime.datetime.combine
    
    mocker.patch('assistant.datetime', mock_dt_class)
    
    # Time 15:35 is after the last entry (15:30) in the mock data
    result_gap = get_task_by_time(query_time="15:35")
    result_data_gap = json.loads(result_gap)
    
    # The logic should wrap around and find the first task of the day (09:00)
    assert result_data_gap["status"] == "next_found"
    assert "Wake up and meditate" in result_data_gap["activity"] 


def test_get_task_by_time_invalid_time():
    """Test handling of invalid time format."""
    result = get_task_by_time(query_time="4 PM") 
    assert '"status": "error"' in result
    assert "Invalid time format" in result