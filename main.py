# End of degree thesis by Hugo García Cuesta (100428954). Computer Engineering Grade, University Carlos III of Madrid

# IMPORTS
import json
# import ogamus
import shutil
import sys
import time
import numpy as np
from ai2thor.controller import Controller
from ai2thor.util.metrics import (get_shortest_path_to_object_type)
from problem_definition import ProblemDefinition
from parser_ai2thor_pddl import ParserAI2THORPDDL
from parser_pddl_ai2thor import ParserPDDLAI2THOR
from planner import Planner
from exec_ogamus import ExecOgamus
from aux import printAgentStatus, printLastActionStatus, createCamera, printObjectStatus, removeResultFolders, isObjectOnScene, ensureDirectoriesExist

# CONSTANTS
DATASET = 'Datasets/test_set_ogn_ithor.json'
LOG = "Results/test_set_ogn_ithor_steps200/episode_0/log.txt"

# MAIN FLOW OF THE PROGRAM

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
    method = "2"


# We ask the user to input the scene number he wants
    # [1-30] - Kitchens
    # [201-230] - Living rooms
    # [301-330] - Bedrooms
    # [401-430] - Bathrooms
scene_number = inputs.scene_selection()


# If method = 1 -> METADATA
if method == '1':

    # Initial start of the environment
    print("*STARTING ENVIRONMENT*\n")
    controller = Controller(
        agentMode="default",  # Agent used is iTHOR -> default
        visibilityDistance=1.5,  # Visibility distance
        scene="FloorPlan" + str(scene_number),
        gridSize=0.25,  # Step size
        snapToGrid=True,
        rotateStepDegrees=90,
        renderDepthImage=False,
        renderInstanceSegmentation=False,
        width=224,  # Controller width
        height=224,  # Controller height
        fieldOfView=90  # Controller fiold of view
    )

    # We create a camera on top of the scene and save an image
    createCamera(controller)

    print("*ENVIRONMENT SUCCESSFULLY STARTED*\n")

    # Loop that allows to repeat actions on the same environment
    iteration = 1
    loop = 'Y'
    while loop == 'Y':

        # Set up problem and output path
        problem_path, output_path = inputs.paths_selection(iteration)

        # Execution of an action inside the controller. GetReachablePositions allow us to get all the positions where the agent is allowed to be in the scene
        event = controller.step(action="GetReachablePositions")

        # Ask user for problem and objective
        problem, objective, liquid = inputs.problem_selection(event)

        start_time = time.time()

        # If the problem selected is drop there is no need to plan anything. Execute the action directly. Otherwise parse the problem and generate a plan.
        if problem == "drop":
            event = controller.step(action="DropHandObject")

        else:
            # Using the parser, we translate the simulator state to a PDDL problem
            ParserAI2THORPDDL(event, problem_path, problem,
                              objective, controller)

            # Execute the planner with the problem file generated and the corresponding domain (based on selected action)
            plan = Planner(problem_path, output_path, problem,
                           1, 3, print=True, ogamus=False)
            actual_plan = plan.get_plan()

            # Parse and execute plan into actions
            parsed = ParserPDDLAI2THOR(
                actual_plan, controller, iteration, liquid)

        # Final state visualization depending on the type of the problem
        printLastActionStatus(controller.last_event)
        if problem == 'move':
            printAgentStatus(controller.last_event)
        else:
            printObjectStatus(controller.last_event, objective)

        end_time = time.time()

        # Ask if the user wants to execute another action. If not, stop the program.
        loop = input('Do you want to execute another action? [Y/n]: ')
        iteration += 1


# If method = 2 -> OGAMUS
else:
    # Compute auxiliary params for OGAMUS execution
    # hfov = 79 / 360. * 2. * np.pi
    # vfov = 2. * np.arctan(np.tan(hfov / 2) * 224 / 224)
    # vfov = np.rad2deg(vfov)

    # Controller start
    print("*STARTING ENVIRONMENT*\n")
    controller = Controller(
        renderDepthImage=1,
        renderObjectImage=True,
        visibilityDistance=1.5,
        gridSize=0.25,
        rotateStepDegrees=45,
        scene="FloorPlan" + str(scene_number),
        continuousMode=True,
        snapToGrid=False,
        width=224,
        height=224,
        fieldOfView=90,
        agentMode='default'
    )

    # We create a camera on top of the scene and save an image
    createCamera(controller)

    # We get initial positions of the agent to pass it to OGAMUS
    event = controller.step("Pass")
    agent_pos = event.metadata["agent"]["position"]
    agent_rot = event.metadata["agent"]["rotation"]
    agent_hor = event.metadata["agent"]["cameraHorizon"]
    print("*ENVIRONMENT SUCCESSFULLY STARTED*\n")

    # Reads problems from CLI or arguments if a PDDL problem is passed.
    if len(sys.argv) == 2:
        problem_list, objective_list = inputs.problem_selection_ogamus_input(
            input=sys.argv[1])
    elif len(sys.argv) == 1:
        problem_list, objective_list = inputs.problem_selection_ogamus()
    else:
        print("Input a valid PDDL problem file as argument or leave args empty.\n")
        exit()

    start_time = time.time()

    # Loop that executes as many times as problems are defined
    iteration = 0
    for problem in problem_list:

        # We create the dictionary to be inserted into the JSON that OGAMUS reads. It contains the scene info previously extracted and the objective
        dictionary = [{
            "episode": 1,
            "scene": "FloorPlan" + scene_number,
            "goal": "(exists (?o1 - " + objective_list[iteration] + ") (and (viewing ?o1) (close_to ?o1)))",
            "agent_position": agent_pos,
            "agent_rotation": agent_rot,
            "initial_orientation": agent_rot['y'],
            "initial_horizon": agent_hor,
            "agent_is_standing": True,
            "agent_in_high_friction_area": False,
            "agent_fov": 90,
            "shortest_path": [
                {
                    "x": -1.0,
                    "y": 0.901863694190979,
                    "z": 2.0
                }
            ],
            "shortest_path_length": 0
        }]

        # Modify json with scene info
        json_object = json.dumps(dictionary, indent=4)
        with open(DATASET, "w") as f:
            f.write(json_object)

        # Call to ogamus to find the objective
        # controller = ogamus.main(controller)

        # Check if OGAMUS has found the objective. If plan has 200 steps -> objective not found.
        with open(LOG, "r") as f:
            log_str = f.read()
            if log_str.find("200:Stop") != -1:
                print(
                    "No se ha encontrado el objetivo indicado tras recorrer la escena durante 200 pasos\n")
                print("Ejecute de nuevo el programa y pruebe con un objetivo distinto\n")
                exit()

        # Call ExecOgamus to execute the action over the objective
        execute = ExecOgamus(controller, problem,
                             objective_list[iteration], iteration)

        # Save facts found from OGAMUS into problems folder
        shutil.copyfile("OGAMUS/Plan/PDDL/facts.pddl",
                        f"pddl/problems/problem{iteration}.pddl")

        # Update agent position in for next OGAMUS execution
        event = controller.step("Pass")
        agent_pos = event.metadata["agent"]["position"]
        agent_rot = event.metadata["agent"]["rotation"]
        agent_hor = event.metadata["agent"]["cameraHorizon"]

        end_time = time.time()

        # Update iteration count
        iteration += 1


print(f"\nElapsed time: {end_time-start_time}")
