# Self-Healing Automation Framework

An intelligent test automation framework that implements AI-powered self-healing capabilities for web element locators. The framework automatically recovers from locator failures by suggesting and trying alternative locators.

## Features

### Core Functionality
- **Intelligent Locator Recovery**
- **Multi-level Fallback System**
- **AI-Powered Healing**
- **Persistent Learning**

### Supported Locator Types
- CSS Selectors
- XPath
- ID
- Name
- Class Name
- Tag Name
- Link Text
- Partial Link Text

## Project Structure
```tree
self_healing_automation/
├── self_healer.py     # Core self-healing implementation
├── locators.py        # Element locator definitions
├── main.py           # Main execution script
├── utils.py          # Utility functions
├── ai_locators.json  # AI suggestions storage
└── .env              # Environment configuration
```

## Setup

### Prerequisites
- Python 3.x
- OpenAI API key
- Chrome/Firefox WebDriver

### Installation

1. Create virtual environment:
```bash
python -m venv venv
.\venv\Scripts\activate

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
- Create a .env file in the project root.
- Add your OpenAI API key:
```bash
OPENAI_API_KEY=your_api_key_here
```

## Usage

```python
from self_healer import SelfHealer
from selenium import webdriver

# Initialize
driver = webdriver.Chrome()
healer = SelfHealer(driver)

# Define locators
locators = {
    "primary": {"type": "id", "value": "submit"},
    "fallbacks": [
        {"type": "css selector", "value": "#submit"},
        {"type": "xpath", "value": "(//button[normalize-space()='Submit'])[1]"},
        {"type": "name", "value": "submit"}
    ]
}
```

# Use self-healing find
```python
try:
    element = healer.find_element(locators)
    element.click()
except Exception as e:
    print(f"Element not found: {e}")    
```

# Initialize

```python
driver = webdriver.Chrome()
healer = SelfHealer(driver)
```

# Define locators
```python
locators = {
    "primary": {"type": "id", "value": "submit1"},
    "fallbacks": [
        {"type": "css selector", "value": "#submit1"},
        {"type": "xpath", "value": "(//button[normalize-space()='Submit'])[2]"},
        {"type": "name", "value": "submit"}
    ]
}
```

# Use self-healing find
```python
try:
    element = healer.find_element(locators)
    element.click()
except Exception as e:
    print(f"Element not found: {e}")
```

## How It Works

### 1. Locator Attempt Sequence
- Tries primary locator
- Attempts fallback locators
- Checks saved AI suggestions
- Generates new AI suggestions

### 2. AI Healing Process
- Uses OpenAI to analyze failed attempts
- Suggests alternative locators
- Tries multiple strategies
- Saves successful findings in json file for future use

### 3. Learning System
Stores successful locators in `ai_locators.json`:
```json
{
    "type": "xpath",
    "value": "//button[contains(text(),\"Submit\")]",
    "success": true,
    "timestamp": "2025-05-12 13:03:29.899004"
}
```

## Best Practices

1. Locator Strategy
   
   - Use stable, unique identifiers
   - Provide multiple fallbacks
   - Prefer ID and CSS selectors

2. Maintenance
   
   - Monitor AI suggestions
   - Update fallback locators
   - Clean outdated entries

## Error Handling

- Detailed logging of failures
- Multiple recovery attempts
- Graceful degradation

## Contributing
1. Fork the repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Create Pull Request

## License
MIT License

This README provides comprehensive documentation of your self-healing automation framework, including setup instructions, usage examples, and implementation details. The content is based on your actual project structure and implementation.