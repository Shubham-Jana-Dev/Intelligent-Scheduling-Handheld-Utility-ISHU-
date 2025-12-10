import pytest
from unittest import mock
import subprocess
import os
import json
from datetime import time

# --- CRITICAL FIX: Direct Import ---
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
# CRITICAL CHANGE: Use monkeypatch to set IS_TESTING environment variable.
# =========================================================

def test_speak_does_not_crash_ci(monkeypatch):
    """
    Mocks subprocess calls and forces the 'say' command path in the speak function
    by setting the IS_TESTING environment variable.
    """
    
    # 1. CRITICAL: Force the speak function into the Mac/Testing path
    monkeypatch.setenv("IS_TESTING", "True")

    # 2. Mock subprocess.Popen for non-blocking calls
    with mock.patch('subprocess.Popen') as mock_popen, \
         mock.patch('subprocess.run') as mock_run:

        # Test non-blocking call (should call Popen)
        speak("Testing non-blocking speech")
        mock_popen.assert_called_once()
        mock_run.assert_not_called()
        
        # Reset mocks for blocking call
        mock_popen.reset_mock()
        
        # Test blocking call (should call run)
        speak("Testing blocking speech", blocking=True)
        mock_run.assert_called_once()
        mock_popen.assert_not_called()

# -----------------------------------------------------------------------------

# =========================================================
# 📅 Test 3: Testing Routine Management Logic
# =========================================================

def test_routine_management_logic_basic(monkeypatch):
    """
    Tests the core routine functions without hitting disk I/O.
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
# ✅ Test 4: Final Sanity Check
# =========================================================

def test_ci_final_runs():
    """A simple test to ensure the pytest framework is functional."""
    assert True
