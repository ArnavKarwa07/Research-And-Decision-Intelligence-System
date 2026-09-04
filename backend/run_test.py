import sys, traceback, importlib
sys.path.append('c:/Users/user/OneDrive/Desktop/CODE/Research-And-Decision-Intelligence-System/backend')

try:
    test_mod = importlib.import_module('tests.unit.test_decision_tools')
    cls = getattr(test_mod, 'TestRunSensitivity')()
    func = getattr(cls, 'test_crossover_switch_point_detected')
    func()
    print('test_crossover_switch_point_detected: PASS')
except Exception as e:
    traceback.print_exc()
    print('FAIL')
