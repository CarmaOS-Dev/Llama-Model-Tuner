# core/llama_cli.py
"""
Introspection of the user's actual llama.cpp build.

llama.cpp changes its CLI constantly (flags get added, renamed and removed every
few weeks). Instead of trusting only the static parameter database, this module
asks the installed `llama-server` for its `--help` output, parses it into a
structured catalogue and uses it to:

  * know which flags the installed build accepts (compatibility check),
  * migrate obsolete flags (e.g. --no-mmap -> -lm none) before launching,
  * expose flags that are new in the build but unknown to the static database.
"""

import os
import re
import subprocess

from .command_builder import Parameter
from .platform_utils import IS_WINDOWS, get_subprocess_kwargs

_HELP_TIMEOUT_S = 30

# Cache keyed by (executable path, mtime) so a llama.cpp update is picked up automatically.
_cache = {}


class HelpEntry:
    """One option block from `llama-server --help`."""
    __slots__ = ('flags', 'placeholder', 'description', 'env', 'options', 'removed', 'deprecated', 'section')

    def __init__(self, flags, placeholder, section):
        self.flags = flags
        self.placeholder = placeholder
        self.description = ''
        self.env = ''
        self.options = []
        self.removed = False
        self.deprecated = False
        self.section = section

    @property
    def primary(self):
        """Shortest flag is the one llama.cpp users usually type (-ngl, -sm, ...)."""
        return min(self.flags, key=len)

    @property
    def takes_value(self):
        return bool(self.placeholder)

    @property
    def value_optional(self):
        return self.placeholder.startswith('[')


class LlamaCliInfo:
    """Parsed `--help` / `--version` of a llama-server executable."""

    def __init__(self, entries, version_text=''):
        self.entries = entries
        self.version_text = version_text
        self.flag_map = {}
        for entry in entries:
            for flag in entry.flags:
                self.flag_map[flag] = entry

    @property
    def build_number(self):
        match = re.search(r'build\s+(\d+)', self.version_text)
        return int(match.group(1)) if match else None

    @property
    def build_label(self):
        match = re.search(r'version:\s*(.+)', self.version_text)
        return match.group(1).strip() if match else ''

    def supports(self, flag):
        entry = self.flag_map.get(flag)
        return entry is not None and not entry.removed

    def is_removed(self, flag):
        entry = self.flag_map.get(flag)
        return entry is not None and entry.removed

    def is_known(self, flag):
        return flag in self.flag_map

    def entry(self, flag):
        return self.flag_map.get(flag)


# --------------------------------------------------------------------------- parsing

_FLAG_TOKEN = re.compile(r'(?:^|[\s,])(-{1,2}[A-Za-z][A-Za-z0-9_.+-]*)')
_SECTION = re.compile(r'^-{3,}\s*(.+?)\s*-{3,}\s*$')


def _split_flags_and_desc(line):
    """Returns (flag_part, inline_description) for a line that starts an option."""
    normalized = re.sub(r',\s+', ', ', line.rstrip())
    parts = re.split(r'\s{2,}', normalized, maxsplit=1)
    flag_part = parts[0]
    desc = parts[1] if len(parts) > 1 else ''
    return flag_part, desc


def _extract_placeholder(flag_part, flags):
    """Text after the last flag token is the value placeholder (N, FNAME, [on|off|auto], ...)."""
    last = flags[-1]
    idx = flag_part.rfind(last)
    tail = flag_part[idx + len(last):].strip() if idx >= 0 else ''
    return tail.lstrip(',').strip()


def _extract_options(placeholder, description):
    for pattern in (r'^\{([^}]+)\}$', r'^\[([^\]]+)\]$', r'^<([^>]+)>$'):
        match = re.match(pattern, placeholder)
        if match:
            sep = ',' if ',' in match.group(1) else '|'
            options = [o.strip() for o in match.group(1).split(sep)]
            if all(re.match(r'^[A-Za-z0-9_+.-]+$', o) for o in options) and len(options) > 1:
                if not any(o.replace('.', '').isdigit() and '...' in match.group(1) for o in options):
                    return options
    match = re.search(r'allowed values:\s*([A-Za-z0-9_,\s]+?)(?:\(|$)', description)
    if match:
        return [o.strip() for o in match.group(1).split(',') if o.strip()]
    if placeholder in ('MODE', 'TYPE'):
        # e.g. -lm: "- auto: mmap, unless ... - none: no special loading mode - mmap: ..."
        bullets = re.findall(r'(?:^|\s)-\s([a-z][a-z0-9+_-]*):', description)
        if len(bullets) > 1:
            return bullets
    if (placeholder and ',' in placeholder and ' ' not in placeholder and '...' not in placeholder
            and not placeholder.isupper()):
        # e.g. "--spec-type none,draft-simple,draft-mtp,..." (comma-separated list of choices)
        return [o for o in placeholder.split(',') if o]
    return []


