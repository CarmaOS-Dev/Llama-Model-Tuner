# parameters_db.py

import platform as _platform

_IS_WINDOWS = _platform.system() == "Windows"

# --- NEW: Help documentation is now stored here and imported by the main app ---
_server_exe = "llama-server.exe" if _IS_WINDOWS else "llama-server"

HELP_DOCUMENTATION = r"""
## Llama.cpp Model Launcher: User Guide

### 1. Introduction

Welcome to the Llama.cpp Model Launcher! This application is a powerful graphical interface for `llama-server`. It transforms the complex command-line experience into a modern desktop workflow.

Beyond just launching models, this version features an intelligent **Tuning Wizard** that benchmarks your specific hardware (CPU, RAM, GPUs) against your model to automatically calculate the optimal configuration for maximum speed and context size.

### 2. First-Time Setup

1.  **Set the Llama.cpp Directory**:
    *   Click **Browse...** next to "Llama.cpp Directory".
    *   **macOS (Homebrew)**: Select `/opt/homebrew/bin` (where `brew install llama.cpp` places `llama-server`).
    *   **Windows**: Select the folder containing your `llama-server.exe`.
2.  **Set the Models File**:
    *   Click **Browse...** next to "Models File".
    *   Select your `.txt` file containing model commands.
    *   *Format*: Model Name on line 1, Command on line 2.
    *   This can be an empty text file or provided example model file.

### 3. The Main Interface

#### Left Panel: Controls & Logs
*   **Model Selection**: Pick a model config to load.
*   **Web UI Options**:
    *   `Enable Web UI`: Runs the standard visual interface.
    *   `Auto-Open Web UI`: Opens your default browser to `localhost:xxxx` upon success.
*   **Action Buttons**:
    *   **Load Model**: Starts the server using current settings.
    *   **Unload Model**: Kills the running server process.
    *   **Tune Model**: Opens the **Tuning Wizard** (see Section 4).
    *   **System**: Displays a static summary of detected hardware and model metadata.
    *   **Commands**: Opens the **Interactive Parameter Browser** to search/add flags.
*   **Output View**:
    *   Displays live server logs.
    *   **Smart Autoscroll**: The view scrolls down automatically. To read history, simply scroll up; autoscroll will pause until you return to the bottom.

#### Right Panel: Configuration Editor
*   **Model Name**: Rename your configuration here.
*   **Parameter List**:
    *   **Text Fields**: For values (e.g., `-c 8192`).
    *   **Checkboxes**: For flags (e.g., `--no-warmup`).
    *   **Browse Buttons**: Parameters like `-m` (Model Path) or `--mmproj` (Vision Adapter) have a browse button to select files easily.
*   **Management**: Duplicate, Delete, or Save configurations to your file.

---

### 4. The Tuning Wizard 🪄

The Tuning Wizard is an automated system that finds the "Perfect Fit" for your model on your specific hardware.

**How to use:**
1.  Select a model from the dropdown.
2.  Click **Tune Model**.
3.  The wizard will scan your hardware and the model file.
4.  A **Tuning Assistant** window will appear.

**Tuning Assistant Options:**
*   **Offload Strategy**:
    *   **Single GPU**: Forces the model onto your main GPU. Best for speed if it fits.
    *   **macOS Apple Silicon**: Your Mac has a single GPU with unified memory (shared between CPU and GPU). The wizard will use this automatically — multi-GPU options do not apply.
    *   **Multi-GPU (VRAM)**: *(Windows/NVIDIA only)* Splits the model across all GPUs.
    *   **Multi-GPU + CPU**: *(Windows/NVIDIA only)* Uses all VRAM, then spills the rest to System RAM.
*   **Maximize Context**: If checked, the wizard will try to increase the Context Size (`-c`) as high as possible without crashing.
*   **Ensure Safe Overhead**: If checked, the wizard reserves a memory buffer for the OS to prevent system freezing. **Uncheck this at your own risk.**
*   **Target Limit**: You can set a specific context limit (e.g., 16384), or leave it on "Auto" to go as high as hardware permits.

**What the Wizard Does:**
1.  **Phase 1**: Detects architecture (Dense vs MoE, Vision models) and layer counts.
2.  **Phase 2**: Probes the "KV Cache" cost per token.
3.  **Phase 3**: Finds the optimal Layer Offload (`-ngl`) and Tensor Split (`-ts`) to balance VRAM usage.
4.  **Phase 4**: Iteratively increases context size until memory is full.
5.  **Benchmark**: Runs a final speed test through the server API and reports generation speed (TG t/s), prompt processing speed (PP t/s) and, with speculative decoding, the draft acceptance rate.
6.  **Phase 6 - Performance Sweep** *(optional, enabled by default)*: keeping the context size found above, it benchmarks variations of the speed-related flags and keeps the fastest:
    *   **Split mode** `-sm layer` vs `-sm tensor` (multi-GPU). `tensor` runs every GPU in parallel on each layer: generation is often much faster with identical GPUs, but prompt processing can be slower.
    *   **Speculative decoding depth**: `--spec-draft-n-max` 1-5 for models with built-in MTP layers (detected from the GGUF), or 2-12 with a draft model (`-md`).
    *   **Micro-batch** `-ub` 256/512/1024/2048 (prompt processing speed vs. VRAM).
    *   **CPU threads** (only when weights are offloaded to RAM). On hybrid Intel CPUs the P-core count is tested.
    *   **Backend sampling** `-bs` (experimental, off by default).

    Choose **Rank by** = generation, prompt processing or balanced. Candidates that run out of memory are simply skipped. Every measurement is appended to `benchmark_history.jsonl`.

---

### 4b. The Benchmark Button (llama-bench) 📊

**Benchmark** opens a llama-bench sweep pre-filled from the selected model. Every field accepts several values (`512,1024,2048`) or ranges (`20-40+5`) and llama-bench tests every combination, showing a sortable table of pp/tg t/s. Useful tests:
*   `-sm layer,tensor` - which split mode is faster on your GPUs.
*   `-ub 512,1024,2048` - prompt processing speed per micro-batch.
*   `-d 0,16384,65536` - how much speed drops with a long conversation in the KV cache.
*   `-ncmoe 0-20+4` - how many MoE layers you can push to RAM before speed collapses.

**Apply Best to Editor** writes the winning values into the configuration (press **Save** to keep them). llama-bench does not measure speculative decoding (MTP/draft); use the Tuning Wizard sweep for that.

---

### 4c. llama.cpp Build Compatibility 🔧

The launcher reads `llama-server --help` from your llama.cpp directory, so it always knows which flags your build accepts:
*   **Automatic migration** when loading: `--no-mmap` → `-lm none`, `--mlock` → `-lm mlock`, `--draft N` → `--spec-draft-n-max N`, `--draft-min` → `--spec-draft-n-min`, and boolean flags stored with a value (`--context-shift disabled`). The editor is updated so you can **Save** the fixed command.
*   **Warnings** for flags your build does not recognise (the server would refuse to start).
*   **Duplicate aliases** (`-sm` + `--split-mode`) are collapsed, keeping the last one.
*   **Commands browser**: flags that exist in your build but not in the built-in database appear in the group *"Detected in your llama.cpp build"*, so new llama.cpp features are available immediately after updating.

---

### 5. Safety Features

**Resource Guard**:
The application monitors your system memory in real-time while loading models.
*   **Trigger**: If available memory drops below critical levels.
*   **Action**: The application immediately kills the `llama-server` process.
*   **Why?**: This prevents your computer from freezing or crashing due to memory starvation (Swap Death).
*   **macOS Note**: On Apple Silicon, RAM and "VRAM" are the same unified memory pool. The guard monitors total system RAM.
*   *Note: You can disable this by unchecking "Ensure Safe Resource Overhead" in the Tuning Wizard, but this is dangerous.*

**MoE Infinite Loop Protection**:
When tuning large models, the wizard detects if the model is too large for your total system memory and aborts, rather than retrying endlessly.

---

### 6. Advanced Tips

*   **Tensor Split (-ts)**: *(Windows/NVIDIA multi-GPU only)* The wizard automatically calculates the split ratio based on the VRAM capacity of each card.
*   **Apple Silicon**: Use `-ngl 999` to offload all layers to the Metal GPU. With unified memory, there is no separate "VRAM" — the GPU and CPU share the same RAM pool. Disabling memory mapping (`-lm none`, formerly `--no-mmap`) is generally NOT recommended on macOS; the default mmap provides faster loading and efficient memory management.
*   **Vision Models**: The app detects `Qwen2-VL`, `Qwen3.5` and similar architectures. Use `--mmproj` to point to the vision projector file (e.g., `mmproj-F32.gguf`) to enable image input.
*   **Speculative Decoding**: Models with Multi-Token-Prediction layers (many Qwen3.x / GLM / DeepSeek "MTP" GGUFs) can use `--spec-type draft-mtp --spec-draft-n-max 3` with no extra model. Requesting `draft-mtp` on a model without MTP layers makes the server abort, so the wizard reads the GGUF first. With a separate draft model (`-md`) the wizard picks the matching `--spec-type` (draft-simple, draft-dflash, draft-eagle3...).
*   **New memory controls**: `-fit on` lets llama.cpp choose unset `-ngl`/`-c`/`-ts` automatically (`-fitt` sets the free margin per GPU); `-ncffn N` keeps the dense FFN weights of the first N layers in RAM (the dense-model equivalent of `-ncmoe`); `-lm dio` (DirectIO) speeds up loading large models from NVMe.
*   **Thinking models**: `-rea off` or `--reasoning-budget N` reduce the time to the first useful token much more than any memory flag.

### 7. Quick Launch (macOS)

Instead of navigating to the project directory each time, add a shell alias to your `~/.zshrc`:

```
alias llama-launcher='cd "/path/to/Llamacpp-Model-Launcher" && source venv/bin/activate && python run_app.py'
```

Then open a new terminal and type `llama-launcher` from anywhere.

### 8. Troubleshooting

*   **"Load Model" does nothing**: Check your Llama.cpp Directory path. On macOS with Homebrew, this should be `/opt/homebrew/bin`.
*   **Resource Guard keeps killing my model**: Your model is too big for your physical memory. Try a higher quantization (e.g., Q4 instead of Q8) or a smaller context size.
*   **Tuning fails with "Soft Failure"**: The server launched but didn't output text. This often happens with incompatible CUDA versions (Windows) or corrupted model files.
*   **macOS: Model path has spaces**: Paths with spaces (e.g., `/Volumes/My Drive/models/...`) are handled automatically. Use backslash-escaping in the models file (e.g., `My\ Drive`).

### 9. Some stuff about -ot command
## Mastering `llamacpp`'s `-ot` Command for Optimized Performance

For enthusiasts and practitioners leveraging the power of `llamacpp` for local large language model inference, optimizing performance, especially on systems with limited VRAM, is a paramount concern. Among the arsenal of command-line arguments available, the `-ot` (or `--override-tensor`) command stands out as a powerful tool for fine-grained control over model layer offloading. This comprehensive guide will demystify the `-ot` command, its parameters, and provide practical examples to help you unlock its full potential.

### The "-ot" Command: Precision Control Over Tensor Placement

The primary function of the `-ot` command is to override the default behavior of `llamacpp`'s layer offloading. Instead of loading entire layers onto the GPU, this command allows you to specify precisely which tensors within the model should be allocated to a different memory buffer, most commonly the CPU. This granular control is particularly beneficial when dealing with large models that would otherwise exceed your GPU's VRAM capacity. By selectively keeping larger, less computationally intensive tensors on the CPU, you can free up precious VRAM for the more critical parts of the model, often leading to significant performance improvements.

The syntax for the `-ot` command is as follows:

```
-ot <tensor_name_pattern>=<buffer_type>
```

Multiple overrides can be applied by separating them with commas or by using the `-ot` flag multiple times. The real power of this command lies in its use of C++ regular expressions (regex) for the `<tensor_name_pattern>`, enabling you to target specific tensors with surgical precision.

### Demystifying the Parameters: Tensor Naming and Regex

To effectively use the `-ot` command, it's crucial to understand the naming convention for tensors within `llamacpp` models and the basics of C++ regex.

#### Tensor Naming Convention

While a definitive, exhaustive list can be model-specific, a general and helpful naming scheme is employed in `llamacpp`:

*   **`blk.<layer_number>`**: This prefix refers to a specific block or layer within the model. The `<layer_number>` is a zero-based index. For example, `blk.0` is the first layer, `blk.1` is the second, and so on.
*   **`ffn`**: This stands for the Feed-Forward Network, a key component of each transformer block. FFN tensors are often quite large and can be good candidates for offloading to the CPU as they involve more basic matrix multiplications.
*   **`ffn_down`, `ffn_gate`, `ffn_up`**: These are sub-tensors within the Feed-Forward Network.
*   **`attn`**: This refers to the attention mechanism tensors, which are generally more computationally intensive and benefit from being on the GPU.
*   **`exps`**: This is particularly relevant for Mixture-of-Experts (MoE) models and refers to the "expert" tensors. Offloading expert tensors to the CPU can be an effective strategy for running very large MoE models on consumer hardware.

#### C++ Regex for Tensor Targeting

The `<tensor_name_pattern>` uses C++'s `std::regex` syntax. Here are some common patterns and their meanings in the context of the `-ot` command:

| Regex Pattern | Description |
| :--- | :--- |
| `.` | Matches any single character. |
| `*` | Matches the preceding element zero or more times. |
| `+` | Matches the preceding element one or more times. |
| `[set]` | Matches any single character within the set. For example, `[0-9]` matches any digit. |
| `(group)` | Groups a part of the pattern. |
| `|` | Acts as an "OR" operator, matching the expression before or after it. |
| `\` | Escapes a special character. For instance, `\.` matches a literal dot. |

### Practical Examples and Use Cases

Now, let's break down the commands from the Reddit post and explore other useful examples:

*   **`-ot blk.([8-9]|[1-9][0-9]).ffn=CPU`**: This command offloads the Feed-Forward Network (`ffn`) tensors of specific layers to the CPU. Let's dissect the regex:
    *   `blk\.`: Matches the literal string "blk.".
    *   `([8-9]|[1-9][0-9])`: This is a clever way to select layers from 8 onwards. It matches either a single digit from 8 to 9, or a two-digit number from 10 to 99.
    *   `\.ffn`: Matches the literal string ".ffn".
    *   **In essence, this command keeps the FFN tensors for layers 8 and above on the CPU.**

*   **`-ot ffn=CPU`**: This is a broader command that offloads all tensors containing "ffn" in their name to the CPU. This is a simple way to move all Feed-Forward Network components off the GPU.

*   **`-ot exps=CPU`**: As mentioned earlier, this is highly effective for Mixture-of-Experts models. It offloads all "expert" tensors to the CPU, which can dramatically reduce VRAM usage.

*   **`-ot blk.2.ffn_down_exps.weight=CPU`**: This is a very specific command that targets the `ffn_down_exps.weight` tensor within the 3rd layer (`blk.2`) and moves it to the CPU.

**More Advanced Examples:**

*   **`-ot "blk\.(1[0-9]|2[0-9]|30)\.ffn_.*=CPU"`**: This command would offload all FFN-related tensors (since `.*` matches any character zero or more times) for layers 10 through 30 to the CPU.
*   **`-ot ".*\.ffn_(gate|up)=CPU"`**: This regex targets the `ffn_gate` and `ffn_up` tensors across all layers and offloads them to the CPU, while potentially leaving the `ffn_down` tensors on the GPU.

### How to Determine Which Tensors to Offload

The decision of which tensors to offload depends on your specific hardware and the model you are running. Here's a general strategy:

1.  **Identify VRAM Bottlenecks**: If a model doesn't fit in your VRAM, the `-ot` command is your friend.
2.  **Prioritize Attention Tensors for GPU**: Attention mechanism tensors are typically more computationally intensive and benefit most from GPU acceleration.
3.  **Experiment with FFN Offloading**: Feed-Forward Network tensors are often large and less demanding on the GPU's parallel processing capabilities, making them prime candidates for CPU offloading.
4.  **Consider MoE Expert Offloading**: For Mixture-of-Experts models, offloading the expert layers (`exps`) is a very effective strategy to reduce VRAM consumption.

By understanding and strategically utilizing the `-ot` command, you can push the boundaries of your hardware and run larger, more capable language models locally with `llamacpp`. Experiment with different regex patterns and tensor targets to find the optimal configuration for your setup and enjoy a smoother, more efficient inference experience.

code to print out large/all tensor for model:

# A simple script to read a GGUF model file and list its tensors by size.

from gguf import GGUFReader

# --- IMPORTANT ---
# Change this path to the full path of YOUR model file.
# macOS example: "/Volumes/Drive/models/your-model.gguf"
# Windows example: "D:/lm_studio/models/your-model.gguf"
MODEL_PATH = "/path/to/your/model.gguf"

print(f"Reading tensors from: {MODEL_PATH}\n")

# Open the model file for reading
reader = GGUFReader(MODEL_PATH, 'r')

# Get all the tensor info
tensors = reader.tensors

# Calculate the size (total number of parameters) for each tensor
tensor_sizes = []
for tensor in tensors:
    # Shape is a list of dimensions, e.g., [32000, 4096]
    # We multiply all dimensions to get the total parameter count
    param_count = 1
    for dim in tensor.shape:
        param_count *= dim
    tensor_sizes.append((tensor.name, param_count, tensor.shape))

# Sort the tensors from largest to smallest
sorted_tensors = sorted(tensor_sizes, key=lambda item: item[1], reverse=True)

# Print the top 10 largest tensors
print("--- Top 10 Largest Tensors ---")
for i in range(min(10, len(sorted_tensors))):
    name, size, shape = sorted_tensors[i]
    print(f"{i+1}. Name: {name:<30} | Parameters: {size:>12,} | Shape: {shape}")
# Print All
# for i in range(len(sorted_tensors)):
#     name, size, shape = sorted_tensors[i]
#     print(f"{i+1}. Name: {name:<30} | Parameters: {size:>12,} | Shape: {shape}")

-------------------------------------------------------------------------------------


Some examples (use CUDA0 on Windows/NVIDIA, Metal on macOS Apple Silicon):


-ot token_embd.weight=CUDA0
put token_embd.weight onto gpu 0, normally token_embd.weight is more dense and often benefit offload to higher performing gpu

-ot blk.[0-9].ffn_gate.weight=CUDA0
put ffn_gate.weight of first 9 layer onto gpu 0

-ot blk.[1-7][0-9].ffn_gate.weight=CUDA0
put ffn_gate.weight of first 80 layer onto gpu 0

-ot blk.[0-9].ffn_up.weight=CUDA0

-ot blk.[0-9].ffn_down.weight=CUDA0

Note: On macOS Apple Silicon, all layers are already in unified memory accessible by both CPU and GPU, so -ot overrides are primarily useful for forcing specific tensors to CPU-only processing to free up GPU compute resources.
"""

