import sys, traceback, importlib
sys.path.append('c:/Users/user/OneDrive/Desktop/CODE/Research-And-Decision-Intelligence-System/backend')

test_mod = importlib.import_module('tests.unit.test_decision_tools')
passed = 0
failed = 0
for name in dir(test_mod):
    if name.startswith('Test'):
        cls = getattr(test_mod, name)()
        for meth in dir(cls):
            if meth.startswith('test_'):
                func = getattr(cls, meth)
                try:
                    func()
                    print(f"{name}.{meth}: PASS")
                    passed += 1
                except Exception as e:
                    print(f"{name}.{meth}: FAIL {type(e).__name__}: {e}")
                    traceback.print_exc()
                    failed += 1
print(f"Total: {passed+failed}, Passed: {passed}, Failed: {failed}")
