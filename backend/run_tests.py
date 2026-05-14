import sys
import os

# 1. Force the correct 'py' module to be loaded
# Find where the real 'py' is (should be in env/Lib/site-packages/py)
env_path = os.path.abspath(os.path.join(os.getcwd(), "..", "env", "Lib", "site-packages"))
if env_path not in sys.path:
    sys.path.insert(0, env_path)

# Add backend to path
sys.path.insert(0, os.getcwd())

# 2. Mock 'py.path' if it's missing from the loaded 'py'
try:
    import py
    if not hasattr(py, 'path'):
        # If it's the wrong 'py', try to find the real one
        print("Wrong 'py' detected, attempting to fix...")
        import importlib.util
        spec = importlib.util.spec_from_file_location("py", os.path.join(env_path, "py", "__init__.py"))
        if spec:
            real_py = importlib.util.module_from_spec(spec)
            sys.modules["py"] = real_py
            spec.loader.exec_module(real_py)
            print("Fixed 'py' module.")
except Exception as e:
    print(f"Error fixing 'py': {e}")

# 3. Now import pytest
import pytest
if __name__ == "__main__":
    args = sys.argv[1:] if len(sys.argv) > 1 else ["tests/test_technician_assignment.py"]
    sys.exit(pytest.main(args))
