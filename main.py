# End of degree thesis by Hugo García Cuesta (100428954). Computer Engineering Grade, University Carlos III of Madrid

import sys
import time

from problem_definition import ProblemDefinition
from aux import removeResultFolders, ensureDirectoriesExist

from runners.metadata_runner import MetadataRunner
from runners.metadata_shallow_autorunner import MetadataShallowAutorunner
from runners.ogamus_runner import OgamusRunner


if __name__ == '__main__':
    ensureDirectoriesExist()

    # We clean the results folder before executing
    try:
        removeResultFolders()
    except FileNotFoundError:
        pass

    # User selects the method he wants to use.
    # 1. METADATA: uses data extracted from the simulator to get object positions and applies a automated planning in order to find the best plan to make an action in the environment
    # 2. OGAMUS: Uses the OGAMUS algorithm (credits in README). Scans the scene using pretrained models to find the desired objective and if the objective is found, it executes the action.
    inputs = ProblemDefinition()

    if len(sys.argv) == 1:
        method = inputs.method_selection()
    else:
        method = "OGAMUS"

    print(f"You have chosen method: {method}")

    # We ask the user to input the scene number he wants
        # [1-30] - Kitchens
        # [201-230] - Living rooms
        # [301-330] - Bedrooms
        # [401-430] - Bathrooms
    start_time = time.time()

    if method == "METADATA":
        #runner = MetadataRunner(inputs)
        runner = MetadataShallowAutorunner(inputs)
        runner.run()

    # If method == OGAMUS
    elif method == "OGAMUS":
        runner = OgamusRunner(inputs)
        runner.run()
    else:
        print(f"Invalid method: {method}")


    print(f"\nElapsed time: {start_time - time.time()}")
