import sys
sys.path.append('c:/Users/user/OneDrive/Desktop/CODE/Research-And-Decision-Intelligence-System/backend')
try:
    from app.tools.decision_tools import compare_options
    print('Import success')
except Exception as e:
    import traceback, json
    traceback.print_exc()
    print('Import failed')