# This file contains the structured database of all Llama.cpp parameters.
# Synced with llama-server build 10903 (0.4.0-dev). Flags that exist in your installed
# build but are missing here are still shown in the Commands browser, under
# "Detected in your llama.cpp build" (read live from `llama-server --help`).

# thanks https://x.com/unmortan for the original info
# https://www.reddit.com/r/LocalLLaMA/comments/1opx9k2/comment/nnf2gr9/?context=1

# Example paths for descriptions (backslashes can't be inside f-string expressions in Python < 3.12)
_windows_server_example = "D:\\NEURAL\\LlamaCpp\\CUDA\\llama-server"
_windows_model_example = "D:\\NEURAL\\models\\Qwen3-30B-A3B-Instruct-2507-Q6_K\\Qwen3-30B-A3B-Instruct-2507-Q6_K.gguf"

_KV_TYPES = ['f16', 'q8_0', 'q4_0', 'q4_1', 'iq4_nl', 'q5_0', 'q5_1', 'bf16', 'f32']

_SPEC_TYPES = ['draft-mtp', 'draft-simple', 'draft-eagle3', 'draft-dflash', 'draft-dspark', 'ngram-mod',
               'ngram-simple', 'ngram-map-k', 'ngram-map-k4v', 'ngram-cache', 'none']

