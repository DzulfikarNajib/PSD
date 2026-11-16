import sys
from streamlit.testing.v1 import AppTest

print("1. Starting", flush=True)
at = AppTest.from_file("home.py", default_timeout=5)
print("2. Created AppTest", flush=True)
at.run()
print("3. Finished run", flush=True)