def parse_help(text):
    """Parses llama.cpp `--help` output into a list of HelpEntry."""
    entries = []
    current = None
    section = ''
    for raw in text.splitlines():
        line = raw.rstrip()
        sec = _SECTION.match(line.strip())
        if sec:
            section = sec.group(1)
            current = None
            continue
        if line.startswith('-') and not line.startswith('---'):
            flag_part, desc = _split_flags_and_desc(line)
            flags = []
            for token in _FLAG_TOKEN.findall(flag_part):
                if token not in flags:
                    flags.append(token)
            if not flags:
                current = None
                continue
            current = HelpEntry(flags, _extract_placeholder(flag_part, flags), section)
            current.description = desc.strip()
            entries.append(current)
        elif current is not None and line.strip():
            text_line = line.strip()
            env = re.match(r'^\(env:\s*([A-Z0-9_]+)\)$', text_line)
            if env:
                current.env = env.group(1)
            else:
                current.description = (current.description + ' ' + text_line).strip()

    for entry in entries:
        lower = entry.description.lower()
        entry.removed = 'argument has been removed' in lower
        entry.deprecated = '(deprecated)' in lower
        entry.options = _extract_options(entry.placeholder, entry.description)
    return entries


# --------------------------------------------------------------------------- discovery

def find_server_executable(llamacpp_dir, executable=''):
    """Resolves the llama-server executable from the configured directory / command."""
    candidates = []
    if executable:
        candidates.append(executable if os.path.isabs(executable) else os.path.join(llamacpp_dir or '', executable))
    name = 'llama-server.exe' if IS_WINDOWS else 'llama-server'
    if llamacpp_dir:
        candidates.append(os.path.join(llamacpp_dir, name))
    for path in candidates:
        if path and os.path.isfile(path):
            return os.path.normpath(path)
    return None


def find_tool(llamacpp_dir, tool_name):
    """Returns the path of another llama.cpp tool (llama-bench, ...) next to llama-server."""
    if not llamacpp_dir:
        return None
    name = tool_name + ('.exe' if IS_WINDOWS else '')
    path = os.path.join(llamacpp_dir, name)
    return path if os.path.isfile(path) else None


def _run(executable, args):
    try:
        proc = subprocess.run([executable] + args, capture_output=True, text=True, encoding='utf-8',
                              errors='ignore', timeout=_HELP_TIMEOUT_S, cwd=os.path.dirname(executable),
                              **get_subprocess_kwargs())
        return (proc.stdout or '') + (proc.stderr or '')
    except (OSError, subprocess.SubprocessError):
        return ''


def get_cli_info(executable):
    """Returns a cached LlamaCliInfo for the executable, or None if it cannot be queried."""
    if not executable or not os.path.isfile(executable):
        return None
    key = (os.path.normcase(executable), os.path.getmtime(executable))
    if key in _cache:
        return _cache[key]
    help_text = _run(executable, ['--help'])
    entries = parse_help(help_text)
    if not entries:
        _cache[key] = None
        return None
    info = LlamaCliInfo(entries, _run(executable, ['--version']))
    _cache[key] = info
    return info


# --------------------------------------------------------------------------- migration

_BOOL_VALUE_FLAGS = {
    # flag: (flag_when_true, flag_when_false)
    '--context-shift': ('--context-shift', '--no-context-shift'),
    '-cb': ('-cb', '-nocb'),
    '--cont-batching': ('-cb', '-nocb'),
    '--slots': ('--slots', '--no-slots'),
    '-e': ('-e', '--no-escape'),
    '--escape': ('-e', '--no-escape'),
    '--jinja': ('--jinja', '--no-jinja'),
    '--warmup': ('--warmup', '--no-warmup'),
}
_TRUE_VALUES = {'enabled', 'true', 'on', '1', 'yes'}
_FALSE_VALUES = {'disabled', 'false', 'off', '0', 'no'}

_RENAMES = {
    '--draft': '--spec-draft-n-max',
    '--draft-n': '--spec-draft-n-max',
    '--draft-max': '--spec-draft-n-max',
    '--draft-min': '--spec-draft-n-min',
    '--draft-n-min': '--spec-draft-n-min',
}

_LOAD_MODE_FLAGS = ('--no-mmap', '--mmap', '--mlock')

# Options that may legitimately appear several times in one command.
_REPEATABLE_FLAGS = {'-ot', '--override-tensor', '-otd', '--override-tensor-draft', '--override-kv', '--lora',
                     '--lora-scaled', '--control-vector', '--control-vector-scaled', '-l', '--logit-bias',
                     '--dry-sequence-breaker', '-r', '--reverse-prompt'}


