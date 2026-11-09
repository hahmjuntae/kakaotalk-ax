"""Compile the production composer check with synthetic text areas, without live UI."""

import pathlib
import re
import shutil
import subprocess
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/kakaotalk_native/ReadKakaoAX.swift"


class ComposerDetectionTests(unittest.TestCase):
    def run_harness(self, harness):
        compiler = shutil.which("swiftc")
        self.assertIsNotNone(compiler, "Swift compiler required; install Apple command-line tools")
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory)
            (path / "test.swift").write_text(harness, encoding="utf-8")
            build = subprocess.run([compiler, str(path / "test.swift"), "-o", str(path / "test")],
                                   capture_output=True, text=True, timeout=60)
            self.assertEqual(build.returncode, 0, build.stderr)
            result = subprocess.run([str(path / "test")], capture_output=True, text=True, timeout=5)
            self.assertEqual(result.returncode, 0, result.stderr)
            return result.stdout.splitlines()

    def test_failed_preview_description_is_skipped_but_composer_counts(self):
        source = SOURCE.read_text(encoding="utf-8")
        block = re.search(r'(        if role == "AXTextArea" \{.*?\n            return\n        \})', source, re.S)
        self.assertIsNotNone(block)
        harness = '''import Foundation
enum ReadFailure: Error { case blocked(String) }
struct Area { let description: String?; let bodyFails: Bool }
var optionalAttributeFailures: [String: Int] = [:]
// nil description mimics Kakao's AXError.failure on the open-chat preview text area.
func string(_ element: Area, _ name: String, optional: Bool = false) throws -> String {
    if let text = element.description { return text }
    if optional { optionalAttributeFailures[name, default: 0] += 1; return "" }
    throw ReadFailure.blocked("accessibility_read_failed_\\(name)_-25200")
}
func count(_ areas: [Area]) -> String {
    var composers = 0
    func visit(_ element: Area) throws {
        let role = "AXTextArea"
BLOCK
    }
    do {
        for area in areas { try visit(area) }
        return "composers=\\(composers)"
    } catch ReadFailure.blocked(let reason) {
        return reason
    } catch {
        return "error"
    }
}
print(count([Area(description: nil, bodyFails: false), Area(description: "메시지 입력", bodyFails: false)]))
print(count([Area(description: "메시지 입력", bodyFails: false)]))
print(count([Area(description: nil, bodyFails: false)]))
print(count([Area(description: "", bodyFails: false), Area(description: "Message", bodyFails: false)]))
print(optionalAttributeFailures["AXDescription", default: 0])
'''.replace("BLOCK", block.group(1))
        self.assertEqual(self.run_harness(harness), ["composers=1", "composers=1", "composers=0", "composers=1", "2"])


if __name__ == "__main__":
    unittest.main()
