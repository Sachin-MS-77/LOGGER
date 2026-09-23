"""Compile field-selection programs to WASM and execute with zero host imports.

Format decoding uses trusted bounded adapters. The proposed field projection runs
in WASM. LLM output is declarative, never executed as Python or arbitrary regex.
"""
import wasmtime
from .schema import SCHEMA

FIELDS = SCHEMA["fields"]

class Sandbox:
    def __init__(self):
        config = wasmtime.Config(); config.consume_fuel = True
        self.engine = wasmtime.Engine(config)
        self.cache = {}
    def compile(self, mapping, keys):
        expressions = "(i32.const -1)"
        for i, target in reversed(list(enumerate(FIELDS))):
            index = keys.index(mapping[target]) if target in mapping and mapping[target] in keys else -1
            expressions = f"(if (result i32) (i32.eq (local.get $field) (i32.const {i})) (then (i32.const {index})) (else {expressions}))"
        wat = f'(module (memory (export "memory") 1 1) (func (export "select") (param $field i32) (result i32) {expressions}))'
        return bytes(wasmtime.wat2wasm(wat))
    def project(self, binary, keys, attributes):
        import hashlib
        if not isinstance(binary, (bytes, bytearray)) or len(binary)>65536:
            raise ValueError("plugin binary size exceeds 64 KiB compile limit")
        h = hashlib.sha256(binary).hexdigest()
        module = self.cache.get(h)
        if module is None:
            module = wasmtime.Module(self.engine, binary)
            if module.imports: raise ValueError("plugin imports are forbidden: no filesystem, network, or host calls")
            if len(self.cache)>256: self.cache.clear()
            self.cache[h] = module
        store = wasmtime.Store(self.engine)
        store.set_limits(memory_size=65536, table_elements=0, instances=1, tables=0, memories=1)
        store.set_fuel(10000)
        instance = wasmtime.Instance(store, module, [])
        selector = instance.exports(store).get("select")
        if selector is None: raise ValueError("plugin lacks select export")
        if not isinstance(selector, wasmtime.Func): raise ValueError("invalid select signature")
        signature = selector.type(store)
        if [str(x) for x in signature.params] != ["i32"] or [str(x) for x in signature.results] != ["i32"]:
            raise ValueError("select signature must be (i32) -> i32")
        mapping = {}
        for i, target in enumerate(FIELDS):
            position = selector(store, i)
            if not isinstance(position, int) or position < -1 or position >= len(keys): raise ValueError("invalid mapping index")
            if position >= 0: mapping[target] = keys[position]
        return mapping