def migrate_parameters(params, cli_info):
    """
    Rewrites flags that the installed llama-server no longer accepts.

    Returns (new_params, notes) where notes is a list of human readable strings.
    Migrations are only applied when the build is known to reject the old flag,
    so older llama.cpp builds keep working unchanged.
    """
    notes = []
    result = []
    keys = [p.key for p in params]

    def rejected(flag):
        return cli_info is not None and (not cli_info.is_known(flag) or cli_info.is_removed(flag))

    has_load_mode = '-lm' in keys or '--load-mode' in keys
    if any(f in keys for f in _LOAD_MODE_FLAGS) and any(rejected(f) for f in _LOAD_MODE_FLAGS if f in keys):
        no_mmap = '--no-mmap' in keys
        mlock = '--mlock' in keys
        mode = ('mlock' if no_mmap else 'mmap+mlock') if mlock else ('none' if no_mmap else 'mmap')
        if has_load_mode:
            notes.append(f"Removed obsolete {', '.join(f for f in _LOAD_MODE_FLAGS if f in keys)} "
                         f"(an explicit --load-mode is already set).")
        else:
            notes.append(f"Replaced {' '.join(f for f in _LOAD_MODE_FLAGS if f in keys)} with '-lm {mode}' "
                         f"(memory-map flags were merged into --load-mode).")
        inserted = has_load_mode
        for p in params:
            if p.key in _LOAD_MODE_FLAGS:
                if not inserted:
                    result.append(Parameter('-lm', mode))
                    inserted = True
                continue
            result.append(p)
        params = result
        result = []

    for p in params:
        key, value = p.key, p.value
        if key == 'Executable':
            result.append(p)
            continue

        # Boolean switches that were (wrongly) stored with an enabled/disabled value
        if key in _BOOL_VALUE_FLAGS and value is not None:
            low = str(value).strip().lower()
            if low in _TRUE_VALUES or low in _FALSE_VALUES:
                on_flag, off_flag = _BOOL_VALUE_FLAGS[key]
                new_key = on_flag if low in _TRUE_VALUES else off_flag
                notes.append(f"Converted '{key} {value}' to the switch '{new_key}'.")
                result.append(Parameter(new_key, None))
                continue

        if key in _RENAMES and rejected(key):
            new_key = _RENAMES[key]
            notes.append(f"Renamed removed flag '{key}' to '{new_key}'.")
            result.append(Parameter(new_key, value))
            continue

        if cli_info is not None and cli_info.is_removed(key):
            notes.append(f"Dropped '{key}': removed from this llama.cpp build "
                         f"({cli_info.entry(key).description[:90]}).")
            continue

        result.append(p)

    return result, notes


def dedupe_aliases(params, cli_info):
    """
    Collapses value-taking synonyms (e.g. '-sm' and '--split-mode') so that a command never carries
    the same option twice. The LAST occurrence wins, mirroring llama.cpp's own parsing. Switch pairs
    that share a help entry but mean opposite things (-kvo/-nkvo, --jinja/--no-jinja) are left alone.
    Returns (new_params, notes).
    """
    if cli_info is None:
        return params, []

    def collapsible(entry):
        return entry is not None and entry.takes_value and not (set(entry.flags) & _REPEATABLE_FLAGS)

    last_index = {}
    for idx, p in enumerate(params):
        entry = cli_info.entry(p.key)
        if collapsible(entry):
            last_index[id(entry)] = idx
    result, notes = [], []
    for idx, p in enumerate(params):
        entry = cli_info.entry(p.key)
        if collapsible(entry) and last_index.get(id(entry)) != idx:
            winner = params[last_index[id(entry)]]
            notes.append(f"'{p.key} {p.value}' is overridden by '{winner.key} {winner.value}' (same option); dropped the duplicate.")
            continue
        result.append(p)
    return result, notes


_NOT_BROWSABLE = {'-h', '--completion-bash', '--version', '--list-devices', '-cl'}


def extra_parameters(cli_info, known_flags):
    """
    Converts help entries that the static parameter database does not cover into
    parameter-browser rows (same dict schema as parameters_db.LLAMA_CPP_PARAMETERS).
    """
    if cli_info is None:
        return []
    rows = []
    for entry in cli_info.entries:
        if entry.removed or entry.deprecated or set(entry.flags) & (set(known_flags) | _NOT_BROWSABLE):
            continue
        flag = entry.primary
        if not entry.takes_value:
            # Switch pairs (--foo / --no-foo): offer the one that changes the documented default
            negatives = [f for f in entry.flags if f.startswith(('--no-', '-no-'))]
            positives = [f for f in entry.flags if f not in negatives]
            default_enabled = 'default: enabled' in entry.description.lower()
            pool = negatives if (default_enabled and negatives) else (positives or entry.flags)
            flag = min(pool, key=len)
            param_type = 'checkbox'
        elif entry.options and not entry.placeholder.startswith(('MiB', 'TOOL')):
            param_type = 'select'
        else:
            param_type = 'text'
        description = entry.description
        if entry.env:
            description += f" Environment variable: {entry.env}"
        if entry.placeholder and param_type == 'text':
            description = f"Value: {entry.placeholder}. " + description
        rows.append({'name': flag.lstrip('-').replace('-', ' ').title(), 'id': flag.lstrip('-'),
                     'type': param_type, 'default': '' if param_type != 'checkbox' else False,
                     'options': entry.options, 'description': description, 'prefix': flag})
    return rows


def find_unsupported(params, cli_info):
    """Flags in the command that the installed build does not recognise."""
    if cli_info is None:
        return []
    unknown = []
    for p in params:
        if p.key == 'Executable' or not p.key.startswith('-'):
            continue
        if not cli_info.is_known(p.key) or cli_info.is_removed(p.key):
            unknown.append(p.key)
    return unknown
