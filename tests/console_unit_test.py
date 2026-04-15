import importlib.util
import os
import sys
import unittest
from unittest.mock import MagicMock

# Mock curses before importing console — curses requires a real terminal and
# may not be installed (e.g. no windows-curses on this host).
_mock_curses = MagicMock()
_mock_curses.LINES = 24
_mock_curses.COLS = 80
_mock_curses.KEY_BACKSPACE = 263
_mock_curses.KEY_ENTER = 343
_mock_curses.KEY_END = 360
sys.modules["curses"] = _mock_curses
sys.modules["_curses"] = MagicMock()

# Load console.py directly from its file path to avoid executing
# trade_strategy/__init__.py (which pulls in main.py and finance_client).
_console_path = os.path.join(
    os.path.dirname(__file__), "..", "trade_strategy", "console.py"
)
_spec = importlib.util.spec_from_file_location("trade_strategy.console", _console_path)
_console_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_console_mod)

Command = _console_mod.Command
InputBox = _console_mod.InputBox
CursesHandler = _console_mod.CursesHandler


class TestCommand(unittest.TestCase):
    def test_all_commands_start_with_slash(self):
        for cmd in Command.all_commands():
            self.assertTrue(cmd.startswith("/"), f"Command '{cmd}' does not start with '/'")

    def test_all_commands_contains_expected(self):
        commands = Command.all_commands()
        self.assertIn(Command.disable, commands)
        self.assertIn(Command.disable_long, commands)
        self.assertIn(Command.disable_short, commands)
        self.assertIn(Command.enable, commands)
        self.assertIn(Command.enable_long, commands)
        self.assertIn(Command.enable_short, commands)
        self.assertIn(Command.update, commands)
        self.assertIn(Command.end, commands)

    def test_end_command_value(self):
        self.assertEqual(Command.end, "/exit")

    def test_disable_command_value(self):
        self.assertEqual(Command.disable, "/disable")

    def test_enable_command_value(self):
        self.assertEqual(Command.enable, "/enable")


class TestInputBox(unittest.TestCase):
    def setUp(self):
        self.box = InputBox()

    def test_initial_input_is_empty(self):
        self.assertEqual(self.box.get_current_input(), "")

    def test_add_chars(self):
        self.box.add_char(ord("/"))
        self.box.add_char(ord("e"))
        self.box.add_char(ord("x"))
        self.assertEqual(self.box.get_current_input(), "/ex")

    def test_backspace_removes_last_char(self):
        self.box.add_char(ord("a"))
        self.box.add_char(ord("b"))
        self.box.add_char(8)  # backspace ASCII
        self.assertEqual(self.box.get_current_input(), "a")

    def test_backspace_on_empty_does_not_raise(self):
        self.box.add_char(8)
        self.assertEqual(self.box.get_current_input(), "")

    def test_reset_clears_input(self):
        self.box.add_char(ord("a"))
        self.box.reset()
        self.assertEqual(self.box.get_current_input(), "")


class TestCursesHandler(unittest.TestCase):
    def _make_handler(self, input_box):
        stdscr = MagicMock()
        handler = CursesHandler(stdscr, input_box)
        return handler, stdscr

    def _get_addstr_texts(self, stdscr):
        """Return the string argument from every addstr call."""
        texts = []
        for c in stdscr.addstr.call_args_list:
            args = c.args
            # addstr(y, x, text) or addstr(text)
            texts.append(args[2] if len(args) >= 3 else args[0])
        return texts

    def test_log_mode_shows_log_lines(self):
        box = InputBox()
        handler, stdscr = self._make_handler(box)
        handler.log_lines = ["log line 1", "log line 2"]

        handler.emit(None)

        texts = self._get_addstr_texts(stdscr)
        self.assertIn("log line 1", texts)
        self.assertIn("log line 2", texts)

    def test_command_mode_shows_header_on_slash(self):
        box = InputBox()
        box.add_char(ord("/"))
        handler, stdscr = self._make_handler(box)

        handler.emit(None)

        texts = self._get_addstr_texts(stdscr)
        self.assertIn("Available commands:", texts)

    def test_command_mode_shows_all_commands_on_slash(self):
        box = InputBox()
        box.add_char(ord("/"))
        handler, stdscr = self._make_handler(box)

        handler.emit(None)

        texts = self._get_addstr_texts(stdscr)
        for cmd in Command.all_commands():
            self.assertIn(cmd, texts)

    def test_command_mode_filters_by_prefix(self):
        box = InputBox()
        for ch in "/dis":
            box.add_char(ord(ch))
        handler, stdscr = self._make_handler(box)

        handler.emit(None)

        texts = self._get_addstr_texts(stdscr)
        self.assertIn(Command.disable, texts)
        self.assertIn(Command.disable_long, texts)
        self.assertIn(Command.disable_short, texts)
        self.assertNotIn(Command.enable, texts)
        self.assertNotIn(Command.enable_long, texts)

    def test_command_mode_hides_log_lines(self):
        box = InputBox()
        box.add_char(ord("/"))
        handler, stdscr = self._make_handler(box)
        handler.log_lines = ["should not appear"]

        handler.emit(None)

        texts = self._get_addstr_texts(stdscr)
        self.assertNotIn("should not appear", texts)

    def test_prompt_shows_current_input(self):
        box = InputBox()
        for ch in "/exit":
            box.add_char(ord(ch))
        handler, stdscr = self._make_handler(box)

        handler.emit(None)

        texts = self._get_addstr_texts(stdscr)
        self.assertIn("Command: /exit", texts)

    def test_backspace_past_slash_restores_log_mode(self):
        box = InputBox()
        box.add_char(ord("/"))
        box.add_char(8)  # backspace — input is now empty
        handler, stdscr = self._make_handler(box)
        handler.log_lines = ["a log line"]

        handler.emit(None)

        texts = self._get_addstr_texts(stdscr)
        self.assertIn("a log line", texts)
        self.assertNotIn("Available commands:", texts)

    def test_log_lines_accumulate_on_emit(self):
        box = InputBox()
        handler, stdscr = self._make_handler(box)
        record = MagicMock()
        record.getMessage.return_value = "msg"
        handler.format = lambda r: "formatted: msg"

        handler.emit(record)

        self.assertEqual(len(handler.log_lines), 1)
        self.assertEqual(handler.log_lines[0], "formatted: msg")


if __name__ == "__main__":
    unittest.main()
