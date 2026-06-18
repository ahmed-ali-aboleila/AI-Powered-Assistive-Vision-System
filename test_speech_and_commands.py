import sys
import os
import unittest
from unittest.mock import MagicMock

# Force UTF-8 encoding for stdout/stderr to avoid Windows CP1252 encoding issues
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Add current directory to path and change working directory to it
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)
os.chdir(script_dir)

import config
from logic_controller import (
    LogicController,
    _WAKE_WORDS, _CLOSE_WORDS, _AR_WORDS, _EN_WORDS,
    _AUTO_PAUSE_WORDS, _AUTO_RESUME_WORDS,
    _REG_WORDS, _IMPROVE_WORDS, _DEL_WORDS, _CLEAR_ALL_WORDS, _BLOCK_WORDS, _UNBLK_WORDS,
    _WHO_WORDS, _LIST_WORDS, _QUIET_WORDS, _SPEAK_WORDS,
    _MALE_AR_WORDS, _FEMALE_AR_WORDS, _MALE_EN_WORDS, _FEMALE_EN_WORDS
)
from shared.stt import OFFLINE_COMMANDS_EN, OFFLINE_COMMANDS_AR

class TestVoiceCommands(unittest.TestCase):
    def setUp(self):
        self.tts = MagicMock()
        self.stt = MagicMock()
        self.reg = MagicMock()
        self.proc = MagicMock()
        self.db = MagicMock()
        
        # Default behavior
        self.db.names.return_value = ["أحمد", "John"]
        self.stt.yes_no.return_value = True
        
        # Instantiate controller
        self.lc = LogicController(self.tts, self.stt, self.reg, self.proc, self.db)
        # Suppress the background thread starting
        self.lc._start_listener = MagicMock()

    def test_wake_words_stripping(self):
        print("\nTesting Wake Words & Prefix Stripping:")
        for w in _WAKE_WORDS:
            phrase = f"{w} مين ده"
            stripped = self.lc._strip_wake_word(phrase)
            self.assertEqual(stripped, "مين ده")
            print(f"  ✓ '{phrase}' stripped to '{stripped}'")

    def test_language_commands(self):
        print("\nTesting Language Switch Commands:")
        for w in _AR_WORDS:
            self.lc._handle_command(w)
            self.assertEqual(config.LANGUAGE, "ar")
            self.tts.set_language.assert_called_with("ar")
            print(f"  ✓ '{w}' -> Switched to Arabic")
            
        for w in _EN_WORDS:
            self.lc._handle_command(w)
            self.assertEqual(config.LANGUAGE, "en")
            self.tts.set_language.assert_called_with("en")
            print(f"  ✓ '{w}' -> Switched to English")

    def test_registration_commands(self):
        print("\nTesting Registration Commands:")
        # Should say "no person" if name is None
        self.lc._current_name = None
        for w in _REG_WORDS:
            self.lc._handle_command(w)
            self.tts.say_wait.assert_called_with(self.lc._t("no_person"))
            print(f"  ✓ '{w}' (no person) -> Handled correctly")
            
        # Should say "already registered" if name is known
        self.lc._current_name = "Ahmed"
        for w in _REG_WORDS:
            self.reg.start_register.reset_mock()
            self.lc._handle_command(w)
            self.reg.start_register.assert_called_once()
            print(f"  ✓ '{w}' (already registered) -> Handled correctly")

        # Should start registration if name is Unknown
        self.lc._current_name = "Unknown"
        for w in _REG_WORDS:
            self.reg.start_register.reset_mock()
            self.lc._handle_command(w)
            self.reg.start_register.assert_called_once()
            print(f"  ✓ '{w}' (Unknown person) -> Started registration flow")

    def test_improve_commands(self):
        print("\nTesting Improve Commands:")
        self.lc._current_name = "Ahmed"
        for w in _IMPROVE_WORDS:
            self.reg.start_improve.reset_mock()
            self.lc._handle_command(w)
            self.reg.start_improve.assert_called_once_with("Ahmed")
            print(f"  ✓ '{w}' (known person) -> Started improve flow")

        self.lc._current_name = "Unknown"
        for w in _IMPROVE_WORDS:
            self.reg.start_improve.reset_mock()
            self.lc._handle_command(w)
            self.reg.start_improve.assert_called_once_with()
            print(f"  ✓ '{w}' (ask name) -> Started improve flow")

    def test_delete_commands(self):
        print("\nTesting Delete Commands:")
        for w in _DEL_WORDS:
            self.reg.start_delete.reset_mock()
            self.lc._handle_command(w)
            self.reg.start_delete.assert_called_once()
            print(f"  ✓ '{w}' -> Started delete flow")

    def test_block_commands(self):
        print("\nTesting Block Commands:")
        self.lc._current_name = "Unknown"
        for w in _BLOCK_WORDS:
            self.reg.start_block.reset_mock()
            self.lc._handle_command(w)
            self.reg.start_block.assert_called_once()
            print(f"  ✓ '{w}' -> Started block flow")

    def test_unblock_commands(self):
        print("\nTesting Unblock Commands:")
        for w in _UNBLK_WORDS:
            self.reg.start_unblock.reset_mock()
            self.lc._handle_command(w)
            self.reg.start_unblock.assert_called_once()
            print(f"  ✓ '{w}' -> Started unblock flow")

    def test_who_commands(self):
        print("\nTesting Identify (Who) Commands:")
        self.lc._current_name = "John"
        self.lc._current_emotion = "Happy"
        for w in _WHO_WORDS:
            self.lc._handle_command(w)
            self.tts.say_wait.assert_called()
            print(f"  ✓ '{w}' -> Identified '{self.lc._current_name}' as '{self.lc._current_emotion}'")

    def test_list_commands(self):
        print("\nTesting List Names Commands:")
        for w in _LIST_WORDS:
            self.lc._handle_command(w)
            self.tts.say_wait.assert_called()
            print(f"  ✓ '{w}' -> Read registered name list")

    def test_quiet_speak_commands(self):
        print("\nTesting Silence & Resume Commands:")
        for w in _QUIET_WORDS:
            self.lc._handle_command(w)
            self.tts.set_quiet.assert_called_with(True)
            print(f"  ✓ '{w}' -> Quiet mode ON")
            
        for w in _SPEAK_WORDS:
            self.lc._handle_command(w)
            self.tts.set_quiet.assert_called_with(False)
            print(f"  ✓ '{w}' -> Quiet mode OFF")

    def test_voice_gender_commands(self):
        print("\nTesting Voice Gender Switching Commands:")
        for w in _MALE_AR_WORDS:
            self.lc._handle_command(w)
            self.tts.set_voice.assert_called_with("ar", "male")
            print(f"  ✓ '{w}' -> Switched to Arabic Male Voice")
            
        for w in _FEMALE_AR_WORDS:
            self.lc._handle_command(w)
            self.tts.set_voice.assert_called_with("ar", "female")
            print(f"  ✓ '{w}' -> Switched to Arabic Female Voice")

        for w in _MALE_EN_WORDS:
            self.lc._handle_command(w)
            self.tts.set_voice.assert_called_with("en", "male")
            print(f"  ✓ '{w}' -> Switched to English Male Voice")

        for w in _FEMALE_EN_WORDS:
            self.lc._handle_command(w)
            self.tts.set_voice.assert_called_with("en", "female")
            print(f"  ✓ '{w}' -> Switched to English Female Voice")

    def test_auto_announcement_commands(self):
        print("\nTesting Automatic Announcement Pause/Resume Commands:")
        for w in _AUTO_PAUSE_WORDS:
            self.tts.reset_mock()
            self.lc._handle_command(w)
            self.assertFalse(self.lc._auto_announce_enabled)
            self.assertFalse(self._said_not_recognized())
            print(f"  ✓ '{w}' -> Auto announcements paused")

        for w in _AUTO_RESUME_WORDS:
            self.tts.reset_mock()
            self.lc._handle_command(w)
            self.assertTrue(self.lc._auto_announce_enabled)
            self.assertFalse(self._said_not_recognized())
            print(f"  ✓ '{w}' -> Auto announcements resumed")

    def _said_not_recognized(self):
        expected = self.lc._t("not_recognized")
        return any(call.args and call.args[0] == expected for call in self.tts.say_wait.call_args_list)

    def _handle_spoken_phrase(self, wake_word, command):
        phrase = f"{wake_word} {command}"
        stripped = self.lc._strip_wake_word(phrase)
        self.assertNotEqual(stripped, phrase)
        self.lc._handle_command(stripped)
        self.assertFalse(self._said_not_recognized(), f"Command was not recognized: {phrase}")

    def test_all_commands_work_with_wake_word_prefix(self):
        print("\nTesting spoken command forms with wake word prefixes:")
        self.lc._current_name = "Unknown"
        command_groups = [
            _AUTO_PAUSE_WORDS, _AUTO_RESUME_WORDS,
            _AR_WORDS, _EN_WORDS,
            _REG_WORDS, _IMPROVE_WORDS, _DEL_WORDS, _CLEAR_ALL_WORDS,
            _BLOCK_WORDS, _UNBLK_WORDS, _WHO_WORDS, _LIST_WORDS,
            _QUIET_WORDS, _SPEAK_WORDS,
            _MALE_AR_WORDS, _FEMALE_AR_WORDS, _MALE_EN_WORDS, _FEMALE_EN_WORDS,
        ]
        for group in command_groups:
            for command in group:
                self.tts.reset_mock()
                self.reg.reset_mock()
                self._handle_spoken_phrase("vision", command)
                print(f"  ✓ 'vision {command}'")

    def test_offline_vosk_grammar_contains_supported_commands(self):
        print("\nTesting offline Vosk command grammar coverage:")
        required_en = {
            "vision quiet", "vision mute", "vision silence", "vision unmute",
            "vision improve person", "vision improved person",
            "vision delete all", "vision delete all names",
            "vision list names", "vision registered names",
        }
        required_ar = {
            "فيجن سجل", "فيجن شخص جديد", "فيجن حسن الشخص", "فيجن حسن التسجيل",
            "فيجن احذف شخص", "فيجن احذف رقم", "فيجن امسح الكل",
            "فيجن اسماء", "فيجن احظر", "فيجن فك حظر",
            "فيجن هدوء", "فيجن تابع", "فيجن اسكت", "فيجن شغل الصوت",
        }
        self.assertTrue(required_en.issubset(set(OFFLINE_COMMANDS_EN)))
        self.assertTrue(required_ar.issubset(set(OFFLINE_COMMANDS_AR)))
        print("  ✓ English and Arabic offline grammars cover the main spoken commands")

    def test_fuzzy_command_matching_for_small_mistakes(self):
        print("\nTesting fuzzy command matching for small speech mistakes:")
        self.lc._current_name = "Unknown"

        self.reg.start_register.reset_mock()
        self._handle_spoken_phrase("vison", "regster")
        self.reg.start_register.assert_called_once()
        print("  ✓ 'vison regster' -> register")

        self.reg.start_improve.reset_mock()
        self._handle_spoken_phrase("vision", "improv person")
        self.reg.start_improve.assert_called_once_with()
        print("  ✓ 'vision improv person' -> improve person")

        self.reg.start_delete.reset_mock()
        self._handle_spoken_phrase("vision", "delet person")
        self.reg.start_delete.assert_called_once()
        print("  ✓ 'vision delet person' -> delete person with confirmation")

        for short_delete in ("delete", "del", "remove"):
            self.reg.start_delete.reset_mock()
            self._handle_spoken_phrase("vision", short_delete)
            self.reg.start_delete.assert_called_once()
            print(f"  ✓ 'vision {short_delete}' -> delete person with confirmation")

        self.reg.start_register.reset_mock()
        self._handle_spoken_phrase("فيج", "سجل")
        self.reg.start_register.assert_called_once()
        print("  ✓ 'فيج سجل' -> register")

if __name__ == "__main__":
    unittest.main()
