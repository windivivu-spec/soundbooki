"""Packaging must carry verified Free weights without source-cache config."""
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('package_macos',ROOT/'scripts/package_macos.py')
packager=importlib.util.module_from_spec(spec);spec.loader.exec_module(packager)

class BundledFreeModelsTests(unittest.TestCase):
    def test_weights_remain_verifiable_after_source_cache_removed(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.qa') as tmp:
            root=Path(tmp);source=root/'cache';source.mkdir();target=root/'App';target.mkdir()
            payload=b'pinned-inference-weights'
            (source/'model.bin').write_bytes(payload)
            (source/'config.json').write_text('{"userCache":"private-path"}')
            manifest=dict(files=[dict(file='model.bin',size=len(payload),sha256=hashlib.sha256(payload).hexdigest())])
            with patch.object(packager.models,'verified_location',return_value=source),patch.object(packager.models,'manifest',return_value=manifest):
                packager.bundle_free_models(target)
            (source/'model.bin').unlink()
            for model_id in ('nano','kitten'):
                self.assertTrue(packager.models.verify(target/'.resources'/('tts-'+model_id)/'model.bin',manifest['files'][0]))
            self.assertFalse((target/'.resources/config.json').exists())
            self.assertFalse((target/'.resources/tts-nano/config.json').exists())
            self.assertEqual({p.name for p in (target/'.resources').iterdir()},{'tts-nano','tts-kitten'})

    def test_copy_corruption_rejects_candidate(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.qa') as tmp:
            target=Path(tmp)
            with patch.object(packager.models,'verified_location',return_value=target),patch.object(packager.models,'manifest',return_value={'files':[{'file':'weights','size':1,'sha256':'invalid'}]}),patch.object(packager.shutil,'copy2'),self.assertRaisesRegex(ValueError,'checksum failed'):
                packager.bundle_free_models(target)

if __name__=='__main__':unittest.main()