LLAMA_CPP_PARAMETERS = [
    {
        "name": "File Paths",
        "collapsed": False,
        "parameters": [
            {'name': 'Server Path', 'id': 'server-path', 'type': 'text', 'default': '', 'description': f'Path to {_server_exe} file without quotes. Example: {_windows_server_example if _IS_WINDOWS else "/opt/homebrew/bin/llama-server"}', 'required': True, 'prefix': ''},
            {'name': 'Model Path', 'id': 'model-path', 'type': 'text', 'default': '', 'description': f'Path to model GGUF file without quotes. Example: {_windows_model_example if _IS_WINDOWS else "/Users/you/models/Qwen3-30B-A3B-Instruct-2507-Q6_K.gguf"}', 'required': True, 'prefix': '-m'},
        ]
    },
    {
        "name": "⚡ Performance: GPU Offload & Multi-GPU",
        "collapsed": True,
        "parameters": [
            {'name': 'GPU Layers', 'id': 'gpu-layers', 'type': 'text', 'default': 'all', 'description': "Max. number of layers to store in VRAM: an exact number, 'auto' (let --fit decide) or 'all' (default: auto). Environment variable: LLAMA_ARG_N_GPU_LAYERS", 'prefix': '-ngl'},
            {'name': 'Split Mode', 'id': 'split-mode', 'type': 'select', 'default': 'layer', 'options': ['layer', 'tensor', 'row', 'none'], 'description': 'How to split the model across GPUs. layer (default): split layers and KV (pipelined). tensor: split weights and KV across GPUs and run them in parallel (EXPERIMENTAL, often the fastest with 2+ identical GPUs). row: split weight rows (parallelized). none: one GPU only. Environment variable: LLAMA_ARG_SPLIT_MODE', 'prefix': '-sm'},
            {'name': 'Tensor Split', 'id': 'tensor-split', 'type': 'text', 'default': '1,1', 'description': 'Fraction of the model to offload to each GPU, comma-separated proportions, e.g. 3,1. Environment variable: LLAMA_ARG_TENSOR_SPLIT', 'prefix': '-ts'},
            {'name': 'Main GPU', 'id': 'main-gpu', 'type': 'number', 'default': '0', 'description': 'GPU used for the model (split-mode none) or for intermediate results and KV (split-mode row) (default: 0). Environment variable: LLAMA_ARG_MAIN_GPU', 'prefix': '-mg'},
            {'name': 'Device', 'id': 'device', 'type': 'text', 'default': '', 'description': "Comma-separated list of devices to use for offloading, e.g. CUDA0,CUDA1 (none = don't offload). Use --list-devices to see them. Environment variable: LLAMA_ARG_DEVICE", 'prefix': '-dev'},
            {'name': 'List Devices', 'id': 'list-devices', 'type': 'checkbox', 'default': False, 'description': 'Print list of available devices and exit', 'prefix': '--list-devices'},
            {'name': 'Fit To Memory', 'id': 'fit', 'type': 'select', 'default': 'on', 'options': ['on', 'off'], 'description': "Automatically adjust UNSET arguments (-ngl, -c, -ts, -ncmoe...) so the model fits in device memory (default: on). Set 'off' when you tune those values yourself. Environment variable: LLAMA_ARG_FIT", 'prefix': '-fit'},
            {'name': 'Fit Target Margin', 'id': 'fit-target', 'type': 'text', 'default': '1024', 'description': 'Free-memory margin per device (MiB) that --fit leaves untouched. Comma list per device or a single value for all (default: 1024). Environment variable: LLAMA_ARG_FIT_TARGET', 'prefix': '-fitt'},
            {'name': 'Fit Min Context', 'id': 'fit-ctx', 'type': 'number', 'default': '4096', 'description': 'Minimum context size that --fit is allowed to set (default: 4096). Environment variable: LLAMA_ARG_FIT_CTX', 'prefix': '-fitc'},
            {'name': 'Override Tensor', 'id': 'override-tensor', 'type': 'text', 'default': '', 'description': 'Override tensor buffer type: <tensor name pattern>=<buffer type>,... e.g. "blk\\.(3[0-9])\\.ffn_.*_exps=CPU". Environment variable: LLAMA_ARG_OVERRIDE_TENSOR', 'prefix': '-ot'},
            {'name': 'CPU MoE', 'id': 'cpu-moe', 'type': 'checkbox', 'default': False, 'description': 'Keep all Mixture of Experts (MoE) weights in the CPU. Environment variable: LLAMA_ARG_CPU_MOE', 'prefix': '-cmoe'},
            {'name': 'N CPU MoE', 'id': 'n-cpu-moe', 'type': 'number', 'default': '0', 'description': 'Keep the MoE expert weights of the first N layers in the CPU. Environment variable: LLAMA_ARG_N_CPU_MOE', 'prefix': '-ncmoe'},
            {'name': 'N CPU FFN (Dense)', 'id': 'n-cpu-ffn', 'type': 'number', 'default': '0', 'description': 'NEW: keep the dense FFN weights of the first N layers in the CPU (dense models; the -ncmoe equivalent for non-MoE). Usually faster than lowering -ngl because attention stays on the GPU. Environment variable: LLAMA_ARG_N_CPU_FFN', 'prefix': '-ncffn'},
            {'name': 'No KV Offload', 'id': 'no-kv-offload', 'type': 'checkbox', 'default': False, 'description': 'Keep the KV cache in system RAM instead of VRAM (default: KV offload enabled). Environment variable: LLAMA_ARG_KV_OFFLOAD', 'prefix': '-nkvo'},
            {'name': 'No Host Buffer', 'id': 'no-host', 'type': 'checkbox', 'default': False, 'description': 'Bypass the host buffer, allowing extra buffer types to be used. Environment variable: LLAMA_ARG_NO_HOST', 'prefix': '--no-host'},
            {'name': 'No Op Offload', 'id': 'no-op-offload', 'type': 'checkbox', 'default': False, 'description': 'Disable offloading host tensor operations to the device (default: op offload enabled). Can help prompt speed with heavy CPU offload.', 'prefix': '--no-op-offload'},
            {'name': 'RPC Servers', 'id': 'rpc', 'type': 'text', 'default': '', 'description': 'Comma-separated list of RPC servers (host:port) to offload to remote machines. Environment variable: LLAMA_ARG_RPC', 'prefix': '--rpc'},
        ]
    },
    {
        "name": "⚡ Performance: Context, Batching & KV Cache",
        "collapsed": True,
        "parameters": [
            {'name': 'Context Size', 'id': 'ctx-size', 'type': 'number', 'default': '0', 'description': 'Size of the prompt context (default: 0 = loaded from model). Environment variable: LLAMA_ARG_CTX_SIZE', 'prefix': '-c'},
            {'name': 'Batch Size', 'id': 'batch-size', 'type': 'number', 'default': '2048', 'description': 'Logical maximum batch size (default: 2048). Environment variable: LLAMA_ARG_BATCH', 'prefix': '-b'},
            {'name': 'UBatch Size', 'id': 'ubatch-size', 'type': 'number', 'default': '512', 'description': 'Physical maximum batch size (default: 512). Bigger values (1024/2048) usually speed up prompt processing at the cost of VRAM. Environment variable: LLAMA_ARG_UBATCH', 'prefix': '-ub'},
            {'name': 'Flash Attention', 'id': 'flash-attn', 'type': 'select', 'default': 'on', 'options': ['on', 'auto', 'off'], 'description': "Flash Attention ('on', 'off' or 'auto', default: auto). Environment variable: LLAMA_ARG_FLASH_ATTN", 'prefix': '-fa'},
            {'name': 'Cache Type K', 'id': 'cache-type-k', 'type': 'select', 'default': 'q8_0', 'options': _KV_TYPES, 'description': 'KV cache data type for K (default: f16). q8_0 halves KV memory with minimal quality loss. Environment variable: LLAMA_ARG_CACHE_TYPE_K', 'prefix': '-ctk'},
            {'name': 'Cache Type V', 'id': 'cache-type-v', 'type': 'select', 'default': 'q8_0', 'options': _KV_TYPES, 'description': 'KV cache data type for V (default: f16). Quantized V needs Flash Attention. Environment variable: LLAMA_ARG_CACHE_TYPE_V', 'prefix': '-ctv'},
            {'name': 'Parallel Slots', 'id': 'parallel', 'type': 'number', 'default': '1', 'description': 'Number of server slots (default: -1 = auto). Use 1 for a single user to get all the context in one slot. Environment variable: LLAMA_ARG_N_PARALLEL', 'prefix': '-np'},
            {'name': 'KV Unified', 'id': 'kv-unified', 'type': 'checkbox', 'default': False, 'description': 'Use a single unified KV buffer shared across all sequences (default: enabled if number of slots is auto). Environment variable: LLAMA_ARG_KV_UNIFIED', 'prefix': '-kvu'},
            {'name': 'No KV Unified', 'id': 'no-kv-unified', 'type': 'checkbox', 'default': False, 'description': 'Force a separate KV buffer per slot. Environment variable: LLAMA_ARG_KV_UNIFIED', 'prefix': '-no-kvu'},
            {'name': 'KV Unified Per Slot', 'id': 'kv-unified-per-slot', 'type': 'number', 'default': '', 'description': 'Context limit per parallel slot. When set without -c, the shared KV pool is sized to n_parallel*N. Environment variable: LLAMA_ARG_KV_UNIFIED_PER_SLOT', 'prefix': '--kv-unified-per-slot'},
            {'name': 'SWA Full', 'id': 'swa-full', 'type': 'checkbox', 'default': False, 'description': 'Use full-size SWA cache (default: false). Environment variable: LLAMA_ARG_SWA_FULL', 'prefix': '--swa-full'},
            {'name': 'No Repack', 'id': 'no-repack', 'type': 'checkbox', 'default': False, 'description': 'Disable CPU weight repacking (default: repacking enabled). Environment variable: LLAMA_ARG_REPACK', 'prefix': '-nr'},
            {'name': 'Performance Timings', 'id': 'perf', 'type': 'checkbox', 'default': False, 'description': 'Enable internal libllama performance timings (default: false). Environment variable: LLAMA_ARG_PERF', 'prefix': '--perf'},
        ]
    },
    {
        "name": "Memory & Model Loading",
        "collapsed": True,
        "parameters": [
            {'name': 'Load Mode', 'id': 'load-mode', 'type': 'select', 'default': 'auto', 'options': ['auto', 'none', 'mmap', 'mlock', 'mmap+mlock', 'dio'], 'description': 'Model loading mode (replaces --mmap/--no-mmap/--mlock). auto: mmap unless a device does not support it. none: read into memory (old --no-mmap). mmap: memory-map. mlock: keep in RAM. mmap+mlock. dio: DirectIO, fastest loading from NVMe when fully offloaded. Environment variable: LLAMA_ARG_LOAD_MODE', 'prefix': '-lm'},
            {'name': 'Lazy Mode', 'id': 'lazy-mode', 'type': 'select', 'default': 'auto', 'options': ['auto', 'on', 'off'], 'description': 'On-demand reading of certain tensors (e.g. per-layer embeddings). on: read rows from disk on demand (requires mmap). auto: on only for tensors > 4 GiB. off: keep resident. Environment variable: LLAMA_ARG_LAZY_MODE', 'prefix': '-lzm'},
            {'name': 'NUMA', 'id': 'numa', 'type': 'select', 'default': 'distribute', 'options': ['distribute', 'isolate', 'numactl'], 'description': 'Attempt optimizations that help on some NUMA systems. Environment variable: LLAMA_ARG_NUMA', 'prefix': '--numa'},
            {'name': 'Check Tensors', 'id': 'check-tensors', 'type': 'checkbox', 'default': False, 'description': 'Check model tensor data for invalid values (default: false)', 'prefix': '--check-tensors'},
            {'name': 'Override KV', 'id': 'override-kv', 'type': 'text', 'default': '', 'description': 'Override model metadata by key, comma-separated. Types: int, float, bool, str. Example: tokenizer.ggml.add_bos_token=bool:false', 'prefix': '--override-kv'},
        ]
    },
    {
        "name": "Threading & CPU Parameters",
        "collapsed": True,
        "parameters": [
            {'name': 'Threads', 'id': 'threads', 'type': 'number', 'default': '-1', 'description': 'Number of CPU threads used during generation (default: -1 = auto). With CPU offload, the number of P-cores is usually best on hybrid Intel CPUs. Environment variable: LLAMA_ARG_THREADS', 'prefix': '-t'},
            {'name': 'Threads Batch', 'id': 'threads-batch', 'type': 'number', 'default': '-1', 'description': 'Number of threads used during batch and prompt processing (default: same as --threads)', 'prefix': '-tb'},
            {'name': 'CPU Mask', 'id': 'cpu-mask', 'type': 'text', 'default': '', 'description': 'CPU affinity mask: arbitrarily long hex. Complements cpu-range (default: "")', 'prefix': '-C'},
            {'name': 'CPU Range', 'id': 'cpu-range', 'type': 'text', 'default': '', 'description': 'Range of CPUs for affinity. Complements --cpu-mask. Format: lo-hi', 'prefix': '-Cr'},
            {'name': 'CPU Strict', 'id': 'cpu-strict', 'type': 'select', 'default': '0', 'options': ['0', '1'], 'description': 'Use strict CPU placement (default: 0)', 'prefix': '--cpu-strict'},
            {'name': 'Priority', 'id': 'priority', 'type': 'select', 'default': '0', 'options': ['-1', '0', '1', '2', '3'], 'description': 'Process/thread priority: low(-1), normal(0), medium(1), high(2), realtime(3) (default: 0)', 'prefix': '--prio'},
            {'name': 'Poll', 'id': 'poll', 'type': 'number', 'default': '50', 'description': 'Polling level to wait for work (0 - no polling, default: 50)', 'prefix': '--poll'},
            {'name': 'CPU Mask Batch', 'id': 'cpu-mask-batch', 'type': 'text', 'default': '', 'description': 'CPU affinity mask for batch processing (default: same as --cpu-mask)', 'prefix': '-Cb'},
            {'name': 'CPU Range Batch', 'id': 'cpu-range-batch', 'type': 'text', 'default': '', 'description': 'Ranges of CPUs for batch affinity. Complements --cpu-mask-batch', 'prefix': '-Crb'},
            {'name': 'CPU Strict Batch', 'id': 'cpu-strict-batch', 'type': 'select', 'default': '0', 'options': ['0', '1'], 'description': 'Strict CPU placement for batch (default: same as --cpu-strict)', 'prefix': '--cpu-strict-batch'},
            {'name': 'Priority Batch', 'id': 'priority-batch', 'type': 'select', 'default': '0', 'options': ['0', '1', '2', '3'], 'description': 'Batch process/thread priority: 0-normal, 1-medium, 2-high, 3-realtime (default: 0)', 'prefix': '--prio-batch'},
            {'name': 'Poll Batch', 'id': 'poll-batch', 'type': 'select', 'default': '0', 'options': ['0', '1'], 'description': 'Use polling to wait for batch work (default: same as --poll)', 'prefix': '--poll-batch'},
        ]
    },
    {
        "name": "⚡ Speculative Decoding (MTP / Draft / N-gram)",
        "collapsed": True,
        "parameters": [
            {'name': 'Speculative Type', 'id': 'spec-type', 'type': 'select', 'default': 'draft-mtp', 'options': _SPEC_TYPES, 'description': 'Comma-separated list of speculative decoding types (default: none). draft-mtp: use the model\'s own Multi-Token-Prediction head (Qwen3.x/GLM/DeepSeek "MTP" GGUFs, no extra model). draft-simple: classic draft model (-md). draft-eagle3 / draft-dflash / draft-dspark: special draft heads. ngram-*: no extra model, great for code edits and repetitive text. Environment variable: LLAMA_ARG_SPEC_TYPE', 'prefix': '--spec-type'},
            {'name': 'Draft Max Tokens', 'id': 'spec-draft-n-max', 'type': 'number', 'default': '3', 'description': 'Number of tokens to draft per step (default: 3). Replaces the removed --draft/--draft-max. MTP usually peaks at 2-4. Environment variable: LLAMA_ARG_SPEC_DRAFT_N_MAX', 'prefix': '--spec-draft-n-max'},
            {'name': 'Draft Min Tokens', 'id': 'spec-draft-n-min', 'type': 'number', 'default': '0', 'description': 'Minimum number of draft tokens (default: 0). Replaces the removed --draft-min. Environment variable: LLAMA_ARG_SPEC_DRAFT_N_MIN', 'prefix': '--spec-draft-n-min'},
            {'name': 'Draft P Min', 'id': 'draft-p-min', 'type': 'number', 'default': '0.0', 'description': 'Minimum speculative decoding probability (greedy) (default: 0.00). Environment variable: LLAMA_ARG_SPEC_DRAFT_P_MIN', 'prefix': '--draft-p-min'},
            {'name': 'Draft P Split', 'id': 'draft-p-split', 'type': 'number', 'default': '0.10', 'description': 'Speculative decoding split probability (default: 0.10). Environment variable: LLAMA_ARG_SPEC_DRAFT_P_SPLIT', 'prefix': '--draft-p-split'},
            {'name': 'Spec Default Config', 'id': 'spec-default', 'type': 'checkbox', 'default': False, 'description': 'Enable the default speculative decoding config', 'prefix': '--spec-default'},
            {'name': 'Model Draft', 'id': 'model-draft', 'type': 'text', 'default': '', 'description': 'Draft model for speculative decoding (default: unused). Environment variable: LLAMA_ARG_SPEC_DRAFT_MODEL', 'prefix': '-md'},
            {'name': 'HF Repo Draft', 'id': 'hf-repo-draft', 'type': 'text', 'default': '', 'description': 'Same as --hf-repo, but for the draft model. Environment variable: LLAMA_ARG_SPEC_DRAFT_HF_REPO', 'prefix': '-hfd'},
            {'name': 'GPU Layers Draft', 'id': 'gpu-layers-draft', 'type': 'text', 'default': 'all', 'description': "Max. draft model layers in VRAM: number, 'auto' or 'all' (default: auto). Environment variable: LLAMA_ARG_N_GPU_LAYERS_DRAFT", 'prefix': '-ngld'},
            {'name': 'Device Draft', 'id': 'device-draft', 'type': 'text', 'default': '', 'description': 'Comma-separated list of devices for the draft model (default: follows --device)', 'prefix': '-devd'},
            {'name': 'Cache Type K Draft', 'id': 'cache-type-k-draft', 'type': 'select', 'default': 'f16', 'options': _KV_TYPES, 'description': 'KV cache data type for K for the draft model / MTP head (default: f16). Environment variable: LLAMA_ARG_SPEC_DRAFT_CACHE_TYPE_K', 'prefix': '-ctkd'},
            {'name': 'Cache Type V Draft', 'id': 'cache-type-v-draft', 'type': 'select', 'default': 'f16', 'options': _KV_TYPES, 'description': 'KV cache data type for V for the draft model / MTP head (default: f16). Environment variable: LLAMA_ARG_SPEC_DRAFT_CACHE_TYPE_V', 'prefix': '-ctvd'},
            {'name': 'Override Tensor Draft', 'id': 'override-tensor-draft', 'type': 'text', 'default': '', 'description': 'Override tensor buffer type for the draft model', 'prefix': '-otd'},
            {'name': 'CPU MoE Draft', 'id': 'cpu-moe-draft', 'type': 'checkbox', 'default': False, 'description': 'Keep all MoE weights in the CPU for the draft model. Environment variable: LLAMA_ARG_SPEC_DRAFT_CPU_MOE', 'prefix': '-cmoed'},
            {'name': 'N CPU MoE Draft', 'id': 'n-cpu-moe-draft', 'type': 'number', 'default': '0', 'description': 'Keep the MoE weights of the first N layers in the CPU for the draft model. Environment variable: LLAMA_ARG_SPEC_DRAFT_N_CPU_MOE', 'prefix': '-ncmoed'},
            {'name': 'Threads Draft', 'id': 'threads-draft', 'type': 'number', 'default': '-1', 'description': 'Threads used by the draft model during generation (default: same as --threads)', 'prefix': '-td'},
            {'name': 'Threads Batch Draft', 'id': 'threads-batch-draft', 'type': 'number', 'default': '-1', 'description': 'Threads used by the draft model for batch processing (default: same as --threads-draft)', 'prefix': '-tbd'},
            {'name': 'No Draft Backend Sampling', 'id': 'no-spec-draft-backend-sampling', 'type': 'checkbox', 'default': False, 'description': 'Do not offload draft sampling to the backend (default: offload enabled). Environment variable: LLAMA_ARG_SPEC_DRAFT_BACKEND_SAMPLING', 'prefix': '--no-spec-draft-backend-sampling'},
            {'name': 'N-gram Mod Min', 'id': 'spec-ngram-mod-n-min', 'type': 'number', 'default': '48', 'description': 'Minimum number of n-gram tokens for ngram-based speculative decoding (default: 48)', 'prefix': '--spec-ngram-mod-n-min'},
            {'name': 'N-gram Mod Max', 'id': 'spec-ngram-mod-n-max', 'type': 'number', 'default': '64', 'description': 'Maximum number of n-gram tokens for ngram-based speculative decoding (default: 64)', 'prefix': '--spec-ngram-mod-n-max'},
            {'name': 'N-gram Mod Match', 'id': 'spec-ngram-mod-n-match', 'type': 'number', 'default': '24', 'description': 'ngram-mod lookup length (default: 24)', 'prefix': '--spec-ngram-mod-n-match'},
            {'name': 'N-gram Simple Size N', 'id': 'spec-ngram-simple-size-n', 'type': 'number', 'default': '12', 'description': 'Lookup n-gram length for ngram-simple (default: 12)', 'prefix': '--spec-ngram-simple-size-n'},
            {'name': 'N-gram Simple Size M', 'id': 'spec-ngram-simple-size-m', 'type': 'number', 'default': '48', 'description': 'Draft m-gram length for ngram-simple (default: 48)', 'prefix': '--spec-ngram-simple-size-m'},
            {'name': 'N-gram Simple Min Hits', 'id': 'spec-ngram-simple-min-hits', 'type': 'number', 'default': '1', 'description': 'Minimum hits for ngram-simple (default: 1)', 'prefix': '--spec-ngram-simple-min-hits'},
            {'name': 'Lookup Cache Static', 'id': 'lookup-cache-static', 'type': 'text', 'default': '', 'description': 'Path to static lookup cache for lookup decoding (not updated by generation)', 'prefix': '-lcs'},
            {'name': 'Lookup Cache Dynamic', 'id': 'lookup-cache-dynamic', 'type': 'text', 'default': '', 'description': 'Path to dynamic lookup cache for lookup decoding (updated by generation)', 'prefix': '-lcd'},
        ]
    },
    {
        "name": "Prompt Cache & Context Checkpoints",
        "collapsed": True,
        "parameters": [
            {'name': 'Cache RAM', 'id': 'cache-ram', 'type': 'number', 'default': '8192', 'description': 'Maximum host-RAM prompt cache size in MiB (default: 8192, -1 = no limit, 0 = disable). Speeds up resuming long conversations. Environment variable: LLAMA_ARG_CACHE_RAM', 'prefix': '-cram'},
            {'name': 'Context Checkpoints', 'id': 'ctx-checkpoints', 'type': 'number', 'default': '8', 'description': 'Max number of context checkpoints per slot (default: 32). Needed by SWA/hybrid models (Gemma, Qwen3.x) to avoid full prompt re-processing. Environment variable: LLAMA_ARG_CTX_CHECKPOINTS', 'prefix': '-ctxcp'},
            {'name': 'Checkpoint Min Step', 'id': 'checkpoint-min-step', 'type': 'number', 'default': '8192', 'description': 'Minimum spacing between context checkpoints in tokens (default: 8192, 0 = no minimum). Environment variable: LLAMA_ARG_CHECKPOINT_MIN_SPACING_NT', 'prefix': '-cms'},
            {'name': 'No Cache Idle Slots', 'id': 'no-cache-idle-slots', 'type': 'checkbox', 'default': False, 'description': 'Do not save idle slots to the prompt cache on new tasks (default: enabled, requires cache-ram). Environment variable: LLAMA_ARG_CACHE_IDLE_SLOTS', 'prefix': '--no-cache-idle-slots'},
            {'name': 'No Cache Prompt', 'id': 'no-cache-prompt', 'type': 'checkbox', 'default': False, 'description': 'Disable prompt caching (default: enabled). Environment variable: LLAMA_ARG_CACHE_PROMPT', 'prefix': '--no-cache-prompt'},
            {'name': 'Cache Reuse', 'id': 'cache-reuse', 'type': 'number', 'default': '256', 'description': 'Min chunk size to attempt reusing from the cache via KV shifting, requires prompt caching (default: 0). Environment variable: LLAMA_ARG_CACHE_REUSE', 'prefix': '--cache-reuse'},
            {'name': 'Slot Prompt Similarity', 'id': 'slot-prompt-similarity', 'type': 'number', 'default': '0.10', 'description': 'How much the prompt of a request must match the prompt of a slot to use that slot (default: 0.10, 0.0 = disabled)', 'prefix': '-sps'},
            {'name': 'Slot Save Path', 'id': 'slot-save-path', 'type': 'text', 'default': '', 'description': 'Path to save slot KV cache (default: disabled)', 'prefix': '--slot-save-path'},
        ]
    },
    {
        "name": "Context & Prediction Parameters",
        "collapsed": True,
        "parameters": [
            {'name': 'Predict Tokens', 'id': 'n-predict', 'type': 'number', 'default': '-1', 'description': 'Number of tokens to predict (default: -1 = infinity). Environment variable: LLAMA_ARG_N_PREDICT', 'prefix': '-n'},
            {'name': 'Keep Tokens', 'id': 'keep', 'type': 'number', 'default': '0', 'description': 'Number of tokens to keep from the initial prompt (default: 0, -1 = all)', 'prefix': '--keep'},
            {'name': 'Context Shift', 'id': 'context-shift', 'type': 'checkbox', 'default': False, 'description': 'Use context shift on infinite text generation (default: disabled). Environment variable: LLAMA_ARG_CONTEXT_SHIFT', 'prefix': '--context-shift'},
            {'name': 'No Warmup', 'id': 'no-warmup', 'type': 'checkbox', 'default': False, 'description': 'Skip warming up the model with an empty run (default: warmup enabled)', 'prefix': '--no-warmup'},
            {'name': 'No Cont Batching', 'id': 'no-cont-batching', 'type': 'checkbox', 'default': False, 'description': 'Disable continuous batching (default: enabled). Environment variable: LLAMA_ARG_CONT_BATCHING', 'prefix': '-nocb'},
            {'name': 'Reverse Prompt', 'id': 'reverse-prompt', 'type': 'text', 'default': '', 'description': 'Halt generation at PROMPT, return control in interactive mode', 'prefix': '-r'},
            {'name': 'Special', 'id': 'special', 'type': 'checkbox', 'default': False, 'description': 'Special tokens output enabled (default: false)', 'prefix': '-sp'},
            {'name': 'SPM Infill', 'id': 'spm-infill', 'type': 'checkbox', 'default': False, 'description': 'Use Suffix/Prefix/Middle pattern for infill (default: disabled)', 'prefix': '--spm-infill'},
            {'name': 'Pooling', 'id': 'pooling', 'type': 'select', 'default': 'mean', 'options': ['none', 'mean', 'cls', 'last', 'rank'], 'description': 'Pooling type for embeddings, model default if unspecified. Environment variable: LLAMA_ARG_POOLING', 'prefix': '--pooling'},
            {'name': 'Embedding Normalize', 'id': 'embd-normalize', 'type': 'number', 'default': '2', 'description': 'Normalisation for embeddings (default: 2) (-1=none, 0=max absolute int16, 1=taxicab, 2=euclidean, >2=p-norm)', 'prefix': '--embd-normalize'},
        ]
    },
    {
        "name": "Model & Adapter Parameters",
        "collapsed": True,
        "parameters": [
            {'name': 'LoRA', 'id': 'lora', 'type': 'text', 'default': '', 'description': 'Path to LoRA adapter (comma-separated values to load multiple adapters)', 'prefix': '--lora'},
            {'name': 'LoRA Scaled', 'id': 'lora-scaled', 'type': 'text', 'default': '', 'description': 'LoRA adapter with user defined scaling. Format: FNAME:SCALE,...', 'prefix': '--lora-scaled'},
            {'name': 'LoRA Init Without Apply', 'id': 'lora-init-without-apply', 'type': 'checkbox', 'default': False, 'description': 'Load LoRA adapters without applying them (apply later via POST /lora-adapters)', 'prefix': '--lora-init-without-apply'},
            {'name': 'Control Vector', 'id': 'control-vector', 'type': 'text', 'default': '', 'description': 'Add a control vector (comma-separated values to add multiple)', 'prefix': '--control-vector'},
            {'name': 'Control Vector Scaled', 'id': 'control-vector-scaled', 'type': 'text', 'default': '', 'description': 'Add a control vector with user defined scaling. Format: FNAME:SCALE,...', 'prefix': '--control-vector-scaled'},
            {'name': 'Control Vector Layer Range', 'id': 'control-vector-layer-range', 'type': 'text', 'default': '', 'description': 'Layer range to apply the control vector(s) to, start and end inclusive. Format: START END', 'prefix': '--control-vector-layer-range'},
        ]
    },
    {
        "name": "Model Download Parameters",
        "collapsed": True,
        "parameters": [
            {'name': 'Model URL', 'id': 'model-url', 'type': 'text', 'default': '', 'description': 'Model download url (default: unused). Environment variable: LLAMA_ARG_MODEL_URL', 'prefix': '-mu'},
            {'name': 'HF Repo', 'id': 'hf-repo', 'type': 'text', 'default': '', 'description': 'Hugging Face model repository <user>/<model>[:quant]; quant defaults to Q4_K_M. mmproj is downloaded automatically if available. Example: ggml-org/GLM-4.7-Flash-GGUF:Q4_K_M. Environment variable: LLAMA_ARG_HF_REPO', 'prefix': '-hf'},
            {'name': 'HF File', 'id': 'hf-file', 'type': 'text', 'default': '', 'description': 'Hugging Face model file. Overrides the quant in --hf-repo. Environment variable: LLAMA_ARG_HF_FILE', 'prefix': '-hff'},
            {'name': 'HF Token', 'id': 'hf-token', 'type': 'text', 'default': '', 'description': 'Hugging Face access token (default: value from HF_TOKEN environment variable)', 'prefix': '-hft'},
            {'name': 'Docker Repo', 'id': 'docker-repo', 'type': 'text', 'default': '', 'description': 'Docker Hub model repository [<repo>/]<model>[:quant], e.g. gemma3. Environment variable: LLAMA_ARG_DOCKER_REPO', 'prefix': '-dr'},
            {'name': 'Offline', 'id': 'offline', 'type': 'checkbox', 'default': False, 'description': 'Offline mode: forces use of cache, prevents network access', 'prefix': '--offline'},
            {'name': 'Cache List', 'id': 'cache-list', 'type': 'checkbox', 'default': False, 'description': 'Show list of models in cache and exit', 'prefix': '-cl'},
        ]
    },
    {
        "name": "Multimodal Parameters",
        "collapsed": True,
        "parameters": [
            {'name': 'MMProj', 'id': 'mmproj', 'type': 'text', 'default': '', 'description': 'Path to a multimodal projector file. Can be omitted with -hf. Environment variable: LLAMA_ARG_MMPROJ', 'prefix': '--mmproj'},
            {'name': 'MMProj URL', 'id': 'mmproj-url', 'type': 'text', 'default': '', 'description': 'URL to a multimodal projector file. Environment variable: LLAMA_ARG_MMPROJ_URL', 'prefix': '-mmu'},
            {'name': 'No MMProj', 'id': 'no-mmproj', 'type': 'checkbox', 'default': False, 'description': 'Do not use a multimodal projector (useful with -hf). Environment variable: LLAMA_ARG_MMPROJ_AUTO', 'prefix': '--no-mmproj'},
            {'name': 'No MMProj Offload', 'id': 'no-mmproj-offload', 'type': 'checkbox', 'default': False, 'description': 'Do not offload the multimodal projector to GPU (saves VRAM for context). Environment variable: LLAMA_ARG_MMPROJ_OFFLOAD', 'prefix': '--no-mmproj-offload'},
            {'name': 'MMProj Device', 'id': 'mmproj-device', 'type': 'text', 'default': '', 'description': 'Device for the multimodal projector, e.g. CUDA1 (none = do not offload, default: follows --device). Environment variable: MTMD_BACKEND_DEVICE', 'prefix': '-mmdev'},
            {'name': 'Image Min Tokens', 'id': 'image-min-tokens', 'type': 'number', 'default': '', 'description': 'Minimum tokens per image for dynamic-resolution vision models (default: read from model)', 'prefix': '--image-min-tokens'},
            {'name': 'Image Max Tokens', 'id': 'image-max-tokens', 'type': 'number', 'default': '1024', 'description': 'Maximum tokens per image for dynamic-resolution vision models; lower = faster image prompts (default: read from model)', 'prefix': '--image-max-tokens'},
            {'name': 'MTMD Batch Max Tokens', 'id': 'mtmd-batch-max-tokens', 'type': 'number', 'default': '1024', 'description': 'Maximum number of image tokens per batch when encoding images (default: 1024)', 'prefix': '--mtmd-batch-max-tokens'},
            {'name': 'Video FPS', 'id': 'video-fps', 'type': 'number', 'default': '4.0', 'description': 'Target video frame rate (default: 4.0)', 'prefix': '--video-fps'},
            {'name': 'Video Timestamp Interval', 'id': 'video-timestamp-interval', 'type': 'number', 'default': '5000', 'description': 'Interval in milliseconds between text timestamps (default: 5000)', 'prefix': '--video-timestamp-interval'},
            {'name': 'Video FFmpeg Dir', 'id': 'video-ffmpeg-dir', 'type': 'text', 'default': '', 'description': 'Directory containing ffmpeg and ffprobe (default: search in PATH)', 'prefix': '--video-ffmpeg-dir'},
            {'name': 'Media Path', 'id': 'media-path', 'type': 'text', 'default': '', 'description': 'Directory for loading local media files via file:// URLs (default: disabled)', 'prefix': '--media-path'},
        ]
    },
    {
        "name": "Sampling Parameters",
        "collapsed": True,
        "parameters": [
            {'name': 'Temperature', 'id': 'temp', 'type': 'number', 'default': '0.8', 'description': 'Temperature (default: 0.80)', 'prefix': '--temp'},
            {'name': 'Top K', 'id': 'top-k', 'type': 'number', 'default': '40', 'description': 'Top-k sampling (default: 40, 0 = disabled)', 'prefix': '--top-k'},
            {'name': 'Top P', 'id': 'top-p', 'type': 'number', 'default': '0.95', 'description': 'Top-p sampling (default: 0.95, 1.0 = disabled)', 'prefix': '--top-p'},
            {'name': 'Min P', 'id': 'min-p', 'type': 'number', 'default': '0.05', 'description': 'Min-p sampling (default: 0.05, 0.0 = disabled)', 'prefix': '--min-p'},
            {'name': 'Presence Penalty', 'id': 'presence-penalty', 'type': 'number', 'default': '0.0', 'description': 'Repeat alpha presence penalty (default: 0.00, 0.0 = disabled)', 'prefix': '--presence-penalty'},
            {'name': 'Repeat Penalty', 'id': 'repeat-penalty', 'type': 'number', 'default': '1.0', 'description': 'Penalize repeat sequence of tokens (default: 1.00, 1.0 = disabled)', 'prefix': '--repeat-penalty'},
            {'name': 'Backend Sampling', 'id': 'backend-sampling', 'type': 'checkbox', 'default': False, 'description': 'NEW: run sampling on the GPU backend (experimental, default: disabled). Can raise t/s on fast GPUs. Environment variable: LLAMA_ARG_BACKEND_SAMPLING', 'prefix': '-bs'},
            {'name': 'Samplers', 'id': 'samplers', 'type': 'text', 'default': 'penalties;dry;top_n_sigma;top_k;typ_p;top_p;min_p;xtc;temperature', 'description': "Samplers used for generation, in order, separated by ';'", 'prefix': '--samplers'},
            {'name': 'Seed', 'id': 'seed', 'type': 'number', 'default': '-1', 'description': 'RNG seed (default: -1, use random seed for -1)', 'prefix': '-s'},
            {'name': 'Sampling Seq', 'id': 'sampling-seq', 'type': 'text', 'default': 'edskypmxt', 'description': 'Simplified sequence for samplers (default: edskypmxt)', 'prefix': '--sampling-seq'},
            {'name': 'Ignore EOS', 'id': 'ignore-eos', 'type': 'checkbox', 'default': False, 'description': 'Ignore end of stream token and continue generating (implies --logit-bias EOS-inf)', 'prefix': '--ignore-eos'},
            {'name': 'Top N Sigma', 'id': 'top-nsigma', 'type': 'number', 'default': '-1.0', 'description': 'Top-n-sigma sampling (default: -1.00 = disabled)', 'prefix': '--top-nsigma'},
            {'name': 'XTC Probability', 'id': 'xtc-probability', 'type': 'number', 'default': '0.0', 'description': 'XTC probability (default: 0.00 = disabled)', 'prefix': '--xtc-probability'},
            {'name': 'XTC Threshold', 'id': 'xtc-threshold', 'type': 'number', 'default': '0.1', 'description': 'XTC threshold (default: 0.10, 1.0 = disabled)', 'prefix': '--xtc-threshold'},
            {'name': 'Typical', 'id': 'typical', 'type': 'number', 'default': '1.0', 'description': 'Locally typical sampling, parameter p (default: 1.00 = disabled)', 'prefix': '--typical'},
            {'name': 'Adaptive-P Target', 'id': 'adaptive-target', 'type': 'number', 'default': '-1.0', 'description': 'NEW adaptive-p sampler: select tokens near this probability (0.0-1.0; negative = disabled)', 'prefix': '--adaptive-target'},
            {'name': 'Adaptive-P Decay', 'id': 'adaptive-decay', 'type': 'number', 'default': '0.90', 'description': 'Adaptive-p decay rate (0.0-0.99, default: 0.90)', 'prefix': '--adaptive-decay'},
            {'name': 'Repeat Last N', 'id': 'repeat-last-n', 'type': 'number', 'default': '64', 'description': 'Last n tokens to consider for penalize (default: 64, 0 = disabled)', 'prefix': '--repeat-last-n'},
            {'name': 'Frequency Penalty', 'id': 'frequency-penalty', 'type': 'number', 'default': '0.0', 'description': 'Repeat alpha frequency penalty (default: 0.00 = disabled)', 'prefix': '--frequency-penalty'},
            {'name': 'DRY Multiplier', 'id': 'dry-multiplier', 'type': 'number', 'default': '0.0', 'description': 'DRY sampling multiplier (default: 0.00 = disabled)', 'prefix': '--dry-multiplier'},
            {'name': 'DRY Base', 'id': 'dry-base', 'type': 'number', 'default': '1.75', 'description': 'DRY sampling base value (default: 1.75)', 'prefix': '--dry-base'},
            {'name': 'DRY Allowed Length', 'id': 'dry-allowed-length', 'type': 'number', 'default': '2', 'description': 'Allowed length for DRY sampling (default: 2)', 'prefix': '--dry-allowed-length'},
            {'name': 'DRY Penalty Last N', 'id': 'dry-penalty-last-n', 'type': 'number', 'default': '64', 'description': 'DRY penalty for the last n tokens (default: 64, 0 = disable)', 'prefix': '--dry-penalty-last-n'},
            {'name': 'DRY Sequence Breaker', 'id': 'dry-sequence-breaker', 'type': 'text', 'default': '', 'description': "Add sequence breaker for DRY sampling, clearing out default breakers; use \"none\" for no breakers", 'prefix': '--dry-sequence-breaker'},
            {'name': 'Dynatemp Range', 'id': 'dynatemp-range', 'type': 'number', 'default': '0.0', 'description': 'Dynamic temperature range (default: 0.00 = disabled)', 'prefix': '--dynatemp-range'},
            {'name': 'Dynatemp Exp', 'id': 'dynatemp-exp', 'type': 'number', 'default': '1.0', 'description': 'Dynamic temperature exponent (default: 1.00)', 'prefix': '--dynatemp-exp'},
            {'name': 'Mirostat', 'id': 'mirostat', 'type': 'select', 'default': '0', 'options': ['0', '1', '2'], 'description': 'Mirostat sampling (0 = disabled, 1 = Mirostat, 2 = Mirostat 2.0)', 'prefix': '--mirostat'},
            {'name': 'Mirostat LR', 'id': 'mirostat-lr', 'type': 'number', 'default': '0.1', 'description': 'Mirostat learning rate, parameter eta (default: 0.10)', 'prefix': '--mirostat-lr'},
            {'name': 'Mirostat Ent', 'id': 'mirostat-ent', 'type': 'number', 'default': '5.0', 'description': 'Mirostat target entropy, parameter tau (default: 5.00)', 'prefix': '--mirostat-ent'},
            {'name': 'Logit Bias', 'id': 'logit-bias', 'type': 'text', 'default': '', 'description': "Modify the likelihood of a token, e.g. 15043+1 to increase ' Hello'", 'prefix': '-l'},
            {'name': 'Grammar', 'id': 'grammar', 'type': 'text', 'default': '', 'description': 'BNF-like grammar to constrain generations', 'prefix': '--grammar'},
            {'name': 'Grammar File', 'id': 'grammar-file', 'type': 'text', 'default': '', 'description': 'File to read grammar from', 'prefix': '--grammar-file'},
            {'name': 'JSON Schema', 'id': 'json-schema', 'type': 'text', 'default': '', 'description': 'JSON schema to constrain generations, e.g. {} for any JSON object', 'prefix': '-j'},
            {'name': 'JSON Schema File', 'id': 'json-schema-file', 'type': 'text', 'default': '', 'description': 'File containing a JSON schema to constrain generations', 'prefix': '-jf'},
        ]
    },
    {
        "name": "ROPE & Context Scaling Parameters",
        "collapsed": True,
        "parameters": [
            {'name': 'No Escape', 'id': 'no-escape', 'type': 'checkbox', 'default': False, 'description': 'Do not process escape sequences (\\n, \\r, \\t, \\\', \\", \\\\) (default: processed)', 'prefix': '--no-escape'},
            {'name': 'ROPE Scaling', 'id': 'rope-scaling', 'type': 'select', 'default': 'yarn', 'options': ['none', 'linear', 'yarn'], 'description': 'RoPE frequency scaling method, defaults to linear unless specified by the model', 'prefix': '--rope-scaling'},
            {'name': 'ROPE Scale', 'id': 'rope-scale', 'type': 'number', 'default': '1.0', 'description': 'RoPE context scaling factor, expands context by a factor of N', 'prefix': '--rope-scale'},
            {'name': 'ROPE Freq Base', 'id': 'rope-freq-base', 'type': 'number', 'default': '0', 'description': 'RoPE base frequency, used by NTK-aware scaling (default: loaded from model)', 'prefix': '--rope-freq-base'},
            {'name': 'ROPE Freq Scale', 'id': 'rope-freq-scale', 'type': 'number', 'default': '1.0', 'description': 'RoPE frequency scaling factor, expands context by a factor of 1/N', 'prefix': '--rope-freq-scale'},
            {'name': 'YARN Orig Ctx', 'id': 'yarn-orig-ctx', 'type': 'number', 'default': '0', 'description': 'YaRN: original context size of model (default: 0 = model training context size)', 'prefix': '--yarn-orig-ctx'},
            {'name': 'YARN Ext Factor', 'id': 'yarn-ext-factor', 'type': 'number', 'default': '-1.0', 'description': 'YaRN: extrapolation mix factor (default: -1.00, 0.0 = full interpolation)', 'prefix': '--yarn-ext-factor'},
            {'name': 'YARN Attn Factor', 'id': 'yarn-attn-factor', 'type': 'number', 'default': '-1.0', 'description': 'YaRN: scale sqrt(t) or attention magnitude (default: -1.00)', 'prefix': '--yarn-attn-factor'},
            {'name': 'YARN Beta Slow', 'id': 'yarn-beta-slow', 'type': 'number', 'default': '-1.0', 'description': 'YaRN: high correction dim or alpha (default: -1.00)', 'prefix': '--yarn-beta-slow'},
            {'name': 'YARN Beta Fast', 'id': 'yarn-beta-fast', 'type': 'number', 'default': '-1.0', 'description': 'YaRN: low correction dim or beta (default: -1.00)', 'prefix': '--yarn-beta-fast'},
        ]
    },
    {
        "name": "Logging & Debug Parameters",
        "collapsed": True,
        "parameters": [
            {'name': 'Verbosity', 'id': 'verbosity', 'type': 'select', 'default': '3', 'options': ['0', '1', '2', '3', '4', '5'], 'description': 'Verbosity threshold: 0 generic, 1 error, 2 warning, 3 info (default), 4 trace, 5 debug. The Tuning Wizard needs 4 to read memory stats.', 'prefix': '-lv'},
            {'name': 'Verbose', 'id': 'verbose', 'type': 'checkbox', 'default': False, 'description': 'Set verbosity level to infinity (log all messages, useful for debugging)', 'prefix': '-v'},
            {'name': 'Log Disable', 'id': 'log-disable', 'type': 'checkbox', 'default': False, 'description': 'Disable logging', 'prefix': '--log-disable'},
            {'name': 'Log File', 'id': 'log-file', 'type': 'text', 'default': '', 'description': 'Log to file. Environment variable: LLAMA_ARG_LOG_FILE', 'prefix': '--log-file'},
            {'name': 'Log JSONL', 'id': 'log-jsonl', 'type': 'checkbox', 'default': False, 'description': 'Log as JSONL (one JSON object per line) to stdout', 'prefix': '--log-jsonl'},
            {'name': 'Log Colors', 'id': 'log-colors', 'type': 'select', 'default': 'auto', 'options': ['auto', 'on', 'off'], 'description': "Colored logging ('on', 'off', or 'auto')", 'prefix': '--log-colors'},
            {'name': 'Log Prefix', 'id': 'log-prefix', 'type': 'checkbox', 'default': False, 'description': 'Enable prefix in log messages', 'prefix': '--log-prefix'},
            {'name': 'Log Timestamps', 'id': 'log-timestamps', 'type': 'checkbox', 'default': False, 'description': 'Enable timestamps in log messages', 'prefix': '--log-timestamps'},
            {'name': 'Log Prompts Dir', 'id': 'log-prompts-dir', 'type': 'text', 'default': '', 'description': 'Log prompts to directory (debugging only, default: disabled)', 'prefix': '--log-prompts-dir'},
            {'name': 'Version', 'id': 'version', 'type': 'checkbox', 'default': False, 'description': 'Show version and build information and exit', 'prefix': '--version'},
        ]
    },
    {
        "name": "Server Parameters",
        "collapsed": True,
        "parameters": [
            {'name': 'Host', 'id': 'host', 'type': 'text', 'default': '127.0.0.1', 'description': 'IP address to listen, or bind to a UNIX socket if it ends with .sock (default: 127.0.0.1). Use 0.0.0.0 to expose on the LAN.', 'prefix': '--host'},
            {'name': 'Port', 'id': 'port', 'type': 'number', 'default': '8080', 'description': 'Port to listen (default: 8080)', 'prefix': '--port'},
            {'name': 'Alias', 'id': 'alias', 'type': 'text', 'default': '', 'description': 'Model name aliases, comma-separated (used by the API)', 'prefix': '-a'},
            {'name': 'Tags', 'id': 'tags', 'type': 'text', 'default': '', 'description': 'Model tags, comma-separated (informational)', 'prefix': '--tags'},
            {'name': 'API Key', 'id': 'api-key', 'type': 'text', 'default': '', 'description': 'API key(s) for authentication, comma-separated (default: none)', 'prefix': '--api-key'},
            {'name': 'API Key File', 'id': 'api-key-file', 'type': 'text', 'default': '', 'description': 'File containing API keys, one per line (default: none)', 'prefix': '--api-key-file'},
            {'name': 'Metrics', 'id': 'metrics', 'type': 'checkbox', 'default': False, 'description': 'Enable prometheus compatible /metrics endpoint (default: disabled)', 'prefix': '--metrics'},
            {'name': 'Props', 'id': 'props', 'type': 'checkbox', 'default': False, 'description': 'Enable changing global properties via POST /props (default: disabled)', 'prefix': '--props'},
            {'name': 'No Slots Endpoint', 'id': 'no-slots', 'type': 'checkbox', 'default': False, 'description': 'Disable the slots monitoring endpoint (default: enabled)', 'prefix': '--no-slots'},
            {'name': 'Timeout', 'id': 'timeout', 'type': 'number', 'default': '3600', 'description': 'Server read/write timeout in seconds (default: 3600)', 'prefix': '-to'},
            {'name': 'Threads HTTP', 'id': 'threads-http', 'type': 'number', 'default': '-1', 'description': 'Number of threads used to process HTTP requests (default: -1)', 'prefix': '--threads-http'},
            {'name': 'SSE Ping Interval', 'id': 'sse-ping-interval', 'type': 'number', 'default': '30', 'description': 'Server SSE ping interval in seconds (-1 = disabled, default: 30)', 'prefix': '--sse-ping-interval'},
            {'name': 'Sleep Idle Seconds', 'id': 'sleep-idle-seconds', 'type': 'number', 'default': '-1', 'description': 'Seconds of idleness after which the server sleeps and frees memory (default: -1 = disabled)', 'prefix': '--sleep-idle-seconds'},
            {'name': 'No Web UI', 'id': 'no-webui', 'type': 'checkbox', 'default': False, 'description': 'Disable the Web UI (default: enabled)', 'prefix': '--no-webui'},
            {'name': 'Web UI Config', 'id': 'ui-config', 'type': 'text', 'default': '', 'description': 'JSON with default Web UI settings', 'prefix': '--ui-config'},
            {'name': 'Web UI Config File', 'id': 'ui-config-file', 'type': 'text', 'default': '', 'description': 'JSON file with default Web UI settings', 'prefix': '--ui-config-file'},
            {'name': 'Path', 'id': 'path', 'type': 'text', 'default': '', 'description': 'Path to serve static files from', 'prefix': '--path'},
            {'name': 'API Prefix', 'id': 'api-prefix', 'type': 'text', 'default': '', 'description': 'Prefix path the server serves from, without the trailing slash', 'prefix': '--api-prefix'},
            {'name': 'Reuse Port', 'id': 'reuse-port', 'type': 'checkbox', 'default': False, 'description': 'Allow multiple sockets to bind to the same port', 'prefix': '--reuse-port'},
            {'name': 'CORS Origins', 'id': 'cors-origins', 'type': 'text', 'default': 'localhost', 'description': "Comma-separated list of allowed CORS origins (default: *). 'localhost' only reflects localhost origins", 'prefix': '--cors-origins'},
            {'name': 'SSL Key File', 'id': 'ssl-key-file', 'type': 'text', 'default': '', 'description': 'Path to a PEM-encoded SSL private key', 'prefix': '--ssl-key-file'},
            {'name': 'SSL Cert File', 'id': 'ssl-cert-file', 'type': 'text', 'default': '', 'description': 'Path to a PEM-encoded SSL certificate', 'prefix': '--ssl-cert-file'},
            {'name': 'Embeddings', 'id': 'embeddings', 'type': 'checkbox', 'default': False, 'description': 'Restrict to embedding use case; use only with dedicated embedding models', 'prefix': '--embeddings'},
            {'name': 'Reranking', 'id': 'reranking', 'type': 'checkbox', 'default': False, 'description': 'Enable reranking endpoint on server', 'prefix': '--reranking'},
            {'name': 'Models Dir (Router)', 'id': 'models-dir', 'type': 'text', 'default': '', 'description': 'Directory containing models for the router server (multi-model, load on demand)', 'prefix': '--models-dir'},
            {'name': 'Models Preset (Router)', 'id': 'models-preset', 'type': 'text', 'default': '', 'description': 'Path to INI file containing model presets for the router server', 'prefix': '--models-preset'},
            {'name': 'Models Max (Router)', 'id': 'models-max', 'type': 'number', 'default': '4', 'description': 'Maximum number of models loaded simultaneously by the router (default: 4, 0 = unlimited)', 'prefix': '--models-max'},
            {'name': 'No Models Autoload', 'id': 'no-models-autoload', 'type': 'checkbox', 'default': False, 'description': 'Router server: do not load models automatically', 'prefix': '--no-models-autoload'},
        ]
    },
    {
        "name": "Chat Template & Reasoning",
        "collapsed": True,
        "parameters": [
            {'name': 'Jinja', 'id': 'jinja', 'type': 'checkbox', 'default': False, 'description': 'Use jinja template engine for chat (default: enabled)', 'prefix': '--jinja'},
            {'name': 'No Jinja', 'id': 'no-jinja', 'type': 'checkbox', 'default': False, 'description': 'Disable the jinja template engine', 'prefix': '--no-jinja'},
            {'name': 'Reasoning', 'id': 'reasoning', 'type': 'select', 'default': 'auto', 'options': ['auto', 'on', 'off'], 'description': "Use reasoning/thinking in the chat ('on', 'off', or 'auto' = detect from template). Turning it off makes thinking models answer much faster.", 'prefix': '-rea'},
            {'name': 'Reasoning Effort', 'id': 'reasoning-effort', 'type': 'select', 'default': 'default', 'options': ['default', 'minimal', 'low', 'medium', 'high', 'xhigh', 'max'], 'description': 'Reasoning effort level given to the chat template (default: template default)', 'prefix': '--reasoning-effort'},
            {'name': 'Reasoning Format', 'id': 'reasoning-format', 'type': 'select', 'default': 'auto', 'options': ['auto', 'none', 'deepseek', 'deepseek-legacy'], 'description': 'How thoughts are returned: none (in content), deepseek (reasoning_content), deepseek-legacy (both). Default: auto', 'prefix': '--reasoning-format'},
            {'name': 'Reasoning Budget', 'id': 'reasoning-budget', 'type': 'number', 'default': '-1', 'description': 'Token budget for thinking: -1 unrestricted, 0 immediate end, N>0 budget (default: -1)', 'prefix': '--reasoning-budget'},
            {'name': 'Reasoning Budget Message', 'id': 'reasoning-budget-message', 'type': 'text', 'default': '', 'description': 'Message injected before the end-of-thinking tag when the reasoning budget is exhausted', 'prefix': '--reasoning-budget-message'},
            {'name': 'No Reasoning Preserve', 'id': 'no-reasoning-preserve', 'type': 'checkbox', 'default': False, 'description': 'Do not preserve the reasoning trace in the full history (default: preserved)', 'prefix': '--no-reasoning-preserve'},
            {'name': 'Skip Chat Parsing', 'id': 'skip-chat-parsing', 'type': 'checkbox', 'default': False, 'description': 'Force a pure content parser: reasoning and tool calls stay in content', 'prefix': '--skip-chat-parsing'},
            {'name': 'Chat Template Kwargs', 'id': 'chat-template-kwargs', 'type': 'text', 'default': '{"enable_thinking": false}', 'description': "Additional params for the jinja template parser, a JSON object string, e.g. '{\"key1\":\"value1\"}'", 'prefix': '--chat-template-kwargs'},
            {'name': 'Chat Template', 'id': 'chat-template', 'type': 'select', 'default': 'chatml', 'options': ['bailing', 'bailing-think', 'bailing2', 'chatglm3', 'chatglm4', 'chatml', 'command-r', 'deepseek', 'deepseek-ocr', 'deepseek2', 'deepseek3', 'exaone-moe', 'exaone3', 'exaone4', 'falcon3', 'gemma', 'gigachat', 'glmedge', 'gpt-oss', 'granite', 'granite-4.0', 'granite-4.1', 'grok-2', 'hunyuan-dense', 'hunyuan-moe', 'hunyuan-vl', 'kimi-k2', 'llama2', 'llama2-sys', 'llama2-sys-bos', 'llama2-sys-strip', 'llama3', 'llama4', 'megrez', 'minicpm', 'mistral-v1', 'mistral-v3', 'mistral-v3-tekken', 'mistral-v7', 'mistral-v7-tekken', 'monarch', 'openchat', 'orion', 'pangu-embedded', 'phi3', 'phi4', 'rwkv-world', 'seed_oss', 'smolvlm', 'solar-open', 'vicuna', 'vicuna-orca', 'yandex', 'zephyr'], 'description': "Built-in chat template (default: template from the model's metadata)", 'prefix': '--chat-template'},
            {'name': 'Chat Template File', 'id': 'chat-template-file', 'type': 'text', 'default': '', 'description': "Custom jinja chat template file (default: template from the model's metadata)", 'prefix': '--chat-template-file'},
            {'name': 'No Prefill Assistant', 'id': 'no-prefill-assistant', 'type': 'checkbox', 'default': False, 'description': 'Treat a trailing assistant message as complete instead of prefilling it', 'prefix': '--no-prefill-assistant'},
        ]
    },
    {
        "name": "Agent Tools & MCP (Experimental)",
        "collapsed": True,
        "parameters": [
            {'name': 'Built-in Tools', 'id': 'tools', 'type': 'text', 'default': 'all', 'description': 'Experimental built-in tools for AI agents: read_file, file_glob_search, grep_search, exec_shell_command, write_file, edit_file, get_info, or "all". Do not enable in untrusted environments.', 'prefix': '--tools'},
            {'name': 'Tools Runtime', 'id': 'tools-runtime', 'type': 'text', 'default': '', 'description': "Run tools in a separate environment: 'docker:<image>', 'podman:<image>', 'docker-container:<id>', 'ssh:<target>'", 'prefix': '--tools-runtime'},
            {'name': 'MCP Servers Config', 'id': 'mcp-servers-config', 'type': 'text', 'default': '', 'description': 'Path to JSON file with MCP server definitions (Cursor-compatible format)', 'prefix': '--mcp-servers-config'},
            {'name': 'MCP Servers JSON', 'id': 'mcp-servers-json', 'type': 'text', 'default': '', 'description': 'Inline JSON with MCP server definitions', 'prefix': '--mcp-servers-json'},
            {'name': 'Web UI MCP Proxy', 'id': 'ui-mcp-proxy', 'type': 'checkbox', 'default': False, 'description': 'Enable the Web UI MCP CORS proxy (experimental)', 'prefix': '--ui-mcp-proxy'},
            {'name': 'Agent Mode', 'id': 'agent', 'type': 'checkbox', 'default': False, 'description': 'Enable CORS proxy and all built-in tools (limits CORS to localhost)', 'prefix': '-ag'},
        ]
    },
    {
        "name": "Pre-configured Model Shortcuts",
        "collapsed": True,
        "parameters": [
            {'name': 'EmbeddingGemma Default', 'id': 'embd-gemma-default', 'type': 'checkbox', 'default': False, 'description': 'Use default EmbeddingGemma model (downloads weights)', 'prefix': '--embd-gemma-default'},
            {'name': 'FIM Qwen 1.5B Default', 'id': 'fim-qwen-1.5b-default', 'type': 'checkbox', 'default': False, 'description': 'Use default Qwen 2.5 Coder 1.5B (downloads weights)', 'prefix': '--fim-qwen-1.5b-default'},
            {'name': 'FIM Qwen 3B Default', 'id': 'fim-qwen-3b-default', 'type': 'checkbox', 'default': False, 'description': 'Use default Qwen 2.5 Coder 3B (downloads weights)', 'prefix': '--fim-qwen-3b-default'},
            {'name': 'FIM Qwen 7B Default', 'id': 'fim-qwen-7b-default', 'type': 'checkbox', 'default': False, 'description': 'Use default Qwen 2.5 Coder 7B (downloads weights)', 'prefix': '--fim-qwen-7b-default'},
            {'name': 'FIM Qwen 7B Spec', 'id': 'fim-qwen-7b-spec', 'type': 'checkbox', 'default': False, 'description': 'Use Qwen 2.5 Coder 7B + 0.5B draft for speculative decoding (downloads weights)', 'prefix': '--fim-qwen-7b-spec'},
            {'name': 'FIM Qwen 14B Spec', 'id': 'fim-qwen-14b-spec', 'type': 'checkbox', 'default': False, 'description': 'Use Qwen 2.5 Coder 14B + 0.5B draft for speculative decoding (downloads weights)', 'prefix': '--fim-qwen-14b-spec'},
            {'name': 'FIM Qwen 30B Default', 'id': 'fim-qwen-30b-default', 'type': 'checkbox', 'default': False, 'description': 'Use default Qwen 3 Coder 30B A3B Instruct (downloads weights)', 'prefix': '--fim-qwen-30b-default'},
            {'name': 'GPT-OSS 20B Default', 'id': 'gpt-oss-20b-default', 'type': 'checkbox', 'default': False, 'description': 'Use gpt-oss-20b (downloads weights)', 'prefix': '--gpt-oss-20b-default'},
            {'name': 'GPT-OSS 120B Default', 'id': 'gpt-oss-120b-default', 'type': 'checkbox', 'default': False, 'description': 'Use gpt-oss-120b (downloads weights)', 'prefix': '--gpt-oss-120b-default'},
            {'name': 'Vision Gemma 4B Default', 'id': 'vision-gemma-4b-default', 'type': 'checkbox', 'default': False, 'description': 'Use Gemma 3 4B QAT (downloads weights)', 'prefix': '--vision-gemma-4b-default'},
            {'name': 'Vision Gemma 12B Default', 'id': 'vision-gemma-12b-default', 'type': 'checkbox', 'default': False, 'description': 'Use Gemma 3 12B QAT (downloads weights)', 'prefix': '--vision-gemma-12b-default'},
        ]
    }
]

