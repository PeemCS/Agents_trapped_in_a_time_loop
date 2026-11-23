from io import BytesIO
import json
from unittest import TestCase
from unittest.mock import Mock, patch

from server.app import create_server


class ServiceTests(TestCase):
    def handler(self, token="test-token"):
        model = Mock()
        model.generate.return_value = {"outputs": [{"answer": "ready"}]}
        with patch("server.app.ThreadingHTTPServer") as factory:
            create_server("127.0.0.1", 8000, token, model)
        handler_type = factory.call_args.args[1]
        handler = handler_type.__new__(handler_type)
        handler.send_json = Mock()
        handler.log_error = Mock()
        return handler, model

    def test_health_can_be_checked_without_generating(self):
        handler, model = self.handler()
        handler.path = "/health"
        handler.do_GET()
        self.assertEqual(handler.send_json.call_args.args[0], 200)
        model.generate.assert_not_called()

    def test_missing_token_cannot_reach_model(self):
        handler, model = self.handler()
        handler.path = "/generate"
        handler.headers = {}
        handler.do_POST()
        self.assertEqual(handler.send_json.call_args.args[0], 401)
        model.generate.assert_not_called()

    def test_authenticated_json_reaches_model(self):
        handler, model = self.handler()
        payload = {"messages": [{"role": "user", "content": "Say ready."}]}
        body = json.dumps(payload).encode()
        handler.path = "/generate"
        handler.headers = {"Authorization": "Bearer test-token", "Content-Length": str(len(body))}
        handler.rfile = BytesIO(body)
        handler.do_POST()
        model.generate.assert_called_once_with(payload)
        handler.send_json.assert_called_once_with(200, {"outputs": [{"answer": "ready"}]})

    def test_malformed_input_is_reported_without_an_inference(self):
        handler, model = self.handler()
        handler.path = "/generate"
        handler.headers = {"Authorization": "Bearer test-token", "Content-Length": "3"}
        handler.rfile = BytesIO(b"x{}")
        handler.do_POST()
        self.assertEqual(handler.send_json.call_args.args[0], 400)
        model.generate.assert_not_called()

    def test_busy_inference_returns_before_a_second_model_call(self):
        handler, model = self.handler()
        other = type(handler).__new__(type(handler))
        other.send_json = Mock()
        other.log_error = Mock()
        for item in (handler, other):
            item.path = "/generate"
            item.headers = {"Authorization": "Bearer test-token", "Content-Length": "2"}
            item.rfile = BytesIO(b"{}")

        def in_flight(_):
            other.do_POST()
            return {"outputs": [{"answer": "ready"}]}

        model.generate.side_effect = in_flight
        handler.do_POST()
        self.assertEqual(other.send_json.call_args.args[0], 429)
        self.assertEqual(handler.send_json.call_args.args[0], 200)
        model.generate.assert_called_once()
