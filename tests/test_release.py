"""Fixture-based tests for reproducible public release archives."""
import importlib.util
import json
import stat
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_release.py"
spec = importlib.util.spec_from_file_location("civilization_release", SCRIPT)
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)
TEMP_PARENT = ROOT / ".tmp" / "release-tests"


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        TEMP_PARENT.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="release-", dir=TEMP_PARENT)
        self.workspace = Path(self.temporary.name).resolve()
        self.assertEqual(self.workspace.parent, TEMP_PARENT.resolve())
        self.addCleanup(self.cleanup_workspace)
        self.repo = self.workspace / "repository"
        self.repo.mkdir()
        for name in release.ROOT_FILES:
            (self.repo / name).write_text("Public fixture file.\n", encoding="utf-8")
        contents = {
            "skills/civilization-os/SKILL.md": "---\nname: civilization-os\n---\n公开测试。\n",
            "skills/civilization-os/references/manifest.json": json.dumps(
                {"schema_version": "2.0", "library_version": "2.7.1"}, ensure_ascii=False),
            "skills/civilization-os/references/data.json": '[{"id":"public-fixture"}]\n',
            "docs/说明.md": "公开说明与 $HOME/.agents/skills、<skill-dir>。\n",
            "tests/fixture_test.py": "# Public fixture test\n",
            "scripts/build_release.py": SCRIPT.read_text(encoding="utf-8"),
        }
        license_text = "MIT fixture license text.\nCopyright (c) 2026 Example Maintainer\n"
        notice_text = "Original fixture documentation; external sources retain their own terms.\n"
        contents.update({"LICENSE": license_text, "NOTICE.md": notice_text,
                         "skills/civilization-os/LICENSE": license_text,
                         "skills/civilization-os/NOTICE.md": notice_text})
        for name, content in contents.items():
            path = self.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        self.output = self.workspace / "release-output"

    def cleanup_workspace(self):
        # Only delete the unique temporary child created by this test.
        resolved = self.workspace.resolve()
        if resolved.parent != TEMP_PARENT.resolve() or not resolved.name.startswith("release-"):
            raise AssertionError("Refusing cleanup outside this test's temporary child")
        self.temporary.cleanup()

    def add_file(self, name, payload):
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(payload, bytes):
            path.write_bytes(payload)
        else:
            path.write_text(payload, encoding="utf-8")
        return path

    def test_reproducible_and_version_comes_from_manifest(self):
        first = release.build_release(self.repo, self.output)
        second_output = self.workspace / "second-output"
        second = release.build_release(self.repo, second_output)
        self.assertEqual(first, second)
        self.assertEqual(first["version"], "2.7.1")
        for name in [item["filename"] for item in first["archives"]] + ["checksums.txt"]:
            self.assertEqual((self.output / name).read_bytes(), (second_output / name).read_bytes())
        checksums = (self.output / "checksums.txt").read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(checksums), 2)
        for item, line in zip(first["archives"], checksums):
            self.assertEqual(line, item["sha256"] + "  " + item["filename"])
            self.assertEqual(item["sha256"], release.digest((self.output / item["filename"]).read_bytes()))

    def test_member_scope_bytes_and_fixed_metadata(self):
        result = release.build_release(self.repo, self.output)
        files = release.collect_public_files(self.repo)
        for item in result["archives"]:
            is_skill = "-skill-" in item["filename"]
            expected = {"civilization-os/" + name[len(release.SKILL_PREFIX):]: data
                        for name, data in files.items() if name.startswith(release.SKILL_PREFIX)} if is_skill else {
                            "civilization-os-repo/" + name: data for name, data in files.items()}
            with zipfile.ZipFile(self.output / item["filename"]) as archive:
                self.assertEqual(archive.namelist(), sorted(expected))
                self.assertEqual(len(archive.infolist()), item["files"])
                for info in archive.infolist():
                    self.assertEqual(archive.read(info.filename), expected[info.filename])
                    self.assertEqual(info.date_time, (1980, 1, 1, 0, 0, 0))
                    self.assertEqual(info.create_system, 3)
                    self.assertEqual(info.external_attr >> 16, stat.S_IFREG | 0o644)
                    self.assertEqual(info.extra, b"")
                    self.assertFalse(info.is_dir())
                    if "说明" in info.filename:
                        self.assertTrue(info.flag_bits & 0x800)
                self.assertFalse(any("checksums.txt" in name for name in archive.namelist()))
                for legal_file in ("LICENSE", "NOTICE.md"):
                    paths = (["civilization-os/" + legal_file] if is_skill else
                             ["civilization-os-repo/" + legal_file,
                              "civilization-os-repo/skills/civilization-os/" + legal_file])
                    for name in paths:
                        self.assertEqual(archive.read(name), files[legal_file])

    def test_missing_skill_legal_copies_are_rejected_before_writing_packages(self):
        for legal_file in ("LICENSE", "NOTICE.md"):
            with self.subTest(legal_file=legal_file):
                path = self.repo / release.SKILL_PREFIX / legal_file
                original = path.read_bytes()
                path.unlink()
                with self.assertRaises(release.ReleaseError) as caught:
                    release.build_release(self.repo, self.output)
                self.assertIn(release.SKILL_PREFIX + legal_file, str(caught.exception))
                self.assertIn("missing required", str(caught.exception))
                self.assertFalse(self.output.exists())
                path.write_bytes(original)

    def test_legal_copy_drift_is_rejected_instead_of_silently_repaired(self):
        for legal_file in ("LICENSE", "NOTICE.md"):
            with self.subTest(legal_file=legal_file):
                root_path = self.repo / legal_file
                copy_path = self.repo / release.SKILL_PREFIX / legal_file
                original = copy_path.read_bytes()
                changed = original + b"Changed fixture copy.\n"
                copy_path.write_bytes(changed)
                with self.assertRaises(release.ReleaseError) as caught:
                    release.build_release(self.repo, self.output)
                self.assertIn(legal_file, str(caught.exception))
                self.assertIn("canonical root bytes", str(caught.exception))
                self.assertFalse(self.output.exists())
                self.assertEqual(copy_path.read_bytes(), changed)
                self.assertEqual(root_path.read_bytes(), original)
                copy_path.write_bytes(original)

    def test_private_files_fail_instead_of_being_silently_skipped(self):
        names = (".env", "work/notes.md", ".claude/settings.json",
                 "docs/.env.example", "unapproved-root.txt")
        for index, name in enumerate(names):
            with self.subTest(name=name):
                path = self.add_file(name, "Do not package this file.\n")
                output = self.workspace / f"private-output-{index}"
                with self.assertRaises(release.ReleaseError):
                    release.build_release(self.repo, output)
                self.assertFalse(output.exists())
                path.unlink()
                # Parent directories can remain empty; they never become members.

    def test_git_caches_dependencies_and_build_artifacts_are_skipped_read_only(self):
        paths = (".git/config", "__pycache__/module.pyc", ".tmp/notes.txt",
                 "node_modules/package/file.js", ".venv/private.bin", "venv/private.bin",
                 "build/generated.bin", "dist/generated.bin", ".pytest_cache/cache.bin")
        for name in paths:
            self.add_file(name, b"\xff\x00excluded")
        result = release.build_release(self.repo, self.output)
        for archive in result["archives"]:
            with zipfile.ZipFile(self.output / archive["filename"]) as opened:
                self.assertFalse(any(any(part in release.EXCLUDED_PARTS for part in Path(name).parts)
                                     for name in opened.namelist()))
        for name in paths:
            self.assertEqual((self.repo / name).read_bytes(), b"\xff\x00excluded")

    def test_private_content_is_rejected_without_echoing_it(self):
        # Assemble deliberately private samples to keep this public test file clean.
        private_path = "C:" + "/" + "Users" + "/" + "private_owner" + "/private.txt"
        private_backslash = private_path.replace("/", "\\")
        conversation = "https://" + "chatgpt.com" + "/c/" + "private-conversation-id"
        token = "sk-" + "x" * 48
        private_key = "-----BEGIN " + "PRIVATE KEY-----"
        assignment = "api_key = " + "'" + "z" * 24 + "'"
        for index, content in enumerate((private_path, json.dumps(private_backslash),
                                         conversation, token, private_key, assignment)):
            with self.subTest(index=index):
                path = self.add_file("docs/private-sample.txt", content)
                with self.assertRaises(release.ReleaseError) as caught:
                    release.build_release(self.repo, self.workspace / f"content-output-{index}")
                self.assertIn("docs/private-sample.txt", str(caught.exception))
                self.assertNotIn(content, str(caught.exception))
                self.assertNotIn("private_owner", str(caught.exception))
                path.unlink()

    def test_generic_home_and_skill_placeholders_are_allowed(self):
        self.add_file("docs/installation.md", "$HOME/.claude/skills and <skill-dir>/scripts/catalog.py\n")
        self.assertEqual(release.build_release(self.repo, self.output)["version"], "2.7.1")

    def test_missing_dependency_and_non_utf8_file_fail(self):
        manifest = self.repo / release.MANIFEST
        original = manifest.read_bytes()
        manifest.unlink()
        with self.assertRaises(release.ReleaseError) as caught:
            release.build_release(self.repo, self.output)
        self.assertIn("missing required", str(caught.exception))
        manifest.write_bytes(original)
        self.add_file("docs/unsupported.bin", b"\xff\x00")
        with self.assertRaises(release.ReleaseError) as caught:
            release.build_release(self.repo, self.output)
        self.assertIn("not UTF-8", str(caught.exception))

    def test_existing_release_refuses_overwrite_then_explicitly_rebuilds(self):
        result = release.build_release(self.repo, self.output)
        original = {path.name: path.read_bytes() for path in self.output.iterdir()}
        self.add_file("docs/changed.md", "New public fixture content.\n")
        with self.assertRaises(release.ReleaseError) as caught:
            release.build_release(self.repo, self.output)
        self.assertIn("already exists", str(caught.exception))
        self.assertEqual(original, {path.name: path.read_bytes() for path in self.output.iterdir()})
        rebuilt = release.build_release(self.repo, self.output, overwrite=True)
        repository = next(item for item in rebuilt["archives"] if "-repository-" in item["filename"])
        previous = next(item for item in result["archives"] if "-repository-" in item["filename"])
        self.assertNotEqual(repository["sha256"], previous["sha256"])
        self.assertFalse(any(path.name.startswith(".civilization-release-") for path in self.output.iterdir()))

    def test_output_inside_repository_is_rejected(self):
        with self.assertRaises(release.ReleaseError) as caught:
            release.build_release(self.repo, self.repo / "docs" / "releases")
        self.assertIn("outside the repository", str(caught.exception))

    def test_bad_version_metadata_does_not_make_a_filename(self):
        for version in (None, [], "2.0", "../escape", "2.0.0/private"):
            with self.subTest(version=version):
                (self.repo / release.MANIFEST).write_text(json.dumps(
                    {"library_version": version}), encoding="utf-8")
                with self.assertRaises(release.ReleaseError):
                    release.build_release(self.repo, self.output)
                self.assertFalse(self.output.exists())

    def test_archive_verification_detects_changed_member_bytes(self):
        archive_path = self.workspace / "tampered.zip"
        entries = {"civilization-os/public.txt": b"original"}
        release.write_archive(archive_path, {"civilization-os/public.txt": b"changed"})
        with self.assertRaises(release.ReleaseError) as caught:
            release.verify_archive(archive_path, entries)
        self.assertIn("bytes differ", str(caught.exception))

    def test_cli_requires_output_and_reports_only_public_summary(self):
        fixture_script = self.repo / "scripts" / "build_release.py"
        missing = subprocess.run([sys.executable, "-X", "utf8", str(fixture_script)],
                                 text=True, encoding="utf-8", capture_output=True)
        self.assertEqual(missing.returncode, 2)
        built = subprocess.run([sys.executable, "-X", "utf8", str(fixture_script),
                                "--output-dir", str(self.output)],
                               text=True, encoding="utf-8", capture_output=True)
        self.assertEqual(built.returncode, 0, built.stderr)
        self.assertNotIn(str(self.workspace), built.stdout)
        self.assertEqual(json.loads(built.stdout)["version"], "2.7.1")
        exists = subprocess.run([sys.executable, "-X", "utf8", str(fixture_script),
                                 "--output-dir", str(self.output)],
                                text=True, encoding="utf-8", capture_output=True)
        self.assertEqual(exists.returncode, 1)
        self.assertIn("already exists", exists.stderr)
        self.assertNotIn(str(self.workspace), exists.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)

