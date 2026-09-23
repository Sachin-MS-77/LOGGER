"""Executable attack evidence against the actual Wasmtime wrapper."""
import pytest,wasmtime
from ulpf.sandbox import Sandbox

def execute(wat):return Sandbox().project(bytes(wasmtime.wat2wasm(wat)),['src'],{'src':'10.0.0.1'})
def test_infinite_loop_runs_out_of_fuel():
    with pytest.raises(wasmtime.Trap,match='fuel'):
        execute('(module (func (export "select") (param i32) (result i32) (loop $forever (br $forever)) (i32.const -1)))')
def test_initial_memory_over_64k_is_rejected():
    with pytest.raises(wasmtime.WasmtimeError,match='memory'):
        execute('(module (memory 2) (func (export "select") (param i32) (result i32) (i32.const -1)))')
def test_memory_growth_cannot_cross_64k():
    # memory.grow returns -1 when the Store resource limiter denies the request.
    assert execute('(module (memory 1) (func (export "select") (param i32) (result i32) (memory.grow (i32.const 1))))')=={}
@pytest.mark.parametrize('module,name',[('wasi_snapshot_preview1','path_open'),('wasi_snapshot_preview1','sock_open'),('wasi_snapshot_preview1','environ_get'),('env','system')])
def test_host_capability_imports_rejected(module,name):
    with pytest.raises(ValueError,match='imports are forbidden'):
        execute(f'(module (import "{module}" "{name}" (func)) (func (export "select") (param i32) (result i32) (i32.const -1)))')
def test_out_of_bounds_memory_traps():
    with pytest.raises(wasmtime.Trap,match='out of bounds'):
        execute('(module (memory 1 1) (func (export "select") (param i32) (result i32) (i32.load (i32.const 65536))))')
def test_malformed_binary_rejected():
    with pytest.raises(wasmtime.WasmtimeError):Sandbox().project(b'not wasm',[],{})
def test_wrong_selector_signature_rejected():
    with pytest.raises(ValueError,match='signature'):
        execute('(module (func (export "select") (result i32) (i32.const -1)))')
def test_oversize_binary_rejected_before_compilation():
    with pytest.raises(ValueError,match='size'):
        Sandbox().project(b'\0asm'+bytes(65536),[],{})
