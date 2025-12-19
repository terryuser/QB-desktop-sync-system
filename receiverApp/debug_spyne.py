import sys
import six
# Ensure the target module is loaded
import six.moves.collections_abc

# Patch deeper
sys.modules['spyne.util.six'] = six
sys.modules['spyne.util.six.moves'] = six.moves
sys.modules['spyne.util.six.moves.collections_abc'] = six.moves.collections_abc

try:
    from spyne.util.oset import oset
    print("Spyne oset imported successfully")
except Exception as e:
    # print(f"Failed: {e}")
    import traceback
    traceback.print_exc()