# NInfer (ninfer-serve) specific parameters
# NInfer uses positional model path (no flag) — appears right after executable
NINFER_PARAMETERS = [
    {
        "name": "File Paths",
        "collapsed": False,
        "parameters": [
            {'name': 'Server Path', 'id': 'server-path', 'type': 'text', 'default': '', 'description': 'Path to ninfer-serve.exe without quotes', 'required': True, 'prefix': ''},
            {'name': 'Model Path', 'id': 'model-path', 'type': 'text', 'default': '', 'description': 'Path to .ninfer model file (positional argument, no flag prefix)', 'required': True, 'prefix': '-m'},
        ]
    },
    {
        "name": "Server Parameters",
        "collapsed": True,
        "parameters": [
            {'name': 'Host', 'id': 'host', 'type': 'text', 'default': '0.0.0.0', 'description': 'IP address to listen on (default: 0.0.0.0)', 'prefix': '--host'},
            {'name': 'Port', 'id': 'port', 'type': 'number', 'default': '8080', 'description': 'Port to listen on (default: 8080)', 'prefix': '--port'},
            {'name': 'Model ID', 'id': 'model-id', 'type': 'text', 'default': '', 'description': 'Alias/ID for the model in HTTP API (default: derived from model name)', 'prefix': '--model-id'},
        ]
    },
    {
        "name": "Context & Memory Parameters",
        "collapsed": True,
        "parameters": [
            {'name': 'Max Context', 'id': 'max-context', 'type': 'number', 'default': '4096', 'description': 'Maximum context size (default: 4096)', 'prefix': '--max-context'},
            {'name': 'Batch Size', 'id': 'batch-size', 'type': 'number', 'default': '2048', 'description': 'Batch size for processing (default: 2048)', 'prefix': '--batch-size'},
            {'name': 'UBatch Size', 'id': 'ubatch-size', 'type': 'number', 'default': '512', 'description': 'Physical maximum batch size (default: 512)', 'prefix': '--ubatch-size'},
            {'name': 'KV Dtype', 'id': 'kv-dtype', 'type': 'select', 'default': 'auto', 'options': ['auto', 'fp16', 'bf16', 'fp32', 'q8_0', 'q4_0'], 'description': 'Data type for KV cache (default: auto)', 'prefix': '--kv-dtype'},
        ]
    },
    {
        "name": "Threading & GPU Parameters",
        "collapsed": True,
        "parameters": [
            {'name': 'Threads', 'id': 'threads', 'type': 'number', 'default': '-1', 'description': 'Number of threads to use (default: -1 = auto)', 'prefix': '--threads'},
            {'name': 'GPU Layers', 'id': 'gpu-layers', 'type': 'number', 'default': '-1', 'description': 'Number of layers to offload to GPU (-1 = all)', 'prefix': '--gpu-layers'},
        ]
    },
    {
        "name": "Vision Parameters",
        "collapsed": True,
        "parameters": [
            {'name': 'Image Max Tokens', 'id': 'image-max-tokens', 'type': 'number', 'default': '', 'description': 'Maximum vision tokens per image; downscales larger images (default: use the model artifact embedded setting). Requires the NInfer binary built with the --image-max-tokens flag (0.6.2); the 0.6.1 binary rejects it. Recommended: 1024 (1M px, ~8 large screenshots per request)', 'prefix': '--image-max-tokens'},
        ]
    },
    {
        "name": "Logging Parameters",
        "collapsed": True,
        "parameters": [
            {'name': 'Verbose', 'id': 'verbose', 'type': 'checkbox', 'default': False, 'description': 'Enable verbose logging output', 'prefix': '--verbose'},
        ]
    },
]

