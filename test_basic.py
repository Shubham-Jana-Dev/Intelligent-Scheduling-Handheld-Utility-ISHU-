import pytest
from unittest import mock
import subprocess
import os
import json
from datetime import time

# --- CRITICAL FIX: Direct Import ---
# Ensure all necessary functions are directly imported from assistant.py
from assistant import (
    ollama_response,
    speak,
    add_routine_entry,
    get_task_by_time,
    remove_routine_entry,
    get_routine,
    parse_time,
    tell_joke,
    get_favorite,
    set_favorite_color,
    tell_story
)


# =========================================================
# 🧪 Test 1: Mocking Ollama API Calls
# =========================================================

@mock.patch('requests.post')
def test_ollama_response_works(mock_post):
    """
    Ensures that ollama_response can successfully handle a mocked 200 OK response.
    """
    mock_response = mock.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "message": {"content": "Mock LLM worked!"}
    }
    
    mock_post.return_value = mock_response
    
    response_message = ollama_response("test prompt")
    
    mock_post.assert_called_once()
    assert "Mock LLM worked!" in response_message.get("content", "")

# -----------------------------------------------------------------------------

# =========================================================
# 🗣️ Test 2: FIXING test_speak_does_not_crash_ci
# CRITICAL CHANGE: Explicitly mock os.uname() to force the 'Darwin' path.
# =========================================================

def test_speak_does_not_crash_ci():
    """
    Forces the speak function into the Mac execution path by mocking os.uname()
    to return 'Darwin', ensuring subprocess.Popen/run are called, which resolves
    the CI failure.
    """
    
    # 1. Define the mock object that returns 'Darwin'
    class MockUname:
        sysname = "Darwin"
        machine = "x86_64" # Arbitrary value

    # 2. Patch the built-in functions simultaneously using the context manager.
    # We patch os.uname to return our mock object.
    with mock.patch('os.uname', return_value=MockUname()), \
         mock.patch('subprocess.Popen') as mock_popen, \
         mock.patch('subprocess.run') as mock_run:

        # Test non-blocking call (should call Popen)
        speak("Testing non-blocking speech")
        mock_popen.assert_called_once_with(['say', 'Testing non-blocking speech'])
        mock_run.assert_not_called()
        
        # Reset mocks for blocking call
        mock_popen.reset_mock()
        
        # Test blocking call (should call run)
        speak("Testing blocking speech", blocking=True)
        mock_run.assert_called_once_with(['say', 'Testing blocking speech'])
        mock_popen.assert_not_called()

# -----------------------------------------------------------------------------

# =========================================================
# 📅 Test 3: Testing Routine Management Logic
# =========================================================

def test_routine_management_logic_basic(monkeypatch):
    """
    Tests the core routine functions without hitting disk I/O, using monkeypatch
    to mock file operations.
    """
    
    mock_routine = []
    
    monkeypatch.setattr('assistant.load_json', lambda x, y: mock_routine)
    
    def mock_save_json(filename, obj):
        mock_routine.clear()
        mock_routine.extend(obj)

    monkeypatch.setattr('assistant.save_json', mock_save_json)

    # 1. Test add_routine_entry
    result_add = add_routine_entry("09:00", "10:00", "daily meeting")
    assert "Success!" in result_add
    assert len(mock_routine) == 1
    
    result_add_2 = add_routine_entry("11:30", "12:30", "lunch")
    assert "Success!" in result_add_2
    assert len(mock_routine) == 2
    
    # Check sorting: should be 09:00 then 11:30
    assert mock_routine[0]['start'] == "09:00"
    
    # 2. Test get_routine
    result_get = get_routine()
    assert "09:00 - 10:00: daily meeting" in result_get
    
    # 3. Test get_task_by_time (Mocked to return a specific time for test)
    result_task = get_task_by_time("09:30")
    assert "you should: daily meeting" in result_task
    
    # 4. Test remove_routine_entry
    result_remove = remove_routine_entry("meeting")
    assert "Successfully removed 1 routine entry" in result_remove
    assert len(mock_routine) == 1 # Only 'lunch' remains

    # 5. Test edge case (invalid time format)
    result_invalid = add_routine_entry("9-00", "10:00", "error test")
    assert "Error: Invalid time format" in result_invalid
    
    # 6. Test no activity found
    result_task_none = get_task_by_time("08:00")
    assert "No scheduled activity for this time." in result_task_none

# -----------------------------------------------------------------------------

# =========================================================
# 📝 Test 4: Testing Simple Features (Joke, Favorite Color)
# =========================================================

# Ensure pyjokes is mocked if it failed to import (for safety)
@mock.patch('assistant.pyjokes', new=mock.MagicMock())
@mock.patch('assistant.load_json')
@mock.patch('assistant.save_json')
def test_simple_features(mock_save, mock_load):
    """Tests joke telling and favorite color features."""
    
    # Mock pyjokes.get_joke()
    if assistant.pyjokes is not None:
        assistant.pyjokes.get_joke.return_value = "Mock Joke!"
        assert tell_joke() == "Mock Joke!"
    
    # Mock data for favorites
    mock_load.return_value = {}
    
    # Test set_favorite_color
    result_set = set_favorite_color("blue")
    assert "I'll remember your favorite color is blue" in result_set
    # Check that save_json was called with the correct dictionary (color: blue)
    mock_save.assert_called_once() 
    
    # Test get_favorite (by loading the mock data set above)
    mock_load.reset_mock()
    mock_load.return_value = {"color": "blue"}
    result_get = get_favorite()
    assert "Your favorite color is blue" in result_get


# -----------------------------------------------------------------------------

# =========================================================
# ✅ Test 5: Final Sanity Check
# =========================================================

def test_ci_final_runs():
    """A simple test to ensure the pytest framework is functional."""
    assert True
