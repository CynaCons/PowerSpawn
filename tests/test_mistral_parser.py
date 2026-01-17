"""Test Mistral parsing logic."""
from PowerSpawn.providers.mistral import extract_mistral_text

class MockOutput:
    def __init__(self, type, content):
        self.type = type
        self.content = content

class MockResponse:
    def __init__(self, outputs):
        self.outputs = outputs

def test_extract_simple_text():
    """Test extracting simple text content."""
    response = MockResponse([
        MockOutput("tool.execution", "ignored"),
        MockOutput("message.output", "hello world")
    ])
    assert extract_mistral_text(response) == "hello world"

def test_extract_list_content():
    """Test extracting content from list of blocks."""
    # Mock content block objects
    class Block:
        def __init__(self, text):
            self.type = "text"
            self.text = text
            
    response = MockResponse([
        MockOutput("message.output", [Block("part1"), Block(" part2")])
    ])
    assert extract_mistral_text(response) == "part1 part2"

def test_extract_no_message():
    """Test extracting when no message output exists."""
    response = MockResponse([
        MockOutput("tool.execution", "result")
    ])
    assert extract_mistral_text(response) == ""
