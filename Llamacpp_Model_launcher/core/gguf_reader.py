# core/gguf_reader.py
"""
Minimal, dependency-free GGUF metadata reader.

Reads only the key/value header (not tensor data), so it is instant even for
100 GB models. Used to detect model features before launching the server
(e.g. Multi-Token-Prediction layers needed by `--spec-type draft-mtp`,
which makes llama-server abort when the model does not have them).
"""

import struct

_GGUF_MAGIC = b'GGUF'

# GGUF value types
_UINT8, _INT8, _UINT16, _INT16, _UINT32, _INT32, _FLOAT32, _BOOL, _STRING, _ARRAY, _UINT64, _INT64, _FLOAT64 = range(13)

_SCALAR_FORMATS = {
    _UINT8: '<B', _INT8: '<b', _UINT16: '<H', _INT16: '<h', _UINT32: '<I', _INT32: '<i',
    _FLOAT32: '<f', _BOOL: '<?', _UINT64: '<Q', _INT64: '<q', _FLOAT64: '<d',
}

# Arrays longer than this (tokenizer vocab, merges...) are skipped instead of decoded.
_MAX_ARRAY_ITEMS = 64


class _Reader:
    def __init__(self, fh):
        self.fh = fh

    def read(self, fmt):
        size = struct.calcsize(fmt)
        data = self.fh.read(size)
        if len(data) != size:
            raise ValueError('Unexpected end of GGUF header')
        return struct.unpack(fmt, data)[0]

    def string(self):
        length = self.read('<Q')
        return self.fh.read(length).decode('utf-8', errors='replace')

    def skip_string(self):
        self.fh.seek(self.read('<Q'), 1)

    def value(self, vtype):
        if vtype in _SCALAR_FORMATS:
            return self.read(_SCALAR_FORMATS[vtype])
        if vtype == _STRING:
            return self.string()
        if vtype == _ARRAY:
            item_type = self.read('<I')
            count = self.read('<Q')
            if count > _MAX_ARRAY_ITEMS:
                self._skip_array(item_type, count)
                return f'<array of {count}>'
            return [self.value(item_type) for _ in range(count)]
        raise ValueError(f'Unknown GGUF value type {vtype}')

    def _skip_array(self, item_type, count):
        if item_type in _SCALAR_FORMATS:
            self.fh.seek(struct.calcsize(_SCALAR_FORMATS[item_type]) * count, 1)
        elif item_type == _STRING:
            for _ in range(count):
                self.skip_string()
        else:
            for _ in range(count):
                self.value(item_type)


def read_metadata(path):
    """Returns the GGUF key/value metadata as a dict, or {} if the file cannot be read."""
    try:
        with open(path, 'rb') as fh:
            if fh.read(4) != _GGUF_MAGIC:
                return {}
            reader = _Reader(fh)
            version = reader.read('<I')
            if version < 2:
                return {}
            reader.read('<Q')  # tensor count
            kv_count = reader.read('<Q')
            metadata = {}
            for _ in range(kv_count):
                key = reader.string()
                metadata[key] = reader.value(reader.read('<I'))
            return metadata
    except (OSError, ValueError, struct.error, MemoryError):
        return {}


class ModelFeatures:
    """Performance-relevant facts about a GGUF model."""

    def __init__(self, metadata):
        self.metadata = metadata
        self.architecture = metadata.get('general.architecture', '')
        arch = self.architecture

        def arch_key(name, default=None):
            return metadata.get(f'{arch}.{name}', default)

        self.block_count = arch_key('block_count', 0) or 0
        self.context_length = arch_key('context_length', 0) or 0
        self.expert_count = arch_key('expert_count', 0) or 0
        self.expert_used_count = arch_key('expert_used_count', 0) or 0
        self.mtp_layers = arch_key('nextn_predict_layers', 0) or 0
        self.name = metadata.get('general.name', '')

    @property
    def is_valid(self):
        return bool(self.architecture)

    @property
    def is_moe(self):
        return self.expert_count > 1

    @property
    def has_mtp(self):
        return self.mtp_layers > 0


def get_model_features(path):
    return ModelFeatures(read_metadata(path))
