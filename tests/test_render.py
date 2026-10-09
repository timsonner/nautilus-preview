import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from nautilus_preview.render import markdown_fragment

FIXTURE = """# Preview demo

```python
print(1)
```

![shot](demo.png)
"""


class RenderTests(unittest.TestCase):
    def test_heading_code_and_image(self) -> None:
        html = markdown_fragment(FIXTURE)
        self.assertIn("<h1>", html)
        self.assertIn("Preview demo", html)
        self.assertIn("<code", html)
        self.assertIn("print(1)", html)
        self.assertIn('src="demo.png"', html)


if __name__ == "__main__":
    unittest.main()
