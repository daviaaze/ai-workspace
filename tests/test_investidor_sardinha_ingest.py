import tempfile
import unittest
from pathlib import Path

from scripts.ingest_investidor_sardinha import (
    clean_vtt,
    format_note,
    remove_caption_overlap,
    select_caption,
    timestamp_seconds,
)


class CaptionIngestionTests(unittest.TestCase):
    def test_vtt_markup_is_cleaned_and_timestamps_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.vtt"
            path.write_text(
                "WEBVTT\n\n00:00:02.100 --> 00:00:03.000 align:start\n" 
                "O <c>mercado</c> subiu &amp; caiu.\n",
                encoding="utf-8",
            )
            self.assertEqual(clean_vtt(path), [("00:00:02.100", "O mercado subiu & caiu.")])

    def test_rolling_caption_overlap_is_removed_without_losing_new_words(self):
        cues = [
            ("00:00:00.000", "O mercado imobiliário está"),
            ("00:00:02.000", "O mercado imobiliário está caro"),
            ("00:00:04.000", "caro para compradores novos"),
        ]
        self.assertEqual(
            remove_caption_overlap(cues),
            [
                ("00:00:00.000", "O mercado imobiliário está"),
                ("00:00:02.000", "caro"),
                ("00:00:04.000", "para compradores novos"),
            ],
        )

    def test_prefers_original_portuguese_caption_track(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            translated = root / "abc.pt.vtt"
            original = root / "abc.pt-orig.vtt"
            translated.touch()
            original.touch()
            self.assertEqual(select_caption("abc", root), (original, "pt-orig"))

    def test_timestamp_handles_youtube_hms_and_mmss(self):
        self.assertEqual(timestamp_seconds("00:02:03.500"), 123)
        self.assertEqual(timestamp_seconds("02:03"), 123)

    def test_missing_caption_note_marks_gap_and_does_not_invent_transcript(self):
        note = format_note(
            {"id": "abc", "title": "Vídeo de teste"}, None, [], None, None
        )
        self.assertIn("Nenhuma legenda em português foi obtida", note)
        self.assertNotIn("Transcrição automática com timestamps", note)
        self.assertNotIn("## Alegações", note)


if __name__ == "__main__":
    unittest.main()
