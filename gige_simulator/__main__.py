# This allows running the simulator using "python -m gige_simulator"
# Ensure that the main logic can correctly find other modules within gige_simulator.
# The core.main.py script already adds the project root to sys.path if run directly,
# which helps, but for module execution, Python's import system should handle it.

from gige_simulator.core.main import run_simulator

if __name__ == "__main__":
    run_simulator()
```
