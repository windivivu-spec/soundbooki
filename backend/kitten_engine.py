"""Preset-only Kitten Mini ONNX adapter. No Hub, spaCy, torch or lazy downloads.

Input preparation follows KittenML/KittenTTS 0.8.1 (Apache-2.0); notice retained in
licenses/KittenTTS-LICENSE.txt. The separate model weights are Apache-2.0.
"""
# Adapted from KittenML/KittenTTS 0.8.1. SPDX-License-Identifier: Apache-2.0
import json
from pathlib import Path
import re

class KittenEngine:
    def __init__(self,root):
        import espeakng_loader
        from phonemizer.backend.espeak.wrapper import EspeakWrapper
        from phonemizer.backend import EspeakBackend
        import numpy as np
        import onnxruntime as ort
        EspeakWrapper.set_library(espeakng_loader.get_library_path())
        data_path=Path(espeakng_loader.get_data_path()).resolve()
        # The wheel's eSpeak C library has a 160-byte path buffer. A nested
        # .app or an accented home path can exceed it and terminate Python.
        # Use real files: phonemizer resolves symlinks before initializing C.
        self._espeak_data=None
        if len(str(data_path).encode('utf-8'))>128:
            import shutil
            import tempfile
            self._espeak_data=tempfile.TemporaryDirectory(prefix='wsn-espeak-',dir='/private/tmp')
            short=Path(self._espeak_data.name)/'espeak-ng-data'
            shutil.copytree(data_path,short)
            data_path=short
        EspeakWrapper.set_data_path(str(data_path))
        root=Path(root);self.config=json.loads((root/'config.json').read_text())
        options=ort.SessionOptions();options.intra_op_num_threads=4;options.inter_op_num_threads=1
        options.add_session_config_entry('session.intra_op.allow_spinning','0')
        self.session=ort.InferenceSession(str(root/self.config['model_file']),options,providers=['CPUExecutionProvider'])
        self.voices=np.load(root/self.config['voices'],allow_pickle=False)
        self.phonemizer=EspeakBackend(language='en-us',preserve_punctuation=True,with_stress=True)
        symbols='$'+';:,.!?¡¿—…"«»"" '+'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'+"ɑɐɒæɓʙβɔɕçɗɖðʤəɘɚɛɜɝɞɟʄɡɠɢʛɦɧħɥʜɨɪʝɭɬɫɮʟɱɯɰŋɳɲɴøɵɸθœɶʘɹɺɾɻʀʁɽʂʃʈʧʉʊʋⱱʌɣɤʍχʎʏʑʐʒʔʡʕʢǀǁǂǃˈˌːˑʼʴʰʱʲʷˠˤ˞↓↑→↗↘'̩'ᵻ"
        self.vocab={c:i for i,c in enumerate(symbols)}

    def list_preset_voices(self):
        return [(name,name) for name in self.config['voice_aliases']]

    def infer(self,text,voice,**kwargs):
        import numpy as np
        if voice not in self.config['voice_aliases']:raise ValueError('Giọng tiếng Anh không hợp lệ.')
        key=self.config['voice_aliases'][voice]
        # Keep original book text intact; inference gets sentence-sized chunks
        # with their punctuation. eSpeak handles English numbers and dates.
        from core import split_text
        output=[]
        for chunk in split_text(text,limit=350):
            if not chunk.strip():continue
            phonemes=self.phonemizer.phonemize([chunk.strip()])[0]
            phonemes=' '.join(re.findall(r'\w+|[^\w\s]',phonemes))
            tokens=[0]+[self.vocab[c] for c in phonemes if c in self.vocab]+[10,0]
            style_index=min(len(chunk.strip()),self.voices[key].shape[0]-1)
            result=self.session.run(None,{'input_ids':np.array([tokens],dtype=np.int64),'style':self.voices[key][style_index:style_index+1],
                                          'speed':np.array([self.config.get('speed_priors',{}).get(key,1.0)],dtype=np.float32)})[0]
            audio=np.asarray(result).reshape(-1)
            if len(audio)<=5000:raise ValueError('Đoạn tiếng Anh tạo ra quá ngắn. Hãy thử lại.')
            output.append(audio[:-5000])
        return np.concatenate(output) if output else np.array([],dtype=np.float32)