BENCHMARK_PROMPT = '''
                **Task:**  
Create a ranked list of the provided LLM models from **fastest to slowest** based on their reported **tokens per second (t/s)**.  

**Persona:**  
You are an expert LLM performance analyst.  

**Output Format:**  
Present the results as a **markdown table** with the following columns, preserving **all characteristics** exactly as given:

| Rank | Model Name | Storage Size | CUDA Version | Context Length | Offload Type | CPU Thread Pool Size | Evaluation Batch Size | Offload KV Cache | Flash Attention | K‑Cache Quantized | V‑Cache Quantized | Tokens per Second |
|------|------------|--------------|--------------|----------------|--------------|----------------------|-----------------------|------------------|-----------------|-------------------|-------------------|--------------------|

- **Rank 1** should be the model with the highest t/s, **Rank N** the lowest.  
- If two models have identical t/s, order them alphabetically by model name.  
- For models lacking a specific attribute (e.g., K‑Cache or V‑Cache Quantized, Offload KV Cache), the corresponding table cell should be left blank.


**Constraints & Guidance:**  
- Include **every** model and **all** listed attributes; do not omit or modify any values.  
- Explicitly state “Verified: all entries sorted correctly by tokens per second.” at the end of the table.  
- If any required information is ambiguous or missing, note it in a separate “Assumptions / Issues” section below the table.  

---  

*Paste the raw model list (as in the original prompt) below this line before running the LLM.* 

```
mistral-small-3.2-24b-instruct-2506 Q6_K_XL - 22.54 GB - cuda 12 - 45k ctx - full offload - 8 - 512 - offload kv checked - flash - kcache - vcache - 41t/s
Qwen3-32B-UD-Q4_K_XL - 20.02 GB - cuda 12 - 35k ctx - full offload - 8 - 512 - offload kv checked - flash - kcache - vcache - 39t/s
Qwen3-Nemotron-32B-RLBFF.i1-Q4_K_M - 19.76 GB - cuda 12 - 30k ctx - full offload - 8 - 512 - offload kv checked - flash - kcache - vcache - 30t/s
Qwen3-VL-32B-Instruct.Q4_K_M_TEXT - 20.96 GB - cuda 12 - 30k ctx - full offload - 8 - 512 - offload kv checked - flash - kcache - vcache - 35t/s
Qwen3-VL-32B-Instruct.Q4_K_M_TEXT_DRAFT - 20.96 GB - cuda 12 - 30k ctx - full offload - 8 - 512 - offload kv checked - flash - kcache - vcache - 50t/s
Qwen3-VL-32B-Thinking.Q4_K_M_TEXT_DRAFT - 20.96 GB - cuda 12 - 15k ctx - full offload - 8 - 512 - offload kv checked - flash - kcache - vcache - 35t/s
Qwen3-VL-32B-Instruct.Q6_K_TEXT_DRAFT - 28.08 GB - cuda 12 - 15k ctx - full offload - 8 - 512 - offload kv checked - flash - kcache - vcache - 37t/s
Qwen3-VL-32B-Instruct.Q4_K_M_VL - 20.96 GB - cuda 12 - 17k ctx - full offload - 8 - 512 - offload kv checked - flash - kcache - vcache - 37t/s
Llama-3.3-70B-Instruct-UD-IQ3_XXS - 27.66 GB - cuda 12 - 10k ctx - full offload - 8 - 512 - offload kv checked - flash - kcache - vcache - speculative decoding 1b - 20t/s
gemma-3-27b-it-UD-Q6_K_XL - 25.41 GB - cuda - 130k ctx - full offload - 8 - 512 - offload kv checked - flash - kcache - vcache - 25t/s
Qwen3-14B-128K-UD-Q8_K_XL - 18.75 GB - cuda 12 - 80k ctx - full offload - 8 - 2048 - offload kv checked - flash - kcache - vcache - 48t/s
nvidia_llama-3_3-nemotron-super-49b-v1_5 - 28.63 GB - cuda 12 - 31k ctx - full offload - 8 - 512 - offload kv checked - flash - kcache - vcache - 21t/s
qwen3-30b-a3b-instruct-2507@q4_k_m - 18.56 GB - cuda 12 - 110k ctx - full offload - 8 - 2048 - offload kv checked - flash - 136t/s
GLM-Z1-32B-0414-Q4_K_M - 19.68 GB - cuda 12 - 32k ctx - full offload - 8 - 512 - offload kv checked - flash - kcache - vcache - 40t/s
UIGEN-X-32B-0727.Q4_K_M - 19.76 GB - cuda 12 - 19k ctx - full offload - 8 - 512- offload kv checked - flash - 39t/s
gemma-3-27b-it-qat-UD-Q4_K_XL - 18.51 GB - cuda 12 - 131k ctx - full offload - 8 - 512 - offload kv checked - flash - kcache - vcache - 42t/s
gpt-oss-20b-MXFP4 - 12.11 GB - cuda 12 - 131k ctx - full offload - 8 - 2048 - offload kv checked - flash -  170t/s
Devstral-Small-2507-Q6_K - 19.35 GB - cuda 12 - 64k ctx - full offload - 8 - 512 - offload kv checked - flash - kcache - vcache - 39t/s
GLM-4.5-Air-UD-Q3_K_XL - 57.73 GB - cuda 12 - 27k ctx - 19/47 layer offload to gpu - 8 - 512 - flash - kcache - vcache - 7t/s
Qwen3-Coder-30B-A3B-Instruct-UD-Q6_K_XL - 26.34 GB - cuda 12 - 75k ctx - full offload - 8 - 512 - offload kv checked - flash - kcache - vcache- 79t/s
Seed-OSS-36B-Instruct-UD-Q4_K_XL - 22.03 GB - cuda 12 - 21k ctx - full offload - 8 - 512 - offload kv checked - flash  - kcache - vcache - 35t/s
Magistral-Small-2509-UD-Q5_K_XL - 18.52 GB - cuda 12 - 85k ctx - full offload - 8 - 512 - offload kv checked - flash - kcache - vcache - 42t/s
gpt-oss-120b-MXFP4 - 63.39 GB - cuda 12 - 45k ctx - 16/36 layer offload to gpu - 8 - 512 - flash - kcache - vcache - 9t/s
Qwen3-VL-30B-A3B-Instruct-UD-Q4_K_XL_TEXT - 19.87 GB - cuda 12 - 70k ctx - full offload - 8 - 512 - offload kv checked - flash - kcache - vcache- 133t/s
```
'''
