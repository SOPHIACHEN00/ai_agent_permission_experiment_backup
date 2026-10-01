"""Free launcher contract tests run only on the remote server."""
import io
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

class Sink(io.BytesIO):
    def close(self): self.captured=self.getvalue(); super().close()

class LauncherTests(unittest.TestCase):
    def test_secret_only_in_stdin_and_launch_is_exclusive(self):
        from agent_permission_harness_v1.server_launch import launch
        captured={}
        class Child:
            pid=1234
            stdin=Sink()
        def popen(args,**kw):
            captured.update(args=args,kwargs=kw)
            return Child()
        with TemporaryDirectory() as d:
            root=Path(d); (root/'agent_permission_harness_v1'/'results').mkdir(parents=True)
            result=launch('SECRET_SENTINEL',project=root,popen=popen)
            self.assertEqual(result['pid'],1234)
            self.assertNotIn('SECRET_SENTINEL',str(captured))
            self.assertTrue(captured['kwargs']['start_new_session'])
            self.assertNotIn('OPENAI_API_KEY',captured['kwargs']['env'])
            self.assertEqual(Child.stdin.captured,b'SECRET_SENTINEL\n')
            self.assertIn('--key-stdin',captured['args'])
            self.assertIn('1800s',captured['args'])
            for f in root.rglob('*'):
                if f.is_file(): self.assertNotIn('SECRET_SENTINEL',f.read_text())
            with self.assertRaises(FileExistsError): launch('SECRET_SENTINEL',project=root,popen=popen)

    def test_invalid_key_stops_before_launch(self):
        from agent_permission_harness_v1.server_launch import launch
        with TemporaryDirectory() as d:
            for bad in ('','line\nbreak',' spaced ', 'x'*16385):
                with self.assertRaises(ValueError):
                    launch(bad,project=Path(d),popen=lambda *a,**k:self.fail('spawned'))
