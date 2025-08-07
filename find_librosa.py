import librosa
import os

try:
    # Print the path to the librosa package
    print(f"librosa path: {os.path.dirname(librosa.__file__)}")

    # Try to get an example audio file
    # This is a common pattern, but might not exist
    try:
        # The documentation suggests using `librosa.ex()`
        example_file = librosa.ex('choice')
        print(f"Librosa example file path: {example_file}")
    except Exception as e:
        print(f"Could not get example file using librosa.ex: {e}")

except ImportError:
    print("Could not import librosa.")
except Exception as e:
    print(f"An error occurred: {e}")
