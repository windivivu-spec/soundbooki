# F5 private voice performance probe — 2026-10-18

Hardware observed: Apple M1 Pro, 16 GiB unified memory. PyTorch 2.6.0,
Metal/MPS, same private model/reference/vocab as the app. Offline socket guard
enabled. This is a short 10.357-second Vietnamese passage, two generations per
configuration in separate processes. Reported time below is the second generation
after model load, not a 30-minute sustained throughput test.

| Configuration | Generation time | Audio duration | MPS driver memory sampled peak |
|---|---:|---:|---:|
| FP32, 16 steps (app default) | 9.714 s | 10.357 s | 2.58 GiB |
| FP32, 8 steps (experiment) | 4.902 s | 10.357 s | 2.58 GiB |
| BF16, 16 steps, FP32 ODE schedule | 12.375 s | 10.357 s | 2.22 GiB |
| BF16, 8 steps, FP32 ODE schedule | 6.250 s | 10.357 s | 2.22 GiB |
| Direct FP16 | rejected | non-finite audio (NaN) | not usable |

Initial BF16 failed because low precision collapsed distinct ODE schedule times;
the benchmark-only retry retained FP32 schedule times. No installed upstream code
was edited. FP32 app defaults remain unchanged. Format/numeric validity does not
establish equal pronunciation or voice similarity: listen to the 8-step file
before adopting it. Both FP32 runs peaked at approximately 2.42 GiB process RSS;
this is distinct from MPS driver allocation and must not be added as if both were
independent physical RAM. Driver samples are collected every 100 ms and may miss
transient peaks. Initial load also creates CPU-side model state.

The 8-step second run was 1.98x faster than the 16-step second run, without a
meaningful GPU-memory reduction. Linear extrapolation of this short sample gives
about 14.2 minutes for 30 minutes of output at 8 steps. This excludes model load,
thermal changes, swapping and passage-length variation; it is not a customer
performance guarantee. The previous real 33.684-second chapter needed 42.548
seconds of compute, illustrating why a single short benchmark is insufficient.

No MacBook Air 8 GiB was available for testing. Neither a model's on-disk size nor
half the RAM predicts inference time. Test actual 8 GiB machines with memory
pressure, swapping and sustained generation before defining support claims.

Next candidate: a local MLX adapter with quantized weights and converted private
checkpoint. [F5-TTS-MLX](https://github.com/lucasnewman/f5-tts-mlx) supports 4/8-bit
models. Its default model configuration differs from this private Base checkpoint;
vocab, masking, weight conversion and output fidelity require validation. No MLX
conversion or MLX performance claim has been made here.

Probe code/logs/data: `.qa/f5-benchmark/`. Full results:
`.qa/f5-benchmark/final-results.json`. A/B WAVs: `fp32-16.wav` and `fp32-8.wav`.
The production app was not changed by this experiment.

The current donor model's [model card](https://huggingface.co/hynt/F5-TTS-Vietnamese-ViVoice)
declares CC BY-NC-SA 4.0 and non-commercial research use. Commercial product plans
need an appropriately licensed model or separate authorization from its owner.
