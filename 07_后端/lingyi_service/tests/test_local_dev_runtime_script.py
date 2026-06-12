"""Guard tests for the local-dev runtime launcher."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import unittest


class LocalDevRuntimeScriptTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.backend_root = Path(__file__).resolve().parents[1]
        cls.script_path = cls.backend_root / "scripts" / "run_local_dev_runtime.sh"

    def _run_script(self, *, host: str | None = None, port: str | None = None) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env.pop("LINGYI_LOCAL_DEV_HOST", None)
        env.pop("LINGYI_LOCAL_DEV_PORT", None)
        if host is not None:
            env["LINGYI_LOCAL_DEV_HOST"] = host
        if port is not None:
            env["LINGYI_LOCAL_DEV_PORT"] = port
        return subprocess.run(
            ["bash", str(self.script_path)],
            cwd=self.backend_root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_rejects_non_loopback_host(self) -> None:
        result = self._run_script(host="0.0.0.0", port="8000")

        self.assertEqual(result.returncode, 2, result)
        self.assertIn("仅允许本地 127.0.0.1:8000", result.stderr)
        self.assertNotIn("启动本地 dev runtime", result.stdout)

    def test_rejects_non_default_port(self) -> None:
        result = self._run_script(host="127.0.0.1", port="9000")

        self.assertEqual(result.returncode, 2, result)
        self.assertIn("仅允许本地 127.0.0.1:8000", result.stderr)
        self.assertNotIn("启动本地 dev runtime", result.stdout)


if __name__ == "__main__":
    unittest.main()
