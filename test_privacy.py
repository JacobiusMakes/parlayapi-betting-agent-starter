"""Offline mode and explicit request boundary tests. No real API requests."""
import __future__
import contextlib
import getpass
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import types
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

import main as starter

ROOT = Path(__file__).parent
CANARY = 'TEST_ONLY_NOT_A_REAL_KEY'


class ClientError(RuntimeError):
    pass


class ClientContract:
    """Only the existing typed client's constructor and two method boundaries."""
    def __init__(self, api_key=None, base_url=None):
        self.api_key = api_key if api_key is not None else os.environ.get('PARLAY_API_KEY')
        self.base_url = base_url
    def demo_odds(self, sport):
        result = self._request('/v1/try/' + sport + '/odds', needs_key=False)
        return types.SimpleNamespace(events=result['events'])
    def get_odds(self, sport, **kwargs):
        return self._request('/v1/sports/' + sport + '/odds', {'markets': 'h2h'}, needs_key=True)


CORE = types.ModuleType('parlayapi_tools.core')
CORE.ParlayAPIClient = ClientContract
CORE.ParlayAPIError = ClientError
PACKAGE = types.ModuleType('parlayapi_tools')


class Response:
    status = 200
    def __init__(self, payload):
        self.body = json.dumps(payload).encode()
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
    def read(self, size):
        return self.body[:size]


class PrivacyTests(unittest.TestCase):
    def test_default_program_has_no_network_or_prompt_even_with_environment_key(self):
        output = io.StringIO()
        with patch.dict(os.environ, {'PARLAY_API_KEY': CANARY}), \
             patch.object(starter, 'build_opener', side_effect=AssertionError('Unexpected network')) as network, \
             patch.object(getpass, 'getpass', side_effect=AssertionError('Unexpected key prompt')) as prompt, \
             contextlib.redirect_stdout(output):
            self.assertEqual(starter.main([]), 0)
        network.assert_not_called()
        prompt.assert_not_called()
        self.assertNotIn(CANARY, output.getvalue())

    def test_notebook_run_all_does_not_install_connect_or_prompt(self):
        notebook = json.loads((ROOT / 'starter.ipynb').read_text())
        output = io.StringIO()
        namespace = {'__name__': 'notebook'}
        with patch.dict(os.environ, {'PARLAY_API_KEY': CANARY}), \
             patch.object(socket.socket, 'connect', side_effect=AssertionError('Unexpected socket')), \
             patch.object(subprocess, 'run', side_effect=AssertionError('Unexpected install')) as install, \
             patch.object(getpass, 'getpass', side_effect=AssertionError('Unexpected key prompt')) as prompt, \
             contextlib.redirect_stdout(output):
            for cell in notebook['cells']:
                if cell['cell_type'] == 'code':
                    exec(compile(''.join(cell['source']), '<notebook-cell>', 'exec',
                                 flags=__future__.annotations.compiler_flag), namespace)
                    self.assertEqual(cell['outputs'], [])
                    self.assertIsNone(cell['execution_count'])
        install.assert_not_called()
        prompt.assert_not_called()
        self.assertNotIn(CANARY, output.getvalue())
        self.assertTrue(notebook['metadata']['colab']['private_outputs'])

    def request_for(self, args, payload):
        module_patch = patch.dict(sys.modules, {'parlayapi_tools': PACKAGE, 'parlayapi_tools.core': CORE})
        with module_patch, \
             patch.object(starter, 'build_opener') as factory, \
             patch.object(getpass, 'getpass', return_value=CANARY) as prompt, \
             patch.dict(os.environ, {'PARLAY_API_KEY': CANARY}), \
             contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            factory.return_value.open.return_value = Response(payload)
            self.assertEqual(starter.main(args), 0)
        self.assertEqual(factory.return_value.open.call_count, 1)
        self.assertIsInstance(factory.call_args.args[0], starter.NoRedirect)
        request = factory.return_value.open.call_args.args[0]
        self.assertEqual(factory.return_value.open.call_args.kwargs['timeout'], 30)
        self.assertNotIn(CANARY, request.full_url)
        return request, prompt

    def test_demo_is_one_request_without_environment_key(self):
        request, prompt = self.request_for(['--demo'], {'demo': True, 'events': []})
        self.assertEqual(request.full_url, 'https://parlay-api.com/v1/try/americanfootball_nfl/odds')
        self.assertIsNone(request.get_header('X-api-key'))
        prompt.assert_not_called()

    def test_account_is_explicit_and_key_is_header_only(self):
        request, prompt = self.request_for(['--account'], [])
        self.assertTrue(request.full_url.startswith('https://parlay-api.com/v1/sports/'))
        self.assertEqual(request.get_header('X-api-key'), CANARY)
        prompt.assert_called_once()

    def test_bad_key_is_rejected_before_transport(self):
        with patch.object(starter, 'create_client') as client:
            with self.assertRaises(ValueError):
                starter.fetch_events('account', 'baseball_mlb', CANARY + '\n')
        client.assert_not_called()

    def test_redirect_and_remote_error_do_not_leak_or_retry(self):
        self.assertIsNone(starter.NoRedirect().redirect_request(None, None, None, None, None, None, None))
        errors = [URLError(CANARY), HTTPError('https://parlay-api.com/?apiKey=' + CANARY, 302,
                                           CANARY, {}, io.BytesIO(CANARY.encode()))]
        for error in errors:
            with self.subTest(error=type(error).__name__):
                output = io.StringIO()
                with patch.dict(sys.modules, {'parlayapi_tools': PACKAGE, 'parlayapi_tools.core': CORE}), \
                     patch.object(starter, 'build_opener') as factory, \
                     patch.object(getpass, 'getpass', return_value=CANARY), \
                     contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                    factory.return_value.open.side_effect = error
                    self.assertEqual(starter.main(['--account']), 1)
                self.assertNotIn(CANARY, output.getvalue())
                self.assertEqual(factory.return_value.open.call_count, 1)

    def test_optional_notebook_install_uses_same_exact_commit_pin(self):
        requirement = (ROOT / 'requirements.txt').read_text().strip()
        self.assertRegex(requirement, r'^parlayapi-agent-tools @ git\+https://github\.com/JacobiusMakes/parlayapi-agent-tools@[0-9a-f]{40}$')
        notebook = json.loads((ROOT / 'starter.ipynb').read_text())
        namespace = {'MODE': 'demo'}
        with patch.object(subprocess, 'run') as install:
            exec(compile(''.join(notebook['cells'][2]['source']), '<install-cell>', 'exec'), namespace)
        install.assert_called_once()
        self.assertEqual(install.call_args.args[0][-1], requirement)
        self.assertTrue(install.call_args.kwargs['check'])

    def test_codespaces_has_no_attach_or_start_execution(self):
        config = json.loads((ROOT / '.devcontainer/devcontainer.json').read_text())
        self.assertNotIn('postAttachCommand', config)
        self.assertNotIn('postStartCommand', config)


if __name__ == '__main__':
    unittest.main()
